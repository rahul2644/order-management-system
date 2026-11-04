from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app import schemas
from app.deps import DB, AdminUser, CurrentUser
from app.models import Category, MovementType, OrderItem, Product, StockMovement, Supplier
from app.services.inventory import InsufficientStockError, adjust_stock, sync_low_stock_alert

router = APIRouter(prefix="/api/products", tags=["products"])

SORTABLE = {
    "name": Product.name,
    "sku": Product.sku,
    "quantity": Product.quantity,
    "unit_price": Product.unit_price,
    "updated_at": Product.updated_at,
}


def _get_or_404(db, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


def _validate_refs(db, category_id: int | None, supplier_id: int | None) -> None:
    if category_id is not None and not db.get(Category, category_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown category_id")
    if supplier_id is not None and not db.get(Supplier, supplier_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown supplier_id")


@router.get("", response_model=schemas.Page[schemas.ProductOut])
def list_products(
    db: DB,
    _: CurrentUser,
    q: str | None = Query(default=None, max_length=100, description="Search name or SKU"),
    category_id: int | None = None,
    supplier_id: int | None = None,
    low_stock: bool = False,
    include_inactive: bool = False,
    sort: Literal["name", "sku", "quantity", "unit_price", "updated_at"] = "name",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
):
    stmt = select(Product)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if supplier_id is not None:
        stmt = stmt.where(Product.supplier_id == supplier_id)
    if low_stock:
        stmt = stmt.where(Product.quantity <= Product.reorder_level)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE[sort]
    stmt = (
        stmt.options(selectinload(Product.category), selectinload(Product.supplier))
        .order_by(column.desc() if order == "desc" else column.asc(), Product.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return schemas.Page(items=db.scalars(stmt).all(), total=total, page=page, size=size)


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: DB, _: CurrentUser):
    return _get_or_404(db, product_id)


@router.post("", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: schemas.ProductCreate, db: DB, user: CurrentUser):
    if db.scalar(select(Product).where(Product.sku == payload.sku)):
        raise HTTPException(status.HTTP_409_CONFLICT, "SKU already exists")
    _validate_refs(db, payload.category_id, payload.supplier_id)

    data = payload.model_dump(exclude={"quantity"})
    product = Product(**data, quantity=0)
    db.add(product)
    db.flush()
    if payload.quantity:
        adjust_stock(db, product, payload.quantity, MovementType.ADJUSTMENT,
                     note="Opening stock", user_id=user.id)
    else:
        sync_low_stock_alert(db, product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductUpdate, db: DB, _: CurrentUser):
    product = _get_or_404(db, product_id)
    changes = payload.model_dump(exclude_unset=True)
    if "sku" in changes and changes["sku"] != product.sku:
        if db.scalar(select(Product).where(Product.sku == changes["sku"])):
            raise HTTPException(status.HTTP_409_CONFLICT, "SKU already exists")
    _validate_refs(db, changes.get("category_id"), changes.get("supplier_id"))
    for field, value in changes.items():
        setattr(product, field, value)
    # Reorder level or active flag may have changed: re-evaluate alerts.
    sync_low_stock_alert(db, product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DB, _: AdminUser):
    """Hard-delete unused products; archive (soft-delete) products that appear on orders."""
    product = _get_or_404(db, product_id)
    used = db.scalar(select(func.count(OrderItem.id)).where(OrderItem.product_id == product_id))
    if used:
        product.is_active = False
        sync_low_stock_alert(db, product)
    else:
        db.delete(product)
    db.commit()


@router.post("/{product_id}/stock", response_model=schemas.ProductOut)
def adjust_product_stock(product_id: int, payload: schemas.StockAdjustment, db: DB, user: CurrentUser):
    product = _get_or_404(db, product_id)
    try:
        adjust_stock(db, product, payload.change, payload.movement_type,
                     note=payload.note, user_id=user.id)
    except InsufficientStockError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}/movements", response_model=list[schemas.StockMovementOut])
def product_movements(product_id: int, db: DB, _: CurrentUser, limit: int = Query(50, le=500)):
    _get_or_404(db, product_id)
    stmt = (
        select(StockMovement)
        .where(StockMovement.product_id == product_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()
