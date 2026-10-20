import uuid

from app.core.config import os_freshness_category


def test_list_devices_includes_seed_data(client, viewer_h):
    res = client.get("/api/devices", headers=viewer_h)
    assert res.status_code == 200
    assert len(res.json()) >= 7


def test_list_devices_requires_auth(client):
    assert client.get("/api/devices").status_code == 401


def test_create_get_device(client, admin_h, viewer_h, create_device):
    device = create_device(mac_address="aa:bb:cc:dd:ee:01")
    assert device["mac_address"] == "AA:BB:CC:DD:EE:01"  # normalized to upper case
    res = client.get(f"/api/devices/{device['id']}", headers=viewer_h)
    assert res.status_code == 200
    assert res.json()["serial_number"] == device["serial_number"]


def test_manager_can_create_device(client, manager_h, device_payload):
    res = client.post("/api/devices", json=device_payload(), headers=manager_h)
    assert res.status_code == 201


def test_viewer_cannot_create_device(client, viewer_h, device_payload):
    res = client.post("/api/devices", json=device_payload(), headers=viewer_h)
    assert res.status_code == 403


def test_create_device_requires_imei_when_cellular(client, admin_h, device_payload):
    res = client.post("/api/devices", json=device_payload(imei_number=None), headers=admin_h)
    assert res.status_code == 422


def test_create_device_rejects_imei_when_wifi_only(client, admin_h, device_payload):
    res = client.post("/api/devices", json=device_payload(is_cellular=False), headers=admin_h)
    assert res.status_code == 422


def test_create_device_rejects_bad_mac_and_imei(client, admin_h, device_payload):
    assert client.post("/api/devices", json=device_payload(mac_address="ZZ:ZZ:ZZ:ZZ:ZZ:ZZ"), headers=admin_h).status_code == 422
    assert client.post("/api/devices", json=device_payload(imei_number="12345"), headers=admin_h).status_code == 422


def test_create_device_duplicate_serial(client, admin_h, device_payload, create_device):
    device = create_device()
    dup = device_payload(serial_number=device["serial_number"])
    assert client.post("/api/devices", json=dup, headers=admin_h).status_code == 409


def test_create_device_with_unknown_assignee(client, admin_h, device_payload):
    res = client.post("/api/devices", json=device_payload(assigned_user_id=str(uuid.uuid4())), headers=admin_h)
    assert res.status_code == 400


def test_filter_and_search_devices(client, admin_h, create_device):
    device = create_device(device_type="smartwatch", os_type="wear_os", is_cellular=False, imei_number=None,
                           company="Filter Team")
    by_type = client.get("/api/devices", params={"device_type": "smartwatch"}, headers=admin_h).json()
    assert all(d["device_type"] == "smartwatch" for d in by_type)
    assert any(d["id"] == device["id"] for d in by_type)

    by_os = client.get("/api/devices", params={"os_type": "wear_os"}, headers=admin_h).json()
    assert all(d["os_type"] == "wear_os" for d in by_os)

    by_company = client.get("/api/devices", params={"company": "filter team"}, headers=admin_h).json()
    assert [d["id"] for d in by_company] == [device["id"]]

    by_q = client.get("/api/devices", params={"q": device["serial_number"]}, headers=admin_h).json()
    assert [d["id"] for d in by_q] == [device["id"]]

    unassigned = client.get("/api/devices", params={"unassigned": "true"}, headers=admin_h).json()
    assert all(d["assigned_user_id"] is None for d in unassigned)

    by_status = client.get("/api/devices", params={"status": "lost"}, headers=admin_h).json()
    assert all(d["status"] == "lost" for d in by_status)


def test_get_missing_device(client, admin_h):
    assert client.get(f"/api/devices/{uuid.uuid4()}", headers=admin_h).status_code == 404


def test_update_device_and_assignment_history(client, admin_h, manager_h, create_device):
    device = create_device()
    manager = client.get("/api/auth/me", headers=manager_h).json()

    res = client.patch(
        f"/api/devices/{device['id']}",
        json={"assigned_user_id": manager["id"], "issued_to": "Field Engineer", "status": "active",
              "project_name": "Pilot", "notes": "Handed over"},
        headers=manager_h,
    )
    assert res.status_code == 200, res.text
    updated = res.json()
    assert updated["assigned_user"]["id"] == manager["id"]
    assert updated["issued_to"] == "Field Engineer"

    history = client.get(f"/api/devices/{device['id']}/history", headers=admin_h).json()
    assert len(history) == 2  # one for the user assignment, one for issued_to
    assert any(h["to_issued_to"] == "Field Engineer" for h in history)

    cleared = client.patch(f"/api/devices/{device['id']}", json={"clear_assigned_user": True}, headers=manager_h)
    assert cleared.status_code == 200
    assert cleared.json()["assigned_user_id"] is None


