"""Pydantic request/response schemas."""
from datetime import date, datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import (
    AlertStatus,
    MovementType,
    OrderStatus,
    PurchaseOrderStatus,
    UserRole,
)

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


# ---------- Auth / users ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.STAFF


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserOut(UserBase, ORMModel):
    id: int
    is_active: bool
    created_at: datetime


# ---------- Categories ----------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CategoryOut(ORMModel):
    id: int
    name: str


# ---------- Suppliers ----------
class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    lead_time_days: int = Field(default=7, ge=0, le=365)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    lead_time_days: int | None = Field(default=None, ge=0, le=365)


class SupplierOut(SupplierBase, ORMModel):
    id: int
    created_at: datetime
    product_count: int = 0


# ---------- Products ----------
class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    unit_price: Decimal = Field(ge=0, decimal_places=2)
    cost_price: Decimal = Field(ge=0, decimal_places=2)
    reorder_level: int = Field(default=10, ge=0)
    reorder_quantity: int = Field(default=50, ge=1)


class ProductCreate(ProductBase):
    quantity: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    reorder_quantity: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class ProductOut(ProductBase, ORMModel):
    id: int
    quantity: int
    is_active: bool
    is_low_stock: bool
    category: CategoryOut | None = None
    supplier_name: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _flatten_supplier(cls, data):
        if hasattr(data, "supplier"):
            supplier = data.supplier
            return {
                **{k: getattr(data, k) for k in cls.model_fields if hasattr(data, k)},
                "supplier_name": supplier.name if supplier else None,
            }
        return data


# ---------- Stock ----------
class StockAdjustment(BaseModel):
    change: int = Field(description="Positive to add stock, negative to remove it")
    movement_type: MovementType = MovementType.ADJUSTMENT
    note: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _non_zero(self):
        if self.change == 0:
            raise ValueError("change must be non-zero")
        return self


class StockMovementOut(ORMModel):
    id: int
    product_id: int
    change: int
    quantity_after: int
    movement_type: MovementType
    reference: str | None
    note: str | None
    created_at: datetime
    product_name: str | None = None
    product_sku: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data):
        if hasattr(data, "product"):
            base = {k: getattr(data, k) for k in cls.model_fields if hasattr(data, k)}
            base["product_name"] = data.product.name
            base["product_sku"] = data.product.sku
            return base
        return data


# ---------- Orders ----------
class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0, description="Defaults to product price")


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=150)
    customer_email: EmailStr | None = None
    notes: str | None = None
    items: list[OrderItemIn] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemOut(ORMModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    product_name: str | None = None
    product_sku: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data):
        if hasattr(data, "product"):
            base = {k: getattr(data, k) for k in cls.model_fields if hasattr(data, k)}
            base["product_name"] = data.product.name
            base["product_sku"] = data.product.sku
            return base
        return data


class OrderOut(ORMModel):
    id: int
    order_number: str
    customer_name: str
    customer_email: str | None
    status: OrderStatus
    notes: str | None
    total: Decimal
    created_at: datetime
    confirmed_at: datetime | None
    items: list[OrderItemOut]


# ---------- Purchase orders ----------
class PurchaseOrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: Decimal | None = Field(default=None, ge=0, description="Defaults to product cost")


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    expected_date: date | None = None
    notes: str | None = None
    items: list[PurchaseOrderItemIn] = Field(min_length=1)


class PurchaseOrderStatusUpdate(BaseModel):
    status: PurchaseOrderStatus


class PurchaseOrderItemOut(ORMModel):
    id: int
    product_id: int
    quantity: int
    unit_cost: Decimal
    product_name: str | None = None
    product_sku: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data):
        if hasattr(data, "product"):
            base = {k: getattr(data, k) for k in cls.model_fields if hasattr(data, k)}
            base["product_name"] = data.product.name
            base["product_sku"] = data.product.sku
            return base
        return data


class PurchaseOrderOut(ORMModel):
    id: int
    po_number: str
    supplier_id: int
    supplier_name: str
    status: PurchaseOrderStatus
    expected_date: date | None
    received_at: datetime | None
    notes: str | None
    total: Decimal
    created_at: datetime
    items: list[PurchaseOrderItemOut]

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data):
        if hasattr(data, "supplier"):
            base = {k: getattr(data, k) for k in cls.model_fields if hasattr(data, k)}
            base["supplier_name"] = data.supplier.name
            return base
        return data


# ---------- Alerts ----------
class AlertOut(ORMModel):
    id: int
    product_id: int
    product_name: str
    product_sku: str
    current_quantity: int
    quantity_at_trigger: int
    reorder_level: int
    status: AlertStatus
    created_at: datetime
    resolved_at: datetime | None

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data):
        if hasattr(data, "product"):
            base = {k: getattr(data, k) for k in cls.model_fields if hasattr(data, k)}
            base.update(
                product_name=data.product.name,
                product_sku=data.product.sku,
                current_quantity=data.product.quantity,
            )
            return base
        return data


# ---------- Reports / dashboard ----------
class SalesSummary(BaseModel):
    revenue: Decimal
    cost: Decimal
    gross_profit: Decimal
    orders: int
    units_sold: int
    average_order_value: Decimal


class DailySales(BaseModel):
    date: date
    revenue: Decimal
    orders: int


class TopProduct(BaseModel):
    product_id: int
    sku: str
    name: str
    units_sold: int
    revenue: Decimal


class CategorySales(BaseModel):
    category: str
    revenue: Decimal
    units_sold: int


class SalesReport(BaseModel):
    start_date: date
    end_date: date
    summary: SalesSummary
    daily: list[DailySales]
    top_products: list[TopProduct]
    by_category: list[CategorySales]


class InventoryValuationRow(BaseModel):
    category: str
    products: int
    units: int
    cost_value: Decimal
    retail_value: Decimal


class InventoryReport(BaseModel):
    total_products: int
    total_units: int
    cost_value: Decimal
    retail_value: Decimal
    by_category: list[InventoryValuationRow]


class DashboardStats(BaseModel):
    total_products: int
    total_suppliers: int
    inventory_value: Decimal
    low_stock_count: int
    open_alerts: int
    pending_orders: int
    revenue_30d: Decimal
    orders_30d: int
    revenue_trend: list[DailySales]
    order_status_breakdown: dict[str, int]
    recent_orders: list[OrderOut]
    low_stock_products: list[ProductOut]
