from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app import schemas
from app.deps import DB, AdminUser, CurrentUser
from app.models import Product, PurchaseOrder, Supplier

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _get_or_404(db, supplier_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return supplier


def _to_out(supplier: Supplier, product_count: int) -> schemas.SupplierOut:
    out = schemas.SupplierOut.model_validate(supplier)
    out.product_count = product_count
    return out


@router.get("", response_model=list[schemas.SupplierOut])
def list_suppliers(db: DB, _: CurrentUser, q: str | None = Query(default=None, max_length=100)):
    product_count = (
        select(func.count(Product.id)).where(Product.supplier_id == Supplier.id).scalar_subquery()
    )
    stmt = select(Supplier, product_count).order_by(Supplier.name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Supplier.name.ilike(like), Supplier.contact_name.ilike(like)))
    return [_to_out(s, count) for s, count in db.execute(stmt).all()]


@router.get("/{supplier_id}", response_model=schemas.SupplierOut)
def get_supplier(supplier_id: int, db: DB, _: CurrentUser):
    supplier = _get_or_404(db, supplier_id)
    count = db.scalar(select(func.count(Product.id)).where(Product.supplier_id == supplier_id))
    return _to_out(supplier, count or 0)


@router.post("", response_model=schemas.SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: schemas.SupplierCreate, db: DB, _: CurrentUser):
    if db.scalar(select(Supplier).where(Supplier.name.ilike(payload.name))):
        raise HTTPException(status.HTTP_409_CONFLICT, "A supplier with this name already exists")
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    return _to_out(supplier, 0)


@router.patch("/{supplier_id}", response_model=schemas.SupplierOut)
def update_supplier(supplier_id: int, payload: schemas.SupplierUpdate, db: DB, user: CurrentUser):
    supplier = _get_or_404(db, supplier_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    return get_supplier(supplier_id, db, user)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, db: DB, _: AdminUser):
    supplier = _get_or_404(db, supplier_id)
    if db.scalar(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.supplier_id == supplier_id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Supplier has purchase orders and cannot be deleted"
        )
    db.delete(supplier)
    db.commit()
