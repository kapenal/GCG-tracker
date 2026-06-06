"""Standalone daily price sync entry point.

Run:
    python -m app.sync_job

Exit codes:
    0 - sync completed without set-level errors
    1 - sync failed or one or more sets reported errors
"""

from __future__ import annotations

import logging
import sys

from app.database import Base, SessionLocal, engine
from app.db_migrate import run_migrations
from app.services.sync_service import run_sync_blocking

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app.sync_job")


def main() -> int:
    logger.info("Starting GCG price sync job")
    try:
        Base.metadata.create_all(bind=engine)
        run_migrations()

        db = SessionLocal()
        try:
            snapshot, set_results = run_sync_blocking(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Sync job failed with an unhandled error")
        return 1

    errors = [row for row in set_results if row.get("error")]
    for row in set_results:
        slug = row.get("slug", "?")
        if row.get("error"):
            logger.error("Set %s failed: %s", slug, row["error"])
        elif slug != "_maintenance":
            logger.info("Set %s: %d cards", slug, row.get("count", 0))

    if any(row.get("slug") == "_maintenance" for row in set_results):
        pruned = next(
            (row.get("count", 0) for row in set_results if row.get("slug") == "_maintenance"),
            0,
        )
        logger.info("Pruned %d snapshots older than 7 days", pruned)

    if errors:
        logger.error(
            "Sync finished with errors. snapshot_id=%s card_count=%s failed_sets=%d",
            snapshot.id,
            snapshot.card_count,
            len(errors),
        )
        return 1

    logger.info(
        "Sync completed successfully. snapshot_id=%s card_count=%s",
        snapshot.id,
        snapshot.card_count,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
