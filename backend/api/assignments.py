"""FastAPI router for GĐ3.3 EXPERT & ADMIN Assignment Lifecycle APIs.

Route ordering discipline (Section 51):
- Static routes (`/admin/assignments/queue`, `/admin/assignments/workload`) are ALWAYS
  declared BEFORE dynamic `/{assignment_id}` routes so FastAPI never misroutes them.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies import require_roles
from config.database import get_db
from models import NguoiDung
from schemas.assignment_api import (
    AdminAssignmentConfigResponse,
    AdminAssignmentConfigUpdateRequest,
    AdminAssignmentResponse,
    AdminCancelAssignmentRequest,
    AdminExpertOverviewResponse,
    AdminExpertWorkloadItem,
    AdminManualAssignmentRequest,
    AdminQueueJobResponse,
    AssignmentDecisionRequest,
    DeclineAssignmentRequest,
    ExpertAssignmentDetailResponse,
    ExpertAssignmentSummaryResponse,
    SaveDraftRequest,
)
from service import assignment_lifecycle_service, assignment_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)

router = APIRouter(tags=["assignments"])


def _handle_workflow_error(exc: Exception) -> None:
    if isinstance(exc, WorkflowForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, WorkflowNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, WorkflowConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


# =====================================================================
# EXPERT Assignment Endpoints
# =====================================================================
@router.get("/expert/assignments", response_model=list[ExpertAssignmentSummaryResponse])
def expert_list_assignments(
    assignment_status: str | None = Query(default=None, alias="status"),
    target_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.list_my_assignments(
            db,
            current_user.maNguoiDung,
            status=assignment_status,
            target_type=target_type,
            limit=limit,
            offset=offset,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.get(
    "/expert/assignments/{assignment_id}",
    response_model=ExpertAssignmentDetailResponse,
)
def expert_get_assignment_detail(
    assignment_id: int,
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.get_my_assignment_detail(
            db, current_user.maNguoiDung, assignment_id
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.post(
    "/expert/assignments/{assignment_id}/accept",
    response_model=ExpertAssignmentSummaryResponse,
)
def expert_accept_assignment(
    assignment_id: int,
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.accept_assignment(
            db, current_user.maNguoiDung, assignment_id
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.post(
    "/expert/assignments/{assignment_id}/decline",
    response_model=ExpertAssignmentSummaryResponse,
)
def expert_decline_assignment(
    assignment_id: int,
    payload: DeclineAssignmentRequest,
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.decline_assignment(
            db,
            current_user.maNguoiDung,
            assignment_id,
            reason_code=payload.maLyDoTuChoi,
            explanation=payload.lyDoTuChoi,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.post(
    "/expert/assignments/{assignment_id}/start",
    response_model=ExpertAssignmentSummaryResponse,
)
def expert_start_assignment(
    assignment_id: int,
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.start_assignment_review(
            db, current_user.maNguoiDung, assignment_id
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.put(
    "/expert/assignments/{assignment_id}/draft",
    response_model=ExpertAssignmentSummaryResponse,
)
def expert_save_draft(
    assignment_id: int,
    payload: SaveDraftRequest,
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.save_assignment_draft(
            db,
            current_user.maNguoiDung,
            assignment_id,
            draft_data=payload.banNhapDanhGia,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.post("/expert/assignments/{assignment_id}/decision")
def expert_submit_decision(
    assignment_id: int,
    payload: AssignmentDecisionRequest,
    current_user: NguoiDung = Depends(require_roles("EXPERT")),
    db: Session = Depends(get_db),
):
    try:
        target, review, pc = assignment_lifecycle_service.submit_assignment_decision(
            db,
            current_user.maNguoiDung,
            assignment_id,
            trang_thai=payload.trangThai,
            noi_dung_danh_gia=payload.noiDungDanhGia,
            ghi_chu=payload.ghiChu,
            diem_ky_thuat=payload.diemKyThuat,
            diem_noi_dung=payload.diemNoiDung,
        )
        return {
            "maPhanCong": int(pc.maPhanCong),
            "trangThaiPhanCong": pc.trangThai,
            "maDanhGia": int(review.maDanhGia),
            "ketQuaDuyet": target.trangThaiDuyet,
            "trangThaiHienThi": target.trangThaiHienThi,
        }
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


# =====================================================================
# ADMIN Assignment Monitoring & Exception Endpoints (Static BEFORE Dynamic!)
# =====================================================================
@router.get("/admin/assignments", response_model=list[AdminAssignmentResponse])
def admin_list_assignments(
    assignment_status: str | None = Query(default=None, alias="status"),
    target_type: str | None = Query(default=None),
    expert_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return assignment_lifecycle_service.admin_list_assignments(
        db,
        status=assignment_status,
        target_type=target_type,
        expert_id=expert_id,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/assignments/overview", response_model=AdminExpertOverviewResponse)
def admin_get_expert_overview(
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return assignment_lifecycle_service.admin_get_expert_overview(db)


@router.get("/admin/assignments/config", response_model=AdminAssignmentConfigResponse)
def admin_get_assignment_config(
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return assignment_lifecycle_service.admin_get_assignment_config(db)


@router.patch("/admin/assignments/config", response_model=AdminAssignmentConfigResponse)
def admin_update_assignment_config(
    payload: AdminAssignmentConfigUpdateRequest,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.admin_update_assignment_config(
            db,
            admin_user_id=int(current_user.maNguoiDung),
            updates=payload.model_dump(exclude_unset=True),
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.post(
    "/admin/assignments/manual",
    response_model=AdminAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_manual_assign_expert(
    payload: AdminManualAssignmentRequest,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        pc = assignment_service.assign_expert_manually(
            db,
            admin_user_id=int(current_user.maNguoiDung),
            target_type=payload.loaiDoiTuong,
            target_id=payload.maDoiTuong,
            expert_id=payload.maChuyenGia,
            reason=payload.lyDoPhanCong,
        )
        return assignment_lifecycle_service.admin_get_assignment_detail(db, int(pc.maPhanCong))
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.get("/admin/assignments/queue", response_model=list[AdminQueueJobResponse])
def admin_list_queue(
    job_status: str | None = Query(default=None, alias="status"),
    target_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return assignment_lifecycle_service.admin_list_queue_jobs(
        db, status=job_status, target_type=target_type, limit=limit, offset=offset
    )


@router.get("/admin/assignments/workload", response_model=list[AdminExpertWorkloadItem])
def admin_get_workload(
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    return assignment_lifecycle_service.admin_get_workload_summary(db)


@router.post(
    "/admin/assignments/queue/{job_id}/retry",
    response_model=AdminQueueJobResponse,
)
def admin_retry_queue_job(
    job_id: int,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.admin_retry_queue_job(
            db, current_user.maNguoiDung, job_id
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.get("/admin/assignments/{assignment_id}", response_model=AdminAssignmentResponse)
def admin_get_assignment_detail(
    assignment_id: int,
    _: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.admin_get_assignment_detail(db, assignment_id)
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)


@router.post(
    "/admin/assignments/{assignment_id}/cancel",
    response_model=AdminAssignmentResponse,
)
def admin_cancel_assignment(
    assignment_id: int,
    payload: AdminCancelAssignmentRequest,
    current_user: NguoiDung = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    try:
        return assignment_lifecycle_service.admin_cancel_assignment(
            db,
            current_user.maNguoiDung,
            assignment_id,
            reason=payload.lyDoHuy,
            requeue=payload.requeue,
        )
    except (WorkflowForbiddenError, WorkflowNotFoundError, WorkflowConflictError) as exc:
        _handle_workflow_error(exc)
