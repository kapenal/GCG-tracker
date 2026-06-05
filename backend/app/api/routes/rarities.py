from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import RarityOut
from app.services import query_service

router = APIRouter(prefix="/rarities", tags=["rarities"])


@router.get("", response_model=list[RarityOut])
def list_rarities(set: str | None = None, db: Session = Depends(get_db)):
    return query_service.list_rarities(db, set_slug=set)


@router.get("/order", response_model=list[str])
def rarity_order():
    return query_service.rarity_order_list()
