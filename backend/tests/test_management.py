import uuid
from datetime import date, timedelta


def _request_payload(**overrides) -> dict:
    payload = {
        "device_type": "phone",
        "os_preference": "ios",
        "project_name": "Test Project",
        "division": "QA",
        "reason": "Need a device for regression testing",
        "duration_days": 10,
    }
    payload.update(overrides)
    return payload


# ---------- Device requests ----------

def test_viewer_creates_and_sees_only_own_requests(client, viewer_h, admin_h):
    res = client.post("/api/management/requests", json=_request_payload(), headers=viewer_h)
    assert res.status_code == 201, res.text
    assert res.json()["status"] == "pending"
    viewer_id = res.json()["user_id"]

    mine = client.get("/api/management/requests", headers=viewer_h).json()
    assert mine and all(r["user_id"] == viewer_id for r in mine)

    everything = client.get("/api/management/requests", headers=admin_h).json()
    assert len(everything) >= len(mine)

    pending = client.get("/api/management/requests", params={"status": "pending"}, headers=admin_h).json()
    assert all(r["status"] == "pending" for r in pending)


def test_request_validation(client, viewer_h):
    res = client.post("/api/management/requests", json=_request_payload(reason="x"), headers=viewer_h)
    assert res.status_code == 422


def test_review_request(client, viewer_h, manager_h):
    req = client.post("/api/management/requests", json=_request_payload(), headers=viewer_h).json()
    assert client.post(f"/api/management/requests/{req['id']}/review", json={"status": "approved"},
                       headers=viewer_h).status_code == 403

    res = client.post(
        f"/api/management/requests/{req['id']}/review",
        json={"status": "rejected", "manager_notes": "No stock"},
        headers=manager_h,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"
    assert res.json()["manager_notes"] == "No stock"
    assert res.json()["reviewed_by"] is not None


def test_review_missing_request(client, manager_h):
    res = client.post(f"/api/management/requests/{uuid.uuid4()}/review", json={"status": "approved"}, headers=manager_h)
    assert res.status_code == 404


def test_fulfill_request_allocates_device(client, viewer_h, manager_h, admin_h, create_device):
    req = client.post("/api/management/requests", json=_request_payload(duration_days=7), headers=viewer_h).json()
    device = create_device()

    res = client.post(
        f"/api/management/requests/{req['id']}/fulfill",
        json={"device_id": device["id"], "notes": "Collected from IT desk"},
        headers=manager_h,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "fulfilled"
    assert body["allocated_device_id"] == device["id"]

    allocated = client.get(f"/api/devices/{device['id']}", headers=admin_h).json()
    assert allocated["assigned_user_id"] == req["user_id"]
    assert allocated["project_name"] == "Test Project"
    assert allocated["date_of_return"] == (date.today() + timedelta(days=7)).isoformat()

    # A fulfilled request cannot be reviewed again
    again = client.post(f"/api/management/requests/{req['id']}/review", json={"status": "rejected"}, headers=manager_h)
    assert again.status_code == 400


def test_fulfill_rejects_inactive_device(client, viewer_h, manager_h, create_device):
    req = client.post("/api/management/requests", json=_request_payload(), headers=viewer_h).json()
    device = create_device(status="retired")
    res = client.post(f"/api/management/requests/{req['id']}/fulfill", json={"device_id": device["id"]},
                      headers=manager_h)
    assert res.status_code == 400


def test_fulfill_missing_request_or_device(client, viewer_h, manager_h, create_device):
    device = create_device()
    res = client.post(f"/api/management/requests/{uuid.uuid4()}/fulfill", json={"device_id": device["id"]},
                      headers=manager_h)
    assert res.status_code == 404
    req = client.post("/api/management/requests", json=_request_payload(), headers=viewer_h).json()
    res = client.post(f"/api/management/requests/{req['id']}/fulfill", json={"device_id": str(uuid.uuid4())},
                      headers=manager_h)
    assert res.status_code == 404


# ---------- Maintenance ----------

def test_maintenance_lifecycle_completed(client, manager_h, viewer_h, admin_h, create_device):
    device = create_device()
    res = client.post(
        "/api/management/maintenance",
        json={"device_id": device["id"], "issue_title": "Cracked screen", "priority": "high",
              "vendor_name": "Repair Center", "estimated_cost": 80},
        headers=manager_h,
    )
    assert res.status_code == 201, res.text
    ticket = res.json()
    assert ticket["repair_status"] == "in_repair"
    assert client.get(f"/api/devices/{device['id']}", headers=admin_h).json()["status"] == "in_repair"

    active = client.get("/api/management/maintenance", params={"active_only": "true"}, headers=viewer_h).json()
    assert any(t["id"] == ticket["id"] for t in active)

    res = client.patch(
        f"/api/management/maintenance/{ticket['id']}",
        json={"repair_status": "completed", "actual_cost": 95.5, "technician_notes": "Replaced panel"},
        headers=manager_h,
    )
    assert res.status_code == 200
    assert res.json()["completed_date"] == date.today().isoformat()
    assert client.get(f"/api/devices/{device['id']}", headers=admin_h).json()["status"] == "active"

    active = client.get("/api/management/maintenance", params={"active_only": "true"}, headers=viewer_h).json()
    assert all(t["id"] != ticket["id"] for t in active)
    assert any(t["id"] == ticket["id"] for t in client.get("/api/management/maintenance", headers=viewer_h).json())


def test_maintenance_unrepairable_retires_device(client, manager_h, admin_h, create_device):
    device = create_device()
    ticket = client.post("/api/management/maintenance",
                         json={"device_id": device["id"], "issue_title": "Water damage"}, headers=manager_h).json()
    res = client.patch(f"/api/management/maintenance/{ticket['id']}", json={"repair_status": "unrepairable"},
                       headers=manager_h)
    assert res.status_code == 200
    assert client.get(f"/api/devices/{device['id']}", headers=admin_h).json()["status"] == "retired"


def test_maintenance_errors(client, manager_h, viewer_h, create_device):
    assert client.post("/api/management/maintenance", json={"device_id": str(uuid.uuid4()), "issue_title": "Broken"},
                       headers=manager_h).status_code == 404
    device = create_device()
    assert client.post("/api/management/maintenance", json={"device_id": device["id"], "issue_title": "Broken"},
                       headers=viewer_h).status_code == 403
    assert client.patch(f"/api/management/maintenance/{uuid.uuid4()}", json={"priority": "low"},
                        headers=manager_h).status_code == 404


# ---------- Returns ----------

def test_returns_overview_buckets(client, viewer_h, create_device):
    today = date.today()
    overdue = create_device(date_of_return=(today - timedelta(days=5)).isoformat(), issued_to="Late Person")
    due_today = create_device(date_of_return=today.isoformat())
    soon = create_device(date_of_return=(today + timedelta(days=3)).isoformat())
    later = create_device(date_of_return=(today + timedelta(days=30)).isoformat())

    res = client.get("/api/management/returns", headers=viewer_h)
    assert res.status_code == 200
    data = res.json()
    overdue_items = {d["device_id"]: d for d in data["overdue_devices"]}
    soon_ids = {d["device_id"] for d in data["due_soon_devices"]}

    assert overdue_items[overdue["id"]]["status_label"] == "overdue"
    assert overdue_items[overdue["id"]]["days_overdue"] == 5
    assert overdue_items[due_today["id"]]["status_label"] == "due_today"
    assert soon["id"] in soon_ids
    assert later["id"] not in soon_ids and later["id"] not in overdue_items
    assert data["overdue_count"] == len(data["overdue_devices"])


def test_extend_return_date(client, manager_h, admin_h, create_device):
    device = create_device(date_of_return=date.today().isoformat())
    new_date = (date.today() + timedelta(days=14)).isoformat()
    res = client.post(f"/api/management/returns/{device['id']}/extend",
                      json={"new_return_date": new_date, "extension_reason": "Project extended"}, headers=manager_h)
    assert res.status_code == 200
    assert client.get(f"/api/devices/{device['id']}", headers=admin_h).json()["date_of_return"] == new_date
    history = client.get(f"/api/devices/{device['id']}/history", headers=admin_h).json()
    assert any("extended" in (h["notes"] or "") for h in history)


def test_process_return_clears_assignment(client, manager_h, admin_h, create_device):
    me = client.get("/api/auth/me", headers=manager_h).json()
    device = create_device(assigned_user_id=me["id"], issued_to="Someone", project_name="Alpha",
                           date_of_return=date.today().isoformat())
    res = client.post(f"/api/management/returns/{device['id']}/return",
                      json={"condition": "Good", "return_notes": "All accessories"}, headers=manager_h)
    assert res.status_code == 200
    returned = client.get(f"/api/devices/{device['id']}", headers=admin_h).json()
    assert returned["assigned_user_id"] is None
    assert returned["issued_to"] is None
    assert returned["project_name"] is None
    assert returned["date_of_return"] is None


def test_returns_errors(client, manager_h, viewer_h, create_device):
    missing = uuid.uuid4()
    assert client.post(f"/api/management/returns/{missing}/extend", json={"new_return_date": "2030-01-01"},
                       headers=manager_h).status_code == 404
    assert client.post(f"/api/management/returns/{missing}/return", json={}, headers=manager_h).status_code == 404
    device = create_device()
    assert client.post(f"/api/management/returns/{device['id']}/return", json={},
                       headers=viewer_h).status_code == 403


# ---------- Audits ----------

def test_record_audit_updates_device(client, manager_h, viewer_h, admin_h, create_device):
    cycle = f"TEST-{uuid.uuid4().hex[:6]}"
    confirmed = create_device()
    missing = create_device()

    res = client.post("/api/management/audits", json={"device_id": confirmed["id"], "audit_cycle": cycle,
                                                      "physical_status": "confirmed", "verified_location": "Lab 2"},
                      headers=manager_h)
    assert res.status_code == 201, res.text
    dev = client.get(f"/api/devices/{confirmed['id']}", headers=admin_h).json()
    assert dev["audit_status"] == "confirmed"
    assert dev["resident_location"] == "Lab 2"

    client.post("/api/management/audits", json={"device_id": missing["id"], "audit_cycle": cycle,
                                                "physical_status": "missing"}, headers=manager_h)
    dev = client.get(f"/api/devices/{missing['id']}", headers=admin_h).json()
    assert dev["status"] == "lost"
    assert dev["audit_status"] == "disputed"

    logs = client.get("/api/management/audits", params={"cycle": cycle}, headers=viewer_h).json()
    assert len(logs) == 2
    by_device = client.get("/api/management/audits", params={"device_id": confirmed["id"]}, headers=viewer_h).json()
    assert len(by_device) == 1

    cycles = {c["audit_cycle"]: c for c in client.get("/api/management/audits/cycles", headers=viewer_h).json()}
    assert cycles[cycle]["audited_devices"] == 2
    assert cycles[cycle]["confirmed_count"] == 1
    assert cycles[cycle]["missing_count"] == 1


def test_audit_errors(client, manager_h, viewer_h, create_device):
    assert client.post("/api/management/audits", json={"device_id": str(uuid.uuid4()), "audit_cycle": "2026-Q4"},
                       headers=manager_h).status_code == 404
    device = create_device()
    assert client.post("/api/management/audits", json={"device_id": device["id"], "audit_cycle": "2026-Q4"},
                       headers=viewer_h).status_code == 403


# ---------- Allocations ----------

def test_allocations_summary(client, viewer_h, create_device):
    create_device(division="Allocation Test Div", project_name="Allocation Test Project",
                  date_of_return=(date.today() - timedelta(days=1)).isoformat())
    res = client.get("/api/management/allocations", headers=viewer_h)
    assert res.status_code == 200
    data = res.json()
    assert data["assigned_devices"] + data["unassigned_devices"] == data["total_devices"]
    divisions = {d["name"]: d for d in data["by_division"]}
    assert divisions["Allocation Test Div"]["device_count"] == 1
    assert divisions["Allocation Test Div"]["overdue_count"] == 1
    projects = {p["name"]: p for p in data["by_project"]}
    assert projects["Allocation Test Project"]["overdue_count"] == 1
    assert sum(loc["device_count"] for loc in data["by_location"]) == data["total_devices"]


def test_review_only_accepts_approve_or_reject(client, viewer_h, manager_h):
    req = client.post("/api/management/requests", json=_request_payload(), headers=viewer_h).json()
    for bad in ("fulfilled", "pending"):
        res = client.post(f"/api/management/requests/{req['id']}/review", json={"status": bad}, headers=manager_h)
        assert res.status_code == 422


def test_cannot_fulfil_rejected_or_already_fulfilled_request(client, viewer_h, manager_h, create_device):
    rejected = client.post("/api/management/requests", json=_request_payload(), headers=viewer_h).json()
    client.post(f"/api/management/requests/{rejected['id']}/review", json={"status": "rejected"}, headers=manager_h)
    res = client.post(f"/api/management/requests/{rejected['id']}/fulfill", json={"device_id": create_device()["id"]},
                      headers=manager_h)
    assert res.status_code == 400

    req = client.post("/api/management/requests", json=_request_payload(), headers=viewer_h).json()
    first = client.post(f"/api/management/requests/{req['id']}/fulfill", json={"device_id": create_device()["id"]},
                        headers=manager_h)
    assert first.status_code == 200
    again = client.post(f"/api/management/requests/{req['id']}/fulfill", json={"device_id": create_device()["id"]},
                        headers=manager_h)
    assert again.status_code == 400


def test_cannot_fulfil_with_device_allocated_to_someone_else(client, viewer_h, manager_h, create_device):
    manager = client.get("/api/auth/me", headers=manager_h).json()
    assigned = create_device(assigned_user_id=manager["id"])
    issued = create_device(issued_to="Field Engineer")
    for device in (assigned, issued):
        req = client.post("/api/management/requests", json=_request_payload(), headers=viewer_h).json()
        res = client.post(f"/api/management/requests/{req['id']}/fulfill", json={"device_id": device["id"]},
                          headers=manager_h)
        assert res.status_code == 409


def test_numeric_inputs_are_bounded(client, viewer_h, manager_h, create_device):
    res = client.post("/api/management/requests", json=_request_payload(duration_days=10**9), headers=viewer_h)
    assert res.status_code == 422
    device = create_device()
    res = client.post("/api/management/maintenance", headers=manager_h,
                      json={"device_id": device["id"], "issue_title": "Negative", "estimated_cost": -1})
    assert res.status_code == 422
