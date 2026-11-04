from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app import schemas
from app.deps import DB, CurrentUser
from app.models import MovementType, StockMovement

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/movements", response_model=list[schemas.StockMovementOut])
def list_movements(
    db: DB,
    _: CurrentUser,
    movement_type: MovementType | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(StockMovement).options(joinedload(StockMovement.product))
    if movement_type:
        stmt = stmt.where(StockMovement.movement_type == movement_type)
    stmt = stmt.order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).limit(limit)
    return db.scalars(stmt).all()
