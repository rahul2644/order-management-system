from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app import schemas
from app.deps import DB, CurrentUser
from app.models import AlertStatus, LowStockAlert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(
    db: DB,
    _: CurrentUser,
    status_filter: AlertStatus | None = Query(default=AlertStatus.OPEN, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(LowStockAlert)
    if status_filter:
        stmt = stmt.where(LowStockAlert.status == status_filter)
    stmt = stmt.order_by(LowStockAlert.created_at.desc(), LowStockAlert.id.desc()).limit(limit)
    return db.scalars(stmt).all()


@router.get("/count")
def alert_count(db: DB, _: CurrentUser) -> dict[str, int]:
    open_count = db.scalar(
        select(func.count(LowStockAlert.id)).where(LowStockAlert.status == AlertStatus.OPEN)
    )
    return {"open": open_count or 0}
