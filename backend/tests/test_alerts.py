def _open_alerts(client, headers):
    return client.get("/api/alerts", headers=headers).json()


def test_alert_raised_when_stock_drops_below_reorder_level(client, admin_headers, make_product):
    product = make_product(quantity=15, reorder_level=10)
    assert _open_alerts(client, admin_headers) == []

    client.post(f"/api/products/{product['id']}/stock", json={"change": -6}, headers=admin_headers)
    alerts = _open_alerts(client, admin_headers)
    assert len(alerts) == 1
    assert alerts[0]["product_id"] == product["id"]
    assert alerts[0]["quantity_at_trigger"] == 9


def test_no_duplicate_alerts(client, admin_headers, make_product):
    product = make_product(quantity=8, reorder_level=10)
    client.post(f"/api/products/{product['id']}/stock", json={"change": -3}, headers=admin_headers)
    assert len(_open_alerts(client, admin_headers)) == 1


def test_alert_resolved_on_restock(client, admin_headers, make_product):
    product = make_product(quantity=5, reorder_level=10)
    assert len(_open_alerts(client, admin_headers)) == 1

    client.post(f"/api/products/{product['id']}/stock",
                json={"change": 50, "movement_type": "purchase"}, headers=admin_headers)
    assert _open_alerts(client, admin_headers) == []
    resolved = client.get("/api/alerts", params={"status": "resolved"}, headers=admin_headers).json()
    assert len(resolved) == 1
    assert resolved[0]["resolved_at"] is not None


def test_changing_reorder_level_triggers_alert(client, admin_headers, make_product):
    product = make_product(quantity=20, reorder_level=10)
    client.patch(f"/api/products/{product['id']}", json={"reorder_level": 25}, headers=admin_headers)
    assert len(_open_alerts(client, admin_headers)) == 1
    assert client.get("/api/alerts/count", headers=admin_headers).json() == {"open": 1}


def test_single_alert_when_threshold_crossed_twice_in_one_transaction(client, admin_headers, make_product):
    # Two lines for the same product: both deductions happen before the commit.
    product = make_product(quantity=12, reorder_level=10)
    order = client.post("/api/orders", headers=admin_headers, json={
        "customer_name": "Dup Lines",
        "items": [{"product_id": product["id"], "quantity": 3}, {"product_id": product["id"], "quantity": 2}],
    }).json()
    client.patch(f"/api/orders/{order['id']}/status", json={"status": "confirmed"}, headers=admin_headers)
    assert len(_open_alerts(client, admin_headers)) == 1

    client.post(f"/api/products/{product['id']}/stock", json={"change": 50}, headers=admin_headers)
    assert _open_alerts(client, admin_headers) == []
