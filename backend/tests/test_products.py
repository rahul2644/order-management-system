def test_create_and_list_products(client, admin_headers, make_product):
    make_product(name="Wireless Mouse")
    make_product(name="USB-C Hub")

    res = client.get("/api/products", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert {p["name"] for p in body["items"]} == {"Wireless Mouse", "USB-C Hub"}
    assert body["items"][0]["supplier_name"] == "Acme Supplies"

    res = client.get("/api/products", params={"q": "mouse"}, headers=admin_headers)
    assert [p["name"] for p in res.json()["items"]] == ["Wireless Mouse"]


def test_duplicate_sku_rejected(client, admin_headers, make_product):
    product = make_product()
    payload = {"sku": product["sku"], "name": "Dup", "unit_price": "1", "cost_price": "1"}
    assert client.post("/api/products", json=payload, headers=admin_headers).status_code == 409


def test_opening_stock_is_recorded_as_movement(client, admin_headers, make_product):
    product = make_product(quantity=30)
    res = client.get(f"/api/products/{product['id']}/movements", headers=admin_headers)
    movements = res.json()
    assert len(movements) == 1
    assert movements[0]["change"] == 30
    assert movements[0]["quantity_after"] == 30


def test_stock_adjustment(client, admin_headers, make_product):
    product = make_product(quantity=20)
    url = f"/api/products/{product['id']}/stock"

    res = client.post(url, json={"change": -5, "note": "Damaged"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["quantity"] == 15

    res = client.post(url, json={"change": -100}, headers=admin_headers)
    assert res.status_code == 409
    assert client.get(f"/api/products/{product['id']}", headers=admin_headers).json()["quantity"] == 15


def test_low_stock_filter(client, admin_headers, make_product):
    make_product(quantity=5, reorder_level=10)
    make_product(quantity=50, reorder_level=10)
    res = client.get("/api/products", params={"low_stock": True}, headers=admin_headers)
    assert res.json()["total"] == 1


def test_staff_cannot_delete(client, staff_headers, admin_headers, make_product):
    product = make_product()
    assert client.delete(f"/api/products/{product['id']}", headers=staff_headers).status_code == 403
    assert client.delete(f"/api/products/{product['id']}", headers=admin_headers).status_code == 204
