"""FastAPI router for GĐ3.5 Expert Availability Management & Notification Center.

Strictly enforces RBAC, ownership, `extra="forbid"` request schemas, and static-before-dynamic
route ordering.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies import AuthenticatedPrincipal, get_current_principal, require_roles
from config.database import get_db
from models import NguoiDung
from schemas.availability_notification import (
    AdminApproveAvailabilityRequest,
    AdminRejectAvailabilityRequest,
    AvailabilityRequestResponse,
    CancelAvailabilityRequest,
    CreateAvailabilityRequest,
    MarkAllReadResponse,
    NotificationItemResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from service import availability_service, notification_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)

router = APIRouter(tags=["availability-notifications"])


def _handle_err(exc: Exception) -> None:
    if isinstance(exc, WorkflowForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, WorkflowNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, WorkflowConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


# =====================================================================
# EXPERT Availability Management (Own Data Only)
# =====================================================================
@router.post(
    "/expert/availability",
    response_model=AvailabilityRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def expert_create_availability(
    payload: CreateAvailabilityRequest,
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return availability_service.create_availability_request(
            db,
            user_id=int(current_user.maNguoiDung),
            start_at=payload.ngayBatDau,
            end_at=payload.ngayKetThuc,
            reason=payload.lyDo,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.get(
    "/expert/availability",
    response_model=list[AvailabilityRequestResponse],
)
def expert_list_availability(
    req_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return availability_service.list_my_availability_requests(
            db,
            user_id=int(current_user.maNguoiDung),
            status=req_status,
            limit=limit,
            offset=offset,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.post(
    "/expert/availability/{request_id}/cancel",
    response_model=AvailabilityRequestResponse,
)
def expert_cancel_availability(
    request_id: int,
    payload: CancelAvailabilityRequest,
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return availability_service.cancel_my_availability_request(
            db,
            user_id=int(current_user.maNguoiDung),
            request_id=request_id,
            reason=payload.lyDoHuy,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


# =====================================================================
# ADMIN Availability Management
# =====================================================================
@router.get(
    "/admin/availability",
    response_model=list[AvailabilityRequestResponse],
)
def admin_list_availability(
    req_status: str | None = Query(default=None, alias="status"),
    expert_id: int | None = Query(default=None, ge=1),
    active_now: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return availability_service.admin_list_availability_requests(
        db,
        status=req_status,
        expert_id=expert_id,
        active_now=active_now,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/admin/availability/{request_id}",
    response_model=AvailabilityRequestResponse,
)
def admin_get_availability(
    request_id: int,
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return availability_service.admin_get_availability_request(
            db, request_id=request_id
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.post(
    "/admin/availability/{request_id}/approve",
    response_model=AvailabilityRequestResponse,
)
def admin_approve_availability(
    request_id: int,
    payload: AdminApproveAvailabilityRequest | None = None,
    admin_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return availability_service.admin_approve_availability(
            db,
            admin_user_id=int(admin_user.maNguoiDung),
            request_id=request_id,
            note=payload.ghiChuXuLy if payload is not None else None,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.post(
    "/admin/availability/{request_id}/reject",
    response_model=AvailabilityRequestResponse,
)
def admin_reject_availability(
    request_id: int,
    payload: AdminRejectAvailabilityRequest,
    admin_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return availability_service.admin_reject_availability(
            db,
            admin_user_id=int(admin_user.maNguoiDung),
            request_id=request_id,
            note=payload.ghiChuXuLy,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.post(
    "/admin/availability/{request_id}/revoke",
    response_model=AvailabilityRequestResponse,
)
def admin_revoke_availability(
    request_id: int,
    payload: CancelAvailabilityRequest,
    admin_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return availability_service.admin_revoke_availability(
            db,
            admin_user_id=int(admin_user.maNguoiDung),
            request_id=request_id,
            reason=payload.lyDoHuy,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


# =====================================================================
# Notification Center (Authenticated User Own Data Only)
# Static routes (/unread-count, /read-all) MUST stay before /{notification_id}
# =====================================================================
@router.get(
    "/notifications",
    response_model=NotificationListResponse,
)
def list_notifications(
    is_read: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    return notification_service.list_user_notifications(
        db,
        user_id=int(principal.user.maNguoiDung),
        is_read=is_read,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/notifications/unread-count",
    response_model=UnreadCountResponse,
)
def get_unread_notification_count(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    cnt = notification_service.count_unread_notifications(
        db, user_id=int(principal.user.maNguoiDung)
    )
    return {"unreadCount": cnt}


@router.post(
    "/notifications/read-all",
    response_model=MarkAllReadResponse,
)
def mark_all_notifications_read(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    updated = notification_service.mark_all_notifications_read(
        db, user_id=int(principal.user.maNguoiDung)
    )
    return {"updatedCount": updated}


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationItemResponse,
)
def mark_one_notification_read(
    notification_id: int,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    try:
        return notification_service.mark_notification_read(
            db,
            user_id=int(principal.user.maNguoiDung),
            notification_id=notification_id,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)
