import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    viewer = "viewer"


class DeviceType(str, enum.Enum):
    phone = "phone"
    tablet_ipad = "tablet_ipad"
    tablet_android = "tablet_android"
    smartwatch = "smartwatch"


class OsType(str, enum.Enum):
    ios = "ios"
    android = "android"
    watchos = "watchos"
    wear_os = "wear_os"


class DeviceStatus(str, enum.Enum):
    active = "active"
    in_repair = "in_repair"
    retired = "retired"
    lost = "lost"


class AuditStatus(str, enum.Enum):
    confirmed = "confirmed"
    pending_audit = "pending_audit"
    disputed = "disputed"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    fulfilled = "fulfilled"


class MaintenanceStatus(str, enum.Enum):
    reported = "reported"
    in_repair = "in_repair"
    waiting_parts = "waiting_parts"
    completed = "completed"
    unrepairable = "unrepairable"


class MaintenancePriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class PhysicalAuditStatus(str, enum.Enum):
    confirmed = "confirmed"
    damaged = "damaged"
    missing = "missing"
    disputed = "disputed"

