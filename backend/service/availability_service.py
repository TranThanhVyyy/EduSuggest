"""GĐ3.5 Expert Availability Management Service (YeuCauTamNgungChuyenGia).

Business rules:
- Max pause duration read from CauHinhPhanCong.thoiGianTamNgungToiDaNgay (default 30 days).
- Half-open UTC interval [ngayBatDau, ngayKetThuc).
- No overlapping PENDING or APPROVED requests for the same expert.
- Strict ARCH-05 lock ordering: ALWAYS locks NguoiDung FOR UPDATE -> ChuyenGia FOR UPDATE
  before checking overlap / creating / approving / cancelling so concurrent assignment
  and approval serialize without deadlocks!
- NEVER cancels existing active assignments when pause is approved.
- Wakes WAITING_ELIGIBLE jobs cleanly when an approved pause ends or is revoked.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import ChuyenGia, YeuCauTamNgungChuyenGia
from repository import assignment_repository
from service import assignment_queue_service, notification_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
    _require_verified_expert,
)

ACTIVE_OR_PENDING_AVAILABILITY_STATUSES = ("PENDING", "APPROVED")


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _has_overlapping_request(
    db: Session,
    *,
    expert_id: int,
    start_at: datetime,
    end_at: datetime,
    statuses: tuple[str, ...] = ACTIVE_OR_PENDING_AVAILABILITY_STATUSES,
    exclude_request_id: int | None = None,
) -> bool:
    """Half-open interval [a, b) overlaps [c, d) iff a < d AND b > c."""
    conditions = [
        YeuCauTamNgungChuyenGia.maChuyenGia == expert_id,
        YeuCauTamNgungChuyenGia.trangThai.in_(statuses),
        YeuCauTamNgungChuyenGia.ngayBatDau < end_at,
        YeuCauTamNgungChuyenGia.ngayKetThuc > start_at,
    ]
    if exclude_request_id is not None:
        conditions.append(YeuCauTamNgungChuyenGia.maYeuCau != exclude_request_id)
    cnt = db.scalar(select(func.count(YeuCauTamNgungChuyenGia.maYeuCau)).where(*conditions))
    return bool(cnt and int(cnt) > 0)


def create_availability_request(
    db: Session,
    *,
    user_id: int,
    start_at: datetime,
    end_at: datetime,
    reason: str,
    now: datetime | None = None,
) -> YeuCauTamNgungChuyenGia:
    """EXPERT submits a new pause request (PENDING) under ARCH-05 lock."""
    ts = now or _utc_now()
    if end_at <= start_at:
        raise WorkflowConflictError("Thời điểm kết thúc phải lớn hơn thời điểm bắt đầu.")
    if end_at <= ts:
        raise WorkflowConflictError("Thời điểm kết thúc tạm ngừng phải ở trong tương lai.")

    cfg = assignment_repository.get_singleton_config(db)
    max_days = int(cfg.thoiGianTamNgungToiDaNgay or 30)
    if (end_at - start_at) > timedelta(days=max_days):
        raise WorkflowConflictError(
            f"Thời gian tạm ngừng không được vượt quá {max_days} ngày theo cấu hình hệ thống."
        )

    # ARCH-05: _require_verified_expert(for_update=True) locks NguoiDung BEFORE ChuyenGia!
    expert = _require_verified_expert(db, user_id, for_update=True)

    if _has_overlapping_request(
        db,
        expert_id=int(expert.maChuyenGia),
        start_at=start_at,
        end_at=end_at,
    ):
        raise WorkflowConflictError(
            "Khoảng thời gian tạm ngừng bị chồng lấn với một yêu cầu đang chờ duyệt hoặc đã phê duyệt."
        )

    req = YeuCauTamNgungChuyenGia(
        maChuyenGia=int(expert.maChuyenGia),
        ngayBatDau=start_at,
        ngayKetThuc=end_at,
        lyDo=reason.strip(),
        trangThai="PENDING",
        ngayGuiYeuCau=ts,
        ngayCapNhat=ts,
    )
    db.add(req)
    db.flush()

    notification_service.notify_active_admins(
        db,
        notification_type="AVAILABILITY_REQUESTED",
        title="Yêu cầu tạm ngừng nhận nhiệm vụ mới",
        body=(
            f"Chuyên gia #{expert.maChuyenGia} gửi yêu cầu tạm ngừng từ "
            f"{start_at.strftime('%Y-%m-%d %H:%M')} đến {end_at.strftime('%Y-%m-%d %H:%M')} (UTC)."
        ),
        event_key=f"AVAIL_REQ:{req.maYeuCau}",
        payload={"maYeuCau": int(req.maYeuCau), "maChuyenGia": int(expert.maChuyenGia)},
        now=ts,
    )
    db.commit()
    db.refresh(req)
    return req


def list_my_availability_requests(
    db: Session,
    *,
    user_id: int,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[YeuCauTamNgungChuyenGia]:
    expert = _require_verified_expert(db, user_id)
    stmt = select(YeuCauTamNgungChuyenGia).where(
        YeuCauTamNgungChuyenGia.maChuyenGia == expert.maChuyenGia
    )
    if status:
        stmt = stmt.where(YeuCauTamNgungChuyenGia.trangThai == status)
    return list(
        db.scalars(
            stmt.order_by(
                YeuCauTamNgungChuyenGia.ngayGuiYeuCau.desc(),
                YeuCauTamNgungChuyenGia.maYeuCau.desc(),
            )
            .offset(offset)
            .limit(min(limit, 100))
        ).all()
    )


def cancel_my_availability_request(
    db: Session,
    *,
    user_id: int,
    request_id: int,
    reason: str,
    now: datetime | None = None,
) -> YeuCauTamNgungChuyenGia:
    """EXPERT cancels own PENDING request, or APPROVED request before ngayBatDau."""
    ts = now or _utc_now()
    expert = _require_verified_expert(db, user_id, for_update=True)
    from service import eligibility_service

    eligibility_service.lock_expert_eligibility(db, int(expert.maChuyenGia))
    req = db.scalars(
        select(YeuCauTamNgungChuyenGia)
        .where(YeuCauTamNgungChuyenGia.maYeuCau == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if req is None or int(req.maChuyenGia) != int(expert.maChuyenGia):
        raise WorkflowForbiddenError("Bạn không có quyền hủy yêu cầu tạm ngừng này.")

    if req.trangThai == "PENDING":
        pass
    elif req.trangThai == "APPROVED" and ts < req.ngayBatDau:
        pass
    else:
        raise WorkflowConflictError(
            f"Không thể hủy yêu cầu ở trạng thái {req.trangThai} hoặc đã đến thời điểm hiệu lực."
        )

    was_approved = req.trangThai == "APPROVED"
    req.trangThai = "CANCELLED"
    req.ngayHuy = ts
    req.lyDoHuy = reason.strip()
    req.ngayCapNhat = ts
    db.commit()
    db.refresh(req)

    if was_approved:
        assignment_queue_service.wake_waiting_eligible_jobs(db, limit=20, now=ts)
        db.commit()
    return req


# =====================================================================
# ADMIN Availability Management
# =====================================================================
def admin_list_availability_requests(
    db: Session,
    *,
    status: str | None = None,
    expert_id: int | None = None,
    active_now: bool = False,
    limit: int = 50,
    offset: int = 0,
    now: datetime | None = None,
) -> list[YeuCauTamNgungChuyenGia]:
    ts = now or _utc_now()
    stmt = select(YeuCauTamNgungChuyenGia)
    if status:
        stmt = stmt.where(YeuCauTamNgungChuyenGia.trangThai == status)
    if expert_id is not None:
        stmt = stmt.where(YeuCauTamNgungChuyenGia.maChuyenGia == expert_id)
    if active_now:
        stmt = stmt.where(
            YeuCauTamNgungChuyenGia.trangThai == "APPROVED",
            YeuCauTamNgungChuyenGia.ngayBatDau <= ts,
            YeuCauTamNgungChuyenGia.ngayKetThuc > ts,
        )
    return list(
        db.scalars(
            stmt.order_by(
                YeuCauTamNgungChuyenGia.ngayGuiYeuCau.desc(),
                YeuCauTamNgungChuyenGia.maYeuCau.desc(),
            )
            .offset(offset)
            .limit(min(limit, 100))
        ).all()
    )


def admin_get_availability_request(
    db: Session, *, request_id: int
) -> YeuCauTamNgungChuyenGia:
    req = db.get(YeuCauTamNgungChuyenGia, request_id)
    if req is None:
        raise WorkflowNotFoundError("Không tìm thấy yêu cầu tạm ngừng.")
    return req


def admin_approve_availability(
    db: Session,
    *,
    admin_user_id: int,
    request_id: int,
    note: str | None = None,
    now: datetime | None = None,
) -> YeuCauTamNgungChuyenGia:
    """ADMIN approves a PENDING availability request under ARCH-05 lock (NguoiDung -> ChuyenGia).

    NEVER cancels already-assigned active assignments!
    """
    ts = now or _utc_now()
    req_probe = db.get(YeuCauTamNgungChuyenGia, request_id)
    if req_probe is None:
        raise WorkflowNotFoundError("Không tìm thấy yêu cầu tạm ngừng.")
    exp_probe = db.get(ChuyenGia, req_probe.maChuyenGia)
    if exp_probe is None or exp_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia.")

    # ARCH-05: Lock NguoiDung BEFORE ChuyenGia -> serializes with Assignment Engine!
    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db,
        user_id=int(exp_probe.maNguoiDung),
        expert_id=int(req_probe.maChuyenGia),
    )
    from service import eligibility_service

    eligibility_service.lock_expert_eligibility(db, int(locked_expert.maChuyenGia))
    req = db.scalars(
        select(YeuCauTamNgungChuyenGia)
        .where(YeuCauTamNgungChuyenGia.maYeuCau == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if req is None:
        raise WorkflowNotFoundError("Không tìm thấy yêu cầu tạm ngừng.")
    if req.trangThai != "PENDING":
        raise WorkflowConflictError(
            f"Chỉ có thể phê duyệt yêu cầu đang ở trạng thái PENDING (hiện tại: {req.trangThai})."
        )
    if req.ngayKetThuc <= ts:
        req.trangThai = "EXPIRED"
        req.ngayCapNhat = ts
        db.commit()
        raise WorkflowConflictError("Yêu cầu tạm ngừng đã quá thời điểm kết thúc nên tự động hết hạn.")

    if _has_overlapping_request(
        db,
        expert_id=int(locked_expert.maChuyenGia),
        start_at=req.ngayBatDau,
        end_at=req.ngayKetThuc,
        statuses=("APPROVED",),
        exclude_request_id=int(req.maYeuCau),
    ):
        raise WorkflowConflictError(
            "Không thể phê duyệt vì bị chồng lấn với lịch tạm ngừng đã được phê duyệt khác."
        )

    req.trangThai = "APPROVED"
    req.maNguoiXuLy = admin_user_id
    req.ngayXuLy = ts
    req.ghiChuXuLy = note.strip() if note else None
    req.ngayCapNhat = ts
    db.flush()

    notification_service.create_notification_idempotent(
        db,
        recipient_user_id=int(locked_user.maNguoiDung),
        notification_type="AVAILABILITY_APPROVED",
        title="Yêu cầu tạm ngừng đã được phê duyệt",
        body=(
            f"Yêu cầu tạm ngừng #{req.maYeuCau} đã được phê duyệt "
            f"({req.ngayBatDau.strftime('%Y-%m-%d %H:%M')} - {req.ngayKetThuc.strftime('%Y-%m-%d %H:%M')} UTC). "
            "Lưu ý: bạn vẫn chịu trách nhiệm hoàn thành các nhiệm vụ đã được giao trước đó."
        ),
        event_key=f"AVAIL_APPROVED:{req.maYeuCau}",
        payload={"maYeuCau": int(req.maYeuCau)},
        now=ts,
    )
    db.commit()
    db.refresh(req)
    return req


def admin_reject_availability(
    db: Session,
    *,
    admin_user_id: int,
    request_id: int,
    note: str,
    now: datetime | None = None,
) -> YeuCauTamNgungChuyenGia:
    """ADMIN rejects a PENDING availability request with mandatory reason."""
    ts = now or _utc_now()
    req_probe = db.get(YeuCauTamNgungChuyenGia, request_id)
    if req_probe is None:
        raise WorkflowNotFoundError("Không tìm thấy yêu cầu tạm ngừng.")
    exp_probe = db.get(ChuyenGia, req_probe.maChuyenGia)
    if exp_probe is None or exp_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia.")

    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db,
        user_id=int(exp_probe.maNguoiDung),
        expert_id=int(req_probe.maChuyenGia),
    )
    from service import eligibility_service

    eligibility_service.lock_expert_eligibility(db, int(locked_expert.maChuyenGia))
    req = db.scalars(
        select(YeuCauTamNgungChuyenGia)
        .where(YeuCauTamNgungChuyenGia.maYeuCau == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if req is None:
        raise WorkflowNotFoundError("Không tìm thấy yêu cầu tạm ngừng.")
    if req.trangThai != "PENDING":
        raise WorkflowConflictError(
            f"Chỉ có thể từ chối yêu cầu đang PENDING (hiện tại: {req.trangThai})."
        )

    req.trangThai = "REJECTED"
    req.maNguoiXuLy = admin_user_id
    req.ngayXuLy = ts
    req.ghiChuXuLy = note.strip()
    req.ngayCapNhat = ts
    db.flush()

    notification_service.create_notification_idempotent(
        db,
        recipient_user_id=int(locked_user.maNguoiDung),
        notification_type="AVAILABILITY_REJECTED",
        title="Yêu cầu tạm ngừng bị từ chối",
        body=f"Yêu cầu tạm ngừng #{req.maYeuCau} đã bị từ chối. Lý do: {note.strip()}",
        event_key=f"AVAIL_REJECTED:{req.maYeuCau}",
        payload={"maYeuCau": int(req.maYeuCau)},
        now=ts,
    )
    db.commit()
    db.refresh(req)
    return req


def admin_revoke_availability(
    db: Session,
    *,
    admin_user_id: int,
    request_id: int,
    reason: str,
    now: datetime | None = None,
) -> YeuCauTamNgungChuyenGia:
    """ADMIN revokes an APPROVED availability request with mandatory reason + wakes queue."""
    ts = now or _utc_now()
    req_probe = db.get(YeuCauTamNgungChuyenGia, request_id)
    if req_probe is None:
        raise WorkflowNotFoundError("Không tìm thấy yêu cầu tạm ngừng.")
    exp_probe = db.get(ChuyenGia, req_probe.maChuyenGia)
    if exp_probe is None or exp_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia.")

    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db,
        user_id=int(exp_probe.maNguoiDung),
        expert_id=int(req_probe.maChuyenGia),
    )
    from service import eligibility_service

    eligibility_service.lock_expert_eligibility(db, int(locked_expert.maChuyenGia))
    req = db.scalars(
        select(YeuCauTamNgungChuyenGia)
        .where(YeuCauTamNgungChuyenGia.maYeuCau == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if req is None:
        raise WorkflowNotFoundError("Không tìm thấy yêu cầu tạm ngừng.")
    if req.trangThai != "APPROVED":
        raise WorkflowConflictError(
            f"Chỉ có thể thu hồi yêu cầu đang APPROVED (hiện tại: {req.trangThai})."
        )

    req.trangThai = "CANCELLED"
    req.ngayHuy = ts
    req.lyDoHuy = reason.strip()
    req.maNguoiXuLy = admin_user_id
    req.ngayXuLy = ts
    req.ngayCapNhat = ts
    db.flush()

    notification_service.create_notification_idempotent(
        db,
        recipient_user_id=int(locked_user.maNguoiDung),
        notification_type="AVAILABILITY_REVOKED",
        title="Lịch tạm ngừng đã bị thu hồi",
        body=f"Quản trị viên đã thu hồi lịch tạm ngừng #{req.maYeuCau}. Lý do: {reason.strip()}",
        event_key=f"AVAIL_REVOKED:{req.maYeuCau}",
        payload={"maYeuCau": int(req.maYeuCau)},
        now=ts,
    )
    db.commit()
    db.refresh(req)

    assignment_queue_service.wake_waiting_eligible_jobs(db, limit=20, now=ts)
    db.commit()
    return req


def complete_ended_availability_requests(
    db: Session,
    *,
    now: datetime | None = None,
    commit: bool = True,
) -> int:
    """Periodic worker task: mark ended APPROVED pauses COMPLETED & ended PENDING EXPIRED.

    Wakes WAITING_ELIGIBLE jobs ONCE if at least one APPROVED pause ended (no retry storm).
    """
    ts = now or _utc_now()
    candidate_expert_ids = list(
        db.scalars(
            select(YeuCauTamNgungChuyenGia.maChuyenGia)
            .where(
                YeuCauTamNgungChuyenGia.trangThai.in_(("APPROVED", "PENDING")),
                YeuCauTamNgungChuyenGia.ngayKetThuc <= ts,
            )
            .distinct()
            .order_by(YeuCauTamNgungChuyenGia.maChuyenGia)
        ).all()
    )
    if candidate_expert_ids:
        from service import eligibility_service

        eligibility_service.lock_experts_eligibility(db, [int(value) for value in candidate_expert_ids])
    ended_approved = list(
        db.scalars(
            select(YeuCauTamNgungChuyenGia)
            .where(
                YeuCauTamNgungChuyenGia.trangThai == "APPROVED",
                YeuCauTamNgungChuyenGia.ngayKetThuc <= ts,
            )
            .with_for_update(skip_locked=True)
        ).all()
    )
    for req in ended_approved:
        req.trangThai = "COMPLETED"
        req.ngayCapNhat = ts

    ended_pending = list(
        db.scalars(
            select(YeuCauTamNgungChuyenGia)
            .where(
                YeuCauTamNgungChuyenGia.trangThai == "PENDING",
                YeuCauTamNgungChuyenGia.ngayKetThuc <= ts,
            )
            .with_for_update(skip_locked=True)
        ).all()
    )
    for req in ended_pending:
        req.trangThai = "EXPIRED"
        req.ngayCapNhat = ts

    if ended_approved:
        db.flush()
        assignment_queue_service.wake_waiting_eligible_jobs(db, limit=20, now=ts)

    if commit and (ended_approved or ended_pending):
        db.commit()
    return len(ended_approved)
