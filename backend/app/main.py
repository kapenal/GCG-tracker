import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cards, rarities, sets, sync
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_migrate import run_migrations
from app.services.sync_service import run_sync

logger = logging.getLogger(__name__)


def _next_sync_time(now: datetime, hour: int, minute: int) -> datetime:
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


async def _daily_sync_worker(stop_event: asyncio.Event) -> None:
    tz = ZoneInfo(settings.auto_sync_timezone)
    while not stop_event.is_set():
        now = datetime.now(tz)
        next_run = _next_sync_time(now, settings.auto_sync_hour, settings.auto_sync_minute)
        wait_seconds = max(1.0, (next_run - now).total_seconds())
        logger.info("Next auto sync scheduled at %s", next_run.isoformat())

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
            break
        except asyncio.TimeoutError:
            pass

        db = SessionLocal()
        try:
            snapshot, _ = await run_sync(db)
            logger.info(
                "Auto sync finished. snapshot_id=%s card_count=%s",
                snapshot.id,
                snapshot.card_count,
            )
        except Exception:
            logger.exception("Auto sync failed")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    stop_event = asyncio.Event()
    worker_task: asyncio.Task | None = None
    if settings.auto_sync_enabled:
        worker_task = asyncio.create_task(_daily_sync_worker(stop_event))
    yield
    if worker_task:
        stop_event.set()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Yu-Yu Tei GCG Price Tracker",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sets.router, prefix="/api")
app.include_router(rarities.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(sync.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
