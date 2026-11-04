import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app import schemas
from app.deps import DB, CurrentUser
from app.services import reports

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _range(start: date | None, end: date | None) -> tuple[date, date]:
    end = end or date.today()
    start = start or end - timedelta(days=29)
    if start > end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "start_date must be before end_date")
    if (end - start).days > 366:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Date range cannot exceed one year")
    return start, end


@router.get("/sales", response_model=schemas.SalesReport)
def sales_report(db: DB, _: CurrentUser, start_date: date | None = None, end_date: date | None = None):
    return reports.sales_report(db, *_range(start_date, end_date))


@router.get("/sales.csv", response_class=StreamingResponse)
def sales_report_csv(db: DB, _: CurrentUser, start_date: date | None = None, end_date: date | None = None):
    start, end = _range(start_date, end_date)
    report = reports.sales_report(db, start, end)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Sales report", start.isoformat(), end.isoformat()])
    s = report.summary
    writer.writerow([])
    writer.writerow(["Revenue", "Cost", "Gross profit", "Orders", "Units sold", "Avg order value"])
    writer.writerow([s.revenue, s.cost, s.gross_profit, s.orders, s.units_sold, s.average_order_value])
    writer.writerow([])
    writer.writerow(["Date", "Revenue", "Orders"])
    writer.writerows([d.date.isoformat(), d.revenue, d.orders] for d in report.daily)
    writer.writerow([])
    writer.writerow(["SKU", "Product", "Units sold", "Revenue"])
    writer.writerows([p.sku, p.name, p.units_sold, p.revenue] for p in report.top_products)
    filename = f"sales_{start.isoformat()}_{end.isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventory", response_model=schemas.InventoryReport)
def inventory_report(db: DB, _: CurrentUser):
    return reports.inventory_report(db)
