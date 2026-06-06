import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cards, rarities, sets, sync
from app.config import settings
from app.database import Base, engine
from app.db_migrate import run_migrations
from app.sync_scheduler import (
    get_last_sync_at,
    is_sync_in_progress,
    maybe_sync_if_stale,
    shutdown_scheduler,
    start_scheduler,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    start_scheduler()
    yield
    shutdown_scheduler()


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


@app.middleware("http")
async def stale_sync_fallback(request: Request, call_next):
    if request.method == "GET" and not request.url.path.startswith("/api/sync"):
        maybe_sync_if_stale()
    return await call_next(request)


app.include_router(sets.router, prefix="/api")
app.include_router(rarities.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(sync.router, prefix="/api")


@app.get("/api/health")
def health():
    last_sync = get_last_sync_at()
    return {
        "status": "ok",
        "last_sync_at": last_sync.isoformat() if last_sync else None,
        "sync_in_progress": is_sync_in_progress(),
    }
