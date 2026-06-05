from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import Card, CardSet, PriceRecord, PriceSnapshot
from app.rarity import RARITY_ORDER, rarity_sort_key
from app.schemas import CardOut, PriceChangeOut, PricePointOut, RarityOut


def get_latest_snapshot(db: Session) -> PriceSnapshot | None:
    return db.scalar(
        select(PriceSnapshot).order_by(PriceSnapshot.fetched_at.desc()).limit(1)
    )


def list_sets_with_counts(db: Session) -> list[tuple[CardSet, int]]:
    latest = get_latest_snapshot(db)
    if not latest:
        sets = db.scalars(select(CardSet).order_by(CardSet.slug)).all()
        return [(s, 0) for s in sets]

    rows = db.execute(
        select(CardSet, func.count(Card.id))
        .join(Card, Card.set_id == CardSet.id)
        .join(PriceRecord, PriceRecord.card_id == Card.id)
        .where(PriceRecord.snapshot_id == latest.id)
        .group_by(CardSet.id)
        .order_by(CardSet.slug)
    ).all()
    return list(rows)


def list_rarities(
    db: Session, *, set_slug: str | None = None
) -> list[RarityOut]:
    latest = get_latest_snapshot(db)
    if not latest:
        return []

    stmt = (
        select(Card.rarity, func.count(Card.id))
        .join(PriceRecord, PriceRecord.card_id == Card.id)
        .where(
            PriceRecord.snapshot_id == latest.id,
            Card.rarity.isnot(None),
        )
        .group_by(Card.rarity)
    )
    if set_slug:
        stmt = stmt.join(CardSet, Card.set_id == CardSet.id).where(
            CardSet.slug == set_slug
        )

    rows = db.execute(stmt).all()
    items = [RarityOut(rarity=r, card_count=c) for r, c in rows if r]
    items.sort(key=lambda x: rarity_sort_key(x.rarity))
    return items


def list_cards(
    db: Session,
    *,
    set_slug: str | None = None,
    rarity: str | None = None,
    q: str | None = None,
    limit: int = 5000,
    offset: int = 0,
) -> tuple[list[CardOut], datetime | None]:
    latest = get_latest_snapshot(db)
    if not latest:
        return [], None

    stmt = (
        select(Card, CardSet, PriceRecord)
        .join(CardSet, Card.set_id == CardSet.id)
        .join(
            PriceRecord,
            (PriceRecord.card_id == Card.id)
            & (PriceRecord.snapshot_id == latest.id),
        )
    )
    if set_slug:
        stmt = stmt.where(CardSet.slug == set_slug)
    if rarity:
        stmt = stmt.where(Card.rarity == rarity)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Card.name.ilike(like))
            | (Card.name_ko.ilike(like))
            | (Card.card_number.ilike(like))
        )

    rows = db.execute(stmt).all()
    current_prices = {card.id: price.price_yen for card, _, price in rows}
    weekly_changes = _weekly_change_map(db, list(current_prices.keys()), latest.fetched_at, current_prices)

    items: list[CardOut] = []
    for card, card_set, price in rows:
        weekly = weekly_changes.get(card.id, (None, None))
        items.append(
            CardOut(
                id=card.id,
                external_id=card.external_id,
                yuyu_card_id=card.yuyu_card_id,
                card_number=card.card_number,
                rarity=card.rarity,
                name=card.name,
                name_ko=card.name_ko,
                image_url=card.image_url,
                detail_url=card.detail_url,
                version=card.version,
                set_slug=card_set.slug,
                set_label=card_set.label,
                price_yen=price.price_yen,
                stock=price.stock,
                price_updated_at=latest.fetched_at,
                week_change_percent=weekly[0],
                week_change_direction=weekly[1],
            )
        )

    items.sort(
        key=lambda c: (
            c.set_slug,
            rarity_sort_key(c.rarity),
            c.card_number or "",
            c.name,
        )
    )
    return items[offset : offset + limit], latest.fetched_at


