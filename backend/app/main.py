from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cards, rarities, sets, sync
from app.config import settings
from app.database import Base, engine
from app.db_migrate import run_migrations
from app.sync_scheduler import (
    get_last_sync_at,
    init_sync_state,
    is_sync_in_progress,
    today_snapshot_exists,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    init_sync_state()
    yield


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
    last_sync = get_last_sync_at()
    return {
        "status": "ok",
        "last_sync_at": last_sync.isoformat() if last_sync else None,
        "sync_in_progress": is_sync_in_progress(),
        "today_snapshot_exists": today_snapshot_exists(),
    }
