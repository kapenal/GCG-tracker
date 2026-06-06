from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import PriceSnapshot
from app.schemas import SnapshotOut, SyncResult
from app.sync_scheduler import execute_sync, is_sync_in_progress

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncResult)
def trigger_sync():
    if is_sync_in_progress():
        raise HTTPException(status_code=409, detail="Sync already in progress")

    result = execute_sync("api", background=False)
    if result is None:
        if is_sync_in_progress():
            raise HTTPException(status_code=409, detail="Sync already in progress")
        raise HTTPException(status_code=500, detail="Sync failed")

    snapshot, sets = result
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
