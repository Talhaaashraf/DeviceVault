from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.api.deps import AdminUser, CurrentUser, DbSession, ManagerOrAdmin
from app.models.assignment import AssignmentHistory
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.device_request import DeviceRequest
from app.models.enums import (
    AuditStatus,
    DeviceStatus,
    MaintenancePriority,
    MaintenanceStatus,
    PhysicalAuditStatus,
    RequestStatus,
    UserRole,
)
from app.models.maintenance import MaintenanceTicket
from app.models.user import User
from app.schemas.management import (
    AllocationItem,
    AllocationSummary,
    AuditCycleSummary,
    AuditLogRead,
    AuditRecordCreate,
    DeviceRequestCreate,
    DeviceRequestFulfill,
    DeviceRequestRead,
    DeviceRequestReview,
    MaintenanceTicketCreate,
    MaintenanceTicketRead,
    MaintenanceTicketUpdate,
    OverdueDeviceItem,
    ProcessReturnPayload,
    ReturnExtendPayload,
    ReturnsOverview,
)

router = APIRouter(prefix="/management", tags=["management"])


# ==========================================
# 1. DEVICE REQUEST & APPROVAL WORKFLOW
# ==========================================

@router.get("/requests", response_model=list[DeviceRequestRead])
def list_requests(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: RequestStatus | None = Query(None, alias="status"),
    my_only: bool = False,
) -> list[DeviceRequest]:
    stmt = (
        select(DeviceRequest)
        .options(
            joinedload(DeviceRequest.user),
            joinedload(DeviceRequest.reviewed_by),
            joinedload(DeviceRequest.allocated_device),
        )
        .order_by(DeviceRequest.created_at.desc())
    )

    if current_user.role == UserRole.viewer or my_only:
        stmt = stmt.where(DeviceRequest.user_id == current_user.id)

    if status_filter is not None:
        stmt = stmt.where(DeviceRequest.status == status_filter)

    return list(db.scalars(stmt).unique().all())


