# StockPilot: Inventory & Order Management System

A full-stack inventory platform for small and mid-sized businesses. It tracks products and stock levels in real time, takes customer orders through fulfilment, manages suppliers and purchase orders, raises low-stock alerts automatically, and reports on sales and inventory value.

**Tech stack:** FastAPI · SQLAlchemy 2.0 · PostgreSQL · Alembic · React 18 + TypeScript · TanStack Query · Recharts · Docker Compose · GitHub Actions

![Dashboard](docs/screenshots/dashboard.png)

---

## Features

| Area | What it does |
| --- | --- |
| **Product management** | CRUD for products with SKU, category, supplier, cost and sale price, and margin. Search, filter, sort and paginate. Products used on past orders are archived instead of deleted. |
| **Stock tracking** | Every quantity change goes through one service and writes an audit row (`purchase`, `sale`, `adjustment`, `return`) with the running balance, user and reference. You can view stock history per product or across the whole catalog. |
| **Automatic low-stock alerts** | An alert opens when stock falls to the product's reorder level and closes on its own when stock is replenished. There is never more than one open alert per product, and a notification hook can be pointed at email or Slack. |
| **Order processing** | Sales orders move through a state machine: `pending → confirmed → shipped → delivered`, or `cancelled`. Stock is deducted on confirmation **atomically**, so if any line is short the whole order is rejected. Cancelling a confirmed order puts the stock back. |
| **Supplier management** | Supplier directory with contacts and lead times. Purchase orders move `draft → ordered → received`, and receiving one adds its stock. **One click drafts purchase orders from all open alerts**, grouped by supplier. Products already on order are skipped. |
| **Sales reports** | Revenue, gross profit, margin, order count, units and average order value for any date range. Includes a daily revenue chart, top products, revenue by category, inventory valuation at cost and retail, and **CSV export**. |
| **Admin dashboard** | KPI cards, a 30-day revenue trend, orders by status, recent orders and items that need restocking. |
| **Auth & roles** | JWT authentication with `admin` and `staff` roles. Deleting records and managing users are admin-only. |

### Screenshots

| | |
| --- | --- |
| ![Products](docs/screenshots/products.png) | ![Reports](docs/screenshots/reports.png) |
| **Products:** filter, sort, adjust stock, view history | **Reports:** sales KPIs, charts, valuation, CSV |
| ![Order detail](docs/screenshots/order-detail.png) | ![Alerts](docs/screenshots/alerts.png) |
| **Order detail:** fulfilment timeline and status actions | **Low-stock alerts:** one-click purchase orders |
| ![Purchase orders](docs/screenshots/purchase-orders.png) | ![Suppliers](docs/screenshots/suppliers.png) |
| **Purchase orders** | **Suppliers** |
| ![New order](docs/screenshots/new-order.png) | ![Stock movements](docs/screenshots/stock.png) |
| **New order** with live stock check | **Stock movement** audit trail |

---

## Quick start (Docker)

```bash
git clone <this-repo> && cd inventory-system
docker compose up --build
```

| Service | URL |
| --- | --- |
| Web app | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 (`inventory` / `inventory`) |

On first start the backend runs the migrations and seeds about 90 days of realistic demo data. That covers 34 products, 6 suppliers, around 450 orders, purchase orders and live low-stock alerts.

**Demo logins**

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@stockpilot.dev` | `admin1234` |
| Staff | `staff@stockpilot.dev` | `staff1234` |

To reset the data, run `docker compose down -v && docker compose up`.

## Local development

**Backend** (Python 3.12+, PostgreSQL running locally):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # edit DATABASE_URL if needed
alembic upgrade head
python seed.py                    # add --reset to start over
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

**Frontend** (Node 20+):

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173 (proxies /api to :8000)
```

## Tests

```bash
cd backend
pytest                                            # in-memory SQLite, about 20s
TEST_DATABASE_URL=postgresql+psycopg://inventory:inventory@localhost:5432/inventory_test pytest
```

