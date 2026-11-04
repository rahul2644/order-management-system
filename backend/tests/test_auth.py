def test_login_and_me(client, admin_headers):
    res = client.get("/api/auth/me", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "admin@test.com"
    assert res.json()["role"] == "admin"


def test_login_rejects_bad_password(client, admin_headers):
    res = client.post("/api/auth/login", data={"username": "admin@test.com", "password": "wrong"})
    assert res.status_code == 401


def test_protected_routes_require_token(client):
    assert client.get("/api/products").status_code == 401
    assert client.get("/api/dashboard", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_only_admin_can_create_users(client, admin_headers, staff_headers):
    payload = {"email": "new@test.com", "full_name": "New User", "password": "supersecret"}
    assert client.post("/api/auth/users", json=payload, headers=staff_headers).status_code == 403
    res = client.post("/api/auth/users", json=payload, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["role"] == "staff"
