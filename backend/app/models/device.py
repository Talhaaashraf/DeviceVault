import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AuditStatus, DeviceStatus, DeviceType, OsType


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_nickname: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(Enum(DeviceType, name="device_type"), nullable=False)
    os_type: Mapped[OsType] = mapped_column(Enum(OsType, name="os_type"), nullable=False)
    os_version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_cellular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    imei_number: Mapped[str | None] = mapped_column(String(15), unique=True, nullable=True)
    serial_number: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    mac_address: Mapped[str] = mapped_column(String(17), unique=True, nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, name="device_status"), nullable=False, default=DeviceStatus.active
    )
    audit_status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, name="audit_status"),
        nullable=False,
        default=AuditStatus.pending_audit,
    )
    resident_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    division: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issued_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issued_to_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_latest_model: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    date_of_return: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    assigned_user = relationship("User", back_populates="assigned_devices", foreign_keys=[assigned_user_id])
    assignment_history = relationship(
        "AssignmentHistory", back_populates="device", cascade="all, delete-orphan"
    )
