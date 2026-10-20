import csv
import hashlib
import io
import re
from datetime import date, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.assignment import AssignmentHistory
from app.models.device import Device
from app.models.enums import AuditStatus, DeviceType, OsType
from app.models.user import User
from app.schemas.device import DeviceCreate

HEADER_ALIASES = {
    "device_name": {"device_name", "name", "name / aka", "name/aka", "aka"},
    "device_nickname": {"device_nickname", "nickname", "aka"},
    "device_type": {"device_type", "device type", "type"},
    "os_type": {"os_type", "os type", "os"},
    "os_version": {"os_version", "current os version", "os version", "version"},
    "serial_number": {"serial_number", "company serial", "serial", "serial no", "serial number"},
    "imei_number": {"imei_number", "imei"},
    "mac_address": {"mac_address", "mac", "mac address"},
    "company": {"company", "company name"},
    "is_cellular": {"is_cellular", "cellular"},
    "status": {"status", "device status"},
    "audit_status": {"audit_status", "audit status"},
    "resident_location": {"resident_location", "resident location", "location"},
    "division": {"division"},
    "issued_to": {"issued_to", "issued to", "issued to (engineer name)", "engineer name", "engineer"},
    "project_manager": {"project_manager", "project manager", "project manager (name)"},
    "project_name": {"project_name", "project name", "project"},
    "date_of_return": {"date_of_return", "date of return", "return date"},
    "purchase_date": {"purchase_date", "purchase date"},
    "assigned_user_email": {"assigned_user_email", "assigned email", "user email"},
    "notes": {"notes"},
}

DEVICE_TYPE_ALIASES = {
    "phone": DeviceType.phone,
    "tablet": DeviceType.tablet_android,
    "tablet (ipad)": DeviceType.tablet_ipad,
    "tablet ipad": DeviceType.tablet_ipad,
    "ipad": DeviceType.tablet_ipad,
    "tablet_ipad": DeviceType.tablet_ipad,
    "tablet (android)": DeviceType.tablet_android,
    "tablet android": DeviceType.tablet_android,
    "tablet_android": DeviceType.tablet_android,
    "smartwatch": DeviceType.smartwatch,
    "watch": DeviceType.smartwatch,
}

OS_TYPE_ALIASES = {
    "ios": OsType.ios,
    "android": OsType.android,
    "watchos": OsType.watchos,
    "watch os": OsType.watchos,
    "wear os": OsType.wear_os,
    "wear_os": OsType.wear_os,
    "wearos": OsType.wear_os,
}

AUDIT_ALIASES = {
    "confirmed": AuditStatus.confirmed,
    "pending": AuditStatus.pending_audit,
    "pending audit": AuditStatus.pending_audit,
    "pending_audit": AuditStatus.pending_audit,
    "disputed": AuditStatus.disputed,
}

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _parse_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date '{value}' (use YYYY-MM-DD)")


def _normalize_headers(fieldnames: list[str | None]) -> dict[str, str]:
    """Map canonical field -> actual CSV header key (lowercased)."""
    raw = {(h or "").strip().lower(): (h or "").strip().lower() for h in fieldnames if h}
    mapping: dict[str, str] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in raw:
                mapping[canonical] = alias
                break
    return mapping


def _get(row: dict, mapping: dict[str, str], key: str, default: str = "") -> str:
    actual = mapping.get(key)
    if not actual:
        return default
    return (row.get(actual) or default).strip()


def _mac_from_serial(serial: str) -> str:
    digest = hashlib.md5(serial.encode("utf-8")).hexdigest()[:12].upper()
    return ":".join(digest[i : i + 2] for i in range(0, 12, 2))


def _resolve_assignee(db: Session, email: str | None):
    if not email:
        return None
    user = db.scalar(select(User).where(User.email == email.lower(), User.is_active.is_(True)))
    if user is None:
        raise ValueError(f"Assigned user email not found or inactive: {email}")
    return user.id


def _format_validation_error(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors())


