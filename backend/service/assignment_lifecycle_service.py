"""GĐ3.3B Assignment Lifecycle Service, Centralized Ownership Guard (SEC-02 Closure),
Automatic Reassignment, and ADMIN Exception Handling.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models import (
    BaiHoc,
    ChuyenGia,
    DanhGiaChuyenGia,
    HangDoiPhanCong,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    PhanCongKiemDuyet,
    TaiLieu,
)
from repository import assignment_repository
from schemas.assignment import TargetType
from service import assignment_queue_service, notification_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
    _require_verified_expert,
)

MAX_DRAFT_JSON_BYTES = 65_536
VALID_DECLINE_REASONS = {
    "WORKLOAD_PERSONAL",
    "CONFLICT_OF_INTEREST",
    "SYSTEM_MISASSIGNMENT",
    "TECHNICAL_ISSUE",
    "OTHER",
}


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _material_access_reference(material: TaiLieu) -> str | None:
    value = material.duongDanTep
    if value and value.startswith("private://materials/"):
        return f"/api/materials/{int(material.maTaiLieu)}/file"
    return value


def _allowed_actions_for_assignment(pc: PhanCongKiemDuyet, now: datetime) -> list[str]:
    if pc.trangThai == "ASSIGNED":
        if now < pc.hanTiepNhan:
            return ["accept", "decline"]
        return []
    if pc.trangThai == "ACCEPTED":
        return ["start", "save_draft", "decide"]
    if pc.trangThai == "IN_PROGRESS":
        return ["save_draft", "decide"]
    return []


def _is_overdue_review(pc: PhanCongKiemDuyet, now: datetime) -> bool:
    return (
        pc.trangThai in ("ACCEPTED", "IN_PROGRESS")
        and pc.hanKiemDuyet is not None
        and now >= pc.hanKiemDuyet
    )


def _target_type_and_id(pc: PhanCongKiemDuyet) -> tuple[TargetType, int]:
    if pc.maKhoaHoc is not None:
        return "COURSE", int(pc.maKhoaHoc)
    return "MATERIAL", int(pc.maTaiLieu)


def require_owned_review_assignment(
    db: Session,
    *,
    user_id: int,
    assignment_id: int | None = None,
    target_type: TargetType | None = None,
    target_id: int | None = None,
    allowed_states: set[str] | None = None,
    require_current_round: bool = False,
    require_current_eligibility: bool = False,
    for_update: bool = False,
) -> tuple[ChuyenGia, PhanCongKiemDuyet, KhoaHoc | TaiLieu]:
    """Centralized SEC-02 Ownership Guard.

    Enforces:
      1. Role EXPERT, account ACTIVE, password changed, profile VERIFIED (SEC-01).
      2. Assignment exists and belongs to the authenticated expert (never leaks others' data).
      3. Optional target_type/target_id match.
      4. Optional allowed_states match.
      5. Optional current review round match.
    """
    # Lock target first if target_id is known and for_update=True (ARCH-05 ordering!)
    target: KhoaHoc | TaiLieu | None = None
    if target_type is not None and target_id is not None:
        target, _ = assignment_repository.get_target(
            db, target_type, target_id, for_update=for_update
        )
        if target is None:
            raise WorkflowNotFoundError("Không tìm thấy nội dung kiểm duyệt.")

    expert = _require_verified_expert(db, user_id, for_update=for_update)

    stmt = select(PhanCongKiemDuyet)
    if assignment_id is not None:
        stmt = stmt.where(PhanCongKiemDuyet.maPhanCong == assignment_id)
    elif target_type is not None and target_id is not None:
        col = (
            PhanCongKiemDuyet.maKhoaHoc
            if target_type == "COURSE"
            else PhanCongKiemDuyet.maTaiLieu
        )
        stmt = stmt.where(
            col == target_id,
            PhanCongKiemDuyet.maChuyenGia == expert.maChuyenGia,
        ).order_by(PhanCongKiemDuyet.maPhanCong.desc())
    else:
        raise WorkflowNotFoundError("Thiếu thông tin phân công kiểm duyệt.")

    if for_update:
        stmt = stmt.with_for_update()

    pc = db.scalars(stmt.execution_options(populate_existing=True)).first()
    if pc is None or int(pc.maChuyenGia) != int(expert.maChuyenGia):
        # Consistent 403/404 without revealing whether another expert owns this ID
        raise WorkflowForbiddenError(
            "Bạn không có nhiệm vụ kiểm duyệt hợp lệ đối với nội dung này."
        )

    pc_type, pc_target_id = _target_type_and_id(pc)
    if target_type is not None and pc_type != target_type:
        raise WorkflowForbiddenError("Loại đối tượng không khớp với nhiệm vụ được giao.")
    if target_id is not None and pc_target_id != target_id:
        raise WorkflowForbiddenError("Đối tượng không khớp với nhiệm vụ được giao.")

    if target is None:
        target, _ = assignment_repository.get_target(
            db, pc_type, pc_target_id, for_update=for_update
        )
        if target is None:
            raise WorkflowNotFoundError("Không tìm thấy nội dung gắn với nhiệm vụ.")

    if require_current_round:
        cur_round = int(target.soVongKiemDuyetHienTai or 0)
        if int(pc.soVongKiemDuyet) != cur_round:
            raise WorkflowConflictError(
                "Nhiệm vụ thuộc vòng kiểm duyệt cũ và không còn hiệu lực."
            )

    if allowed_states is not None and pc.trangThai not in allowed_states:
        raise WorkflowConflictError(
            f"Trạng thái nhiệm vụ ({pc.trangThai}) không cho phép thực hiện thao tác này."
        )

    if require_current_eligibility:
        from service import eligibility_service

        eligibility_service.lock_expert_eligibility(db, int(expert.maChuyenGia))
        reasons = eligibility_service.current_assignment_ineligibility_reasons(
            db,
            expert_id=int(expert.maChuyenGia),
            target_type=pc_type,
            target_id=pc_target_id,
            category_id=int(pc.maDanhMuc),
        )
        if reasons:
            raise WorkflowForbiddenError(
                "Expert eligibility is no longer valid: " + ", ".join(reasons)
            )

    return expert, pc, target


def _serialize_expert_summary(
    pc: PhanCongKiemDuyet, title: str | None, now: datetime
) -> dict[str, Any]:
    t_type, t_id = _target_type_and_id(pc)
    return {
        "maPhanCong": int(pc.maPhanCong),
        "loaiDoiTuong": t_type,
        "maDoiTuong": t_id,
        "tieuDeDoiTuong": title,
        "maDanhMuc": int(pc.maDanhMuc),
        "soVongKiemDuyet": int(pc.soVongKiemDuyet),
        "trangThai": pc.trangThai,
        "phuongThucPhanCong": pc.phuongThucPhanCong,
        "diemPhuHop": float(pc.diemPhuHop) if pc.diemPhuHop is not None else None,
        "lyDoPhanCong": pc.lyDoPhanCong,
        "ngayPhanCong": pc.ngayPhanCong,
        "hanTiepNhan": pc.hanTiepNhan,
        "hanKiemDuyet": pc.hanKiemDuyet,
        "ngayChapNhan": pc.ngayChapNhan,
        "ngayBatDau": pc.ngayBatDau,
        "ngayHoanThanh": pc.ngayHoanThanh,
        "isOverdueReview": _is_overdue_review(pc, now),
        "allowedActions": _allowed_actions_for_assignment(pc, now),
    }


def list_my_assignments(
    db: Session,
    user_id: int,
    *,
    status: str | None = None,
    target_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    expert = _require_verified_expert(db, user_id)
    ts = now or _utc_now()
    stmt = (
        select(PhanCongKiemDuyet)
        .options(
            joinedload(PhanCongKiemDuyet.khoaHoc),
            joinedload(PhanCongKiemDuyet.taiLieu),
        )
        .where(PhanCongKiemDuyet.maChuyenGia == expert.maChuyenGia)
    )
    if status:
        stmt = stmt.where(PhanCongKiemDuyet.trangThai == status)
    if target_type == "COURSE":
        stmt = stmt.where(PhanCongKiemDuyet.maKhoaHoc.is_not(None))
    elif target_type == "MATERIAL":
        stmt = stmt.where(PhanCongKiemDuyet.maTaiLieu.is_not(None))

    rows = list(
        db.scalars(
            stmt.order_by(PhanCongKiemDuyet.ngayPhanCong.desc(), PhanCongKiemDuyet.maPhanCong.desc())
            .offset(offset)
            .limit(min(limit, 100))
        ).unique().all()
    )
    results = []
    for pc in rows:
        title = (
            pc.khoaHoc.tieuDe
            if pc.khoaHoc is not None
            else (pc.taiLieu.tieuDe if pc.taiLieu is not None else None)
        )
        results.append(_serialize_expert_summary(pc, title, ts))
    return results


def get_my_assignment_detail(
    db: Session,
    user_id: int,
    assignment_id: int,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Section 45 Access Matrix strictly enforced by assignment state."""
    ts = now or _utc_now()
    _, pc, target = require_owned_review_assignment(
        db, user_id=user_id, assignment_id=assignment_id
    )
    t_type, _ = _target_type_and_id(pc)
    data = _serialize_expert_summary(pc, target.tieuDe, ts)
    data["chiTietDiem"] = pc.chiTietDiem
    data["banNhapDanhGia"] = (
        pc.banNhapDanhGia if pc.trangThai in ("ACCEPTED", "IN_PROGRESS", "COMPLETED") else None
    )
    data["noiDungKiemDuyet"] = None
    data["ketQuaDanhGia"] = None

    # Full private content ONLY when ACCEPTED or IN_PROGRESS on current review round
    if pc.trangThai in ("ACCEPTED", "IN_PROGRESS") and int(pc.soVongKiemDuyet) == int(
        target.soVongKiemDuyetHienTai or 0
    ):
        if t_type == "COURSE":
            assert isinstance(target, KhoaHoc)
            lessons = list(
                db.scalars(
                    select(BaiHoc)
                    .where(BaiHoc.maKhoaHoc == target.maKhoaHoc)
                    .order_by(BaiHoc.thuTu.asc(), BaiHoc.maBaiHoc.asc())
                ).all()
            )
            linked_mats = list(
                db.scalars(
                    select(TaiLieu).where(TaiLieu.maKhoaHoc == target.maKhoaHoc)
                ).all()
            )
            data["noiDungKiemDuyet"] = {
                "maKhoaHoc": target.maKhoaHoc,
                "tieuDe": target.tieuDe,
                "moTa": target.moTa,
                "trinhDo": target.trinhDo,
                "thoiLuong": target.thoiLuong,
                "baiHocs": [
                    {
                        "maBaiHoc": b.maBaiHoc,
                        "tieuDe": b.tieuDe,
                        "noiDung": b.noiDung,
                        "duongDanVideo": b.duongDanVideo,
                        "thuTu": b.thuTu,
                    }
                    for b in lessons
                ],
                "taiLieus": [
                    {
                        "maTaiLieu": m.maTaiLieu,
                        "tieuDe": m.tieuDe,
                        "loai": m.loai,
                        "duongDanTep": _material_access_reference(m),
                    }
                    for m in linked_mats
                ],
            }
        else:
            assert isinstance(target, TaiLieu)
            data["noiDungKiemDuyet"] = {
                "maTaiLieu": target.maTaiLieu,
                "tieuDe": target.tieuDe,
                "moTa": target.moTa,
                "loai": target.loai,
                "duongDanTep": _material_access_reference(target),
            }
    elif pc.trangThai == "COMPLETED":
        review = db.scalars(
            select(DanhGiaChuyenGia).where(DanhGiaChuyenGia.maPhanCong == pc.maPhanCong)
        ).first()
        if review is not None:
            data["ketQuaDanhGia"] = {
                "maDanhGia": review.maDanhGia,
                "trangThai": review.trangThai,
                "noiDungDanhGia": review.noiDungDanhGia,
                "ghiChu": review.ghiChu,
                "ngayTao": review.ngayTao.isoformat() if review.ngayTao else None,
            }

    return data


def accept_assignment(
    db: Session,
    user_id: int,
    assignment_id: int,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Section 31: Accept ASSIGNED assignment before hanTiepNhan (idempotent on ACCEPTED)."""
    ts = now or _utc_now()
    # Pre-read target_type/id so ARCH-05 locks target BEFORE expert & assignment
    pc_probe = db.get(PhanCongKiemDuyet, assignment_id)
    if pc_probe is None:
        raise WorkflowForbiddenError("Bạn không có nhiệm vụ kiểm duyệt hợp lệ.")
    t_type, t_id = _target_type_and_id(pc_probe)

    _, pc, target = require_owned_review_assignment(
        db,
        user_id=user_id,
        assignment_id=assignment_id,
        target_type=t_type,
        target_id=t_id,
        allowed_states={"ASSIGNED", "ACCEPTED"},
        require_current_round=True,
        require_current_eligibility=True,
        for_update=True,
    )
    if target.trangThaiDuyet != "PENDING":
        raise WorkflowConflictError("Nội dung không còn ở trạng thái chờ kiểm duyệt.")

    # Idempotent accept: never extend deadline if already ACCEPTED
    if pc.trangThai == "ACCEPTED":
        return _serialize_expert_summary(pc, target.tieuDe, ts)

    if ts >= pc.hanTiepNhan:
        raise WorkflowConflictError(
            "Nhiệm vụ đã quá hạn tiếp nhận và không thể chấp nhận."
        )

    cfg = assignment_repository.get_singleton_config(db)
    pc.trangThai = "ACCEPTED"
    pc.ngayChapNhan = ts
    pc.hanKiemDuyet = ts + timedelta(hours=int(cfg.hanKiemDuyetGio))
    pc.ngayCapNhat = ts
    db.commit()
    return _serialize_expert_summary(pc, target.tieuDe, ts)


def decline_assignment(
    db: Session,
    user_id: int,
    assignment_id: int,
    *,
    reason_code: str,
    explanation: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Section 32: Decline ASSIGNED assignment -> DECLINED + durable REASSIGN_DECLINED."""
    ts = now or _utc_now()
    if reason_code not in VALID_DECLINE_REASONS:
        raise WorkflowConflictError("Mã lý do từ chối không hợp lệ.")
    clean_reason = (explanation or "").strip()
    if len(clean_reason) < 5:
        raise WorkflowConflictError("Vui lòng nhập lý do từ chối rõ ràng (tối thiểu 5 ký tự).")

    pc_probe = db.get(PhanCongKiemDuyet, assignment_id)
    if pc_probe is None:
        raise WorkflowForbiddenError("Bạn không có nhiệm vụ kiểm duyệt hợp lệ.")
    t_type, t_id = _target_type_and_id(pc_probe)

    _, pc, target = require_owned_review_assignment(
        db,
        user_id=user_id,
        assignment_id=assignment_id,
        target_type=t_type,
        target_id=t_id,
        allowed_states={"ASSIGNED"},
        require_current_round=True,
        for_update=True,
    )
    if ts >= pc.hanTiepNhan:
        raise WorkflowConflictError("Nhiệm vụ đã quá hạn tiếp nhận.")

    pc.trangThai = "DECLINED"
    pc.maLyDoTuChoi = reason_code
    pc.lyDoTuChoi = clean_reason
    pc.ngayCapNhat = ts
    cfg = assignment_repository.get_singleton_config(db)
    # Preserve immutable terminal evidence in chiTietDiem for GĐ3.4/GĐ3.5 Accountability (ACC-11)
    details = dict(pc.chiTietDiem or {})
    details["accountabilityEvent"] = {
        "eventType": "DECLINED_ASSIGNMENT",
        "reasonCode": reason_code,
        "explanation": clean_reason,
        "occurredAt": ts.isoformat(),
        "expertId": int(pc.maChuyenGia),
        "policySnapshot": {
            "tinhViPhamHetHan": bool(cfg.tinhViPhamHetHan),
            "khoangThongKeGio": int(cfg.khoangThongKeGio),
            "nguongCanhBao": int(cfg.nguongCanhBao),
            "nguongKhoaTaiKhoan": int(cfg.nguongKhoaTaiKhoan),
            "tuDongKhoa": bool(cfg.tuDongKhoa),
        },
    }
    pc.chiTietDiem = details
    db.flush()

    if target.trangThaiDuyet == "PENDING":
        try:
            assignment_queue_service.enqueue_assignment_job(
                db,
                target_type=t_type,
                target_id=t_id,
                review_round=int(pc.soVongKiemDuyet),
                event_type="REASSIGN_DECLINED",
                source_assignment_id=int(pc.maPhanCong),
                now=ts,
            )
        except assignment_queue_service.QueueValidationError:
            notification_service.notify_active_admins(
                db,
                notification_type="ASSIGNMENT_REASSIGN_LIMIT",
                title="Đạt giới hạn tái phân công sau khi chuyên gia từ chối",
                body=f"{t_type} #{t_id} vòng {pc.soVongKiemDuyet} đã đạt trần tái phân công.",
                event_key=f"REASSIGN_LIMIT:{t_type}:{t_id}:R{pc.soVongKiemDuyet}",
                now=ts,
            )

    db.commit()

    # GĐ3.4 fail-closed Accountability hook: record DECLINED_ASSIGNMENT & durable revocation if auto-locked
    from service import accountability_service

    if accountability_service.is_accountability_enabled():
        acc_res = accountability_service.record_violation_for_assignment(
            db,
            assignment_id=int(pc.maPhanCong),
            violation_type="DECLINED_ASSIGNMENT",
            now=ts,
            commit=True,
        )
        if acc_res.autoLocked:
            accountability_service.reconcile_locked_expert_assignments(
                db, expert_id=int(pc.maChuyenGia), now=ts, commit=True
            )

    return _serialize_expert_summary(pc, target.tieuDe, ts)


def start_assignment_review(
    db: Session,
    user_id: int,
    assignment_id: int,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Section 36: Transition ACCEPTED -> IN_PROGRESS and record ngayBatDau."""
    ts = now or _utc_now()
    pc_probe = db.get(PhanCongKiemDuyet, assignment_id)
    if pc_probe is None:
        raise WorkflowForbiddenError("Bạn không có nhiệm vụ kiểm duyệt hợp lệ.")
    t_type, t_id = _target_type_and_id(pc_probe)

    _, pc, target = require_owned_review_assignment(
        db,
        user_id=user_id,
        assignment_id=assignment_id,
        target_type=t_type,
        target_id=t_id,
        allowed_states={"ACCEPTED", "IN_PROGRESS"},
        require_current_round=True,
        require_current_eligibility=True,
        for_update=True,
    )
    if pc.trangThai == "ACCEPTED":
        pc.trangThai = "IN_PROGRESS"
        pc.ngayBatDau = ts
        pc.ngayCapNhat = ts
        db.commit()
    return _serialize_expert_summary(pc, target.tieuDe, ts)


def save_assignment_draft(
    db: Session,
    user_id: int,
    assignment_id: int,
    *,
    draft_data: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Section 36: Save private review draft without creating official DanhGiaChuyenGia."""
    ts = now or _utc_now()
    encoded = json.dumps(draft_data, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_DRAFT_JSON_BYTES:
        raise WorkflowConflictError("Bản nháp đánh giá vượt quá kích thước cho phép (64KB).")

    pc_probe = db.get(PhanCongKiemDuyet, assignment_id)
    if pc_probe is None:
        raise WorkflowForbiddenError("Bạn không có nhiệm vụ kiểm duyệt hợp lệ.")
    t_type, t_id = _target_type_and_id(pc_probe)

    _, pc, target = require_owned_review_assignment(
        db,
        user_id=user_id,
        assignment_id=assignment_id,
        target_type=t_type,
        target_id=t_id,
        allowed_states={"ACCEPTED", "IN_PROGRESS"},
        require_current_round=True,
        require_current_eligibility=True,
        for_update=True,
    )
    pc.banNhapDanhGia = draft_data
    pc.ngayCapNhat = ts
    db.commit()
    return _serialize_expert_summary(pc, target.tieuDe, ts)


def submit_assignment_decision(
    db: Session,
    user_id: int,
    assignment_id: int,
    *,
    trang_thai: str,
    noi_dung_danh_gia: str | None = None,
    ghi_chu: str | None = None,
    diem_ky_thuat: Decimal | None = None,
    diem_noi_dung: Decimal | None = None,
    now: datetime | None = None,
) -> tuple[KhoaHoc | TaiLieu, DanhGiaChuyenGia, PhanCongKiemDuyet]:
    """Section 37: Atomic Review Completion (DanhGiaChuyenGia + target + COMPLETED + wake-up)."""
    ts = now or _utc_now()
    if trang_thai not in {"APPROVED", "REJECTED", "NEEDS_REVISION"}:
        raise WorkflowConflictError("Quyết định kiểm duyệt không hợp lệ.")
    note = (ghi_chu or "").strip() or (noi_dung_danh_gia or "").strip() or None
    if trang_thai != "APPROVED" and not note:
        raise WorkflowConflictError(
            "Bắt buộc nhập nhận xét hoặc ghi chú khi từ chối hoặc yêu cầu chỉnh sửa."
        )

    pc_probe = db.get(PhanCongKiemDuyet, assignment_id)
    if pc_probe is None:
        raise WorkflowForbiddenError("Bạn không có nhiệm vụ kiểm duyệt hợp lệ.")
    t_type, t_id = _target_type_and_id(pc_probe)

    expert, pc, target = require_owned_review_assignment(
        db,
        user_id=user_id,
        assignment_id=assignment_id,
        target_type=t_type,
        target_id=t_id,
        allowed_states={"ACCEPTED", "IN_PROGRESS"},
        require_current_round=True,
        require_current_eligibility=True,
        for_update=True,
    )
    if target.trangThaiDuyet != "PENDING":
        raise WorkflowConflictError("Nội dung không còn ở trạng thái chờ kiểm duyệt.")

    review = DanhGiaChuyenGia(
        maKhoaHoc=t_id if t_type == "COURSE" else None,
        maTaiLieu=t_id if t_type == "MATERIAL" else None,
        maChuyenGia=expert.maChuyenGia,
        maPhanCong=pc.maPhanCong,
        noiDungDanhGia=noi_dung_danh_gia,
        diemKyThuat=diem_ky_thuat,
        diemNoiDung=diem_noi_dung,
        ghiChu=ghi_chu,
        trangThai=trang_thai,
        ngayTao=ts,
    )
    db.add(review)

    # Never auto-publish on APPROVED (remains HIDDEN until explicit publish step)
    target.trangThaiDuyet = trang_thai
    target.trangThaiHienThi = "HIDDEN"
    target.ngayCapNhat = ts
    if trang_thai == "APPROVED":
        target.maNguoiDuyet = user_id
        target.ngayDuyet = ts
        target.lyDoTuChoi = None
    else:
        target.maNguoiDuyet = None
        target.ngayDuyet = None
        target.lyDoTuChoi = note

    pc.trangThai = "COMPLETED"
    pc.ngayHoanThanh = ts
    pc.ngayCapNhat = ts
    db.flush()

    # Cancel any leftover open jobs for this target and wake WAITING_ELIGIBLE jobs (capacity freed!)
    assignment_queue_service.cancel_open_jobs_for_target(
        db,
        target_type=t_type,
        target_id=t_id,
        reason=f"Review completed with outcome {trang_thai}",
        now=ts,
    )
    assignment_queue_service.wake_waiting_eligible_jobs(db, limit=10, now=ts)

    # Notify PROVIDER idempotently
    if target.maNhaCungCap is not None:
        prov_uid = db.scalar(
            select(NhaCungCapKhoaHoc.maNguoiDung).where(
                NhaCungCapKhoaHoc.maNhaCungCap == target.maNhaCungCap
            )
        )
        if prov_uid is not None:
            notification_service.create_notification_idempotent(
                db,
                recipient_user_id=int(prov_uid),
                notification_type="REVIEW_COMPLETED",
                title="Nội dung của bạn đã có kết quả kiểm duyệt",
                body=f"{t_type} #{t_id} đã được kiểm duyệt với kết quả: {trang_thai}.",
                event_key=f"REVIEW_DONE:{pc.maPhanCong}",
                payload={
                    "maPhanCong": int(pc.maPhanCong),
                    "loaiDoiTuong": t_type,
                    "maDoiTuong": t_id,
                    "ketQua": trang_thai,
                },
                now=ts,
            )

    db.commit()
    db.refresh(target)
    db.refresh(review)
    db.refresh(pc)
    return target, review, pc


# =====================================================================
# ADMIN Monitoring & Exception Handling
# =====================================================================
def _serialize_admin_assignment(pc: PhanCongKiemDuyet, now: datetime) -> dict[str, Any]:
    t_type, t_id = _target_type_and_id(pc)
    title = (
        pc.khoaHoc.tieuDe
        if pc.khoaHoc is not None
        else (pc.taiLieu.tieuDe if pc.taiLieu is not None else None)
    )
    expert_name = (
        pc.chuyenGia.nguoiDung.hoTen
        if pc.chuyenGia is not None and pc.chuyenGia.nguoiDung is not None
        else None
    )
    cat_name = pc.danhMuc.tenDanhMuc if pc.danhMuc is not None else None
    return {
        "maPhanCong": int(pc.maPhanCong),
        "loaiDoiTuong": t_type,
        "maDoiTuong": t_id,
        "tieuDeDoiTuong": title,
        "maChuyenGia": int(pc.maChuyenGia),
        "tenChuyenGia": expert_name,
        "maDanhMuc": int(pc.maDanhMuc),
        "tenDanhMuc": cat_name,
        "maChuyenMonKhop": pc.maChuyenMonKhop,
        "soVongKiemDuyet": int(pc.soVongKiemDuyet),
        "phuongThucPhanCong": pc.phuongThucPhanCong,
        "trangThai": pc.trangThai,
        "diemPhuHop": float(pc.diemPhuHop) if pc.diemPhuHop is not None else None,
        "chiTietDiem": pc.chiTietDiem,
        "lyDoPhanCong": pc.lyDoPhanCong,
        "ngayPhanCong": pc.ngayPhanCong,
        "hanTiepNhan": pc.hanTiepNhan,
        "hanKiemDuyet": pc.hanKiemDuyet,
        "ngayChapNhan": pc.ngayChapNhan,
        "ngayBatDau": pc.ngayBatDau,
        "ngayHoanThanh": pc.ngayHoanThanh,
        "maLyDoTuChoi": pc.maLyDoTuChoi,
        "lyDoTuChoi": pc.lyDoTuChoi,
        "lyDoHuy": pc.lyDoHuy,
        "isOverdueReview": _is_overdue_review(pc, now),
    }


def admin_list_assignments(
    db: Session,
    *,
    status: str | None = None,
    target_type: str | None = None,
    expert_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    ts = now or _utc_now()
    stmt = select(PhanCongKiemDuyet).options(
        joinedload(PhanCongKiemDuyet.khoaHoc),
        joinedload(PhanCongKiemDuyet.taiLieu),
        joinedload(PhanCongKiemDuyet.chuyenGia).joinedload(ChuyenGia.nguoiDung),
        joinedload(PhanCongKiemDuyet.danhMuc),
    )
    if status:
        stmt = stmt.where(PhanCongKiemDuyet.trangThai == status)
    if target_type == "COURSE":
        stmt = stmt.where(PhanCongKiemDuyet.maKhoaHoc.is_not(None))
    elif target_type == "MATERIAL":
        stmt = stmt.where(PhanCongKiemDuyet.maTaiLieu.is_not(None))
    if expert_id is not None:
        stmt = stmt.where(PhanCongKiemDuyet.maChuyenGia == expert_id)
    rows = list(
        db.scalars(
            stmt.order_by(PhanCongKiemDuyet.ngayPhanCong.desc(), PhanCongKiemDuyet.maPhanCong.desc())
            .offset(offset)
            .limit(min(limit, 100))
        ).unique().all()
    )
    return [_serialize_admin_assignment(pc, ts) for pc in rows]


def admin_get_assignment_detail(
    db: Session, assignment_id: int, *, now: datetime | None = None
) -> dict[str, Any]:
    ts = now or _utc_now()
    pc = db.scalars(
        select(PhanCongKiemDuyet)
        .options(
            joinedload(PhanCongKiemDuyet.khoaHoc),
            joinedload(PhanCongKiemDuyet.taiLieu),
            joinedload(PhanCongKiemDuyet.chuyenGia).joinedload(ChuyenGia.nguoiDung),
            joinedload(PhanCongKiemDuyet.danhMuc),
        )
        .where(PhanCongKiemDuyet.maPhanCong == assignment_id)
    ).first()
    if pc is None:
        raise WorkflowNotFoundError("Không tìm thấy phân công kiểm duyệt.")
    return _serialize_admin_assignment(pc, ts)


def admin_list_queue_jobs(
    db: Session,
    *,
    status: str | None = None,
    target_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[HangDoiPhanCong]:
    stmt = select(HangDoiPhanCong)
    if status:
        stmt = stmt.where(HangDoiPhanCong.trangThai == status)
    if target_type:
        stmt = stmt.where(HangDoiPhanCong.loaiDoiTuong == target_type)
    return list(
        db.scalars(
            stmt.order_by(HangDoiPhanCong.ngayTao.desc(), HangDoiPhanCong.maCongViec.desc())
            .offset(offset)
            .limit(min(limit, 100))
        ).all()
    )


def admin_get_workload_summary(db: Session) -> list[dict[str, Any]]:
    cfg = assignment_repository.get_singleton_config(db)
    experts = list(
        db.scalars(
            select(ChuyenGia)
            .options(joinedload(ChuyenGia.nguoiDung).joinedload(NguoiDung.vaiTro))
            .order_by(ChuyenGia.maChuyenGia.asc())
        ).unique().all()
    )
    load_rows = db.execute(
        select(
            PhanCongKiemDuyet.maChuyenGia,
            func.count(PhanCongKiemDuyet.maPhanCong),
        )
        .where(PhanCongKiemDuyet.trangThai.in_(assignment_repository.ACTIVE_ASSIGNMENT_STATUSES))
        .group_by(PhanCongKiemDuyet.maChuyenGia)
    ).all()
    load_map = {int(eid): int(cnt) for eid, cnt in load_rows}
    out = []
    for e in experts:
        if e.nguoiDung is None or (e.nguoiDung.vaiTro and e.nguoiDung.vaiTro.tenVaiTro != "EXPERT"):
            continue
        out.append(
            {
                "maChuyenGia": int(e.maChuyenGia),
                "maNguoiDung": int(e.maNguoiDung),
                "hoTen": e.nguoiDung.hoTen,
                "trangThaiTaiKhoan": e.nguoiDung.trangThai,
                "trangThaiHoSo": e.trangThaiHoSo,
                "activeAssignments": load_map.get(int(e.maChuyenGia), 0),
                "maxAssignments": int(cfg.gioiHanTaiToiDa),
            }
        )
    return out


def admin_cancel_assignment(
    db: Session,
    admin_user_id: int,
    assignment_id: int,
    *,
    reason: str,
    requeue: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """ADMIN cancels an active assignment, preserves draft, optionally enqueues REASSIGN_CANCELLED."""
    ts = now or _utc_now()
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 5:
        raise WorkflowConflictError("Bắt buộc nhập lý do thu hồi (tối thiểu 5 ký tự).")

    pc_probe = db.get(PhanCongKiemDuyet, assignment_id)
    if pc_probe is None:
        raise WorkflowNotFoundError("Không tìm thấy phân công kiểm duyệt.")
    t_type, t_id = _target_type_and_id(pc_probe)

    target, _ = assignment_repository.get_target(db, t_type, t_id, for_update=True)
    pc = db.scalars(
        select(PhanCongKiemDuyet)
        .where(PhanCongKiemDuyet.maPhanCong == assignment_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if pc is None:
        raise WorkflowNotFoundError("Không tìm thấy phân công kiểm duyệt.")
    if pc.trangThai not in ("ASSIGNED", "ACCEPTED", "IN_PROGRESS"):
        raise WorkflowConflictError(
            f"Chỉ có thể thu hồi nhiệm vụ đang hoạt động (hiện tại: {pc.trangThai})."
        )

    pc.trangThai = "CANCELLED"
    pc.lyDoHuy = clean_reason
    pc.ngayCapNhat = ts
    details = dict(pc.chiTietDiem or {})
    details["cancellationEvent"] = {
        "cancelledByAdminId": admin_user_id,
        "reason": clean_reason,
        "occurredAt": ts.isoformat(),
    }
    pc.chiTietDiem = details
    db.flush()

    if requeue and target is not None and target.trangThaiDuyet == "PENDING":
        try:
            assignment_queue_service.enqueue_assignment_job(
                db,
                target_type=t_type,
                target_id=t_id,
                review_round=int(pc.soVongKiemDuyet),
                event_type="REASSIGN_CANCELLED",
                source_assignment_id=int(pc.maPhanCong),
                now=ts,
            )
        except assignment_queue_service.QueueValidationError:
            pass

    if pc.chuyenGia and pc.chuyenGia.maNguoiDung:
        notification_service.create_notification_idempotent(
            db,
            recipient_user_id=int(pc.chuyenGia.maNguoiDung),
            notification_type="ASSIGNMENT_CANCELLED",
            title="Nhiệm vụ kiểm duyệt đã bị thu hồi",
            body=f"Nhiệm vụ #{pc.maPhanCong} đã được Quản trị viên thu hồi. Lý do: {clean_reason}",
            event_key=f"ASSIGN_CANCELLED:{pc.maPhanCong}",
            payload={"maPhanCong": int(pc.maPhanCong)},
            now=ts,
        )

    db.commit()
    return _serialize_admin_assignment(pc, ts)


def admin_retry_queue_job(
    db: Session,
    admin_user_id: int,
    job_id: int,
    *,
    now: datetime | None = None,
) -> HangDoiPhanCong:
    """ADMIN retries a FAILED or WAITING_ELIGIBLE job without bypassing reassignment cap."""
    ts = now or _utc_now()
    src_job = db.get(HangDoiPhanCong, job_id)
    if src_job is None:
        raise WorkflowNotFoundError("Không tìm thấy công việc trong hàng đợi.")

    t_type: TargetType = src_job.loaiDoiTuong  # type: ignore[assignment]
    t_id = int(src_job.maKhoaHoc if t_type == "COURSE" else src_job.maTaiLieu)
    target, _ = assignment_repository.get_target(db, t_type, t_id, for_update=True)
    if target is None or target.trangThaiDuyet != "PENDING":
        raise WorkflowConflictError("Nội dung không còn ở trạng thái PENDING.")

    cur_round = int(target.soVongKiemDuyetHienTai or 0)
    if cur_round < 1:
        raise WorkflowConflictError("Nội dung chưa có vòng kiểm duyệt hợp lệ.")

    if assignment_repository.get_active_assignment(db, t_type, t_id) is not None:
        raise WorkflowConflictError("Nội dung đã có phân công đang hoạt động.")

    try:
        new_job, _ = assignment_queue_service.enqueue_assignment_job(
            db,
            target_type=t_type,
            target_id=t_id,
            review_round=cur_round,
            event_type="ADMIN_RETRY",
            priority=1,
            now=ts,
        )
    except assignment_queue_service.QueueValidationError as exc:
        raise WorkflowConflictError(str(exc)) from exc

    db.commit()
    db.refresh(new_job)
    return new_job


def bootstrap_legacy_pending_course(
    db: Session,
    course_id: int,
    *,
    now: datetime | None = None,
) -> tuple[KhoaHoc, HangDoiPhanCong]:
    """Controlled legacy bootstrap (Section 58) for rehearsal on test DB ONLY.

    Transitions legacy PENDING/HIDDEN course with round=0 -> round=1 + idempotent SUBMIT job.
    """
    ts = now or _utc_now()
    course, _ = assignment_repository.get_target(db, "COURSE", course_id, for_update=True)
    if course is None:
        raise WorkflowNotFoundError("Không tìm thấy khóa học.")
    assert isinstance(course, KhoaHoc)
    if course.trangThaiDuyet != "PENDING":
        raise WorkflowConflictError("Khóa học không ở trạng thái PENDING.")
    if course.maDanhMuc is None:
        raise WorkflowConflictError("Khóa học thiếu danh mục hợp lệ.")
    if int(course.soVongKiemDuyetHienTai or 0) == 0:
        course.soVongKiemDuyetHienTai = 1
        course.ngayCapNhat = ts
        db.flush()
    job, _ = assignment_queue_service.enqueue_assignment_job(
        db,
        target_type="COURSE",
        target_id=course.maKhoaHoc,
        review_round=int(course.soVongKiemDuyetHienTai),
        event_type="SUBMIT",
        now=ts,
    )
    db.commit()
    db.refresh(course)
    db.refresh(job)
    return course, job


# =====================================================================
# GĐ3.6 Admin System Config (CauHinhPhanCong) & Expert Management Overview
# =====================================================================
def admin_get_assignment_config(db: Session):
    return assignment_repository.get_singleton_config(db)


def admin_update_assignment_config(
    db: Session,
    *,
    admin_user_id: int,
    updates: dict[str, Any],
    now: datetime | None = None,
):
    """Update CauHinhPhanCong singleton under FOR UPDATE lock without altering historical data."""
    from models import CauHinhPhanCong

    ts = now or _utc_now()
    cfg = db.scalars(
        select(CauHinhPhanCong)
        .where(CauHinhPhanCong.maCauHinh == 1)
        .with_for_update()
    ).first()
    if cfg is None:
        raise WorkflowNotFoundError("Không tìm thấy bản ghi cấu hình phân công (CauHinhPhanCong #1).")

    new_warn = updates.get("nguongCanhBao", cfg.nguongCanhBao)
    new_lock = updates.get("nguongKhoaTaiKhoan", cfg.nguongKhoaTaiKhoan)
    if new_lock <= new_warn:
        raise WorkflowConflictError("Ngưỡng khóa tài khoản phải lớn hơn ngưỡng cảnh báo.")

    allowed_fields = (
        "gioiHanTaiToiDa",
        "hanTiepNhanGio",
        "hanKiemDuyetGio",
        "soLanTaiPhanCongToiDa",
        "khoangThongKeGio",
        "nguongCanhBao",
        "nguongKhoaTaiKhoan",
        "thoiGianTamNgungToiDaNgay",
        "tinhViPhamHetHan",
        "tuDongKhoa",
        "uuTienTuyetDoiChuyenMonChinh",
    )
    for field in allowed_fields:
        if field in updates and updates[field] is not None:
            setattr(cfg, field, updates[field])
    cfg.maNguoiCapNhat = admin_user_id
    cfg.ngayCapNhat = ts
    db.commit()
    db.refresh(cfg)
    return cfg


def admin_get_expert_overview(
    db: Session, *, now: datetime | None = None
) -> dict[str, Any]:
    """Real-time PostgreSQL aggregation for ADMIN Expert Management Dashboard (zero mock data)."""
    from models import ViPhamChuyenGia, YeuCauTamNgungChuyenGia
    from service import accountability_service

    ts = now or _utc_now()
    experts = list(
        db.scalars(
            select(ChuyenGia)
            .options(joinedload(ChuyenGia.nguoiDung).joinedload(NguoiDung.vaiTro))
        ).unique().all()
    )
    expert_rows = [
        e
        for e in experts
        if e.nguoiDung is not None
        and e.nguoiDung.vaiTro is not None
        and e.nguoiDung.vaiTro.tenVaiTro == "EXPERT"
    ]

    total_experts = len(expert_rows)
    verified_experts = sum(1 for e in expert_rows if (e.trangThaiHoSo or "").upper() == "VERIFIED")
    pending_ver_experts = sum(
        1 for e in expert_rows if (e.trangThaiHoSo or "").upper() in ("PENDING", "PENDING_VERIFICATION", "UNVERIFIED", "DRAFT")
    )
    locked_experts = sum(1 for e in expert_rows if (e.nguoiDung.trangThai or "").upper() == "LOCKED")

    paused_expert_ids = set(
        db.scalars(
            select(YeuCauTamNgungChuyenGia.maChuyenGia).where(
                YeuCauTamNgungChuyenGia.trangThai == "APPROVED",
                YeuCauTamNgungChuyenGia.ngayBatDau <= ts,
                YeuCauTamNgungChuyenGia.ngayKetThuc > ts,
            )
        ).all()
    )
    paused_experts = len(paused_expert_ids)

    active_working_ids = set(
        db.scalars(
            select(PhanCongKiemDuyet.maChuyenGia).where(
                PhanCongKiemDuyet.trangThai.in_(assignment_repository.ACTIVE_ASSIGNMENT_STATUSES)
            )
        ).all()
    )
    active_working_experts = len(active_working_ids)

    # Assignment breakdown
    pc_counts = db.execute(
        select(PhanCongKiemDuyet.trangThai, func.count(PhanCongKiemDuyet.maPhanCong)).group_by(
            PhanCongKiemDuyet.trangThai
        )
    ).all()
    assignment_breakdown = {str(st): int(cnt) for st, cnt in pc_counts}
    active_assignments = sum(
        assignment_breakdown.get(st, 0) for st in assignment_repository.ACTIVE_ASSIGNMENT_STATUSES
    )

    overdue_assignments = int(
        db.scalar(
            select(func.count(PhanCongKiemDuyet.maPhanCong)).where(
                (
                    (PhanCongKiemDuyet.trangThai == "ASSIGNED")
                    & (PhanCongKiemDuyet.hanTiepNhan <= ts)
                )
                | (
                    PhanCongKiemDuyet.trangThai.in_(("ACCEPTED", "IN_PROGRESS"))
                    & PhanCongKiemDuyet.hanKiemDuyet.is_not(None)
                    & (PhanCongKiemDuyet.hanKiemDuyet <= ts)
                )
            )
        )
        or 0
    )

    # Queue breakdown
    q_counts = db.execute(
        select(HangDoiPhanCong.trangThai, func.count(HangDoiPhanCong.maCongViec)).group_by(
            HangDoiPhanCong.trangThai
        )
    ).all()
    queue_breakdown = {str(st): int(cnt) for st, cnt in q_counts}
    pending_queue_jobs = sum(
        queue_breakdown.get(st, 0) for st in ("PENDING", "RETRYING", "WAITING_ELIGIBLE", "PROCESSING")
    )

    pending_violations = int(
        db.scalar(
            select(func.count(ViPhamChuyenGia.maViPham)).where(
                ViPhamChuyenGia.trangThaiXuLy == "PENDING_REVIEW"
            )
        )
        or 0
    )
    pending_avail = int(
        db.scalar(
            select(func.count(YeuCauTamNgungChuyenGia.maYeuCau)).where(
                YeuCauTamNgungChuyenGia.trangThai == "PENDING"
            )
        )
        or 0
    )

    # Discipline level breakdown across experts
    discipline_breakdown = {"NORMAL": 0, "WARNING": 0, "FINAL_WARNING": 0, "LOCKED": 0}
    for e in expert_rows:
        if (e.nguoiDung.trangThai or "").upper() == "LOCKED":
            discipline_breakdown["LOCKED"] += 1
        else:
            s = accountability_service.get_expert_accountability_summary(
                db, expert_id=int(e.maChuyenGia), now=ts
            )
            lvl = s["disciplineLevel"]
            discipline_breakdown[lvl] = discipline_breakdown.get(lvl, 0) + 1

    return {
        "totalExperts": total_experts,
        "verifiedExperts": verified_experts,
        "pendingVerificationExperts": pending_ver_experts,
        "activeWorkingExperts": active_working_experts,
        "pausedExperts": paused_experts,
        "lockedExperts": locked_experts,
        "activeAssignments": active_assignments,
        "overdueAssignments": overdue_assignments,
        "pendingQueueJobs": pending_queue_jobs,
        "pendingViolations": pending_violations,
        "pendingAvailabilityRequests": pending_avail,
        "assignmentStatusBreakdown": assignment_breakdown,
        "queueStatusBreakdown": queue_breakdown,
        "disciplineLevelBreakdown": discipline_breakdown,
        "evaluatedAt": ts,
    }
