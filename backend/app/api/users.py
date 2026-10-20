from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DbSession, ManagerOrAdmin
from app.core.security import hash_password
from app.models.assignment import AssignmentHistory
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.enums import UserRole
from app.models.maintenance import MaintenanceTicket
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import UserBrief, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: DbSession, _: AdminUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


@router.get("/assignees", response_model=list[UserBrief])
def list_assignees(db: DbSession, _: ManagerOrAdmin) -> list[User]:
    return list(
        db.scalars(
            select(User).where(User.is_active.is_(True)).order_by(User.full_name.asc())
        ).all()
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, _: AdminUser) -> User:
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        department=payload.department,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: UserUpdate, db: DbSession, current_admin: AdminUser) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = payload.model_dump(exclude_unset=True)
    if user.id == current_admin.id:
        if data.get("is_active") is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")
        if "role" in data and data["role"] != UserRole.admin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove your own admin role")
    password = data.pop("password", None)
    if "email" in data and data["email"] is not None:
        data["email"] = data["email"].lower()
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.password_hash = hash_password(password)
    if password or data.get("is_active") is False:
        # Sign the user out everywhere when their password changes or the account is disabled
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: DbSession, current_admin: AdminUser) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

    # Clear device assignments pointing at this user
    db.execute(
        update(Device).where(Device.assigned_user_id == user_id).values(assigned_user_id=None)
    )
    # assignment_history.changed_by is RESTRICT — reassign to the acting admin
    db.execute(
        update(AssignmentHistory)
        .where(AssignmentHistory.changed_by == user_id)
        .values(changed_by=current_admin.id)
    )
    # Maintenance tickets and audit records are RESTRICT too — keep them, attributed to the acting admin
    db.execute(
        update(MaintenanceTicket)
        .where(MaintenanceTicket.reported_by_id == user_id)
        .values(reported_by_id=current_admin.id)
    )
    db.execute(update(AuditLog).where(AuditLog.auditor_id == user_id).values(auditor_id=current_admin.id))
    db.execute(
        update(AssignmentHistory)
        .where(AssignmentHistory.from_user_id == user_id)
        .values(from_user_id=None)
    )
    db.execute(
        update(AssignmentHistory)
        .where(AssignmentHistory.to_user_id == user_id)
        .values(to_user_id=None)
    )

    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User cannot be deleted because related records still reference them",
        )