@router.post("/requests", response_model=DeviceRequestRead, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: DeviceRequestCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> DeviceRequest:
    request_obj = DeviceRequest(
        user_id=current_user.id,
        device_type=payload.device_type,
        os_preference=payload.os_preference,
        project_name=payload.project_name,
        division=payload.division,
        reason=payload.reason,
        duration_days=payload.duration_days,
        date_needed=payload.date_needed,
        status=RequestStatus.pending,
    )
    db.add(request_obj)
    db.commit()
    db.refresh(request_obj)

    stmt = (
        select(DeviceRequest)
        .options(
            joinedload(DeviceRequest.user),
            joinedload(DeviceRequest.reviewed_by),
            joinedload(DeviceRequest.allocated_device),
        )
        .where(DeviceRequest.id == request_obj.id)
    )
    return db.scalar(stmt)


@router.post("/requests/{request_id}/review", response_model=DeviceRequestRead)
def review_request(
    request_id: UUID,
    payload: DeviceRequestReview,
    db: DbSession,
    current_user: ManagerOrAdmin,
) -> DeviceRequest:
    request_obj = db.get(DeviceRequest, request_id)
    if not request_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    if request_obj.status == RequestStatus.fulfilled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is already fulfilled")

    request_obj.status = payload.status
    request_obj.manager_notes = payload.manager_notes
    request_obj.reviewed_by_id = current_user.id
    db.commit()

    stmt = (
        select(DeviceRequest)
        .options(
            joinedload(DeviceRequest.user),
            joinedload(DeviceRequest.reviewed_by),
            joinedload(DeviceRequest.allocated_device),
        )
        .where(DeviceRequest.id == request_id)
    )
    return db.scalar(stmt)


@router.post("/requests/{request_id}/fulfill", response_model=DeviceRequestRead)
def fulfill_request(
    request_id: UUID,
    payload: DeviceRequestFulfill,
    db: DbSession,
    current_user: ManagerOrAdmin,
) -> DeviceRequest:
    request_obj = db.get(DeviceRequest, request_id)
    if not request_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    device = db.get(Device, payload.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    if device.status != DeviceStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device is not active (current status: {device.status})",
        )

    requester = db.get(User, request_obj.user_id)
    old_assigned_user = device.assigned_user_id

    # Allocate device to user
    device.assigned_user_id = requester.id
    device.issued_to = requester.full_name
    device.issued_to_email = requester.email
    device.project_name = request_obj.project_name
    if request_obj.division:
        device.division = request_obj.division

    # Calculate return date
    if payload.date_of_return:
        device.date_of_return = payload.date_of_return
    elif request_obj.duration_days:
        device.date_of_return = date.today() + timedelta(days=request_obj.duration_days)

    if payload.notes:
        device.notes = payload.notes

    # Add assignment history
    db.add(
        AssignmentHistory(
            device_id=device.id,
            from_user_id=old_assigned_user,
            to_user_id=requester.id,
            changed_by=current_user.id,
            to_issued_to=requester.full_name,
            project_name=request_obj.project_name,
            division=request_obj.division,
            date_of_return=device.date_of_return,
            notes=f"Fulfilled Request #{str(request_obj.id)[:8]}: {payload.notes or ''}".strip(),
        )
    )

    request_obj.status = RequestStatus.fulfilled
    request_obj.allocated_device_id = device.id
    request_obj.reviewed_by_id = current_user.id
    db.commit()

    stmt = (
        select(DeviceRequest)
        .options(
            joinedload(DeviceRequest.user),
            joinedload(DeviceRequest.reviewed_by),
            joinedload(DeviceRequest.allocated_device),
        )
        .where(DeviceRequest.id == request_id)
    )
    return db.scalar(stmt)


# ==========================================
# 2. MAINTENANCE & REPAIR TRACKING
# ==========================================

@router.get("/maintenance", response_model=list[MaintenanceTicketRead])
def list_maintenance_tickets(
    db: DbSession,
    _: CurrentUser,
    active_only: bool = False,
) -> list[MaintenanceTicket]:
    stmt = (
        select(MaintenanceTicket)
        .options(
            joinedload(MaintenanceTicket.device),
            joinedload(MaintenanceTicket.reported_by),
        )
        .order_by(MaintenanceTicket.created_at.desc())
    )

    if active_only:
        stmt = stmt.where(MaintenanceTicket.repair_status != MaintenanceStatus.completed)

    return list(db.scalars(stmt).unique().all())


@router.post("/maintenance", response_model=MaintenanceTicketRead, status_code=status.HTTP_201_CREATED)
def create_maintenance_ticket(
    payload: MaintenanceTicketCreate,
    db: DbSession,
    current_user: ManagerOrAdmin,
) -> MaintenanceTicket:
    device = db.get(Device, payload.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    ticket = MaintenanceTicket(
        device_id=payload.device_id,
        reported_by_id=current_user.id,
        issue_title=payload.issue_title,
        issue_description=payload.issue_description,
        priority=payload.priority,
        repair_status=MaintenanceStatus.in_repair,
        vendor_name=payload.vendor_name,
        estimated_cost=payload.estimated_cost or 0.0,
        sent_date=payload.sent_date or date.today(),
    )
    db.add(ticket)

    # Change device status to in_repair
    device.status = DeviceStatus.in_repair

    db.add(
        AssignmentHistory(
            device_id=device.id,
            from_user_id=device.assigned_user_id,
            to_user_id=device.assigned_user_id,
            changed_by=current_user.id,
            notes=f"Maintenance logged: {payload.issue_title} (Vendor: {payload.vendor_name or 'N/A'})",
        )
    )

    db.commit()

    stmt = (
        select(MaintenanceTicket)
        .options(
            joinedload(MaintenanceTicket.device),
            joinedload(MaintenanceTicket.reported_by),
        )
        .where(MaintenanceTicket.id == ticket.id)
    )
    return db.scalar(stmt)


@router.patch("/maintenance/{ticket_id}", response_model=MaintenanceTicketRead)
def update_maintenance_ticket(
    ticket_id: UUID,
    payload: MaintenanceTicketUpdate,
    db: DbSession,
    current_user: ManagerOrAdmin,
) -> MaintenanceTicket:
    ticket = db.get(MaintenanceTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance ticket not found")

    data = payload.model_dump(exclude_unset=True)
    new_status = data.get("repair_status")

    for key, value in data.items():
        setattr(ticket, key, value)

    device = db.get(Device, ticket.device_id)
    if device and new_status == MaintenanceStatus.completed:
        device.status = DeviceStatus.active
        if not ticket.completed_date:
            ticket.completed_date = date.today()
        db.add(
            AssignmentHistory(
                device_id=device.id,
                from_user_id=device.assigned_user_id,
                to_user_id=device.assigned_user_id,
                changed_by=current_user.id,
                notes=f"Maintenance completed: {ticket.issue_title}. Cost: ${ticket.actual_cost or ticket.estimated_cost or 0:.2f}",
            )
        )
    elif device and new_status == MaintenanceStatus.unrepairable:
        device.status = DeviceStatus.retired

    db.commit()

    stmt = (
        select(MaintenanceTicket)
        .options(
            joinedload(MaintenanceTicket.device),
            joinedload(MaintenanceTicket.reported_by),
        )
        .where(MaintenanceTicket.id == ticket_id)
    )
    return db.scalar(stmt)


# ==========================================
# 3. RETURNS & OVERDUE MANAGEMENT
# ==========================================

@router.get("/returns", response_model=ReturnsOverview)
def get_returns_overview(db: DbSession, _: CurrentUser) -> ReturnsOverview:
    today = date.today()
    next_week = today + timedelta(days=7)

    stmt = (
        select(Device)
        .options(joinedload(Device.assigned_user))
        .where(Device.date_of_return.is_not(None))
    )
    devices_with_return = list(db.scalars(stmt).unique().all())

    overdue_list: list[OverdueDeviceItem] = []
    due_soon_list: list[OverdueDeviceItem] = []

    for d in devices_with_return:
        diff_days = (today - d.date_of_return).days
        user_name = d.assigned_user.full_name if d.assigned_user else (d.issued_to or "Unassigned")

        if diff_days > 0:
            status_lbl = "overdue"
            item = OverdueDeviceItem(
                device_id=d.id,
                device_name=d.device_name,
                device_nickname=d.device_nickname,
                serial_number=d.serial_number,
                device_type=d.device_type,
                assigned_user_name=user_name,
                issued_to=d.issued_to,
                issued_to_email=d.issued_to_email,
                project_name=d.project_name,
                division=d.division,
                date_of_return=d.date_of_return,
                days_overdue=diff_days,
                status_label=status_lbl,
            )
            overdue_list.append(item)
        elif diff_days == 0:
            item = OverdueDeviceItem(
                device_id=d.id,
                device_name=d.device_name,
                device_nickname=d.device_nickname,
                serial_number=d.serial_number,
                device_type=d.device_type,
                assigned_user_name=user_name,
                issued_to=d.issued_to,
                issued_to_email=d.issued_to_email,
                project_name=d.project_name,
                division=d.division,
                date_of_return=d.date_of_return,
                days_overdue=0,
                status_label="due_today",
            )
            overdue_list.append(item)
        elif d.date_of_return <= next_week:
            item = OverdueDeviceItem(
                device_id=d.id,
                device_name=d.device_name,
                device_nickname=d.device_nickname,
                serial_number=d.serial_number,
                device_type=d.device_type,
                assigned_user_name=user_name,
                issued_to=d.issued_to,
                issued_to_email=d.issued_to_email,
                project_name=d.project_name,
                division=d.division,
                date_of_return=d.date_of_return,
                days_overdue=diff_days,  # negative
                status_label="due_soon",
            )
            due_soon_list.append(item)

    overdue_list.sort(key=lambda x: x.days_overdue, reverse=True)
    due_soon_list.sort(key=lambda x: x.days_overdue, reverse=True)

    total_assigned = db.scalar(
        select(func.count()).select_from(Device).where(Device.assigned_user_id.is_not(None))
    ) or 0

    return ReturnsOverview(
        overdue_count=len(overdue_list),
        due_soon_count=len(due_soon_list),
        total_assigned=total_assigned,
        overdue_devices=overdue_list,
        due_soon_devices=due_soon_list,
    )


@router.post("/returns/{device_id}/extend")
def extend_return_date(
    device_id: UUID,
    payload: ReturnExtendPayload,
    db: DbSession,
    current_user: ManagerOrAdmin,
):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    old_return_date = device.date_of_return
    device.date_of_return = payload.new_return_date

    db.add(
        AssignmentHistory(
            device_id=device.id,
            from_user_id=device.assigned_user_id,
            to_user_id=device.assigned_user_id,
            changed_by=current_user.id,
            date_of_return=payload.new_return_date,
            notes=f"Return date extended from {old_return_date} to {payload.new_return_date}. Reason: {payload.extension_reason or 'No reason provided'}",
        )
    )
    db.commit()
    return {"status": "ok", "message": "Return date successfully extended", "new_date": payload.new_return_date}


@router.post("/returns/{device_id}/return")
def process_device_return(
    device_id: UUID,
    payload: ProcessReturnPayload,
    db: DbSession,
    current_user: ManagerOrAdmin,
):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    old_user = device.assigned_user_id
    old_issued_to = device.issued_to
    old_project = device.project_name

    # Clear assignment
    device.assigned_user_id = None
    device.issued_to = None
    device.issued_to_email = None
    device.project_name = None
    device.project_manager = None
    device.date_of_return = None

    db.add(
        AssignmentHistory(
            device_id=device.id,
            from_user_id=old_user,
            to_user_id=None,
            changed_by=current_user.id,
            from_issued_to=old_issued_to,
            to_issued_to=None,
            project_name=old_project,
            notes=f"Device returned. Condition: {payload.condition}. Notes: {payload.return_notes or 'None'}",
        )
    )
    db.commit()
    return {"status": "ok", "message": "Device returned successfully and added back to available pool"}


# ==========================================
# 4. AUDIT & PHYSICAL VERIFICATION
# ==========================================

@router.get("/audits", response_model=list[AuditLogRead])
def list_audits(
    db: DbSession,
    _: CurrentUser,
    cycle: str | None = Query(None),
    device_id: UUID | None = Query(None),
) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .options(
            joinedload(AuditLog.device),
            joinedload(AuditLog.auditor),
        )
        .order_by(AuditLog.created_at.desc())
    )

    if cycle:
        stmt = stmt.where(AuditLog.audit_cycle == cycle)
    if device_id:
        stmt = stmt.where(AuditLog.device_id == device_id)

    return list(db.scalars(stmt).unique().all())


@router.post("/audits", response_model=AuditLogRead, status_code=status.HTTP_201_CREATED)
def record_audit(
    payload: AuditRecordCreate,
    db: DbSession,
    current_user: ManagerOrAdmin,
) -> AuditLog:
    device = db.get(Device, payload.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    audit_entry = AuditLog(
        device_id=payload.device_id,
        auditor_id=current_user.id,
        audit_cycle=payload.audit_cycle,
        physical_status=payload.physical_status,
        verified_location=payload.verified_location or device.resident_location,
        notes=payload.notes,
    )
    db.add(audit_entry)

    # Sync device audit status
    if payload.physical_status == PhysicalAuditStatus.confirmed:
        device.audit_status = AuditStatus.confirmed
    elif payload.physical_status == PhysicalAuditStatus.disputed:
        device.audit_status = AuditStatus.disputed
    elif payload.physical_status == PhysicalAuditStatus.missing:
        device.status = DeviceStatus.lost
        device.audit_status = AuditStatus.disputed
    elif payload.physical_status == PhysicalAuditStatus.damaged:
        device.audit_status = AuditStatus.disputed

    if payload.verified_location:
        device.resident_location = payload.verified_location

    db.commit()

    stmt = (
        select(AuditLog)
        .options(
            joinedload(AuditLog.device),
            joinedload(AuditLog.auditor),
        )
        .where(AuditLog.id == audit_entry.id)
    )
    return db.scalar(stmt)


@router.get("/audits/cycles", response_model=list[AuditCycleSummary])
def get_audit_cycles_summary(db: DbSession, _: CurrentUser) -> list[AuditCycleSummary]:
    total_devices = db.scalar(select(func.count()).select_from(Device)) or 1

    distinct_cycles = db.scalars(
        select(AuditLog.audit_cycle).distinct()
    ).all()

    if not distinct_cycles:
        # Default current quarter
        now = datetime.now()
        q = (now.month - 1) // 3 + 1
        distinct_cycles = [f"{now.year}-Q{q}"]

    summaries = []
    for c in distinct_cycles:
        logs = db.scalars(select(AuditLog).where(AuditLog.audit_cycle == c)).all()
        audited_device_ids = {l.device_id for l in logs}
        audited_count = len(audited_device_ids)

        confirmed = sum(1 for l in logs if l.physical_status == PhysicalAuditStatus.confirmed)
        missing = sum(1 for l in logs if l.physical_status == PhysicalAuditStatus.missing)
        damaged = sum(1 for l in logs if l.physical_status == PhysicalAuditStatus.damaged)
        disputed = sum(1 for l in logs if l.physical_status == PhysicalAuditStatus.disputed)

        summaries.append(
            AuditCycleSummary(
                audit_cycle=c,
                total_devices=total_devices,
                audited_devices=audited_count,
                completion_percentage=round((audited_count / total_devices) * 100, 1),
                confirmed_count=confirmed,
                missing_count=missing,
                damaged_count=damaged,
                disputed_count=disputed,
            )
        )

    return summaries


# ==========================================
# 5. DEPARTMENT & PROJECT ASSET ALLOCATION
# ==========================================

@router.get("/allocations", response_model=AllocationSummary)
def get_allocations_summary(db: DbSession, _: CurrentUser) -> AllocationSummary:
    total = db.scalar(select(func.count()).select_from(Device)) or 0
    assigned = db.scalar(
        select(func.count()).select_from(Device).where(
            or_(Device.assigned_user_id.is_not(None), Device.issued_to.is_not(None))
        )
    ) or 0
    unassigned = total - assigned
    utilization = round((assigned / total * 100), 1) if total > 0 else 0.0

    today = date.today()

    # By Division / Department
    division_rows = db.execute(
        select(
            func.coalesce(Device.division, "Unassigned"),
            func.count(Device.id),
        ).group_by(Device.division)
    ).all()

    by_division = []
    for div_name, count in division_rows:
        overdue = db.scalar(
            select(func.count())
            .select_from(Device)
            .where(
                Device.division == div_name,
                Device.date_of_return.is_not(None),
                Device.date_of_return < today,
            )
        ) or 0
        by_division.append(
            AllocationItem(
                name=div_name,
                device_count=count,
                percentage=round((count / total * 100), 1) if total else 0.0,
                overdue_count=overdue,
            )
        )

    # By Project
    project_rows = db.execute(
        select(
            func.coalesce(Device.project_name, "Unassigned / Bench"),
            func.count(Device.id),
        ).group_by(Device.project_name)
    ).all()

    by_project = []
    for proj_name, count in project_rows:
        overdue = db.scalar(
            select(func.count())
            .select_from(Device)
            .where(
                Device.project_name == proj_name,
                Device.date_of_return.is_not(None),
                Device.date_of_return < today,
            )
        ) or 0
        by_project.append(
            AllocationItem(
                name=proj_name,
                device_count=count,
                percentage=round((count / total * 100), 1) if total else 0.0,
                overdue_count=overdue,
            )
        )

    # By Location
    location_rows = db.execute(
        select(
            func.coalesce(Device.resident_location, "HQ - Main"),
            func.count(Device.id),
        ).group_by(Device.resident_location)
    ).all()

    by_location = []
    for loc_name, count in location_rows:
        by_location.append(
            AllocationItem(
                name=loc_name,
                device_count=count,
                percentage=round((count / total * 100), 1) if total else 0.0,
                overdue_count=0,
            )
        )

    by_division.sort(key=lambda x: x.device_count, reverse=True)
    by_project.sort(key=lambda x: x.device_count, reverse=True)
    by_location.sort(key=lambda x: x.device_count, reverse=True)

    return AllocationSummary(
        total_devices=total,
        assigned_devices=assigned,
        unassigned_devices=unassigned,
        utilization_rate=utilization,
        by_division=by_division,
        by_project=by_project,
        by_location=by_location,
    )
