"""Sync orchestration: today-missing auto sync and manual API triggers."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select

from app.cache import invalidate_api_cache
from app.database import SessionLocal
from app.models import PriceSnapshot
from app.services.sync_service import run_sync_blocking
from app.snapshot_dates import today_snapshot_exists_db

logger = logging.getLogger(__name__)


@dataclass
class _SyncState:
    last_sync_at: datetime | None = None
    in_progress: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


_state = _SyncState()


def today_snapshot_exists() -> bool:
    """True if at least one PriceSnapshot was recorded today (KST)."""
    db = SessionLocal()
    try:
        return today_snapshot_exists_db(db)
    finally:
        db.close()


def _load_last_sync_at() -> datetime | None:
    db = SessionLocal()
    try:
        return db.scalar(
            select(PriceSnapshot.fetched_at)
            .order_by(PriceSnapshot.fetched_at.desc())
            .limit(1)
        )
    finally:
        db.close()


def get_last_sync_at() -> datetime | None:
    return _state.last_sync_at


def is_sync_in_progress() -> bool:
    return _state.in_progress


def is_today_stale() -> bool:
    """Stale when no PriceSnapshot exists for today (KST)."""
    return not today_snapshot_exists()


def init_sync_state() -> None:
    _state.last_sync_at = _load_last_sync_at()
    if _state.last_sync_at:
        logger.info("Last sync loaded from DB: %s", _state.last_sync_at.isoformat())
    else:
        logger.info("No previous sync found in DB")
    if today_snapshot_exists():
        logger.info("Today's snapshot already exists (KST)")
    else:
        logger.info("Today's snapshot missing (KST) — will sync on next data API request")


def _run_sync(trigger: str) -> tuple[PriceSnapshot, list[dict]] | None:
    logger.info("Sync started (trigger=%s)", trigger)
    db = SessionLocal()
    try:
        snapshot, set_results = run_sync_blocking(db)
        _state.last_sync_at = snapshot.fetched_at
        invalidate_api_cache()
        errors = [row for row in set_results if row.get("error")]
        if errors:
            logger.error(
                "Sync completed with set errors. snapshot_id=%s card_count=%s errors=%d",
                snapshot.id,
                snapshot.card_count,
                len(errors),
            )
            for row in errors:
                logger.error("Set %s failed: %s", row.get("slug"), row.get("error"))
        else:
            logger.info(
                "Sync completed. snapshot_id=%s card_count=%s",
                snapshot.id,
                snapshot.card_count,
            )
        return snapshot, set_results
    except Exception:
        logger.exception("Sync failed (trigger=%s)", trigger)
        return None
    finally:
        db.close()
        with _state.lock:
            _state.in_progress = False


def execute_sync(
    trigger: str, *, background: bool = False
) -> tuple[PriceSnapshot, list[dict]] | None:
    """Run sync unless one is already in progress."""
    with _state.lock:
        if _state.in_progress:
            logger.info("Sync skipped (already in progress, trigger=%s)", trigger)
            return None
        _state.in_progress = True

    if background:
        threading.Thread(
            target=_run_sync,
            args=(trigger,),
            name=f"sync-{trigger}",
            daemon=True,
        ).start()
        return None

    return _run_sync(trigger)


def maybe_sync_if_today_missing() -> None:
    """Start background sync when today's snapshot is missing."""
    if is_sync_in_progress():
        return
    if not is_today_stale():
        return
    logger.info("Today's snapshot missing — starting background sync")
    execute_sync("today_missing", background=True)
