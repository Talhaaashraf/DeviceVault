import uuid


def _new_user_payload(role: str = "viewer") -> dict:
    suffix = uuid.uuid4().hex[:8]
    return {
        "full_name": f"Test User {suffix}",
        "email": f"user.{suffix}@company.com",
        "role": role,
        "department": "QA",
        "password": "Password123!",
    }


def test_list_users_admin_only(client, admin_h, manager_h, viewer_h):
    res = client.get("/api/users", headers=admin_h)
    assert res.status_code == 200
    emails = {u["email"] for u in res.json()}
    assert {"admin@company.com", "manager@company.com", "viewer@company.com"} <= emails

    assert client.get("/api/users", headers=manager_h).status_code == 403
    assert client.get("/api/users", headers=viewer_h).status_code == 403


def test_list_assignees_manager_and_admin(client, admin_h, manager_h, viewer_h):
    assert client.get("/api/users/assignees", headers=admin_h).status_code == 200
    res = client.get("/api/users/assignees", headers=manager_h)
    assert res.status_code == 200
    assert all("email" in u for u in res.json())
    assert client.get("/api/users/assignees", headers=viewer_h).status_code == 403


def test_create_user_and_login(client, admin_h):
    payload = _new_user_payload("manager")
    res = client.post("/api/users", json=payload, headers=admin_h)
    assert res.status_code == 201, res.text
    assert res.json()["role"] == "manager"
    assert res.json()["is_active"] is True

    login = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 200


def test_create_user_duplicate_email(client, admin_h):
    payload = _new_user_payload()
    assert client.post("/api/users", json=payload, headers=admin_h).status_code == 201
    payload["email"] = payload["email"].upper()
    assert client.post("/api/users", json=payload, headers=admin_h).status_code == 409


def test_create_user_validation(client, admin_h):
    payload = _new_user_payload()
    payload["password"] = "short"
    assert client.post("/api/users", json=payload, headers=admin_h).status_code == 422


def test_create_user_forbidden_for_manager(client, manager_h):
    assert client.post("/api/users", json=_new_user_payload(), headers=manager_h).status_code == 403


def test_update_user_fields_and_password(client, admin_h):
    payload = _new_user_payload()
    user = client.post("/api/users", json=payload, headers=admin_h).json()

    res = client.patch(
        f"/api/users/{user['id']}",
        json={"full_name": "Renamed User", "department": "Ops", "password": "NewPassword456!"},
        headers=admin_h,
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Renamed User"
    assert res.json()["department"] == "Ops"

    old = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert old.status_code == 401
    new = client.post("/api/auth/login", json={"email": payload["email"], "password": "NewPassword456!"})
    assert new.status_code == 200


def test_deactivated_user_cannot_login(client, admin_h):
    payload = _new_user_payload()
    user = client.post("/api/users", json=payload, headers=admin_h).json()
    res = client.patch(f"/api/users/{user['id']}", json={"is_active": False}, headers=admin_h)
    assert res.status_code == 200
    login = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 403


def test_update_missing_user(client, admin_h):
    res = client.patch(f"/api/users/{uuid.uuid4()}", json={"full_name": "x"}, headers=admin_h)
    assert res.status_code == 404


def test_delete_user_clears_assignments(client, admin_h, create_device):
    user = client.post("/api/users", json=_new_user_payload(), headers=admin_h).json()
    device = create_device(assigned_user_id=user["id"])
    assert device["assigned_user_id"] == user["id"]

    assert client.delete(f"/api/users/{user['id']}", headers=admin_h).status_code == 204

    refreshed = client.get(f"/api/devices/{device['id']}", headers=admin_h).json()
    assert refreshed["assigned_user_id"] is None
    history = client.get(f"/api/devices/{device['id']}/history", headers=admin_h)
    assert history.status_code == 200


def test_admin_cannot_delete_self(client, admin_h):
    me = client.get("/api/auth/me", headers=admin_h).json()
    assert client.delete(f"/api/users/{me['id']}", headers=admin_h).status_code == 400


def test_delete_missing_user(client, admin_h):
    assert client.delete(f"/api/users/{uuid.uuid4()}", headers=admin_h).status_code == 404


def test_delete_user_with_requests_tickets_and_audits(client, admin_h, create_device):
    payload = _new_user_payload("manager")
    user = client.post("/api/users", json=payload, headers=admin_h).json()
    tok = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]}).json()
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    device = create_device()

    req = client.post("/api/management/requests", headers=h, json={
        "device_type": "phone", "project_name": "P", "reason": "Testing delete"}).json()
    ticket = client.post("/api/management/maintenance", headers=h,
                         json={"device_id": device["id"], "issue_title": "Broken port"}).json()
    audit = client.post("/api/management/audits", headers=h,
                        json={"device_id": device["id"], "audit_cycle": "DEL-TEST"}).json()

    assert client.delete(f"/api/users/{user['id']}", headers=admin_h).status_code == 204

    # The deleted user's own requests go away with them; nothing can be fulfilled for a missing user
    requests = client.get("/api/management/requests", headers=admin_h).json()
    assert all(r["id"] != req["id"] for r in requests)

    # Tickets and audits they recorded are kept and re-attributed to the acting admin
    admin = client.get("/api/auth/me", headers=admin_h).json()
    tickets = {t["id"]: t for t in client.get("/api/management/maintenance", headers=admin_h).json()}
    assert tickets[ticket["id"]]["reported_by"]["id"] == admin["id"]
    audits = client.get("/api/management/audits", params={"cycle": "DEL-TEST"}, headers=admin_h).json()
    assert audits[0]["id"] == audit["id"] and audits[0]["auditor"]["id"] == admin["id"]


def test_admin_cannot_lock_themselves_out(client, admin_h):
    me = client.get("/api/auth/me", headers=admin_h).json()
    assert client.patch(f"/api/users/{me['id']}", json={"is_active": False}, headers=admin_h).status_code == 400
    assert client.patch(f"/api/users/{me['id']}", json={"role": "viewer"}, headers=admin_h).status_code == 400
    assert client.patch(f"/api/users/{me['id']}", json={"department": "IT"}, headers=admin_h).status_code == 200


def test_password_change_and_deactivation_revoke_sessions(client, admin_h):
    for change in ({"password": "Another789!"}, {"is_active": False}):
        payload = _new_user_payload()
        user = client.post("/api/users", json=payload, headers=admin_h).json()
        tok = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]}).json()
        assert client.patch(f"/api/users/{user['id']}", json=change, headers=admin_h).status_code == 200
        assert client.post("/api/auth/refresh", json={"refresh_token": tok["refresh_token"]}).status_code == 401
