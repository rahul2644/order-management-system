"""Populate the database with realistic demo data.

Usage:
    python seed.py           # seed only if the database is empty
    python seed.py --reset   # drop all data and reseed

Simulates ~90 days of business: opening stock, daily customer orders moving through
the fulfilment pipeline, and supplier purchase orders, all through the same
``adjust_stock`` service the API uses, so stock levels, movements and low-stock
alerts are internally consistent.
"""
import argparse
import random
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db import Base, SessionLocal, engine
from app.models import (
    Category,
    MovementType,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
    User,
    UserRole,
)
from app.services.inventory import adjust_stock

random.seed(42)
DAYS = 90

SUPPLIERS = [
    ("Northwind Electronics", "Priya Raman", "orders@northwind.example", "+1 415 555 0134", 5),
    ("Bluepeak Office Supply", "Marcus Lee", "sales@bluepeak.example", "+1 206 555 0199", 3),
    ("Evergreen Home Goods", "Sofia Alvarez", "hello@evergreen.example", "+1 503 555 0172", 10),
    ("Summit Outdoor Co.", "Daniel Okafor", "b2b@summit.example", "+1 303 555 0110", 14),
    ("Harbor Kitchenware", "Mei Chen", "wholesale@harbor.example", "+1 617 555 0145", 7),
    ("Atlas Fitness Supply", "Jonah Weiss", "trade@atlasfit.example", "+1 312 555 0168", 6),
]

# (sku, name, category, supplier index, cost, price, reorder level, reorder qty, popularity)
PRODUCTS = [
    ("EL-1001", "Wireless Mouse", "Electronics", 0, 8.50, 24.99, 25, 100, 9),
    ("EL-1002", "Mechanical Keyboard", "Electronics", 0, 38.00, 89.99, 15, 40, 6),
    ("EL-1003", "USB-C Hub 7-in-1", "Electronics", 0, 14.20, 39.99, 20, 60, 7),
    ("EL-1004", "27\" 4K Monitor", "Electronics", 0, 210.00, 379.00, 5, 15, 3),
    ("EL-1005", "Noise-Cancelling Headphones", "Electronics", 0, 72.00, 159.00, 10, 30, 5),
    ("EL-1006", "1080p Webcam", "Electronics", 0, 19.00, 54.99, 12, 40, 5),
    ("EL-1007", "Portable SSD 1TB", "Electronics", 0, 55.00, 109.00, 10, 30, 4),
    ("OF-2001", "A5 Hardcover Notebook", "Office", 1, 2.10, 8.99, 50, 200, 10),
    ("OF-2002", "Gel Pens (12 pack)", "Office", 1, 3.40, 11.49, 40, 150, 8),
    ("OF-2003", "Ergonomic Desk Chair", "Office", 1, 120.00, 249.00, 4, 10, 2),
    ("OF-2004", "Standing Desk Converter", "Office", 1, 85.00, 189.00, 5, 12, 2),
    ("OF-2005", "Desk Organizer Set", "Office", 1, 9.00, 27.99, 15, 50, 4),
    ("OF-2006", "Whiteboard 90x60cm", "Office", 1, 22.00, 54.00, 6, 20, 2),
    ("HG-3001", "Scented Soy Candle", "Home", 2, 4.50, 18.00, 30, 120, 7),
    ("HG-3002", "Linen Throw Blanket", "Home", 2, 16.00, 45.00, 12, 40, 4),
    ("HG-3003", "Ceramic Plant Pot", "Home", 2, 6.00, 21.00, 20, 60, 5),
    ("HG-3004", "LED Desk Lamp", "Home", 2, 13.00, 36.99, 15, 50, 5),
    ("HG-3005", "Cotton Bath Towel Set", "Home", 2, 18.00, 49.99, 10, 40, 3),
    ("OD-4001", "Insulated Water Bottle", "Outdoor", 3, 7.80, 29.99, 30, 120, 9),
    ("OD-4002", "Trekking Backpack 40L", "Outdoor", 3, 34.00, 89.00, 8, 25, 3),
    ("OD-4003", "Camping Hammock", "Outdoor", 3, 15.00, 44.99, 10, 30, 3),
    ("OD-4004", "Headlamp 300lm", "Outdoor", 3, 6.50, 22.99, 20, 60, 5),
    ("OD-4005", "2-Person Tent", "Outdoor", 3, 58.00, 139.00, 5, 15, 2),
    ("KT-5001", "Chef's Knife 8\"", "Kitchen", 4, 21.00, 64.99, 10, 30, 4),
    ("KT-5002", "Cast Iron Skillet 10\"", "Kitchen", 4, 14.00, 39.99, 12, 40, 4),
    ("KT-5003", "Pour-Over Coffee Set", "Kitchen", 4, 11.00, 34.99, 15, 45, 5),
    ("KT-5004", "Bamboo Cutting Board", "Kitchen", 4, 5.50, 19.99, 20, 60, 5),
    ("KT-5005", "Glass Food Containers (10)", "Kitchen", 4, 12.00, 32.99, 15, 50, 4),
    ("FT-6001", "Yoga Mat 6mm", "Fitness", 5, 9.00, 32.00, 20, 60, 6),
    ("FT-6002", "Adjustable Dumbbells 24kg", "Fitness", 5, 95.00, 219.00, 4, 10, 2),
    ("FT-6003", "Resistance Bands Set", "Fitness", 5, 5.00, 19.99, 25, 80, 6),
    ("FT-6004", "Foam Roller", "Fitness", 5, 6.00, 24.99, 15, 45, 4),
    ("FT-6005", "Jump Rope Pro", "Fitness", 5, 3.00, 14.99, 20, 60, 4),
    ("FT-6006", "Kettlebell 16kg", "Fitness", 5, 26.00, 64.00, 6, 20, 2),
]