There are 27 API-level tests. They cover auth and roles, product CRUD and validation, stock adjustments, how alerts open, resolve and avoid duplicates, order state transitions, atomic stock reservation, restocking on cancel, receiving purchase orders, drafting purchase orders from alerts, report math and CSV export. CI runs the suite against both SQLite and PostgreSQL and builds the frontend on every push.

---

## Architecture

```
inventory-system/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── models.py            # SQLAlchemy 2.0 typed ORM models
│   │   ├── schemas.py           # Pydantic v2 request/response models
│   │   ├── deps.py              # DB session, current user, admin guard
│   │   ├── core/                # settings (pydantic-settings), JWT + bcrypt
│   │   ├── routers/             # auth, products, stock, orders, purchase_orders,
│   │   │                        # suppliers, categories, alerts, reports, dashboard
│   │   └── services/
│   │       ├── inventory.py     # adjust_stock(): the single entry point for stock changes
│   │       ├── reports.py       # aggregate SQL for reports and dashboard
│   │       └── numbering.py     # SO-2026-00001 / PO-2026-00001 document numbers
│   ├── alembic/                 # migrations
│   ├── tests/
│   └── seed.py                  # 90-day business simulation
├── frontend/
│   └── src/
│       ├── api/                 # typed fetch client + TS types mirroring the API
│       ├── auth/                # auth context (JWT in localStorage)
│       ├── components/          # layout, modal, badges, line-item editor, toasts
│       └── pages/               # Dashboard, Products, Stock, Orders, PurchaseOrders,
│                                # Suppliers, Alerts, Reports, Login
├── docker-compose.yml           # postgres + api + nginx-served SPA
└── .github/workflows/ci.yml
```

### Design decisions

- **One path for stock changes.** Every change, whether it comes from an order, a purchase order or a manual adjustment, goes through `services.inventory.adjust_stock`. That one function guards against negative stock, writes the `StockMovement` audit row and re-checks the low-stock alert, so the alert logic can't drift out of sync with the stock level.
- **Transactions.** Confirming an order deducts stock for every line inside one transaction. If any line fails, the transaction rolls back and nothing is partially reserved.
- **Revenue is recognised at confirmation.** Reports count orders that are `confirmed`, `shipped` or `delivered`, dated by `confirmed_at`. Each order line stores its unit price and unit cost at the time of sale, so later price changes don't rewrite past margins.
- **Database-portable SQL.** Reports use plain SQLAlchemy aggregates, which lets the same test suite run on SQLite (fast, local) and PostgreSQL (CI and production).

### API overview

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/auth/login` | OAuth2 password login, returns a JWT |
| `GET` | `/api/dashboard` | KPIs, trend, recent orders, low-stock items |
| `GET/POST/PATCH/DELETE` | `/api/products` | Catalog with search, filters, sort and pagination |
| `POST` | `/api/products/{id}/stock` | Adjust stock (writes a movement and syncs alerts) |
| `GET` | `/api/products/{id}/movements` | Stock history for one product |
| `GET` | `/api/stock/movements` | Global audit trail |
| `GET/POST` | `/api/orders` · `PATCH /api/orders/{id}/status` | Sales orders and fulfilment |
| `GET/POST` | `/api/purchase-orders` · `PATCH …/{id}/status` | Restocking from suppliers |
| `POST` | `/api/purchase-orders/from-alerts` | Draft purchase orders for every open alert |
| `GET/POST/PATCH/DELETE` | `/api/suppliers` | Supplier directory |
| `GET` | `/api/alerts` · `/api/alerts/count` | Low-stock alerts |
| `GET` | `/api/reports/sales` · `/sales.csv` · `/inventory` | Reporting and export |

Interactive docs are at `/docs` when the API is running.

## Possible extensions

- Multi-warehouse stock with transfers between locations
- Email or Slack delivery for low-stock notifications (the hook is in `notify_low_stock`)
- Barcode scanning for receiving and stock counts
- Demand forecasting to suggest reorder levels from sales velocity

## License

MIT
