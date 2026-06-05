from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import SetOut
from app.services import query_service

router = APIRouter(prefix="/sets", tags=["sets"])


@router.get("", response_model=list[SetOut])
def list_sets(db: Session = Depends(get_db)):
    return [
        SetOut(
            id=s.id,
            slug=s.slug,
            label=s.label,
            source_url=s.source_url,
            card_count=count,
        )
        for s, count in query_service.list_sets_with_counts(db)
    ]
