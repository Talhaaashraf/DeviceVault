import os
import tempfile
import uuid
from pathlib import Path

import pytest

# Configure an isolated SQLite database before the app (and its engine) is imported.
_TMP_DIR = Path(tempfile.mkdtemp(prefix="devicevault-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}"
os.environ["SEED_ON_STARTUP"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-0123456789"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CREDENTIALS = {
    "admin": ("admin@company.com", "Admin123!"),
    "manager": ("manager@company.com", "Manager123!"),
    "viewer": ("viewer@company.com", "Viewer123!"),
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client: TestClient, role: str) -> dict:
    email, password = CREDENTIALS[role]
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture(scope="session")
def tokens(client):
    return {role: login(client, role) for role in CREDENTIALS}


@pytest.fixture(scope="session")
def admin_h(tokens):
    return {"Authorization": f"Bearer {tokens['admin']['access_token']}"}


@pytest.fixture(scope="session")
def manager_h(tokens):
    return {"Authorization": f"Bearer {tokens['manager']['access_token']}"}


@pytest.fixture(scope="session")
def viewer_h(tokens):
    return {"Authorization": f"Bearer {tokens['viewer']['access_token']}"}


def _unique_suffix() -> str:
    return uuid.uuid4().hex[:6].upper()


def _unique_mac() -> str:
    raw = uuid.uuid4().hex[:12].upper()
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2))


def _unique_imei() -> str:
    return str(uuid.uuid4().int)[:15]


@pytest.fixture
def device_payload():
    def build(**overrides) -> dict:
        suffix = _unique_suffix()
        payload = {
            "device_name": f"Test Phone {suffix}",
            "device_nickname": f"QA Phone {suffix}",
            "device_type": "phone",
            "os_type": "android",
            "os_version": "14",
            "is_cellular": True,
            "imei_number": _unique_imei(),
            "serial_number": f"SN-TEST-{suffix}",
            "mac_address": _unique_mac(),
            "company": "Main Office",
        }
        payload.update(overrides)
        return payload

    return build


@pytest.fixture
def create_device(client, admin_h, device_payload):
    def create(**overrides) -> dict:
        res = client.post("/api/devices", json=device_payload(**overrides), headers=admin_h)
        assert res.status_code == 201, res.text
        return res.json()

    return create
