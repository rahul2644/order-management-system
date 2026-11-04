def test_receive_purchase_order_adds_stock_and_resolves_alert(client, admin_headers, make_product, supplier):
    p = make_product(quantity=3, reorder_level=10)
    assert len(client.get("/api/alerts", headers=admin_headers).json()) == 1

    res = client.post("/api/purchase-orders", headers=admin_headers, json={
        "supplier_id": supplier.id,
        "items": [{"product_id": p["id"], "quantity": 50}],
    })
    assert res.status_code == 201
    po = res.json()
    assert po["po_number"].startswith("PO-")
    assert float(po["total"]) == 500.0

    url = f"/api/purchase-orders/{po['id']}/status"
    # Must be ordered before it can be received.
    assert client.patch(url, json={"status": "received"}, headers=admin_headers).status_code == 409
    assert client.patch(url, json={"status": "ordered"}, headers=admin_headers).status_code == 200
    res = client.patch(url, json={"status": "received"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["received_at"] is not None

    assert client.get(f"/api/products/{p['id']}", headers=admin_headers).json()["quantity"] == 53
    assert client.get("/api/alerts", headers=admin_headers).json() == []


def test_generate_purchase_orders_from_alerts(client, admin_headers, make_product):
    low1 = make_product(quantity=2, reorder_level=10)
    low2 = make_product(quantity=0, reorder_level=5)
    make_product(quantity=100)

    res = client.post("/api/purchase-orders/from-alerts", headers=admin_headers)
    assert res.status_code == 201
    pos = res.json()
    assert len(pos) == 1  # both low products share one supplier
    lines = {i["product_id"]: i["quantity"] for i in pos[0]["items"]}
    assert set(lines) == {low1["id"], low2["id"]}
    assert lines[low1["id"]] == 48  # shortfall (8) + reorder quantity (40)

    # Running again doesn't duplicate products already on an open PO.
    assert client.post("/api/purchase-orders/from-alerts", headers=admin_headers).json() == []
