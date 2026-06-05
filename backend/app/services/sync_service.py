import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.jp_to_ko import to_korean_name
from app.models import Card, CardSet, PriceRecord, PriceSnapshot
from app.scraper import parse_sell_page
from app.scraper_config import SET_PAGES


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
    snapshot = PriceSnapshot(card_count=0)
    db.add(snapshot)
    db.flush()

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
    pruned = _prune_old_snapshots(db, keep_days=7)
    db.commit()
    db.refresh(snapshot)
    if pruned:
        set_results.append({"slug": "_maintenance", "label": "Prune >7d", "count": pruned})
    return snapshot, set_results


def run_sync_blocking(db: Session) -> tuple[PriceSnapshot, list[dict]]:
    return asyncio.run(run_sync(db))
