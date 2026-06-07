"""KST calendar-day helpers for daily price snapshots."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PriceSnapshot


def sync_timezone() -> ZoneInfo:
    return ZoneInfo(settings.sync_timezone)


def kst_day_utc_bounds(day: date) -> tuple[datetime, datetime]:
    """Return [start, end) UTC bounds for a KST calendar day."""
    tz = sync_timezone()
    start_kst = datetime(day.year, day.month, day.day, tzinfo=tz)
    end_kst = start_kst + timedelta(days=1)
    return start_kst.astimezone(timezone.utc), end_kst.astimezone(timezone.utc)


def kst_today_utc_bounds() -> tuple[datetime, datetime]:
    now_kst = datetime.now(sync_timezone())
    return kst_day_utc_bounds(now_kst.date())


def kst_yesterday_utc_bounds() -> tuple[datetime, datetime]:
    today = datetime.now(sync_timezone()).date()
    return kst_day_utc_bounds(today - timedelta(days=1))


def to_kst_date(dt: datetime) -> date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(sync_timezone()).date()


def get_snapshot_for_kst_day(db: Session, day: date) -> PriceSnapshot | None:
    start_utc, end_utc = kst_day_utc_bounds(day)
    return db.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.fetched_at >= start_utc)
        .where(PriceSnapshot.fetched_at < end_utc)
        .order_by(PriceSnapshot.fetched_at.desc())
        .limit(1)
    )


def get_today_snapshot(db: Session) -> PriceSnapshot | None:
    return get_snapshot_for_kst_day(db, datetime.now(sync_timezone()).date())


def get_yesterday_snapshot(db: Session) -> PriceSnapshot | None:
    today = datetime.now(sync_timezone()).date()
    return get_snapshot_for_kst_day(db, today - timedelta(days=1))


def today_snapshot_exists_db(db: Session) -> bool:
    return get_today_snapshot(db) is not None