FIRST = ["Olivia", "Liam", "Aarav", "Emma", "Noah", "Ava", "Mateo", "Zara", "Ethan", "Mia",
         "Lucas", "Isla", "Arjun", "Chloe", "Kenji", "Amara", "Leo", "Nora", "Ravi", "Hana"]
LAST = ["Patel", "Smith", "Garcia", "Kim", "Nguyen", "Brown", "Rossi", "Khan", "Silva", "Müller",
        "Johnson", "Tanaka", "Lopez", "Singh", "Martin", "Okafor", "Chen", "Davis", "Ali", "Moreau"]


def at(day_offset: int, hour: int | None = None) -> datetime:
    now = datetime.now(timezone.utc)
    day = now.date() - timedelta(days=day_offset)
    when = datetime.combine(day, time(hour if hour is not None else random.randint(8, 19),
                                      random.randint(0, 59)), tzinfo=timezone.utc)
    if when > now:  # keep "today" in the past
        when = now - timedelta(minutes=random.randint(5, max(6, now.hour * 50)))
    return when


def seed(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    db = SessionLocal()
    if db.scalar(select(User).limit(1)):
        print("Database already seeded; use --reset to start over.")
        return

    admin = User(email="admin@stockpilot.dev", full_name="Alex Morgan", role=UserRole.ADMIN,
                 hashed_password=hash_password("admin1234"))
    staff = User(email="staff@stockpilot.dev", full_name="Sam Taylor", role=UserRole.STAFF,
                 hashed_password=hash_password("staff1234"))
    db.add_all([admin, staff])

    suppliers = [
        Supplier(name=n, contact_name=c, email=e, phone=p, lead_time_days=lt,
                 address=f"{random.randint(100, 9999)} Commerce Way", created_at=at(DAYS + 5))
        for n, c, e, p, lt in SUPPLIERS
    ]
    db.add_all(suppliers)

    categories = {name: Category(name=name) for name in sorted({p[2] for p in PRODUCTS})}
    db.add_all(categories.values())
    db.flush()

    products: list[tuple[Product, int]] = []
    for sku, name, cat, sup, cost, price, rl, rq, pop in PRODUCTS:
        product = Product(
            sku=sku, name=name, category=categories[cat], supplier=suppliers[sup],
            cost_price=Decimal(str(cost)), unit_price=Decimal(str(price)),
            reorder_level=rl, reorder_quantity=rq, quantity=0, created_at=at(DAYS + 1),
            description=f"{name} — part of our {cat.lower()} range.",
        )
        db.add(product)
        db.flush()
        opening = int(rq * random.uniform(1.6, 2.6))
        adjust_stock(db, product, opening, MovementType.ADJUSTMENT, note="Opening stock",
                     user_id=admin.id, occurred_at=at(DAYS + 1, 9))
        products.append((product, pop))
    db.flush()

    weights = [pop for _, pop in products]
    pending_pos: list[tuple[PurchaseOrder, int]] = []  # (po, day it arrives)
    so_count = po_count = 0

    for day in range(DAYS, -1, -1):
        # Receive purchase orders that arrive today.
        for po, arrival in list(pending_pos):
            if arrival >= day:
                when = at(day, 10)
                for item in po.items:
                    adjust_stock(db, item.product, item.quantity, MovementType.PURCHASE,
                                 reference=po.po_number, user_id=staff.id, occurred_at=when)
                po.status, po.received_at = PurchaseOrderStatus.RECEIVED, when
                pending_pos.remove((po, arrival))

        # Customer orders: busier on weekdays, growing slightly over time.
        weekday = (datetime.now(timezone.utc).date() - timedelta(days=day)).weekday()
        n_orders = random.randint(2, 5) + (1 if weekday < 5 else 0) + (DAYS - day) // 40
        for _ in range(n_orders):
            created = at(day)
            so_count += 1
            order = Order(
                order_number=f"SO-{created.year}-{so_count:05d}",
                customer_name=f"{random.choice(FIRST)} {random.choice(LAST)}",
                created_by_id=random.choice([admin.id, staff.id]),
                created_at=created,
            )
            order.customer_email = order.customer_name.lower().replace(" ", ".").replace("ü", "u") + "@example.com"
            picks = {p.id: p for p, _ in random.choices(products, weights=weights, k=random.randint(1, 4))}
            for product in picks.values():
                order.items.append(OrderItem(product=product, quantity=random.randint(1, 4),
                                             unit_price=product.unit_price, unit_cost=product.cost_price))
            db.add(order)

            # Recent orders are still moving through the pipeline.
            if random.random() < {0: 0.5, 1: 0.2}.get(day, 0):
                continue  # stays pending
            if random.random() < 0.05:
                order.status = OrderStatus.CANCELLED
                continue
            if any(i.product.quantity < i.quantity for i in order.items):
                continue  # can't fulfil yet: leave pending
            confirmed = min(created + timedelta(minutes=random.randint(5, 90)),
                            datetime.now(timezone.utc) - timedelta(minutes=1))
            for item in order.items:
                adjust_stock(db, item.product, -item.quantity, MovementType.SALE,
                             reference=order.order_number, user_id=staff.id, occurred_at=confirmed)
            order.confirmed_at = confirmed
            order.status = (OrderStatus.CONFIRMED if day <= 2 else
                            OrderStatus.SHIPPED if day <= 5 else OrderStatus.DELIVERED)

        # Weekly restock run: order everything at/below the reorder level, except the
        # last two weeks so the demo has live low-stock alerts to act on.
        if weekday == 0 and day > 14:
            by_supplier: dict[int, list[Product]] = {}
            for product, _ in products:
                if product.quantity <= product.reorder_level * 1.5:
                    by_supplier.setdefault(product.supplier_id, []).append(product)
            for sup_id, items in by_supplier.items():
                po_count += 1
                created = at(day, 9)
                supplier = next(s for s in suppliers if s.id == sup_id)
                po = PurchaseOrder(po_number=f"PO-{created.year}-{po_count:05d}", supplier=supplier,
                                   status=PurchaseOrderStatus.ORDERED, created_at=created,
                                   expected_date=(created + timedelta(days=supplier.lead_time_days)).date())
                for product in items:
                    po.items.append(PurchaseOrderItem(product=product, quantity=product.reorder_quantity * 2,
                                                      unit_cost=product.cost_price))
                db.add(po)
                pending_pos.append((po, day - supplier.lead_time_days))
        db.flush()

    # One draft PO waiting for approval.
    po_count += 1
    supplier = suppliers[1]
    draft = PurchaseOrder(po_number=f"PO-{datetime.now().year}-{po_count:05d}", supplier=supplier,
                          status=PurchaseOrderStatus.DRAFT, created_at=at(0, 9),
                          notes="Back-to-school stock up")
    for product in supplier.products[:3]:
        draft.items.append(PurchaseOrderItem(product=product, quantity=product.reorder_quantity,
                                             unit_cost=product.cost_price))
    db.add(draft)
    db.commit()

    low = sum(1 for p, _ in products if p.is_low_stock)
    print(f"Seeded {len(products)} products, {len(suppliers)} suppliers, {so_count} sales orders, "
          f"{po_count} purchase orders; {low} products currently low on stock.")
    print("Log in with admin@stockpilot.dev / admin1234 or staff@stockpilot.dev / staff1234")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="drop all tables and reseed")
    seed(parser.parse_args().reset)
