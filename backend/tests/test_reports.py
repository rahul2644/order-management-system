from datetime import date


def _sell(client, headers, product_id, qty):
    order = client.post("/api/orders", headers=headers, json={
        "customer_name": "Buyer", "items": [{"product_id": product_id, "quantity": qty}],
    }).json()
    client.patch(f"/api/orders/{order['id']}/status", json={"status": "confirmed"}, headers=headers)
    return order


def test_sales_report(client, admin_headers, make_product):
    p1 = make_product(unit_price="20.00", cost_price="8.00")
    p2 = make_product(unit_price="5.00", cost_price="2.00")
    _sell(client, admin_headers, p1["id"], 3)   # 60 revenue / 24 cost
    _sell(client, admin_headers, p2["id"], 10)  # 50 revenue / 20 cost
    # Pending orders aren't revenue.
    client.post("/api/orders", headers=admin_headers,
                json={"customer_name": "X", "items": [{"product_id": p1["id"], "quantity": 1}]})

    res = client.get("/api/reports/sales", headers=admin_headers)
    assert res.status_code == 200
    report = res.json()
    s = report["summary"]
    assert float(s["revenue"]) == 110.0
    assert float(s["gross_profit"]) == 66.0
    assert s["orders"] == 2
    assert s["units_sold"] == 13
    assert float(s["average_order_value"]) == 55.0
    assert len(report["daily"]) == 30
    today = [d for d in report["daily"] if d["date"] == date.today().isoformat()][0]
    assert float(today["revenue"]) == 110.0
    assert report["top_products"][0]["product_id"] == p1["id"]
    assert report["by_category"][0]["category"] == "Electronics"


def test_sales_csv_export(client, admin_headers, make_product):
    p = make_product()
    _sell(client, admin_headers, p["id"], 2)
    res = client.get("/api/reports/sales.csv", headers=admin_headers)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "Revenue" in res.text and p["sku"] in res.text


def test_inventory_report_and_dashboard(client, admin_headers, make_product):
    make_product(quantity=10, reorder_level=3, cost_price="4.00", unit_price="9.00")
    make_product(quantity=2, reorder_level=5, cost_price="1.00", unit_price="3.00")

    inv = client.get("/api/reports/inventory", headers=admin_headers).json()
    assert float(inv["cost_value"]) == 42.0
    assert float(inv["retail_value"]) == 96.0

    dash = client.get("/api/dashboard", headers=admin_headers).json()
    assert dash["total_products"] == 2
    assert dash["low_stock_count"] == 1
    assert dash["open_alerts"] == 1
    assert float(dash["inventory_value"]) == 42.0
    assert len(dash["revenue_trend"]) == 30


def test_invalid_date_range(client, admin_headers):
    res = client.get("/api/reports/sales", params={"start_date": "2026-05-01", "end_date": "2026-01-01"},
                     headers=admin_headers)
    assert res.status_code == 422