def test_update_device_cellular_rules(client, admin_h, create_device):
    device = create_device()
    # Switching to Wi-Fi only without clearing the IMEI is rejected
    res = client.patch(f"/api/devices/{device['id']}", json={"is_cellular": False}, headers=admin_h)
    assert res.status_code == 422
    res = client.patch(f"/api/devices/{device['id']}", json={"is_cellular": False, "clear_imei": True}, headers=admin_h)
    assert res.status_code == 200
    assert res.json()["imei_number"] is None


def test_update_device_clear_dates(client, admin_h, create_device):
    device = create_device(purchase_date="2024-01-01", date_of_return="2030-01-01")
    res = client.patch(
        f"/api/devices/{device['id']}",
        json={"clear_purchase_date": True, "clear_date_of_return": True},
        headers=admin_h,
    )
    assert res.status_code == 200
    assert res.json()["purchase_date"] is None
    assert res.json()["date_of_return"] is None


def test_update_device_duplicate_serial(client, admin_h, create_device):
    first = create_device()
    second = create_device()
    res = client.patch(f"/api/devices/{second['id']}", json={"serial_number": first["serial_number"]}, headers=admin_h)
    assert res.status_code == 409


def test_viewer_cannot_update_device(client, viewer_h, create_device):
    device = create_device()
    assert client.patch(f"/api/devices/{device['id']}", json={"notes": "x"}, headers=viewer_h).status_code == 403


def test_delete_device_admin_only(client, admin_h, manager_h, create_device):
    device = create_device()
    assert client.delete(f"/api/devices/{device['id']}", headers=manager_h).status_code == 403
    assert client.delete(f"/api/devices/{device['id']}", headers=admin_h).status_code == 204
    assert client.get(f"/api/devices/{device['id']}", headers=admin_h).status_code == 404
    assert client.delete(f"/api/devices/{device['id']}", headers=admin_h).status_code == 404


def test_history_for_missing_device(client, admin_h):
    assert client.get(f"/api/devices/{uuid.uuid4()}/history", headers=admin_h).status_code == 404


def test_dashboard_summary(client, viewer_h):
    res = client.get("/api/dashboard/summary", headers=viewer_h)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_devices"] == data["allocated_devices"] + data["unassigned_devices"]
    assert data["apple_count"] + data["android_count"] == data["total_devices"]
    assert data["cellular_count"] + data["wifi_only_count"] == data["total_devices"]
    assert sum(data["by_status"].values()) == data["total_devices"]
    assert set(data["by_category"]) == {"iPhone", "iPad", "Android Phone", "Android Tablet", "Smartwatch"}
    assert data["pending_requests_count"] >= 1  # seeded request
    assert data["active_repairs_count"] >= 1  # seeded maintenance ticket
    assert data["overdue_returns_count"] >= 1  # seeded overdue device
    assert {a["type"] for a in data["urgent_alerts"]} >= {"overdue", "request", "maintenance"}
    assert data["in_stock"]["count"] == len(data["in_stock"]["list"])


def test_os_freshness_category():
    assert os_freshness_category("ios", "18.1") == "Latest"
    assert os_freshness_category("ios", "17") == "Recent"
    assert os_freshness_category("android", "10") == "Outdated"
    assert os_freshness_category("android", "beta") == "Unknown"
    assert os_freshness_category("symbian", "3") == "Unknown"
    assert os_freshness_category(None, None) == "Unknown"


def test_delete_device_removes_dependent_records(client, admin_h, viewer_h, create_device):
    device = create_device()
    ticket = client.post("/api/management/maintenance", headers=admin_h,
                         json={"device_id": device["id"], "issue_title": "Battery swelling"}).json()
    client.post("/api/management/audits", headers=admin_h, json={"device_id": device["id"], "audit_cycle": "DEV-DEL"})
    req = client.post("/api/management/requests", headers=viewer_h, json={
        "device_type": "phone", "project_name": "P", "reason": "Testing delete"}).json()
    client.patch(f"/api/devices/{device['id']}", json={"status": "active"}, headers=admin_h)
    client.post(f"/api/management/requests/{req['id']}/fulfill", json={"device_id": device["id"]}, headers=admin_h)

    assert client.delete(f"/api/devices/{device['id']}", headers=admin_h).status_code == 204

    assert all(t["id"] != ticket["id"] for t in client.get("/api/management/maintenance", headers=admin_h).json())
    assert client.get("/api/management/audits", params={"cycle": "DEV-DEL"}, headers=admin_h).json() == []
    fulfilled = next(r for r in client.get("/api/management/requests", headers=admin_h).json() if r["id"] == req["id"])
    assert fulfilled["allocated_device_id"] is None
