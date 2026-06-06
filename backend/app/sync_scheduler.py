"""APScheduler-based daily sync and stale-data fallback."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.cache import invalidate_api_cache
from app.config import settings
from app.database import SessionLocal
from app.models import PriceSnapshot
from app.services.sync_service import run_sync_blocking

logger = logging.getLogger(__name__)

SYNC_JOB_ID = "daily_sync"


@dataclass
class _SyncState:
    last_sync_at: datetime | None = None
    in_progress: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


_state = _SyncState()
_scheduler: BackgroundScheduler | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    """Run sync unless one is already in progress.

    Returns (snapshot, set_results) for blocking runs, None if skipped or failed.
    Background runs always return None immediately after enqueueing.
    """
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


def _scheduled_sync() -> None:
    execute_sync("scheduled", background=False)


def _is_stale() -> bool:
    last = _state.last_sync_at
    if last is None:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return _utc_now() - last >= timedelta(hours=settings.sync_stale_hours)


def maybe_sync_if_stale() -> None:
    if not _is_stale():
        return
    execute_sync("stale_fallback", background=True)


def start_scheduler() -> BackgroundScheduler:
    global _scheduler

    _state.last_sync_at = _load_last_sync_at()
    if _state.last_sync_at:
        logger.info("Last sync loaded from DB: %s", _state.last_sync_at.isoformat())
    else:
        logger.info("No previous sync found in DB")

    _scheduler = BackgroundScheduler(timezone=settings.sync_timezone)
    job = _scheduler.add_job(
        _scheduled_sync,
        CronTrigger(
            hour=settings.sync_hour,
            minute=settings.sync_minute,
            timezone=settings.sync_timezone,
        ),
        id=SYNC_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()

    logger.info("Scheduler started")
    logger.info("Next run time: %s", job.next_run_time)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
