import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AuditStatus, DeviceStatus, DeviceType, OsType
from app.schemas.user import UserBrief

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
IMEI_RE = re.compile(r"^\d{15}$")


class DeviceBase(BaseModel):
    device_name: str = Field(min_length=1, max_length=255)
    device_nickname: str = Field(min_length=1, max_length=255)
    device_type: DeviceType
    os_type: OsType
    os_version: str = Field(min_length=1, max_length=50)
    is_cellular: bool = False
    imei_number: str | None = None
    serial_number: str = Field(min_length=1, max_length=255)
    mac_address: str = Field(min_length=17, max_length=17)
    company: str = Field(min_length=1, max_length=255)
    assigned_user_id: UUID | None = None
    status: DeviceStatus = DeviceStatus.active
    audit_status: AuditStatus = AuditStatus.pending_audit
    resident_location: str | None = None
    division: str | None = None
    issued_to: str | None = None
    issued_to_email: str | None = None
    project_manager: str | None = None
    project_name: str | None = None
    is_latest_model: bool = False
    date_of_return: date | None = None
    notes: str | None = None
    purchase_date: date | None = None

    @field_validator("mac_address")
    @classmethod
    def normalize_mac(cls, v: str) -> str:
        v = v.strip().upper()
        if not MAC_RE.match(v):
            raise ValueError("mac_address must match XX:XX:XX:XX:XX:XX")
        return v

    @field_validator("imei_number")
    @classmethod
    def validate_imei_format(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip()
        if not IMEI_RE.match(v):
            raise ValueError("imei_number must be exactly 15 digits")
        return v

    @model_validator(mode="after")
    def require_imei_if_cellular(self):
        if self.is_cellular and not self.imei_number:
            raise ValueError("imei_number is required when is_cellular is true")
        if not self.is_cellular and self.imei_number:
            raise ValueError("imei_number must be empty when is_cellular is false")
        return self


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    device_name: str | None = Field(default=None, min_length=1, max_length=255)
    device_nickname: str | None = Field(default=None, min_length=1, max_length=255)
    device_type: DeviceType | None = None
    os_type: OsType | None = None
    os_version: str | None = Field(default=None, min_length=1, max_length=50)
    is_cellular: bool | None = None
    imei_number: str | None = None
    serial_number: str | None = Field(default=None, min_length=1, max_length=255)
    mac_address: str | None = Field(default=None, min_length=17, max_length=17)
    company: str | None = Field(default=None, min_length=1, max_length=255)
    assigned_user_id: UUID | None = None
    status: DeviceStatus | None = None
    audit_status: AuditStatus | None = None
    resident_location: str | None = None
    division: str | None = None
    issued_to: str | None = None
    issued_to_email: str | None = None
    project_manager: str | None = None
    project_name: str | None = None
    is_latest_model: bool | None = None
    date_of_return: date | None = None
    notes: str | None = None
    purchase_date: date | None = None
    clear_assigned_user: bool = False
    clear_imei: bool = False
    clear_purchase_date: bool = False
    clear_date_of_return: bool = False

    @field_validator("mac_address")
    @classmethod
    def normalize_mac(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if not MAC_RE.match(v):
            raise ValueError("mac_address must match XX:XX:XX:XX:XX:XX")
        return v

    @field_validator("imei_number")
    @classmethod
    def validate_imei_format(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip()
        if not IMEI_RE.match(v):
            raise ValueError("imei_number must be exactly 15 digits")
        return v


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: UUID
    device_name: str
    device_nickname: str
    device_type: DeviceType
    os_type: OsType
    os_version: str
    is_cellular: bool
    imei_number: str | None
    serial_number: str
    mac_address: str
    company: str
    assigned_user_id: UUID | None
    status: DeviceStatus
    audit_status: AuditStatus = AuditStatus.pending_audit
    resident_location: str | None = None
    division: str | None = None
    issued_to: str | None = None
    issued_to_email: str | None = None
    project_manager: str | None = None
    project_name: str | None = None
    is_latest_model: bool = False
    date_of_return: date | None = None
    notes: str | None = None
    purchase_date: date | None
    created_at: datetime
    updated_at: datetime
    assigned_user: UserBrief | None = None
 
 
class DashboardProjectItem(BaseModel):
    project_name: str
    count: int
 
 
class LatestModelItem(BaseModel):
    id: UUID
    device_name: str
    device_nickname: str
    os_type: OsType
    issued_to: str | None = None
 
 
class InStockDeviceItem(BaseModel):
    id: UUID
    device_name: str
    device_type: DeviceType
    os_type: OsType
    serial_number: str
 
 
class InStockSummary(BaseModel):
    count: int
    list: list[InStockDeviceItem]
 
 
class DashboardAlertItem(BaseModel):
    id: UUID
    title: str
    subtitle: str
    type: str  # "overdue", "request", "maintenance"
    badge: str


class DashboardSummary(BaseModel):
    total_devices: int
    unassigned_devices: int
    allocated_devices: int
    utilization_rate: float
    by_status: dict[str, int]
    by_os: dict[str, int]
    by_type: dict[str, int]
    by_category: dict[str, int]
    by_os_freshness: dict[str, dict[str, int]]
    by_project: dict[str, int]
    by_division: dict[str, int]
    by_location: dict[str, int]
    by_company: dict[str, int]
    by_purchase_year: dict[str, int]
    by_audit_status: dict[str, int]
    apple_count: int
    android_count: int
    cellular_count: int
    wifi_only_count: int
    pending_requests_count: int
    overdue_returns_count: int
    active_repairs_count: int
    total_repair_expense: float
    audit_completion_percentage: float
    urgent_alerts: list[DashboardAlertItem]
    latest_models: list[LatestModelItem]
    in_stock: InStockSummary



class AssignmentHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    from_user_id: UUID | None
    to_user_id: UUID | None
    changed_by: UUID
    from_issued_to: str | None = None
    to_issued_to: str | None = None
    project_name: str | None = None
    project_manager: str | None = None
    division: str | None = None
    resident_location: str | None = None
    audit_status: str | None = None
    date_of_return: date | None = None
    notes: str | None = None
    created_at: datetime
    from_user: UserBrief | None = None
    to_user: UserBrief | None = None
    changed_by_user: UserBrief | None = None


class ImportRowError(BaseModel):
    row: int
    error: str


class ImportResult(BaseModel):
    created: int
    failed: int
    errors: list[ImportRowError]
