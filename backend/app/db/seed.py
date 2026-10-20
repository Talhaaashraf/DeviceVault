from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.device import Device
from app.models.enums import DeviceStatus, DeviceType, OsType, UserRole
from app.models.user import User


def seed_database(db: Session) -> None:
    existing = db.scalar(select(User).where(User.email == "admin@company.com"))
    if existing:
        seed_management_data(db)
        return


    admin = User(
        full_name="System Admin",
        email="admin@company.com",
        password_hash=hash_password("Admin123!"),
        role=UserRole.admin,
        department="IT",
        is_active=True,
    )
    manager = User(
        full_name="Sara Manager",
        email="manager@company.com",
        password_hash=hash_password("Manager123!"),
        role=UserRole.manager,
        department="Operations",
        is_active=True,
    )
    viewer = User(
        full_name="View Only",
        email="viewer@company.com",
        password_hash=hash_password("Viewer123!"),
        role=UserRole.viewer,
        department="Finance",
        is_active=True,
    )
    db.add_all([admin, manager, viewer])
    db.flush()

    devices = [
        Device(
            device_name="iPhone 14 Pro",
            device_nickname="Ali's Work Phone",
            device_type=DeviceType.phone,
            os_type=OsType.ios,
            os_version="17.4.1",
            is_cellular=True,
            imei_number="356938035643809",
            serial_number="SN-IPHONE-001",
            mac_address="A1:B2:C3:D4:E5:F6",
            company="Main Office",
            assigned_user_id=manager.id,
            status=DeviceStatus.active,
            purchase_date=date(2024, 3, 15),
        ),
        Device(
            device_name="Samsung Galaxy S24",
            device_nickname="Ops Android Phone",
            device_type=DeviceType.phone,
            os_type=OsType.android,
            os_version="14",
            is_cellular=True,
            imei_number="490154203237518",
            serial_number="SN-GALAXY-002",
            mac_address="11:22:33:44:55:66",
            company="Main Office",
            assigned_user_id=None,
            status=DeviceStatus.active,
            purchase_date=date(2024, 6, 1),
        ),
        Device(
            device_name="iPad Pro 12.9",
            device_nickname="Design Wi-Fi iPad",
            device_type=DeviceType.tablet_ipad,
            os_type=OsType.ios,
            os_version="17.5",
            is_cellular=False,
            imei_number=None,
            serial_number="SN-IPAD-003",
            mac_address="AA:BB:CC:DD:EE:FF",
            company="Design Team",
            assigned_user_id=viewer.id,
            status=DeviceStatus.active,
            purchase_date=date(2023, 11, 20),
        ),
        Device(
            device_name="Samsung Galaxy Tab S9",
            device_nickname="Field Tablet",
            device_type=DeviceType.tablet_android,
            os_type=OsType.android,
            os_version="14",
            is_cellular=True,
            imei_number="353918101234567",
            serial_number="SN-TAB-004",
            mac_address="01:23:45:67:89:AB",
            company="Field Team",
            assigned_user_id=None,
            status=DeviceStatus.in_repair,
            purchase_date=date(2024, 1, 10),
        ),
        Device(
            device_name="Apple Watch Series 9",
            device_nickname="Admin Watch",
            device_type=DeviceType.smartwatch,
            os_type=OsType.watchos,
            os_version="10.3",
            is_cellular=False,
            imei_number=None,
            serial_number="SN-WATCH-005",
            mac_address="DE:AD:BE:EF:00:01",
            company="Main Office",
            assigned_user_id=admin.id,
            status=DeviceStatus.active,
            purchase_date=date(2024, 2, 2),
        ),
        Device(
            device_name="Google Pixel Watch 2",
            device_nickname="Retired Wear OS",
            device_type=DeviceType.smartwatch,
            os_type=OsType.wear_os,
            os_version="4.0",
            is_cellular=True,
            imei_number="359827104567890",
            serial_number="SN-WATCH-006",
            mac_address="CA:FE:BA:BE:12:34",
            company="Legacy Pool",
            assigned_user_id=None,
            status=DeviceStatus.retired,
            purchase_date=date(2022, 8, 8),
        ),
        Device(
            device_name="iPhone 12",
            device_nickname="Lost Device Case",
            device_type=DeviceType.phone,
            os_type=OsType.ios,
            os_version="16.7",
            is_cellular=True,
            imei_number="354281076543210",
            serial_number="SN-IPHONE-007",
            mac_address="AB:CD:EF:12:34:56",
            company="Main Office",
            assigned_user_id=None,
            status=DeviceStatus.lost,
            purchase_date=date(2021, 5, 5),
        ),
    ]
    db.add_all(devices)
    db.commit()

    seed_management_data(db)


