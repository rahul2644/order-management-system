from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app import schemas
from app.deps import DB, CurrentUser
from app.models import AlertStatus, LowStockAlert, Order, OrderStatus, Product, Supplier
from app.services import reports

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardStats)
def dashboard(db: DB, _: CurrentUser):
    today = date.today()
    start = today - timedelta(days=29)
    active = Product.is_active.is_(True)
    low_stock = Product.quantity <= Product.reorder_level

    summary = reports.sales_summary(db, start, today)
    status_rows = db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all()

    return schemas.DashboardStats(
        total_products=db.scalar(select(func.count(Product.id)).where(active)) or 0,
        total_suppliers=db.scalar(select(func.count(Supplier.id))) or 0,
        inventory_value=reports.inventory_report(db).cost_value,
        low_stock_count=db.scalar(select(func.count(Product.id)).where(active, low_stock)) or 0,
        open_alerts=db.scalar(
            select(func.count(LowStockAlert.id)).where(LowStockAlert.status == AlertStatus.OPEN)
        ) or 0,
        pending_orders=db.scalar(
            select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)
        ) or 0,
        revenue_30d=summary.revenue,
        orders_30d=summary.orders,
        revenue_trend=reports.daily_sales(db, start, today),
        order_status_breakdown={s.value: n for s, n in status_rows},
        recent_orders=db.scalars(select(Order).order_by(Order.created_at.desc()).limit(6)).all(),
        low_stock_products=db.scalars(
            select(Product).where(active, low_stock).order_by(Product.quantity).limit(6)
        ).all(),
    )
