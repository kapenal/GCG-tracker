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
from app.set_catalog import ensure_configured_sets
from app.snapshot_dates import kst_today_utc_bounds, to_kst_date

logger = logging.getLogger(__name__)


async def _fetch_html(client: httpx.AsyncClient, url: str) -> str:
    res = await client.get(url, timeout=60.0)
    res.raise_for_status()
    return res.text


def _ensure_sets(db: Session) -> dict[str, CardSet]:
    return ensure_configured_sets(db, commit=True)


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


def _delete_snapshots_by_ids(db: Session, snapshot_ids: list[int]) -> int:
    """Delete snapshots by id; DB CASCADE removes price_records (no ORM nulling)."""
    if not snapshot_ids:
        return 0
    db.execute(delete(PriceSnapshot).where(PriceSnapshot.id.in_(snapshot_ids)))
    db.flush()
    return len(snapshot_ids)


def _delete_today_snapshots(db: Session) -> int:
    """Remove today's (KST) snapshots before inserting a fresh one."""
    start_utc, end_utc = kst_today_utc_bounds()
    ids = list(
        db.scalars(
            select(PriceSnapshot.id)
            .where(PriceSnapshot.fetched_at >= start_utc)
            .where(PriceSnapshot.fetched_at < end_utc)
        ).all()
    )
    if not ids:
        return 0
    removed = _delete_snapshots_by_ids(db, ids)
    logger.info("Deleted %d existing snapshot(s) for today before insert", removed)
    return removed


def _prune_to_one_snapshot_per_day(db: Session, keep_days: int = 7) -> int:
    """Keep only the latest snapshot per KST calendar day within the retention window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    rows = db.execute(
        select(PriceSnapshot.id, PriceSnapshot.fetched_at)
        .where(PriceSnapshot.fetched_at >= cutoff)
        .order_by(PriceSnapshot.fetched_at.desc())
    ).all()

    by_day: dict[date, list[tuple[int, datetime]]] = defaultdict(list)
    for snap_id, fetched_at in rows:
        by_day[to_kst_date(fetched_at)].append((snap_id, fetched_at))

    remove_ids: list[int] = []
    for day_snaps in by_day.values():
        day_snaps.sort(key=lambda row: row[1], reverse=True)
        remove_ids.extend(snap_id for snap_id, _ in day_snaps[1:])

    return _delete_snapshots_by_ids(db, remove_ids)


def _prune_old_snapshots(db: Session, keep_days: int = 7) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    old_ids = list(
        db.scalars(
            select(PriceSnapshot.id).where(PriceSnapshot.fetched_at < cutoff)
        ).all()
    )
    return _delete_snapshots_by_ids(db, old_ids)


async def run_sync(db: Session) -> tuple[PriceSnapshot, list[dict]]:
    sets_map = _ensure_sets(db)

    set_results: list[dict] = []
    removed_today = _delete_today_snapshots(db)
    if removed_today:
        set_results.append(
            {"slug": "_maintenance", "label": "Replace today snapshot", "count": removed_today}
        )

    snapshot = PriceSnapshot(card_count=0)
    db.add(snapshot)
    db.flush()

    if snapshot.id is None:
        raise RuntimeError("PriceSnapshot.id was not assigned after flush")

    logger.info("Created snapshot id=%s for today (insert-only)", snapshot.id)
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
