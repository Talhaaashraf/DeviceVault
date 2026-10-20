from conftest import login


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_login_success_returns_tokens(client):
    data = login(client, "admin")
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


def test_login_is_case_insensitive_on_email(client):
    res = client.post("/api/auth/login", json={"email": "ADMIN@company.com", "password": "Admin123!"})
    assert res.status_code == 200


def test_login_wrong_password(client):
    res = client.post("/api/auth/login", json={"email": "admin@company.com", "password": "wrong"})
    assert res.status_code == 401


def test_login_unknown_user(client):
    res = client.post("/api/auth/login", json={"email": "nobody@company.com", "password": "whatever"})
    assert res.status_code == 401


def test_me_returns_current_user(client, admin_h):
    res = client.get("/api/auth/me", headers=admin_h)
    assert res.status_code == 200
    assert res.json()["email"] == "admin@company.com"
    assert res.json()["role"] == "admin"


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_garbage_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert res.status_code == 401


def test_me_rejects_refresh_token_as_access(client):
    data = login(client, "viewer")
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['refresh_token']}"})
    assert res.status_code == 401


def test_refresh_rotates_tokens(client):
    data = login(client, "manager")
    res = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert res.status_code == 200
    new = res.json()
    assert new["refresh_token"] != data["refresh_token"]

    # The old refresh token is revoked after rotation
    reuse = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert reuse.status_code == 401

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new['access_token']}"})
    assert me.status_code == 200


def test_refresh_rejects_access_token(client):
    data = login(client, "manager")
    res = client.post("/api/auth/refresh", json={"refresh_token": data["access_token"]})
    assert res.status_code == 401


def test_logout_revokes_refresh_token(client):
    data = login(client, "viewer")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    res = client.post("/api/auth/logout", json={"refresh_token": data["refresh_token"]}, headers=headers)
    assert res.status_code == 204
    res = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert res.status_code == 401
