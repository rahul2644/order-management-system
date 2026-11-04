"""Core stock-keeping logic.

Every change to a product's on-hand quantity goes through ``adjust_stock`` so that
(1) an auditable ``StockMovement`` row is always written and (2) low-stock alerts are
raised or resolved automatically.
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AlertStatus, LowStockAlert, MovementType, Product, StockMovement, utcnow

logger = logging.getLogger("inventory")


class InsufficientStockError(Exception):
    def __init__(self, product: Product, requested: int):
        self.product = product
        self.requested = requested
        super().__init__(
            f"Insufficient stock for {product.sku}: requested {requested}, available {product.quantity}"
        )


def adjust_stock(
    db: Session,
    product: Product,
    change: int,
    movement_type: MovementType,
    *,
    reference: str | None = None,
    note: str | None = None,
    user_id: int | None = None,
    occurred_at: datetime | None = None,
) -> StockMovement:
    """Apply a stock change, record it, and sync low-stock alerts. Does not commit.

    ``occurred_at`` lets historical imports (and the demo seeder) record backdated movements.
    """
    new_quantity = product.quantity + change
    if new_quantity < 0:
        raise InsufficientStockError(product, -change)

    product.quantity = new_quantity
    movement = StockMovement(
        product=product,
        change=change,
        quantity_after=new_quantity,
        movement_type=movement_type,
        reference=reference,
        note=note,
        user_id=user_id,
        created_at=occurred_at or utcnow(),
    )
    db.add(movement)
    sync_low_stock_alert(db, product, occurred_at=occurred_at)
    return movement


def sync_low_stock_alert(
    db: Session, product: Product, *, occurred_at: datetime | None = None
) -> LowStockAlert | None:
    """Open an alert when stock falls to/below the reorder level, resolve it when replenished."""
    # Flush so alerts created earlier in this unit of work are visible to the query
    # (the session runs with autoflush disabled).
    db.flush()
    open_alerts = db.scalars(
        select(LowStockAlert).where(
            LowStockAlert.product_id == product.id,
            LowStockAlert.status == AlertStatus.OPEN,
        )
    ).all()

    if product.is_active and product.quantity <= product.reorder_level:
        if open_alerts:
            return open_alerts[0]
        alert = LowStockAlert(
            product=product,
            quantity_at_trigger=product.quantity,
            reorder_level=product.reorder_level,
            created_at=occurred_at or utcnow(),
        )
        db.add(alert)
        notify_low_stock(product)
        return alert

    for alert in open_alerts:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = occurred_at or utcnow()
    return None


def notify_low_stock(product: Product) -> None:
    """Notification hook. Swap this for email/Slack/webhook delivery in production."""
    logger.warning(
        "LOW STOCK: %s (%s) has %s units, reorder level is %s",
        product.name,
        product.sku,
        product.quantity,
        product.reorder_level,
    )
