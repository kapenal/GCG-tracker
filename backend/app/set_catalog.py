"""Configured Yu-Yu Tei set pages and DB rows."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CardSet
from app.scraper_config import SET_PAGES


def ensure_configured_sets(db: Session, *, commit: bool = False) -> dict[str, CardSet]:
    by_slug: dict[str, CardSet] = {}
    for page in SET_PAGES:
        row = db.scalar(select(CardSet).where(CardSet.slug == page.slug))
        if not row:
            row = CardSet(slug=page.slug, label=page.label, source_url=page.url)
            db.add(row)
            db.flush()
        else:
            row.label = page.label
            row.source_url = page.url
        by_slug[page.slug] = row
    if commit:
        db.commit()
    return by_slug
