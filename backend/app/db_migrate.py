from sqlalchemy import inspect, text

from app.database import engine


def run_migrations() -> None:
    """Lightweight schema updates for existing PostgreSQL volumes."""
    insp = inspect(engine)
    if not insp.has_table("cards"):
        return

    columns = {c["name"] for c in insp.get_columns("cards")}
    if "rarity" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE cards ADD COLUMN rarity VARCHAR(16)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_cards_rarity ON cards (rarity)")
            )

    if "name_ko" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE cards ADD COLUMN name_ko VARCHAR(512)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_cards_name_ko ON cards (name_ko)")
            )
