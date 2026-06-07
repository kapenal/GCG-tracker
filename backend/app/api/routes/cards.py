from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.cache import CACHE_CONTROL_HEADER, TTL_CARDS, api_cache
from app.sync_scheduler import maybe_sync_if_today_missing
from app.models import Card
from app.schemas import CardOut, ChangesResponse, PricePointOut
from app.services import query_service

router = APIRouter(prefix="/cards", tags=["cards"])


def _cards_cache_key(
    set_slug: str | None,
    rarity: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> str:
    return f"{set_slug or ''}|{rarity or ''}|{q or ''}|{limit}|{offset}"


@router.get("", response_model=list[CardOut])
def list_cards(
    response: Response,
    set: str | None = None,
    rarity: str | None = None,
    q: str | None = None,
    limit: int = 5000,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    maybe_sync_if_today_missing()
    response.headers["Cache-Control"] = CACHE_CONTROL_HEADER

    cache_key = _cards_cache_key(set, rarity, q, limit, offset)
    cached = api_cache.get("cards", cache_key)
    if cached is not None:
        return cached

    cards, _ = query_service.list_cards(
        db,
        set_slug=set,
        rarity=rarity,
        q=q,
        limit=limit,
        offset=offset,
    )
    api_cache.set("cards", cache_key, cards, TTL_CARDS)
    return cards


@router.get("/changes", response_model=ChangesResponse)
def price_changes(db: Session = Depends(get_db)):
    from_at, to_at, changes = query_service.compare_latest_snapshots(db)
    return ChangesResponse(
        from_snapshot_at=from_at,
        to_snapshot_at=to_at,
        changes=changes,
    )


@router.get("/{card_id}", response_model=CardOut)
def get_card(card_id: int, db: Session = Depends(get_db)):
    cards, _ = query_service.list_cards(db, limit=10000, offset=0)
    match = next((c for c in cards if c.id == card_id), None)
    if match:
        return match
    raise HTTPException(status_code=404, detail="Card not found")


@router.get("/{card_id}/history", response_model=list[PricePointOut])
def card_history(card_id: int, days: int = 7, db: Session = Depends(get_db)):
    if not db.scalar(select(Card.id).where(Card.id == card_id)):
        raise HTTPException(status_code=404, detail="Card not found")
    return query_service.card_price_history(db, card_id, days=days)
