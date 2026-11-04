"""Test fixtures.

Runs against an in-memory SQLite database by default. Set TEST_DATABASE_URL to a
PostgreSQL URL to run the same suite against Postgres (as CI does).
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import Category, Supplier, User, UserRole

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")

if TEST_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
else:
    engine = create_engine(TEST_DATABASE_URL)

TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(db, email: str, role: UserRole) -> User:
    user = User(email=email, full_name=email.split("@")[0].title(), role=role,
                hashed_password=hash_password("password123"))
    db.add(user)
    db.commit()
    return user


def _login(client, email: str) -> dict[str, str]:
    res = client.post("/api/auth/login", data={"username": email, "password": "password123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client, db):
    _make_user(db, "admin@test.com", UserRole.ADMIN)
    return _login(client, "admin@test.com")


@pytest.fixture()
def staff_headers(client, db):
    _make_user(db, "staff@test.com", UserRole.STAFF)
    return _login(client, "staff@test.com")


@pytest.fixture()
def supplier(db) -> Supplier:
    s = Supplier(name="Acme Supplies", email="sales@acme.test", lead_time_days=5)
    db.add(s)
    db.commit()
    return s


@pytest.fixture()
def category(db) -> Category:
    c = Category(name="Electronics")
    db.add(c)
    db.commit()
    return c


@pytest.fixture()
def make_product(client, admin_headers, supplier, category):
    counter = {"n": 0}

    def _make(quantity: int = 100, reorder_level: int = 10, **overrides) -> dict:
        counter["n"] += 1
        payload = {
            "sku": f"SKU-{counter['n']:03d}",
            "name": f"Product {counter['n']}",
            "unit_price": "25.00",
            "cost_price": "10.00",
            "quantity": quantity,
            "reorder_level": reorder_level,
            "reorder_quantity": 40,
            "supplier_id": supplier.id,
            "category_id": category.id,
            **overrides,
        }
        res = client.post("/api/products", json=payload, headers=admin_headers)
        assert res.status_code == 201, res.text
        return res.json()

    return _make
