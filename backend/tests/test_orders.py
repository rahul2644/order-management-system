def _create_order(client, headers, *lines):
    payload = {
        "customer_name": "Jane Doe",
        "customer_email": "jane@example.com",
        "items": [{"product_id": pid, "quantity": qty} for pid, qty in lines],
    }
    res = client.post("/api/orders", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _qty(client, headers, product_id):
    return client.get(f"/api/products/{product_id}", headers=headers).json()["quantity"]


def _set_status(client, headers, order_id, status):
    return client.patch(f"/api/orders/{order_id}/status", json={"status": status}, headers=headers)


def test_create_order_computes_total_and_number(client, admin_headers, make_product):
    p = make_product(unit_price="12.50")
    order = _create_order(client, admin_headers, (p["id"], 4))
    assert order["status"] == "pending"
    assert order["order_number"].startswith("SO-")
    assert float(order["total"]) == 50.0
    # Pending orders don't touch stock.
    assert _qty(client, admin_headers, p["id"]) == 100


def test_confirm_deducts_stock(client, admin_headers, make_product):
    p1, p2 = make_product(quantity=10), make_product(quantity=10)
    order = _create_order(client, admin_headers, (p1["id"], 3), (p2["id"], 7))
    res = _set_status(client, admin_headers, order["id"], "confirmed")
    assert res.status_code == 200
    assert res.json()["confirmed_at"] is not None
    assert _qty(client, admin_headers, p1["id"]) == 7
    assert _qty(client, admin_headers, p2["id"]) == 3


def test_confirm_is_atomic_when_stock_insufficient(client, admin_headers, make_product):
    p1, p2 = make_product(quantity=10), make_product(quantity=2)
    order = _create_order(client, admin_headers, (p1["id"], 5), (p2["id"], 5))
    res = _set_status(client, admin_headers, order["id"], "confirmed")
    assert res.status_code == 409
    assert _qty(client, admin_headers, p1["id"]) == 10
    assert _qty(client, admin_headers, p2["id"]) == 2
    assert client.get(f"/api/orders/{order['id']}", headers=admin_headers).json()["status"] == "pending"


def test_cancel_confirmed_order_restocks(client, admin_headers, make_product):
    p = make_product(quantity=10)
    order = _create_order(client, admin_headers, (p["id"], 4))
    _set_status(client, admin_headers, order["id"], "confirmed")
    assert _qty(client, admin_headers, p["id"]) == 6
    assert _set_status(client, admin_headers, order["id"], "cancelled").status_code == 200
    assert _qty(client, admin_headers, p["id"]) == 10


def test_invalid_transitions_rejected(client, admin_headers, make_product):
    p = make_product()
    order = _create_order(client, admin_headers, (p["id"], 1))
    assert _set_status(client, admin_headers, order["id"], "shipped").status_code == 409
    for status in ("confirmed", "shipped", "delivered"):
        assert _set_status(client, admin_headers, order["id"], status).status_code == 200
    assert _set_status(client, admin_headers, order["id"], "cancelled").status_code == 409


def test_order_list_filters(client, admin_headers, make_product):
    p = make_product()
    a = _create_order(client, admin_headers, (p["id"], 1))
    _create_order(client, admin_headers, (p["id"], 1))
    _set_status(client, admin_headers, a["id"], "confirmed")
    res = client.get("/api/orders", params={"status": "pending"}, headers=admin_headers).json()
    assert res["total"] == 1
