from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def next_number(db: Session, model, column, prefix: str) -> str:
    """Generate human-friendly document numbers like ``SO-2026-00042``."""
    year = datetime.now(timezone.utc).year
    stem = f"{prefix}-{year}-"
    count = db.scalar(select(func.count()).select_from(model).where(column.like(f"{stem}%"))) or 0
    return f"{stem}{count + 1:05d}"
