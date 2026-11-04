"""Reporting queries shared by the reports and dashboard endpoints."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.models import Category, Order, OrderItem, OrderStatus, Product

# Orders that count as revenue: stock has been committed and the sale not cancelled.
REVENUE_STATUSES = (OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED)
ZERO = Decimal("0.00")


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, tzinfo=timezone.utc),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _base_filter(start: date, end: date):
    lo, hi = _bounds(start, end)
    return (
        Order.status.in_(REVENUE_STATUSES),
        Order.confirmed_at >= lo,
        Order.confirmed_at < hi,
    )


def sales_summary(db: Session, start: date, end: date) -> schemas.SalesSummary:
    filters = _base_filter(start, end)
    revenue, cost, units = db.execute(
        select(
            func.sum(OrderItem.unit_price * OrderItem.quantity),
            func.sum(OrderItem.unit_cost * OrderItem.quantity),
            func.sum(OrderItem.quantity),
        ).join(Order).where(*filters)
    ).one()
    orders = db.scalar(select(func.count(Order.id)).where(*filters)) or 0
    revenue, cost = _money(revenue), _money(cost)
    return schemas.SalesSummary(
        revenue=revenue,
        cost=cost,
        gross_profit=revenue - cost,
        orders=orders,
        units_sold=int(units or 0),
        average_order_value=_money(revenue / orders) if orders else ZERO,
    )


def daily_sales(db: Session, start: date, end: date) -> list[schemas.DailySales]:
    day = func.date(Order.confirmed_at)
    rows = db.execute(
        select(
            day.label("day"),
            func.sum(OrderItem.unit_price * OrderItem.quantity),
            func.count(func.distinct(Order.id)),
        )
        .join(Order)
        .where(*_base_filter(start, end))
        .group_by(day)
    ).all()
    by_day = {_as_date(d): (rev, n) for d, rev, n in rows}
    out, cursor = [], start
    while cursor <= end:
        rev, n = by_day.get(cursor, (0, 0))
        out.append(schemas.DailySales(date=cursor, revenue=_money(rev), orders=n))
        cursor += timedelta(days=1)
    return out


def top_products(db: Session, start: date, end: date, limit: int = 10) -> list[schemas.TopProduct]:
    revenue = func.sum(OrderItem.unit_price * OrderItem.quantity)
    rows = db.execute(
        select(Product.id, Product.sku, Product.name, func.sum(OrderItem.quantity), revenue)
        .select_from(OrderItem)
        .join(Order)
        .join(Product, OrderItem.product_id == Product.id)
        .where(*_base_filter(start, end))
        .group_by(Product.id, Product.sku, Product.name)
        .order_by(revenue.desc())
        .limit(limit)
    ).all()
    return [
        schemas.TopProduct(product_id=pid, sku=sku, name=name, units_sold=int(units), revenue=_money(rev))
        for pid, sku, name, units, rev in rows
    ]


def sales_by_category(db: Session, start: date, end: date) -> list[schemas.CategorySales]:
    revenue = func.sum(OrderItem.unit_price * OrderItem.quantity)
    name = func.coalesce(Category.name, "Uncategorized")
    rows = db.execute(
        select(name, revenue, func.sum(OrderItem.quantity))
        .select_from(OrderItem)
        .join(Order)
        .join(Product, OrderItem.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(*_base_filter(start, end))
        .group_by(name)
        .order_by(revenue.desc())
    ).all()
    return [
        schemas.CategorySales(category=c, revenue=_money(r), units_sold=int(u)) for c, r, u in rows
    ]


def sales_report(db: Session, start: date, end: date) -> schemas.SalesReport:
    return schemas.SalesReport(
        start_date=start,
        end_date=end,
        summary=sales_summary(db, start, end),
        daily=daily_sales(db, start, end),
        top_products=top_products(db, start, end),
        by_category=sales_by_category(db, start, end),
    )


def inventory_report(db: Session) -> schemas.InventoryReport:
    name = func.coalesce(Category.name, "Uncategorized")
    rows = db.execute(
        select(
            name,
            func.count(Product.id),
            func.sum(Product.quantity),
            func.sum(Product.cost_price * Product.quantity),
            func.sum(Product.unit_price * Product.quantity),
        )
        .select_from(Product)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(Product.is_active.is_(True))
        .group_by(name)
        .order_by(func.sum(Product.cost_price * Product.quantity).desc())
    ).all()
    by_category = [
        schemas.InventoryValuationRow(
            category=c, products=n, units=int(u or 0), cost_value=_money(cv), retail_value=_money(rv)
        )
        for c, n, u, cv, rv in rows
    ]
    return schemas.InventoryReport(
        total_products=sum(r.products for r in by_category),
        total_units=sum(r.units for r in by_category),
        cost_value=sum((r.cost_value for r in by_category), ZERO),
        retail_value=sum((r.retail_value for r in by_category), ZERO),
        by_category=by_category,
    )
