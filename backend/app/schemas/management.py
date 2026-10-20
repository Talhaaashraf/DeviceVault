from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    DeviceType,
    MaintenancePriority,
    MaintenanceStatus,
    OsType,
    PhysicalAuditStatus,
    RequestStatus,
)
from app.schemas.device import DeviceRead
from app.schemas.user import UserBrief


# --- Device Requests ---
class DeviceRequestCreate(BaseModel):
    device_type: DeviceType
    os_preference: OsType | None = None
    project_name: str = Field(min_length=1, max_length=255)
    division: str | None = None
    reason: str = Field(min_length=3)
    duration_days: int | None = Field(default=30, ge=1)
    date_needed: date | None = None


class DeviceRequestReview(BaseModel):
    status: RequestStatus  # approved or rejected
    manager_notes: str | None = None


class DeviceRequestFulfill(BaseModel):
    device_id: UUID
    date_of_return: date | None = None
    notes: str | None = None


class DeviceRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    device_type: DeviceType
    os_preference: OsType | None
    project_name: str
    division: str | None
    reason: str
    duration_days: int | None
    date_needed: date | None
    status: RequestStatus
    manager_notes: str | None
    reviewed_by_id: UUID | None
    allocated_device_id: UUID | None
    created_at: datetime
    updated_at: datetime

    user: UserBrief | None = None
    reviewed_by: UserBrief | None = None
    allocated_device: DeviceRead | None = None


# --- Maintenance Tickets ---
class MaintenanceTicketCreate(BaseModel):
    device_id: UUID
    issue_title: str = Field(min_length=3, max_length=255)
    issue_description: str | None = None
    priority: MaintenancePriority = MaintenancePriority.medium
    vendor_name: str | None = None
    estimated_cost: float | None = 0.0
    sent_date: date | None = None


class MaintenanceTicketUpdate(BaseModel):
    issue_title: str | None = None
    issue_description: str | None = None
    priority: MaintenancePriority | None = None
    repair_status: MaintenanceStatus | None = None
    vendor_name: str | None = None
    estimated_cost: float | None = None
    actual_cost: float | None = None
    sent_date: date | None = None
    completed_date: date | None = None
    technician_notes: str | None = None


class MaintenanceTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    reported_by_id: UUID
    issue_title: str
    issue_description: str | None
    priority: MaintenancePriority
    repair_status: MaintenanceStatus
    vendor_name: str | None
    estimated_cost: float | None
    actual_cost: float | None
    sent_date: date | None
    completed_date: date | None
    technician_notes: str | None
    created_at: datetime
    updated_at: datetime

    device: DeviceRead | None = None
    reported_by: UserBrief | None = None


# --- Audits & Physical Verification ---
class AuditRecordCreate(BaseModel):
    device_id: UUID
    audit_cycle: str = Field(min_length=2, max_length=100)
    physical_status: PhysicalAuditStatus = PhysicalAuditStatus.confirmed
    verified_location: str | None = None
    notes: str | None = None


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    auditor_id: UUID
    audit_cycle: str
    physical_status: PhysicalAuditStatus
    verified_location: str | None
    notes: str | None
    created_at: datetime

    device: DeviceRead | None = None
    auditor: UserBrief | None = None


class AuditCycleSummary(BaseModel):
    audit_cycle: str
    total_devices: int
    audited_devices: int
    completion_percentage: float
    confirmed_count: int
    missing_count: int
    damaged_count: int
    disputed_count: int


# --- Returns & Overdue Management ---
class ReturnExtendPayload(BaseModel):
    new_return_date: date
    extension_reason: str | None = None


class ProcessReturnPayload(BaseModel):
    return_notes: str | None = None
    condition: str | None = "Good"


class OverdueDeviceItem(BaseModel):
    device_id: UUID
    device_name: str
    device_nickname: str
    serial_number: str
    device_type: DeviceType
    assigned_user_name: str | None
    issued_to: str | None
    issued_to_email: str | None
    project_name: str | None
    division: str | None
    date_of_return: date | None
    days_overdue: int  # positive if overdue, negative if upcoming
    status_label: str  # "overdue", "due_today", "due_soon"


class ReturnsOverview(BaseModel):
    overdue_count: int
    due_soon_count: int
    total_assigned: int
    overdue_devices: list[OverdueDeviceItem]
    due_soon_devices: list[OverdueDeviceItem]


# --- Allocation & Department Management ---
class AllocationItem(BaseModel):
    name: str
    device_count: int
    percentage: float
    overdue_count: int


class AllocationSummary(BaseModel):
    total_devices: int
    assigned_devices: int
    unassigned_devices: int
    utilization_rate: float
    by_division: list[AllocationItem]
    by_project: list[AllocationItem]
    by_location: list[AllocationItem]