def _weekly_change_map(
    db: Session,
    card_ids: list[int],
    latest_at: datetime,
    current_prices: dict[int, int],
) -> dict[int, tuple[float | None, str | None]]:
    if not card_ids:
        return {}

    since = latest_at - timedelta(days=7)
    history_rows = db.execute(
        select(PriceRecord.card_id, PriceRecord.price_yen, PriceSnapshot.fetched_at)
        .join(PriceSnapshot, PriceSnapshot.id == PriceRecord.snapshot_id)
        .where(
            PriceRecord.card_id.in_(card_ids),
            PriceSnapshot.fetched_at >= since,
        )
        .order_by(PriceRecord.card_id.asc(), PriceSnapshot.fetched_at.asc())
    ).all()

    first_price_by_card: dict[int, int] = {}
    for card_id, price_yen, _ in history_rows:
        if card_id not in first_price_by_card:
            first_price_by_card[card_id] = price_yen

    changes: dict[int, tuple[float | None, str | None]] = {}
    for card_id, current in current_prices.items():
        first = first_price_by_card.get(card_id)
        if first is None or first <= 0:
            changes[card_id] = (None, None)
            continue

        delta = current - first
        if delta == 0:
            changes[card_id] = (0.0, "flat")
            continue

        pct = round((delta / first) * 100, 2)
        direction = "up" if delta > 0 else "down"
        changes[card_id] = (pct, direction)

    return changes


def card_price_history(db: Session, card_id: int, days: int | None = None) -> list[PricePointOut]:
    stmt = (
        select(PriceSnapshot.fetched_at, PriceRecord.price_yen, PriceRecord.stock)
        .join(PriceRecord, PriceRecord.snapshot_id == PriceSnapshot.id)
        .where(PriceRecord.card_id == card_id)
    )
    if days and days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = stmt.where(PriceSnapshot.fetched_at >= since)

    rows = db.execute(stmt.order_by(PriceSnapshot.fetched_at.asc())).all()
    return [
        PricePointOut(recorded_at=at, price_yen=price, stock=stock)
        for at, price, stock in rows
    ]


def compare_latest_snapshots(
    db: Session,
) -> tuple[datetime | None, datetime | None, list[PriceChangeOut]]:
    snaps = db.scalars(
        select(PriceSnapshot).order_by(PriceSnapshot.fetched_at.desc()).limit(2)
    ).all()
    if len(snaps) < 2:
        return None, snaps[0].fetched_at if snaps else None, []

    current, previous = snaps[0], snaps[1]
    prev_alias = aliased(PriceRecord)
    cur_alias = aliased(PriceRecord)

    rows = db.execute(
        select(Card, CardSet, prev_alias.price_yen, cur_alias.price_yen)
        .join(CardSet, Card.set_id == CardSet.id)
        .join(
            cur_alias,
            (cur_alias.card_id == Card.id) & (cur_alias.snapshot_id == current.id),
        )
        .join(
            prev_alias,
            (prev_alias.card_id == Card.id) & (prev_alias.snapshot_id == previous.id),
        )
        .where(cur_alias.price_yen != prev_alias.price_yen)
        .order_by(func.abs(cur_alias.price_yen - prev_alias.price_yen).desc())
    ).all()

    changes = [
        PriceChangeOut(
            card_id=card.id,
            external_id=card.external_id,
            card_number=card.card_number,
            rarity=card.rarity,
            name=card.name,
            name_ko=card.name_ko,
            image_url=card.image_url,
            set_slug=card_set.slug,
            previous_price=prev_price,
            current_price=cur_price,
            delta=cur_price - prev_price,
        )
        for card, card_set, prev_price, cur_price in rows
    ]
    return previous.fetched_at, current.fetched_at, changes


def rarity_order_list() -> list[str]:
    return list(RARITY_ORDER)