def _parse_name_aka(row: dict, mapping: dict[str, str]) -> tuple[str, str]:
    name = _get(row, mapping, "device_name")
    nick = _get(row, mapping, "device_nickname")
    if "name / aka" in mapping.values() or mapping.get("device_name") in {"name / aka", "name/aka"}:
        if " / " in name:
            left, right = name.split(" / ", 1)
            return left.strip() or right.strip(), right.strip() or left.strip()
    if not nick:
        nick = name
    if not name and nick:
        name = nick
    return name, nick


def import_devices_from_csv(db: Session, content: bytes, changed_by_id) -> dict:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    mapping = _normalize_headers(list(reader.fieldnames))
    required_any = ["device_name", "device_type", "os_type", "os_version", "serial_number"]
    missing = [k for k in required_any if k not in mapping]
    if missing:
        raise ValueError(
            "Missing required columns (or aliases): "
            + ", ".join(missing)
            + ". Expected headers like: OS Type, Device Type, Name / AKA, Current OS Version, Company Serial, ..."
        )

    created = 0
    errors: list[dict] = []

    for index, raw in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(row.values()):
            continue

        try:
            with db.begin_nested():
                name, nick = _parse_name_aka(row, mapping)
                dtype_raw = _get(row, mapping, "device_type").lower()
                os_raw = _get(row, mapping, "os_type").lower()
                serial = _get(row, mapping, "serial_number")
                imei = _get(row, mapping, "imei_number") or None
                mac = _get(row, mapping, "mac_address")
                if mac and not MAC_RE.match(mac):
                    # Spreadsheet sometimes puts MAC into IMEI — swap if needed
                    if imei and MAC_RE.match(imei) and re.fullmatch(r"\d{15}", mac.replace(":", "")):
                        imei, mac = mac, imei
                    elif MAC_RE.match(imei or ""):
                        mac = imei
                        imei = None

                if not mac:
                    mac = _mac_from_serial(serial or f"row-{index}")

                cellular_raw = _get(row, mapping, "is_cellular")
                if cellular_raw:
                    is_cellular = _truthy(cellular_raw)
                else:
                    is_cellular = bool(imei)

                if not is_cellular:
                    imei = None

                audit_raw = _get(row, mapping, "audit_status").lower()
                audit_status = AUDIT_ALIASES.get(audit_raw, AuditStatus.pending_audit)

                assigned_user_id = _resolve_assignee(db, _get(row, mapping, "assigned_user_email") or None)
                issued_to = _get(row, mapping, "issued_to") or None
                company = _get(row, mapping, "company") or "Unknown"

                payload = DeviceCreate(
                    device_name=name,
                    device_nickname=nick,
                    device_type=DEVICE_TYPE_ALIASES.get(dtype_raw, dtype_raw),
                    os_type=OS_TYPE_ALIASES.get(os_raw, os_raw),
                    os_version=_get(row, mapping, "os_version"),
                    is_cellular=is_cellular,
                    imei_number=imei,
                    serial_number=serial,
                    mac_address=mac,
                    company=company,
                    assigned_user_id=assigned_user_id,
                    status=(_get(row, mapping, "status") or "active").lower(),
                    audit_status=audit_status,
                    resident_location=_get(row, mapping, "resident_location") or None,
                    division=_get(row, mapping, "division") or None,
                    issued_to=issued_to,
                    project_manager=_get(row, mapping, "project_manager") or None,
                    project_name=_get(row, mapping, "project_name") or None,
                    date_of_return=_parse_date(_get(row, mapping, "date_of_return")),
                    notes=_get(row, mapping, "notes") or None,
                    purchase_date=_parse_date(_get(row, mapping, "purchase_date")),
                )

                device = Device(**payload.model_dump())
                db.add(device)
                db.flush()

                if assigned_user_id is not None:
                    db.add(
                        AssignmentHistory(
                            device_id=device.id,
                            from_user_id=None,
                            to_user_id=assigned_user_id,
                            changed_by=changed_by_id,
                        )
                    )
            created += 1
        except ValidationError as exc:
            errors.append({"row": index, "error": _format_validation_error(exc)})
        except (ValueError, KeyError, IntegrityError) as exc:
            errors.append({"row": index, "error": str(exc.orig if isinstance(exc, IntegrityError) else exc)})

    db.commit()
    return {"created": created, "failed": len(errors), "errors": errors}
