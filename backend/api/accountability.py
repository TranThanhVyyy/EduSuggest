"""FastAPI router for GĐ3.4 EXPERT & ADMIN Accountability, Violation & Unlock APIs.

Strictly enforces RBAC, ownership, `extra="forbid"` request schemas, and static-before-dynamic
route ordering. Never exposes update/delete endpoints on NhatKyKyLuatChuyenGia (insert-only).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import require_roles
from config.database import get_db
from models import ChuyenGia, NguoiDung, ViPhamChuyenGia
from schemas.accountability import (
    AdminAccountabilityConfigUpdateRequest,
    AdminExpertAccountabilityItem,
    AdminLockUnlockRequest,
    AdminViolationDecisionRequest,
    AuditLogResponse,
    ExpertAccountabilityPolicyResponse,
    ExpertAccountabilitySummaryResponse,
    ViolationResponse,
)
from service import accountability_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)

router = APIRouter(tags=["accountability"])


def _handle_err(exc: Exception) -> None:
    if isinstance(exc, WorkflowForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, WorkflowNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, WorkflowConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


# =====================================================================
# EXPERT Read-only Accountability Endpoints (Own Data Only)
# =====================================================================
@router.get(
    "/expert/accountability/summary",
    response_model=ExpertAccountabilitySummaryResponse,
)
def expert_accountability_summary(
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    profile = db.scalars(
        select(ChuyenGia).where(ChuyenGia.maNguoiDung == current_user.maNguoiDung)
    ).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ chuyên gia.",
        )
    try:
        return accountability_service.get_expert_accountability_summary(
            db, expert_id=int(profile.maChuyenGia)
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.get(
    "/expert/accountability/violations",
    response_model=list[ViolationResponse],
)
def expert_accountability_violations(
    violation_status: str | None = Query(default=None, alias="status"),
    cycle: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    profile = db.scalars(
        select(ChuyenGia).where(ChuyenGia.maNguoiDung == current_user.maNguoiDung)
    ).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ chuyên gia.",
        )
    return accountability_service.list_violations(
        db,
        expert_id=int(profile.maChuyenGia),
        status=violation_status,
        cycle=cycle,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/expert/accountability/policy",
    response_model=ExpertAccountabilityPolicyResponse,
)
def expert_accountability_policy(
    _: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    return accountability_service.get_accountability_policy(db)


# =====================================================================
# ADMIN Accountability, Violation Review, Lock/Unlock & Audit Endpoints
# =====================================================================
@router.get(
    "/admin/accountability/experts",
    response_model=list[AdminExpertAccountabilityItem],
)
def admin_list_accountability_experts(
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return accountability_service.admin_list_experts_accountability(db)


@router.get(
    "/admin/accountability/experts/{expert_id}",
    response_model=ExpertAccountabilitySummaryResponse,
)
def admin_get_accountability_expert(
    expert_id: int,
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return accountability_service.get_expert_accountability_summary(
            db, expert_id=expert_id
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.post("/admin/accountability/experts/{expert_id}/lock")
def admin_lock_expert_account(
    expert_id: int,
    payload: AdminLockUnlockRequest,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return accountability_service.admin_lock_expert(
            db,
            admin_user_id=current_user.maNguoiDung,
            expert_id=expert_id,
            reason=payload.lyDo,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.post("/admin/accountability/experts/{expert_id}/unlock")
def admin_unlock_expert_account(
    expert_id: int,
    payload: AdminLockUnlockRequest,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return accountability_service.admin_unlock_expert(
            db,
            admin_user_id=current_user.maNguoiDung,
            expert_id=expert_id,
            reason=payload.lyDo,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.get(
    "/admin/accountability/violations",
    response_model=list[ViolationResponse],
)
def admin_list_violations(
    expert_id: int | None = Query(default=None),
    violation_status: str | None = Query(default=None, alias="status"),
    cycle: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return accountability_service.list_violations(
        db,
        expert_id=expert_id,
        status=violation_status,
        cycle=cycle,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/admin/accountability/violations/{violation_id}",
    response_model=ViolationResponse,
)
def admin_get_violation(
    violation_id: int,
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    vp = db.get(ViPhamChuyenGia, violation_id)
    if vp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy bản ghi vi phạm.",
        )
    return vp


@router.post(
    "/admin/accountability/violations/{violation_id}/confirm",
    response_model=ViolationResponse,
)
def admin_confirm_violation(
    violation_id: int,
    payload: AdminViolationDecisionRequest,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        vp, _ = accountability_service.admin_confirm_violation(
            db,
            admin_user_id=current_user.maNguoiDung,
            violation_id=violation_id,
            note=payload.ghiChuXuLy,
        )
        return vp
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.post(
    "/admin/accountability/violations/{violation_id}/exempt",
    response_model=ViolationResponse,
)
def admin_exempt_violation(
    violation_id: int,
    payload: AdminViolationDecisionRequest,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return accountability_service.admin_exempt_violation(
            db,
            admin_user_id=current_user.maNguoiDung,
            violation_id=violation_id,
            note=payload.ghiChuXuLy,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)


@router.get(
    "/admin/accountability/audit-logs",
    response_model=list[AuditLogResponse],
)
def admin_list_audit_logs(
    expert_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    cycle: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return accountability_service.list_audit_logs(
        db,
        expert_id=expert_id,
        action=action,
        cycle=cycle,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/admin/accountability/config",
    response_model=ExpertAccountabilityPolicyResponse,
)
def admin_update_accountability_config(
    payload: AdminAccountabilityConfigUpdateRequest,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return accountability_service.admin_update_accountability_config(
            db,
            admin_user_id=current_user.maNguoiDung,
            updates=payload.model_dump(exclude_unset=True),
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_err(exc)
