"""Import data/latest.json into PostgreSQL as an initial snapshot."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal, engine
from app.jp_to_ko import to_korean_name
from app.models import Base, Card, CardSet, PriceRecord, PriceSnapshot
from app.scraper_config import SET_PAGES

ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = ROOT / "data" / "latest.json"


def main():
    if not JSON_PATH.exists():
        print(f"Missing {JSON_PATH}")
        sys.exit(1)

    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    cards_data = payload.get("cards", [])
    fetched_at = payload.get("fetchedAt")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    sets_by_slug = {}
    for page in SET_PAGES:
        row = db.scalar(select(CardSet).where(CardSet.slug == page.slug))
        if not row:
            row = CardSet(slug=page.slug, label=page.label, source_url=page.url)
            db.add(row)
            db.flush()
        sets_by_slug[page.slug] = row

    snapshot = PriceSnapshot(card_count=len(cards_data))
    db.add(snapshot)
    db.flush()

    for item in cards_data:
        set_slug = item.get("setSlug") or item.get("version")
        card_set = sets_by_slug.get(set_slug)
        if not card_set:
            card_set = CardSet(
                slug=set_slug,
                label=set_slug,
                source_url=item.get("sourceUrl", ""),
            )
            db.add(card_set)
            db.flush()
            sets_by_slug[set_slug] = card_set

        external_id = item.get("id") or f"{item.get('version')}:{item.get('cardId')}"
        card = db.scalar(select(Card).where(Card.external_id == external_id))
        if not card:
            card = Card(
                external_id=external_id,
                yuyu_card_id=str(item["cardId"]) if item.get("cardId") else None,
                card_number=item.get("cardNumber"),
                rarity=item.get("rarity"),
                name=item["name"],
                name_ko=to_korean_name(item["name"]),
                image_url=item.get("imageUrl"),
                detail_url=item.get("detailUrl"),
                version=item.get("version", set_slug),
                set_id=card_set.id,
            )
            db.add(card)
            db.flush()
        else:
            card.name = item["name"]
            card.name_ko = to_korean_name(item["name"])
            card.rarity = item.get("rarity") or card.rarity
            card.image_url = item.get("imageUrl")
            card.detail_url = item.get("detailUrl")

        db.add(
            PriceRecord(
                snapshot_id=snapshot.id,
                card_id=card.id,
                price_yen=item["priceYen"],
                stock=item.get("stock"),
            )
        )

    db.commit()
    print(f"Imported {len(cards_data)} cards into snapshot #{snapshot.id}")
    if fetched_at:
        print(f"  (source fetchedAt: {fetched_at})")
    db.close()


if __name__ == "__main__":
    main()
