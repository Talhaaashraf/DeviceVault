import uuid

HEADER = "device_name,device_nickname,device_type,os_type,os_version,is_cellular,imei_number,serial_number,mac_address,company,status,purchase_date,assigned_user_email"


def _csv(*rows: str) -> bytes:
    return ("\n".join([HEADER, *rows]) + "\n").encode("utf-8")


def _row(serial: str, mac: str, **kw) -> str:
    values = {
        "device_name": "Pixel 9",
        "device_nickname": "Import Phone",
        "device_type": "phone",
        "os_type": "android",
        "os_version": "15",
        "is_cellular": "false",
        "imei_number": "",
        "serial_number": serial,
        "mac_address": mac,
        "company": "Main Office",
        "status": "active",
        "purchase_date": "2024-05-01",
        "assigned_user_email": "",
    }
    values.update(kw)
    return ",".join(values[col] for col in HEADER.split(","))


def _ids():
    s = uuid.uuid4().hex[:10].upper()
    return f"SN-IMP-{s}", ":".join([s[0:2], s[2:4], s[4:6], s[6:8], s[8:10], "0A"])


def test_import_csv_creates_devices(client, manager_h):
    s1, m1 = _ids()
    s2, m2 = _ids()
    content = _csv(_row(s1, m1), _row(s2, m2, assigned_user_email="viewer@company.com"))
    res = client.post("/api/devices/import", files={"file": ("devices.csv", content, "text/csv")}, headers=manager_h)
    assert res.status_code == 200, res.text
    assert res.json() == {"created": 2, "failed": 0, "errors": []}

    found = client.get("/api/devices", params={"q": s2}, headers=manager_h).json()
    assert found[0]["assigned_user"]["email"] == "viewer@company.com"


def test_import_csv_reports_row_errors(client, manager_h):
    s1, m1 = _ids()
    bad = _row("SN-BAD-" + uuid.uuid4().hex[:6], "not-a-mac", device_type="laptop")
    res = client.post(
        "/api/devices/import",
        files={"file": ("devices.csv", _csv(_row(s1, m1), bad), "text/csv")},
        headers=manager_h,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["created"] == 1
    assert body["failed"] == 1
    assert body["errors"][0]["row"] >= 2


def test_import_rejects_non_csv(client, manager_h):
    res = client.post("/api/devices/import", files={"file": ("devices.txt", b"abc", "text/plain")}, headers=manager_h)
    assert res.status_code == 400


def test_import_rejects_empty_file(client, manager_h):
    res = client.post("/api/devices/import", files={"file": ("devices.csv", b"", "text/csv")}, headers=manager_h)
    assert res.status_code == 400


def test_import_rejects_missing_columns(client, manager_h):
    res = client.post(
        "/api/devices/import",
        files={"file": ("devices.csv", b"device_name,company\nPhone,Main Office\n", "text/csv")},
        headers=manager_h,
    )
    assert res.status_code == 400
    assert "Missing required columns" in res.json()["detail"]


def test_import_forbidden_for_viewer(client, viewer_h):
    s1, m1 = _ids()
    res = client.post("/api/devices/import", files={"file": ("d.csv", _csv(_row(s1, m1)), "text/csv")}, headers=viewer_h)
    assert res.status_code == 403


def test_import_rejects_oversized_file(client, manager_h):
    big = b"x" * (5 * 1024 * 1024 + 10)
    res = client.post("/api/devices/import", files={"file": ("big.csv", big, "text/csv")}, headers=manager_h)
    assert res.status_code == 413
