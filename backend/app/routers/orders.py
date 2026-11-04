from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app import schemas
from app.deps import DB, CurrentUser
from app.models import MovementType, Order, OrderItem, OrderStatus, Product, utcnow
from app.services.inventory import InsufficientStockError, adjust_stock
from app.services.numbering import next_number

router = APIRouter(prefix="/api/orders", tags=["orders"])

# Allowed status transitions for a sales order.
TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def _get_or_404(db, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.get("", response_model=schemas.Page[schemas.OrderOut])
def list_orders(
    db: DB,
    _: CurrentUser,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(Order)
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Order.order_number.ilike(like), Order.customer_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Order.created_at.desc(), Order.id.desc()).offset((page - 1) * size).limit(size)
    return schemas.Page(items=db.scalars(stmt).all(), total=total, page=page, size=size)


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: DB, _: CurrentUser):
    return _get_or_404(db, order_id)


@router.post("", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: schemas.OrderCreate, db: DB, user: CurrentUser):
    order = Order(
        order_number=next_number(db, Order, Order.order_number, "SO"),
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        notes=payload.notes,
        created_by_id=user.id,
    )
    for line in payload.items:
        product = db.get(Product, line.product_id)
        if not product or not product.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown product {line.product_id}")
        order.items.append(
            OrderItem(
                product=product,
                quantity=line.quantity,
                unit_price=line.unit_price if line.unit_price is not None else product.unit_price,
                unit_cost=product.cost_price,
            )
        )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
def update_order_status(order_id: int, payload: schemas.OrderStatusUpdate, db: DB, user: CurrentUser):
    order = _get_or_404(db, order_id)
    target = payload.status
    if target not in TRANSITIONS[order.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot move order from '{order.status.value}' to '{target.value}'",
        )

    if target == OrderStatus.CONFIRMED:
        # Stock is committed when an order is confirmed. All lines succeed or none do.
        try:
            for item in order.items:
                adjust_stock(db, item.product, -item.quantity, MovementType.SALE,
                             reference=order.order_number, user_id=user.id)
        except InsufficientStockError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        order.confirmed_at = utcnow()
    elif target == OrderStatus.CANCELLED and order.status == OrderStatus.CONFIRMED:
        # Return committed stock to inventory.
        for item in order.items:
            adjust_stock(db, item.product, item.quantity, MovementType.RETURN,
                         reference=order.order_number, note="Order cancelled", user_id=user.id)

    order.status = target
    db.commit()
    db.refresh(order)
    return order
