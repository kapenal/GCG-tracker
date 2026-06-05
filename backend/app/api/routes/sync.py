from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import PriceSnapshot
from app.schemas import SnapshotOut, SyncResult
from app.services.sync_service import run_sync_blocking

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncResult)
def trigger_sync(db: Session = Depends(get_db)):
    snapshot, sets = run_sync_blocking(db)
    return SyncResult(
        snapshot_id=snapshot.id,
        fetched_at=snapshot.fetched_at,
        total_cards=snapshot.card_count,
        sets=sets,
    )


@router.get("/snapshots", response_model=list[SnapshotOut])
def list_snapshots(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(PriceSnapshot).order_by(PriceSnapshot.fetched_at.desc()).limit(30)
    ).all()
    return rows
