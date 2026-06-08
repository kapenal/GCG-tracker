from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.cache import CACHE_CONTROL_HEADER, TTL_RARITIES, api_cache
from app.schemas import RarityOut
from app.services import query_service

router = APIRouter(prefix="/rarities", tags=["rarities"])


def _rarities_cache_key(set_slug: str | None) -> str:
    return set_slug or ""


@router.get("", response_model=list[RarityOut])
def list_rarities(
    response: Response, set: str | None = None, db: Session = Depends(get_db)
):
    response.headers["Cache-Control"] = CACHE_CONTROL_HEADER

    cache_key = _rarities_cache_key(set)
    cached = api_cache.get("rarities", cache_key)
    if cached is not None:
        return cached

    result = query_service.list_rarities(db, set_slug=set)
    api_cache.set("rarities", cache_key, result, TTL_RARITIES)
    return result


@router.get("/order", response_model=list[str])
def rarity_order():
    return query_service.rarity_order_list()
