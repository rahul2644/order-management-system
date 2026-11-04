from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app import schemas
from app.deps import DB, CurrentUser
from app.models import (
    AlertStatus,
    LowStockAlert,
    MovementType,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
    utcnow,
)
from app.services.inventory import adjust_stock
from app.services.numbering import next_number

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase orders"])

TRANSITIONS: dict[PurchaseOrderStatus, set[PurchaseOrderStatus]] = {
    PurchaseOrderStatus.DRAFT: {PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.ORDERED: {PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.RECEIVED: set(),
    PurchaseOrderStatus.CANCELLED: set(),
}


def _get_or_404(db, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return po


@router.get("", response_model=list[schemas.PurchaseOrderOut])
def list_purchase_orders(
    db: DB,
    _: CurrentUser,
    status_filter: PurchaseOrderStatus | None = Query(default=None, alias="status"),
    supplier_id: int | None = None,
):
    stmt = select(PurchaseOrder)
    if status_filter:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    if supplier_id:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    return db.scalars(stmt.order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id.desc())).all()


@router.get("/{po_id}", response_model=schemas.PurchaseOrderOut)
def get_purchase_order(po_id: int, db: DB, _: CurrentUser):
    return _get_or_404(db, po_id)


@router.post("", response_model=schemas.PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
def create_purchase_order(payload: schemas.PurchaseOrderCreate, db: DB, _: CurrentUser):
    if not db.get(Supplier, payload.supplier_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown supplier_id")
    po = PurchaseOrder(
        po_number=next_number(db, PurchaseOrder, PurchaseOrder.po_number, "PO"),
        supplier_id=payload.supplier_id,
        expected_date=payload.expected_date,
        notes=payload.notes,
    )
    for line in payload.items:
        product = db.get(Product, line.product_id)
        if not product:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown product {line.product_id}")
        po.items.append(
            PurchaseOrderItem(
                product=product,
                quantity=line.quantity,
                unit_cost=line.unit_cost if line.unit_cost is not None else product.cost_price,
            )
        )
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.post("/from-alerts", response_model=list[schemas.PurchaseOrderOut],
             status_code=status.HTTP_201_CREATED)
def create_from_alerts(db: DB, _: CurrentUser):
    """Draft one purchase order per supplier covering every product with an open low-stock alert.

    Products already on an open (draft/ordered) purchase order are skipped.
    """
    already_on_order = set(
        db.scalars(
            select(PurchaseOrderItem.product_id)
            .join(PurchaseOrder)
            .where(PurchaseOrder.status.in_([PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.ORDERED]))
        )
    )
    alerts = db.scalars(select(LowStockAlert).where(LowStockAlert.status == AlertStatus.OPEN)).all()
    by_supplier: dict[int, list[Product]] = defaultdict(list)
    for alert in alerts:
        product = alert.product
        if product.supplier_id and product.id not in already_on_order:
            by_supplier[product.supplier_id].append(product)

    created = []
    for supplier_id, products in by_supplier.items():
        po = PurchaseOrder(
            po_number=next_number(db, PurchaseOrder, PurchaseOrder.po_number, "PO"),
            supplier_id=supplier_id,
            notes="Auto-generated from low-stock alerts",
        )
        for product in products:
            # Order enough to get back above the reorder level, at least the reorder quantity.
            shortfall = product.reorder_level - product.quantity
            qty = max(product.reorder_quantity, shortfall + product.reorder_quantity)
            po.items.append(PurchaseOrderItem(product=product, quantity=qty, unit_cost=product.cost_price))
        db.add(po)
        db.flush()
        created.append(po)
    db.commit()
    for po in created:
        db.refresh(po)
    return created


@router.patch("/{po_id}/status", response_model=schemas.PurchaseOrderOut)
def update_purchase_order_status(
    po_id: int, payload: schemas.PurchaseOrderStatusUpdate, db: DB, user: CurrentUser
):
    po = _get_or_404(db, po_id)
    target = payload.status
    if target not in TRANSITIONS[po.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot move purchase order from '{po.status.value}' to '{target.value}'",
        )
    if target == PurchaseOrderStatus.RECEIVED:
        for item in po.items:
            adjust_stock(db, item.product, item.quantity, MovementType.PURCHASE,
                         reference=po.po_number, user_id=user.id)
        po.received_at = utcnow()
    po.status = target
    db.commit()
    db.refresh(po)
    return po
