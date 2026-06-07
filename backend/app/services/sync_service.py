import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.jp_to_ko import to_korean_name
from app.models import Card, CardSet, PriceRecord, PriceSnapshot
from app.scraper import parse_sell_page
from app.scraper_config import SET_PAGES
from app.snapshot_dates import kst_today_utc_bounds, to_kst_date

logger = logging.getLogger(__name__)


async def _fetch_html(client: httpx.AsyncClient, url: str) -> str:
    res = await client.get(url, timeout=60.0)
    res.raise_for_status()
    return res.text


def _ensure_sets(db: Session) -> dict[str, CardSet]:
    by_slug: dict[str, CardSet] = {}
    for page in SET_PAGES:
        row = db.scalar(select(CardSet).where(CardSet.slug == page.slug))
        if not row:
            row = CardSet(slug=page.slug, label=page.label, source_url=page.url)
            db.add(row)
            db.flush()
        else:
            row.label = page.label
            row.source_url = page.url
        by_slug[page.slug] = row
    db.commit()
    return by_slug


def _upsert_card(db: Session, scraped, card_set: CardSet) -> Card:
    card = db.scalar(select(Card).where(Card.external_id == scraped.external_id))
    if not card:
        card = Card(
            external_id=scraped.external_id,
            yuyu_card_id=scraped.yuyu_card_id,
            card_number=scraped.card_number,
            rarity=scraped.rarity,
            name=scraped.name,
            name_ko=to_korean_name(scraped.name),
            image_url=scraped.image_url,
            detail_url=scraped.detail_url,
            version=scraped.version,
            set_id=card_set.id,
        )
        db.add(card)
    else:
        card.yuyu_card_id = scraped.yuyu_card_id
        card.card_number = scraped.card_number
        card.rarity = scraped.rarity
        card.name = scraped.name
        card.name_ko = to_korean_name(scraped.name)
        card.image_url = scraped.image_url
        card.detail_url = scraped.detail_url
        card.version = scraped.version
        card.set_id = card_set.id
    db.flush()
    return card


def _prepare_today_snapshot(db: Session) -> PriceSnapshot:
    """Reuse today's snapshot (KST) or create one. Same-day re-sync replaces prices."""
    start_utc, end_utc = kst_today_utc_bounds()
    today_snapshots = db.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.fetched_at >= start_utc)
        .where(PriceSnapshot.fetched_at < end_utc)
        .order_by(PriceSnapshot.fetched_at.desc())
    ).all()

    if today_snapshots:
        snapshot = today_snapshots[0]
        for extra in today_snapshots[1:]:
            db.delete(extra)
        db.execute(delete(PriceRecord).where(PriceRecord.snapshot_id == snapshot.id))
        snapshot.card_count = 0
        snapshot.fetched_at = datetime.now(timezone.utc)
        db.flush()
        logger.info("Reusing today's snapshot id=%s (replacing price records)", snapshot.id)
        return snapshot

    snapshot = PriceSnapshot(card_count=0)
    db.add(snapshot)
    db.flush()
    logger.info("Created new snapshot for today id=%s", snapshot.id)
    return snapshot


def _prune_to_one_snapshot_per_day(db: Session, keep_days: int = 7) -> int:
    """Keep only the latest snapshot per KST calendar day within the retention window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    snapshots = db.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.fetched_at >= cutoff)
        .order_by(PriceSnapshot.fetched_at.desc())
    ).all()

    by_day: dict[date, list[PriceSnapshot]] = defaultdict(list)
    for snap in snapshots:
        by_day[to_kst_date(snap.fetched_at)].append(snap)

    removed = 0
    for snaps in by_day.values():
        snaps.sort(key=lambda s: s.fetched_at, reverse=True)
        for extra in snaps[1:]:
            db.delete(extra)
            removed += 1
    return removed


def _prune_old_snapshots(db: Session, keep_days: int = 7) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    old_ids = db.scalars(
        select(PriceSnapshot.id).where(PriceSnapshot.fetched_at < cutoff)
    ).all()
    if not old_ids:
        return 0
    db.execute(delete(PriceSnapshot).where(PriceSnapshot.id.in_(old_ids)))
    return len(old_ids)


async def run_sync(db: Session) -> tuple[PriceSnapshot, list[dict]]:
    sets_map = _ensure_sets(db)
    snapshot = _prepare_today_snapshot(db)

    set_results: list[dict] = []
    all_count = 0

    headers = {"User-Agent": settings.user_agent, "Accept-Language": "ja"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for i, page in enumerate(SET_PAGES):
            try:
                html = await _fetch_html(client, page.url)
                scraped_list = parse_sell_page(html, page.slug, page.url)
                card_set = sets_map[page.slug]

                for scraped in scraped_list:
                    card = _upsert_card(db, scraped, card_set)
                    db.add(
                        PriceRecord(
                            snapshot_id=snapshot.id,
                            card_id=card.id,
                            price_yen=scraped.price_yen,
                            stock=scraped.stock,
                        )
                    )
                    all_count += 1

                set_results.append(
                    {"slug": page.slug, "label": page.label, "count": len(scraped_list)}
                )
            except Exception as exc:
                set_results.append(
                    {
                        "slug": page.slug,
                        "label": page.label,
                        "count": 0,
                        "error": str(exc),
                    }
                )

            if i < len(SET_PAGES) - 1:
                await asyncio.sleep(settings.fetch_delay_seconds)

    snapshot.card_count = all_count
    deduped = _prune_to_one_snapshot_per_day(db, keep_days=7)
    pruned = _prune_old_snapshots(db, keep_days=7)
    db.commit()
    db.refresh(snapshot)
    if deduped:
        set_results.append(
            {"slug": "_maintenance", "label": "Dedupe same-day", "count": deduped}
        )
    if pruned:
        set_results.append({"slug": "_maintenance", "label": "Prune >7d", "count": pruned})
    return snapshot, set_results


def run_sync_blocking(db: Session) -> tuple[PriceSnapshot, list[dict]]:
    return asyncio.run(run_sync(db))
