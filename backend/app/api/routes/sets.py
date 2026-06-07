from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.cache import CACHE_CONTROL_HEADER, TTL_SETS, api_cache
from app.sync_scheduler import maybe_sync_if_today_missing
from app.schemas import SetOut
from app.services import query_service

router = APIRouter(prefix="/sets", tags=["sets"])


@router.get("", response_model=list[SetOut])
def list_sets(response: Response, db: Session = Depends(get_db)):
    maybe_sync_if_today_missing()
    response.headers["Cache-Control"] = CACHE_CONTROL_HEADER

    cached = api_cache.get("sets")
    if cached is not None:
        return cached

    result = [
        SetOut(
            id=s.id,
            slug=s.slug,
            label=s.label,
            source_url=s.source_url,
            card_count=count,
        )
        for s, count in query_service.list_sets_with_counts(db)
    ]
    api_cache.set("sets", "", result, TTL_SETS)
    return result