def seed_management_data(db: Session) -> None:
    from datetime import date, timedelta
    from app.models.device_request import DeviceRequest
    from app.models.maintenance import MaintenanceTicket
    from app.models.audit import AuditLog
    from app.models.enums import RequestStatus, MaintenanceStatus, MaintenancePriority, PhysicalAuditStatus, AuditStatus

    # Check if requests exist
    if not db.scalar(select(DeviceRequest)):
        viewer = db.scalar(select(User).where(User.email == "viewer@company.com"))
        manager = db.scalar(select(User).where(User.email == "manager@company.com"))
        admin = db.scalar(select(User).where(User.email == "admin@company.com"))
        devices = db.scalars(select(Device)).all()

        if viewer and manager and devices:
            req1 = DeviceRequest(
                user_id=viewer.id,
                device_type=DeviceType.phone,
                os_preference=OsType.ios,
                project_name="Mobile Banking App",
                division="QA & Testing",
                reason="Need an iOS test phone for biometric auth testing",
                duration_days=14,
                date_needed=date.today(),
                status=RequestStatus.pending,
            )
            req2 = DeviceRequest(
                user_id=manager.id,
                device_type=DeviceType.tablet_android,
                os_preference=OsType.android,
                project_name="Field Operations",
                division="Operations",
                reason="Tablet needed for on-site client demonstrations",
                duration_days=30,
                date_needed=date.today() - timedelta(days=2),
                status=RequestStatus.approved,
                manager_notes="Approved for Q3 client visits.",
                reviewed_by_id=admin.id if admin else None,
            )
            db.add_all([req1, req2])

            # Ensure device return dates for demo
            if len(devices) > 0:
                devices[0].date_of_return = date.today() - timedelta(days=3)  # Overdue
                devices[0].division = "Engineering"
                devices[0].project_name = "Core Mobile App"
                devices[0].issued_to = "Sara Manager"
                devices[0].resident_location = "Karachi HQ - Lab 1"
            if len(devices) > 2:
                devices[2].date_of_return = date.today() + timedelta(days=4)  # Due soon
                devices[2].division = "UI/UX Design"
                devices[2].project_name = "Design System"
                devices[2].issued_to = "View Only"
                devices[2].resident_location = "Lahore Office"

            # Seed maintenance ticket
            repair_device = next((d for d in devices if d.status == DeviceStatus.in_repair), devices[0])
            m_ticket = MaintenanceTicket(
                device_id=repair_device.id,
                reported_by_id=manager.id,
                issue_title="Screen flicker and damaged charging port",
                issue_description="Screen intermittently blinks when tilted; USB-C port is loose.",
                priority=MaintenancePriority.high,
                repair_status=MaintenanceStatus.in_repair,
                vendor_name="Authorized Repair Center",
                estimated_cost=120.0,
                sent_date=date.today() - timedelta(days=5),
            )
            db.add(m_ticket)

            # Seed audit log for 2026-Q3
            now_year = date.today().year
            q_str = f"{now_year}-Q3"
            for d in devices[:3]:
                db.add(
                    AuditLog(
                        device_id=d.id,
                        auditor_id=admin.id if admin else manager.id,
                        audit_cycle=q_str,
                        physical_status=PhysicalAuditStatus.confirmed,
                        verified_location=d.resident_location or "HQ - Lab",
                        notes="Physical inspection passed. Serial number and MAC verified.",
                    )
                )
                d.audit_status = AuditStatus.confirmed

            db.commit()



DEMO_CREDENTIALS = {
    "admin@company.com": "Admin123!",
    "manager@company.com": "Manager123!",
    "viewer@company.com": "Viewer123!",
}


def demo_accounts_with_default_password(db: Session) -> list[str]:
    """Active seeded accounts that still use their published demo password."""
    found = []
    for email, password in DEMO_CREDENTIALS.items():
        user = db.scalar(select(User).where(User.email == email))
        if user and user.is_active and verify_password(password, user.password_hash):
            found.append(email)
    return found
