"""GĐ3.4 Expert Accountability, Rolling Window 168h, Automatic Account Locking,
Durable Assignment Revocation Recovery & ADMIN Unlock Service.

Key invariants:
- Rolling window is strictly half-open: (T - khoangThongKeGio, T].
- Only CONFIRMED violations in the current disciplinary cycle count toward thresholds.
- Never creates retroactive violations; never punishes REJECTED/NEEDS_REVISION content reviews.
- Never auto-unlocks; ONLY ADMIN can unlock (increments chuKyKyLuatSo + sets mocChuKyKyLuat).
- ARCH-05 lock ordering preserved: Account lock locks NguoiDung -> ChuyenGia; durable
  assignment revocation runs in target-first transactions (KhoaHoc/TaiLieu -> NguoiDung
  -> ChuyenGia -> PhanCongKiemDuyet) so worker & lock never invert locks!
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models import (
    CauHinhPhanCong,
    ChuyenGia,
    NguoiDung,
    NhatKyKyLuatChuyenGia,
    PhanCongKiemDuyet,
    ViPhamChuyenGia,
)
from repository import assignment_repository
from schemas.assignment import AssignmentConfigurationError, TargetType
from service import assignment_queue_service, notification_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)

# Official Violation Reason Policy Mapping (Section 15):
# - WORKLOAD_PERSONAL: auto-CONFIRMED
# - CONFLICT_OF_INTEREST, SYSTEM_MISASSIGNMENT, TECHNICAL_ISSUE, OTHER: PENDING_REVIEW
#   (NEVER auto-exempted just because expert picked a special reason!)
AUTO_CONFIRMED_DECLINE_REASONS = frozenset({"WORKLOAD_PERSONAL"})
PENDING_REVIEW_DECLINE_REASONS = frozenset(
    {"CONFLICT_OF_INTEREST", "SYSTEM_MISASSIGNMENT", "TECHNICAL_ISSUE", "OTHER"}
)


@dataclass(frozen=True)
class ViolationProcessingResult:
    violationId: int | None
    created: bool
    status: str | None
    confirmedCountInWindow: int
    disciplineLevel: str
    autoLocked: bool
    cycle: int
    message: str


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def is_accountability_enabled() -> bool:
    """Server-side fail-closed flag (default False on Production until approved rollout)."""
    from config.config import get_settings

    return bool(get_settings().accountability_enabled)


def _get_validated_accountability_config(db: Session) -> CauHinhPhanCong:
    """Load and validate CauHinhPhanCong singleton (fail-closed if missing/invalid)."""
    cfg = assignment_repository.get_singleton_config(db)
    if cfg.khoangThongKeGio is None or cfg.khoangThongKeGio <= 0:
        raise AssignmentConfigurationError(
            f"Invalid khoangThongKeGio={cfg.khoangThongKeGio}."
        )
    if cfg.nguongCanhBao is None or cfg.nguongCanhBao < 1:
        raise AssignmentConfigurationError(
            f"Invalid nguongCanhBao={cfg.nguongCanhBao}."
        )
    if cfg.nguongKhoaTaiKhoan is None or cfg.nguongKhoaTaiKhoan <= cfg.nguongCanhBao:
        raise AssignmentConfigurationError(
            f"Invalid nguongKhoaTaiKhoan={cfg.nguongKhoaTaiKhoan} <= nguongCanhBao={cfg.nguongCanhBao}."
        )
    return cfg


def _policy_snapshot(cfg: CauHinhPhanCong) -> dict[str, Any]:
    return {
        "khoangThongKeGio": int(cfg.khoangThongKeGio),
        "nguongCanhBao": int(cfg.nguongCanhBao),
        "nguongKhoaTaiKhoan": int(cfg.nguongKhoaTaiKhoan),
        "tinhViPhamHetHan": bool(cfg.tinhViPhamHetHan),
        "tuDongKhoa": bool(cfg.tuDongKhoa),
    }


def classify_initial_violation_status(
    *,
    violation_type: str,
    decline_reason_code: str | None,
    expiration_counts_as_violation: bool,
) -> str | None:
    """Pure policy classifier (Section 15 & Section 17).

    Returns: 'CONFIRMED', 'PENDING_REVIEW', or None (when EXPIRED_ACCEPTANCE disabled).
    """
    if violation_type == "DECLINED_ASSIGNMENT":
        if decline_reason_code in AUTO_CONFIRMED_DECLINE_REASONS:
            return "CONFIRMED"
        return "PENDING_REVIEW"
    if violation_type == "EXPIRED_ACCEPTANCE":
        if not expiration_counts_as_violation:
            return None
        return "CONFIRMED"
    if violation_type == "ABANDONED_ASSIGNMENT":
        return "PENDING_REVIEW"
    raise WorkflowConflictError(f"Loại vi phạm không hợp lệ: {violation_type!r}")


def compute_discipline_level(
    confirmed_count: int,
    *,
    warning_threshold: int,
    lock_threshold: int,
) -> tuple[str, int]:
    """Return (level_name, numeric_level) based on dynamic thresholds.

    Default (warning=2, lock=4):
      0 -> ('NORMAL', 0)
      1 -> ('REMINDER', 1)
      2 -> ('WARNING_1', 2)
      3 -> ('WARNING_FINAL', 3)
      >=4 -> ('AUTO_LOCK', 4)
    """
    if confirmed_count <= 0:
        return "NORMAL", 0
    if confirmed_count >= lock_threshold:
        return "AUTO_LOCK", 4
    final_warning = lock_threshold - 1
    if final_warning > warning_threshold and confirmed_count >= final_warning:
        return "WARNING_FINAL", 3
    if confirmed_count >= warning_threshold:
        return "WARNING_1", 2
    return "REMINDER", 1


def count_confirmed_violations_in_window(
    db: Session,
    *,
    expert_id: int,
    cycle: int,
    cycle_started_at: datetime | None,
    window_hours: int,
    evaluated_at: datetime,
) -> int:
    """Count CONFIRMED violations in half-open rolling window (T - window_hours, T].

    Strictly excludes:
    - PENDING_REVIEW and EXEMPTED violations.
    - Violations from previous cycles.
    - Violations at or before (T - window_hours) (exact 168h boundary is excluded!).
    - Violations strictly after evaluated_at (future timestamps).
    - Violations before cycle_started_at (mocChuKyKyLuat).
    """
    window_start = evaluated_at - timedelta(hours=window_hours)
    conditions = [
        ViPhamChuyenGia.maChuyenGia == expert_id,
        ViPhamChuyenGia.trangThaiXuLy == "CONFIRMED",
        ViPhamChuyenGia.chuKyKyLuatSo == cycle,
        ViPhamChuyenGia.ngayViPham > window_start,
        ViPhamChuyenGia.ngayViPham <= evaluated_at,
    ]
    if cycle_started_at is not None:
        conditions.append(ViPhamChuyenGia.ngayViPham >= cycle_started_at)

    cnt = db.scalar(select(func.count(ViPhamChuyenGia.maViPham)).where(*conditions))
    return int(cnt or 0)


def _append_audit_log(
    db: Session,
    *,
    expert_id: int,
    user_id: int,
    action: str,
    actor_source: str,
    actor_user_id: int | None,
    cycle: int,
    prev_status: str | None,
    new_status: str | None,
    violation_count: int | None,
    reason: str,
    policy_snap: dict[str, Any] | None,
    now: datetime,
) -> NhatKyKyLuatChuyenGia:
    """Insert-only disciplinary audit log helper."""
    entry = NhatKyKyLuatChuyenGia(
        maChuyenGia=expert_id,
        maNguoiDung=user_id,
        hanhDong=action,
        nguonThucHien=actor_source,
        maNguoiThucHien=actor_user_id,
        chuKyKyLuatSo=cycle,
        trangThaiTruoc=prev_status,
        trangThaiSau=new_status,
        soViPhamTaiThoiDiem=violation_count,
        lyDo=reason,
        chinhSachSnapshot=policy_snap,
        ngayTao=now,
    )
    db.add(entry)
    db.flush()
    return entry


def _build_discipline_notification_text(
    level_name: str,
    *,
    confirmed_count: int,
    cfg: CauHinhPhanCong,
) -> tuple[str, str]:
    days = round(int(cfg.khoangThongKeGio) / 24, 1)
    days_str = f"{int(days)}" if days == int(days) else f"{days}"
    if level_name == "REMINDER":
        return (
            "Nhắc nhở trách nhiệm kiểm duyệt",
            f"Bạn có {confirmed_count} vi phạm đã xác nhận trong khoảng thống kê hiện tại ({cfg.khoangThongKeGio} giờ). Vui lòng theo dõi thời hạn tiếp nhận nhiệm vụ.",
        )
    if level_name == "WARNING_1":
        return (
            "Cảnh báo vi phạm kiểm duyệt",
            f"Bạn đã đạt ngưỡng cảnh báo {confirmed_count} vi phạm trong {days_str} ngày. Tài khoản có thể bị khóa khi đạt ngưỡng {cfg.nguongKhoaTaiKhoan} vi phạm.",
        )
    if level_name == "WARNING_FINAL":
        return (
            "Cảnh báo cuối trước khi khóa tài khoản",
            f"Bạn có {confirmed_count} vi phạm đã xác nhận. Nếu phát sinh thêm 1 vi phạm hợp lệ trong khoảng thống kê hiện tại, tài khoản sẽ đạt ngưỡng tự động khóa ({cfg.nguongKhoaTaiKhoan}).",
        )
    return (
        "Tài khoản chuyên gia đã bị khóa tự động",
        f"Tài khoản chuyên gia đã bị khóa do đạt ngưỡng {confirmed_count}/{cfg.nguongKhoaTaiKhoan} vi phạm theo chính sách kiểm duyệt. Vui lòng liên hệ quản trị viên để được xem xét.",
    )


def _evaluate_and_apply_discipline_under_lock(
    db: Session,
    *,
    locked_user: NguoiDung,
    locked_expert: ChuyenGia,
    violation: ViPhamChuyenGia,
    cfg: CauHinhPhanCong,
    now: datetime,
) -> tuple[int, str, bool]:
    """Re-count confirmed violations under NguoiDung+ChuyenGia lock and apply warning / AUTO_LOCK."""
    cycle = int(locked_expert.chuKyKyLuatSo or 1)
    confirmed_count = count_confirmed_violations_in_window(
        db,
        expert_id=int(locked_expert.maChuyenGia),
        cycle=cycle,
        cycle_started_at=locked_expert.mocChuKyKyLuat,
        window_hours=int(cfg.khoangThongKeGio),
        evaluated_at=now,
    )
    level_name, level_num = compute_discipline_level(
        confirmed_count,
        warning_threshold=int(cfg.nguongCanhBao),
        lock_threshold=int(cfg.nguongKhoaTaiKhoan),
    )

    # Only evaluate warnings/auto-lock when this violation belongs to the current cycle & is CONFIRMED
    if violation.trangThaiXuLy != "CONFIRMED" or int(violation.chuKyKyLuatSo) != cycle:
        return confirmed_count, level_name, False

    role_name = locked_user.vaiTro.tenVaiTro if locked_user.vaiTro else None
    policy_snap = _policy_snapshot(cfg)
    auto_locked = False

    if level_num in (1, 2, 3):
        title, body = _build_discipline_notification_text(
            level_name, confirmed_count=confirmed_count, cfg=cfg
        )
        _append_audit_log(
            db,
            expert_id=int(locked_expert.maChuyenGia),
            user_id=int(locked_user.maNguoiDung),
            action=level_name,
            actor_source="SYSTEM",
            actor_user_id=None,
            cycle=cycle,
            prev_status=locked_user.trangThai,
            new_status=locked_user.trangThai,
            violation_count=confirmed_count,
            reason=body,
            policy_snap=policy_snap,
            now=now,
        )
        notification_service.create_notification_idempotent(
            db,
            recipient_user_id=int(locked_user.maNguoiDung),
            notification_type=f"ACCOUNTABILITY_{level_name}",
            title=title,
            body=body,
            event_key=f"ACC_L{level_num}:E{locked_expert.maChuyenGia}:C{cycle}:V{violation.maViPham}",
            payload={
                "maViPham": int(violation.maViPham),
                "level": level_name,
                "confirmedCount": confirmed_count,
                "cycle": cycle,
            },
            now=now,
        )
    elif level_num == 4:
        # Auto-lock eligibility (Section 27):
        # MUST be role EXPERT, currently ACTIVE, tuDongKhoa=True!
        if (
            role_name == "EXPERT"
            and (locked_user.trangThai or "").upper() == "ACTIVE"
            and bool(cfg.tuDongKhoa)
        ):
            prev_st = locked_user.trangThai
            locked_user.trangThai = "LOCKED"
            auto_locked = True
            title, body = _build_discipline_notification_text(
                "AUTO_LOCK", confirmed_count=confirmed_count, cfg=cfg
            )
            _append_audit_log(
                db,
                expert_id=int(locked_expert.maChuyenGia),
                user_id=int(locked_user.maNguoiDung),
                action="AUTO_LOCK",
                actor_source="SYSTEM",
                actor_user_id=None,
                cycle=cycle,
                prev_status=prev_st,
                new_status="LOCKED",
                violation_count=confirmed_count,
                reason=body,
                policy_snap=policy_snap,
                now=now,
            )
            notification_service.create_notification_idempotent(
                db,
                recipient_user_id=int(locked_user.maNguoiDung),
                notification_type="ACCOUNTABILITY_AUTO_LOCK",
                title=title,
                body=body,
                event_key=f"ACC_L4:E{locked_expert.maChuyenGia}:C{cycle}:V{violation.maViPham}",
                payload={
                    "maViPham": int(violation.maViPham),
                    "confirmedCount": confirmed_count,
                    "cycle": cycle,
                },
                now=now,
            )
            notification_service.notify_active_admins(
                db,
                notification_type="ACCOUNTABILITY_AUTO_LOCK_ADMIN",
                title="Hệ thống đã tự động khóa tài khoản chuyên gia",
                body=f"Chuyên gia #{locked_expert.maChuyenGia} đạt {confirmed_count}/{cfg.nguongKhoaTaiKhoan} vi phạm trong {cfg.khoangThongKeGio} giờ (chu kỳ {cycle}) và đã bị khóa tự động.",
                event_key=f"ACC_L4_ADMIN:E{locked_expert.maChuyenGia}:C{cycle}:V{violation.maViPham}",
                payload={
                    "maChuyenGia": int(locked_expert.maChuyenGia),
                    "maViPham": int(violation.maViPham),
                    "confirmedCount": confirmed_count,
                },
                now=now,
            )
        elif not bool(cfg.tuDongKhoa) and role_name == "EXPERT":
            # tuDongKhoa=False: notify admins & warn expert, do NOT set LOCKED
            notification_service.notify_active_admins(
                db,
                notification_type="ACCOUNTABILITY_THRESHOLD_REACHED",
                title="Chuyên gia đạt ngưỡng khóa (tự động khóa đang tắt)",
                body=f"Chuyên gia #{locked_expert.maChuyenGia} đạt {confirmed_count}/{cfg.nguongKhoaTaiKhoan} vi phạm (tuDongKhoa=False).",
                event_key=f"ACC_L4_MANUAL:E{locked_expert.maChuyenGia}:C{cycle}:V{violation.maViPham}",
                now=now,
            )

    return confirmed_count, level_name, auto_locked


def record_violation_for_assignment(
    db: Session,
    *,
    assignment_id: int,
    violation_type: str,
    now: datetime | None = None,
    commit: bool = False,
) -> ViolationProcessingResult:
    """Idempotently record a violation from a terminal assignment and evaluate discipline.

    Enforces:
    - Expert ID & reason derived ONLY from PhanCongKiemDuyet (never client input).
    - Terminal state matches violation_type (never COMPLETED).
    - ARCH-05 lock ordering: NguoiDung FOR UPDATE -> ChuyenGia FOR UPDATE.
    - Cross-cycle delayed event protection (occurred_at < mocChuKyKyLuat -> old cycle, PENDING_REVIEW).
    - UNIQUE(maPhanCong) idempotency.
    """
    eval_now = now or _utc_now()
    cfg = _get_validated_accountability_config(db)

    pc = db.get(PhanCongKiemDuyet, assignment_id)
    if pc is None:
        raise WorkflowNotFoundError(f"Không tìm thấy phân công #{assignment_id}.")

    expected_terminal = {
        "DECLINED_ASSIGNMENT": "DECLINED",
        "EXPIRED_ACCEPTANCE": "EXPIRED",
        "ABANDONED_ASSIGNMENT": "CANCELLED",
    }.get(violation_type)
    if expected_terminal is None or pc.trangThai != expected_terminal:
        raise WorkflowConflictError(
            f"Trạng thái phân công ({pc.trangThai}) không khớp loại vi phạm {violation_type}."
        )

    expert_probe = db.get(ChuyenGia, pc.maChuyenGia)
    if expert_probe is None or expert_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia của phân công.")

    # ARCH-05: Lock NguoiDung BEFORE ChuyenGia
    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db,
        user_id=int(expert_probe.maNguoiDung),
        expert_id=int(pc.maChuyenGia),
    )
    if locked_user is None or locked_expert is None:
        raise WorkflowNotFoundError("Không tìm thấy tài khoản hoặc hồ sơ chuyên gia.")

    # Idempotency check by UNIQUE(maPhanCong)
    existing = db.scalars(
        select(ViPhamChuyenGia)
        .where(ViPhamChuyenGia.maPhanCong == assignment_id)
        .execution_options(populate_existing=True)
    ).first()
    if existing is not None:
        if int(existing.maChuyenGia) != int(locked_expert.maChuyenGia):
            raise WorkflowConflictError("Dữ liệu vi phạm hiện hữu không khớp chuyên gia sở hữu phân công.")
        cur_cycle = int(locked_expert.chuKyKyLuatSo or 1)
        cnt = count_confirmed_violations_in_window(
            db,
            expert_id=int(locked_expert.maChuyenGia),
            cycle=cur_cycle,
            cycle_started_at=locked_expert.mocChuKyKyLuat,
            window_hours=int(cfg.khoangThongKeGio),
            evaluated_at=eval_now,
        )
        lvl_name, _ = compute_discipline_level(
            cnt,
            warning_threshold=int(cfg.nguongCanhBao),
            lock_threshold=int(cfg.nguongKhoaTaiKhoan),
        )
        return ViolationProcessingResult(
            violationId=int(existing.maViPham),
            created=False,
            status=existing.trangThaiXuLy,
            confirmedCountInWindow=cnt,
            disciplineLevel=lvl_name,
            autoLocked=False,
            cycle=int(existing.chuKyKyLuatSo),
            message="Violation already recorded (idempotent).",
        )

    # Determine initial violation status via policy (ACC-11: honor event-time policySnapshot if present)
    acc_ev = (pc.chiTietDiem or {}).get("accountabilityEvent") or {}
    ev_policy = acc_ev.get("policySnapshot") or {}
    effective_exp_counts = (
        bool(ev_policy["tinhViPhamHetHan"])
        if "tinhViPhamHetHan" in ev_policy
        else bool(cfg.tinhViPhamHetHan)
    )
    initial_status = classify_initial_violation_status(
        violation_type=violation_type,
        decline_reason_code=pc.maLyDoTuChoi,
        expiration_counts_as_violation=effective_exp_counts,
    )
    if initial_status is None:
        # Mark skipped event so reconciliation does not re-scan infinitely (GĐ3.6 hardening)
        details = dict(pc.chiTietDiem or {})
        ev_copy = dict(details.get("accountabilityEvent") or {})
        ev_copy["reconciledSkipped"] = True
        ev_copy["reconciledOutcome"] = "EXPIRED_VIOLATION_DISABLED"
        details["accountabilityEvent"] = ev_copy
        pc.chiTietDiem = details
        db.flush()
        if commit:
            db.commit()
        cur_cycle = int(locked_expert.chuKyKyLuatSo or 1)
        return ViolationProcessingResult(
            violationId=None,
            created=False,
            status=None,
            confirmedCountInWindow=0,
            disciplineLevel="NORMAL",
            autoLocked=False,
            cycle=cur_cycle,
            message="Expiration policy disabled (tinhViPhamHetHan=False); no violation recorded.",
        )

    # Determine true event occurrence timestamp (Section 13 & Section 17)
    if violation_type == "EXPIRED_ACCEPTANCE":
        occurred_at = pc.hanTiepNhan
    elif acc_ev.get("occurredAt"):
        occurred_at = datetime.fromisoformat(acc_ev["occurredAt"])
    else:
        occurred_at = eval_now

    # ACC-10: Exact historical cycle resolution across multiple ADMIN unlocks (no cycle-1 guessing!)
    current_cycle = int(locked_expert.chuKyKyLuatSo or 1)
    target_cycle = current_cycle
    applied_cycle_anchor = locked_expert.mocChuKyKyLuat
    if (
        locked_expert.mocChuKyKyLuat is not None
        and occurred_at < locked_expert.mocChuKyKyLuat
    ):
        unlock_logs = list(
            db.scalars(
                select(NhatKyKyLuatChuyenGia)
                .where(
                    NhatKyKyLuatChuyenGia.maChuyenGia == int(locked_expert.maChuyenGia),
                    NhatKyKyLuatChuyenGia.hanhDong == "ADMIN_UNLOCK",
                )
                .order_by(NhatKyKyLuatChuyenGia.ngayTao.asc(), NhatKyKyLuatChuyenGia.maNhatKy.asc())
            ).all()
        )
        resolved_cycle = 1
        resolved_anchor: datetime | None = None
        for ulog in unlock_logs:
            if occurred_at >= ulog.ngayTao:
                resolved_cycle = int(ulog.chuKyKyLuatSo)
                resolved_anchor = ulog.ngayTao
            else:
                break
        target_cycle = resolved_cycle
        applied_cycle_anchor = resolved_anchor
        initial_status = "PENDING_REVIEW"

    reason_text = (
        pc.lyDoTuChoi
        if violation_type == "DECLINED_ASSIGNMENT"
        else (
            f"Hết hạn tiếp nhận nhiệm vụ #{pc.maPhanCong} (hạn: {pc.hanTiepNhan.isoformat()})."
            if violation_type == "EXPIRED_ACCEPTANCE"
            else (pc.lyDoHuy or f"Bỏ dở nhiệm vụ #{pc.maPhanCong}.")
        )
    )

    sp = db.begin_nested()
    try:
        vp = ViPhamChuyenGia(
            maChuyenGia=int(locked_expert.maChuyenGia),
            maPhanCong=int(pc.maPhanCong),
            loaiViPham=violation_type,
            maLyDoTuChoi=pc.maLyDoTuChoi,
            lyDo=reason_text,
            trangThaiXuLy=initial_status,
            chuKyKyLuatSo=target_cycle,
            mocChuKyApDung=applied_cycle_anchor,
            ngayViPham=occurred_at,
        )
        db.add(vp)
        db.flush()
        sp.commit()
    except IntegrityError:
        sp.rollback()
        existing_after = db.scalars(
            select(ViPhamChuyenGia).where(ViPhamChuyenGia.maPhanCong == assignment_id)
        ).first()
        if existing_after is not None:
            return ViolationProcessingResult(
                violationId=int(existing_after.maViPham),
                created=False,
                status=existing_after.trangThaiXuLy,
                confirmedCountInWindow=0,
                disciplineLevel="NORMAL",
                autoLocked=False,
                cycle=int(existing_after.chuKyKyLuatSo),
                message="Concurrent duplicate violation safely deduplicated.",
            )
        raise

    confirmed_cnt, lvl_name, auto_locked = _evaluate_and_apply_discipline_under_lock(
        db,
        locked_user=locked_user,
        locked_expert=locked_expert,
        violation=vp,
        cfg=cfg,
        now=eval_now,
    )

    if commit:
        db.commit()

    return ViolationProcessingResult(
        violationId=int(vp.maViPham),
        created=True,
        status=vp.trangThaiXuLy,
        confirmedCountInWindow=confirmed_cnt,
        disciplineLevel=lvl_name,
        autoLocked=auto_locked,
        cycle=target_cycle,
        message=f"Recorded {violation_type} ({vp.trangThaiXuLy}), level={lvl_name}.",
    )


def reconcile_unrecorded_accountability_events(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 50,
    commit: bool = True,
) -> int:
    """ACC-12: Durable violation event recovery after crash/restart.

    Finds DECLINED/EXPIRED assignments that carry an accountabilityEvent in chiTietDiem
    but do not yet have a corresponding ViPhamChuyenGia row, and records each idempotently.
    """
    ts = now or _utc_now()
    existing_pc_subq = select(ViPhamChuyenGia.maPhanCong)
    rows = list(
        db.scalars(
            select(PhanCongKiemDuyet)
            .where(
                PhanCongKiemDuyet.trangThai.in_(("DECLINED", "EXPIRED")),
                PhanCongKiemDuyet.chiTietDiem.is_not(None),
                ~PhanCongKiemDuyet.maPhanCong.in_(existing_pc_subq),
            )
            .order_by(PhanCongKiemDuyet.maPhanCong.asc())
            .limit(limit)
        ).all()
    )
    recovered = 0
    for pc in rows:
        acc_ev = (pc.chiTietDiem or {}).get("accountabilityEvent")
        if not isinstance(acc_ev, dict) or acc_ev.get("reconciledSkipped"):
            continue
        ev_type = acc_ev.get("eventType")
        if ev_type not in ("DECLINED_ASSIGNMENT", "EXPIRED_ACCEPTANCE"):
            continue
        res = record_violation_for_assignment(
            db,
            assignment_id=int(pc.maPhanCong),
            violation_type=ev_type,
            now=ts,
            commit=commit,
        )
        if res.created:
            recovered += 1
        if res.autoLocked:
            reconcile_locked_expert_assignments(
                db, expert_id=int(pc.maChuyenGia), now=ts, commit=commit
            )
    return recovered


def reconcile_locked_expert_assignments(
    db: Session,
    *,
    expert_id: int | None = None,
    now: datetime | None = None,
    commit: bool = True,
) -> int:
    """Durable Step-2 Assignment Revocation Recovery (Section 35).

    Finds active assignments belonging to LOCKED experts and revokes each in strict
    ARCH-05 target-first order (KhoaHoc/TaiLieu -> NguoiDung -> ChuyenGia -> PhanCongKiemDuyet):
    - Sets trangThai = 'CANCELLED', lyDoHuy = 'ACCOUNT_LOCKED: ...'
    - Preserves banNhapDanhGia & chiTietDiem
    - NEVER creates a violation for lock-induced cancellation
    - Enqueues durable REASSIGN_CANCELLED if target is still PENDING on current round
    """
    ts = now or _utc_now()
    stmt = (
        select(PhanCongKiemDuyet.maPhanCong)
        .join(ChuyenGia, ChuyenGia.maChuyenGia == PhanCongKiemDuyet.maChuyenGia)
        .join(NguoiDung, NguoiDung.maNguoiDung == ChuyenGia.maNguoiDung)
        .where(
            NguoiDung.trangThai == "LOCKED",
            PhanCongKiemDuyet.trangThai.in_(assignment_repository.ACTIVE_ASSIGNMENT_STATUSES),
        )
        .order_by(PhanCongKiemDuyet.maPhanCong.asc())
    )
    if expert_id is not None:
        stmt = stmt.where(PhanCongKiemDuyet.maChuyenGia == expert_id)

    pc_ids = list(db.scalars(stmt).all())
    revoked = 0
    for pc_id in pc_ids:
        pc_probe = db.get(PhanCongKiemDuyet, pc_id)
        if pc_probe is None or pc_probe.trangThai not in assignment_repository.ACTIVE_ASSIGNMENT_STATUSES:
            continue
        t_type: TargetType = "COURSE" if pc_probe.maKhoaHoc is not None else "MATERIAL"
        t_id = int(pc_probe.maKhoaHoc if t_type == "COURSE" else pc_probe.maTaiLieu)

        # ARCH-05 Step 2: Lock target first
        target, _ = assignment_repository.get_target(db, t_type, t_id, for_update=True)
        # Lock assignment
        pc = db.scalars(
            select(PhanCongKiemDuyet)
            .where(PhanCongKiemDuyet.maPhanCong == pc_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).first()
        if pc is None or pc.trangThai not in assignment_repository.ACTIVE_ASSIGNMENT_STATUSES:
            continue

        pc.trangThai = "CANCELLED"
        pc.lyDoHuy = "ACCOUNT_LOCKED: Thu hồi tự động do tài khoản chuyên gia bị khóa."
        pc.ngayCapNhat = ts
        details = dict(pc.chiTietDiem or {})
        details["revocationEvent"] = {
            "reason": "ACCOUNT_LOCKED",
            "occurredAt": ts.isoformat(),
        }
        pc.chiTietDiem = details
        db.flush()

        if (
            target is not None
            and target.trangThaiDuyet == "PENDING"
            and int(target.soVongKiemDuyetHienTai or 0) == int(pc.soVongKiemDuyet)
        ):
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

        revoked += 1
        if commit:
            db.commit()

    return revoked


def admin_confirm_violation(
    db: Session,
    *,
    admin_user_id: int,
    violation_id: int,
    note: str,
    now: datetime | None = None,
) -> tuple[ViPhamChuyenGia, bool]:
    """ADMIN confirms a PENDING_REVIEW violation -> re-evaluates warnings & auto-lock."""
    eval_now = now or _utc_now()
    cfg = _get_validated_accountability_config(db)
    vp_probe = db.get(ViPhamChuyenGia, violation_id)
    if vp_probe is None:
        raise WorkflowNotFoundError("Không tìm thấy bản ghi vi phạm.")
    expert_probe = db.get(ChuyenGia, vp_probe.maChuyenGia)
    if expert_probe is None or expert_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia.")

    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db,
        user_id=int(expert_probe.maNguoiDung),
        expert_id=int(vp_probe.maChuyenGia),
    )
    vp = db.scalars(
        select(ViPhamChuyenGia)
        .where(ViPhamChuyenGia.maViPham == violation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if vp is None:
        raise WorkflowNotFoundError("Không tìm thấy bản ghi vi phạm.")
    if vp.trangThaiXuLy == "EXEMPTED":
        raise WorkflowConflictError("Không thể xác nhận lại vi phạm đã được miễn trừ.")
    if vp.trangThaiXuLy == "CONFIRMED":
        return vp, False

    vp.trangThaiXuLy = "CONFIRMED"
    vp.maNguoiXuLy = admin_user_id
    vp.ngayXuLy = eval_now
    vp.ghiChuXuLy = note.strip()
    db.flush()

    _append_audit_log(
        db,
        expert_id=int(locked_expert.maChuyenGia),
        user_id=int(locked_user.maNguoiDung),
        action="CONFIRM_VIOLATION",
        actor_source="ADMIN",
        actor_user_id=admin_user_id,
        cycle=int(vp.chuKyKyLuatSo),
        prev_status=locked_user.trangThai,
        new_status=locked_user.trangThai,
        violation_count=None,
        reason=f"ADMIN xác nhận vi phạm #{vp.maViPham}: {note.strip()}",
        policy_snap=_policy_snapshot(cfg),
        now=eval_now,
    )

    _, _, auto_locked = _evaluate_and_apply_discipline_under_lock(
        db,
        locked_user=locked_user,
        locked_expert=locked_expert,
        violation=vp,
        cfg=cfg,
        now=eval_now,
    )
    db.commit()
    db.refresh(vp)

    if auto_locked:
        reconcile_locked_expert_assignments(
            db, expert_id=int(locked_expert.maChuyenGia), now=eval_now, commit=True
        )
    return vp, auto_locked


def admin_exempt_violation(
    db: Session,
    *,
    admin_user_id: int,
    violation_id: int,
    note: str,
    now: datetime | None = None,
) -> ViPhamChuyenGia:
    """ADMIN exempts a PENDING_REVIEW or CONFIRMED violation. NEVER auto-unlocks account."""
    eval_now = now or _utc_now()
    cfg = _get_validated_accountability_config(db)
    vp_probe = db.get(ViPhamChuyenGia, violation_id)
    if vp_probe is None:
        raise WorkflowNotFoundError("Không tìm thấy bản ghi vi phạm.")
    expert_probe = db.get(ChuyenGia, vp_probe.maChuyenGia)
    if expert_probe is None or expert_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia.")

    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db,
        user_id=int(expert_probe.maNguoiDung),
        expert_id=int(vp_probe.maChuyenGia),
    )
    vp = db.scalars(
        select(ViPhamChuyenGia)
        .where(ViPhamChuyenGia.maViPham == violation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if vp is None:
        raise WorkflowNotFoundError("Không tìm thấy bản ghi vi phạm.")
    if vp.trangThaiXuLy == "EXEMPTED":
        return vp

    vp.trangThaiXuLy = "EXEMPTED"
    vp.maNguoiXuLy = admin_user_id
    vp.ngayXuLy = eval_now
    vp.ghiChuXuLy = note.strip()
    db.flush()

    _append_audit_log(
        db,
        expert_id=int(locked_expert.maChuyenGia),
        user_id=int(locked_user.maNguoiDung),
        action="EXEMPT_VIOLATION",
        actor_source="ADMIN",
        actor_user_id=admin_user_id,
        cycle=int(vp.chuKyKyLuatSo),
        prev_status=locked_user.trangThai,
        new_status=locked_user.trangThai,
        violation_count=None,
        reason=f"ADMIN miễn trừ vi phạm #{vp.maViPham}: {note.strip()}",
        policy_snap=_policy_snapshot(cfg),
        now=eval_now,
    )
    db.commit()
    db.refresh(vp)
    return vp


def admin_lock_expert(
    db: Session,
    *,
    admin_user_id: int,
    expert_id: int,
    reason: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """ADMIN manually locks an EXPERT account with audit log + durable assignment revocation."""
    eval_now = now or _utc_now()
    cfg = _get_validated_accountability_config(db)
    expert_probe = db.get(ChuyenGia, expert_id)
    if expert_probe is None or expert_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia.")

    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db,
        user_id=int(expert_probe.maNguoiDung),
        expert_id=expert_id,
    )
    role_name = locked_user.vaiTro.tenVaiTro if locked_user.vaiTro else None
    if role_name != "EXPERT":
        raise WorkflowConflictError("Tài khoản này không có vai trò EXPERT.")
    if (locked_user.trangThai or "").upper() == "LOCKED":
        raise WorkflowConflictError("Tài khoản chuyên gia đã ở trạng thái LOCKED.")

    prev_st = locked_user.trangThai
    locked_user.trangThai = "LOCKED"
    cycle = int(locked_expert.chuKyKyLuatSo or 1)
    _append_audit_log(
        db,
        expert_id=expert_id,
        user_id=int(locked_user.maNguoiDung),
        action="ADMIN_LOCK",
        actor_source="ADMIN",
        actor_user_id=admin_user_id,
        cycle=cycle,
        prev_status=prev_st,
        new_status="LOCKED",
        violation_count=None,
        reason=reason.strip(),
        policy_snap=_policy_snapshot(cfg),
        now=eval_now,
    )
    db.commit()

    revoked = reconcile_locked_expert_assignments(
        db, expert_id=expert_id, now=eval_now, commit=True
    )
    return {
        "maChuyenGia": expert_id,
        "trangThaiTaiKhoan": "LOCKED",
        "revokedAssignments": revoked,
    }


def admin_unlock_expert(
    db: Session,
    *,
    admin_user_id: int,
    expert_id: int,
    reason: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """ONLY ADMIN can unlock a LOCKED EXPERT account.

    - Completes any pending assignment revocation BEFORE unlocking.
    - Increments chuKyKyLuatSo by 1 and sets mocChuKyKyLuat = now.
    - Rejects unlocking an already-ACTIVE account (never allows cycle reset on ACTIVE).
    - Preserves all historical violations & audit logs; NEVER auto-verifies profile.
    """
    eval_now = now or _utc_now()
    cfg = _get_validated_accountability_config(db)
    expert_probe = db.get(ChuyenGia, expert_id)
    if expert_probe is None or expert_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia.")

    # Step 1: Ensure all active assignments from locked state are revoked BEFORE unlocking
    reconcile_locked_expert_assignments(
        db, expert_id=expert_id, now=eval_now, commit=True
    )

    # Step 2: Lock NguoiDung -> ChuyenGia and perform atomic unlock + new cycle
    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db,
        user_id=int(expert_probe.maNguoiDung),
        expert_id=expert_id,
    )
    role_name = locked_user.vaiTro.tenVaiTro if locked_user.vaiTro else None
    if role_name != "EXPERT":
        raise WorkflowConflictError("Tài khoản này không có vai trò EXPERT.")
    if (locked_user.trangThai or "").upper() != "LOCKED":
        raise WorkflowConflictError(
            "Tài khoản chuyên gia không ở trạng thái LOCKED nên không thể mở khóa."
        )

    new_cycle = int(locked_expert.chuKyKyLuatSo or 1) + 1
    locked_user.trangThai = "ACTIVE"
    locked_expert.chuKyKyLuatSo = new_cycle
    locked_expert.mocChuKyKyLuat = eval_now

    _append_audit_log(
        db,
        expert_id=expert_id,
        user_id=int(locked_user.maNguoiDung),
        action="ADMIN_UNLOCK",
        actor_source="ADMIN",
        actor_user_id=admin_user_id,
        cycle=new_cycle,
        prev_status="LOCKED",
        new_status="ACTIVE",
        violation_count=0,
        reason=reason.strip(),
        policy_snap=_policy_snapshot(cfg),
        now=eval_now,
    )
    notification_service.create_notification_idempotent(
        db,
        recipient_user_id=int(locked_user.maNguoiDung),
        notification_type="ACCOUNTABILITY_UNLOCKED",
        title="Tài khoản chuyên gia đã được mở khóa",
        body=f"Quản trị viên đã mở khóa tài khoản của bạn (chu kỳ kỷ luật #{new_cycle}). Vui lòng đăng nhập lại để tiếp tục.",
        event_key=f"ACC_UNLOCK:E{expert_id}:C{new_cycle}",
        payload={"cycle": new_cycle},
        now=eval_now,
    )
    db.commit()

    # Step 3: Safely wake WAITING_ELIGIBLE jobs after unlock commits
    assignment_queue_service.wake_waiting_eligible_jobs(db, limit=20, now=eval_now)
    db.commit()

    return {
        "maChuyenGia": expert_id,
        "trangThaiTaiKhoan": "ACTIVE",
        "chuKyKyLuatSo": new_cycle,
        "mocChuKyKyLuat": eval_now,
    }


# =====================================================================
# Read & Summary APIs (EXPERT + ADMIN) + Policy Config Update
# =====================================================================
def get_expert_accountability_summary(
    db: Session,
    *,
    expert_id: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    eval_now = now or _utc_now()
    cfg = _get_validated_accountability_config(db)
    expert = db.scalars(
        select(ChuyenGia)
        .options(joinedload(ChuyenGia.nguoiDung))
        .where(ChuyenGia.maChuyenGia == expert_id)
    ).first()
    if expert is None or expert.nguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia.")

    cycle = int(expert.chuKyKyLuatSo or 1)
    confirmed = count_confirmed_violations_in_window(
        db,
        expert_id=expert_id,
        cycle=cycle,
        cycle_started_at=expert.mocChuKyKyLuat,
        window_hours=int(cfg.khoangThongKeGio),
        evaluated_at=eval_now,
    )
    pending_cnt = int(
        db.scalar(
            select(func.count(ViPhamChuyenGia.maViPham)).where(
                ViPhamChuyenGia.maChuyenGia == expert_id,
                ViPhamChuyenGia.chuKyKyLuatSo == cycle,
                ViPhamChuyenGia.trangThaiXuLy == "PENDING_REVIEW",
            )
        )
        or 0
    )
    exempted_cnt = int(
        db.scalar(
            select(func.count(ViPhamChuyenGia.maViPham)).where(
                ViPhamChuyenGia.maChuyenGia == expert_id,
                ViPhamChuyenGia.chuKyKyLuatSo == cycle,
                ViPhamChuyenGia.trangThaiXuLy == "EXEMPTED",
            )
        )
        or 0
    )
    lvl_name, _ = compute_discipline_level(
        confirmed,
        warning_threshold=int(cfg.nguongCanhBao),
        lock_threshold=int(cfg.nguongKhoaTaiKhoan),
    )
    remaining = max(0, int(cfg.nguongKhoaTaiKhoan) - confirmed)
    return {
        "maChuyenGia": expert_id,
        "confirmedViolationsInWindow": confirmed,
        "pendingReviewCount": pending_cnt,
        "exemptedCount": exempted_cnt,
        "warningThreshold": int(cfg.nguongCanhBao),
        "finalWarningThreshold": max(int(cfg.nguongCanhBao), int(cfg.nguongKhoaTaiKhoan) - 1),
        "lockThreshold": int(cfg.nguongKhoaTaiKhoan),
        "remainingBeforeLock": remaining,
        "disciplineLevel": lvl_name,
        "windowHours": int(cfg.khoangThongKeGio),
        "currentCycle": cycle,
        "cycleStartedAt": expert.mocChuKyKyLuat,
        "accountStatus": expert.nguoiDung.trangThai,
        "automaticLockEnabled": bool(cfg.tuDongKhoa),
        "expirationCountsAsViolation": bool(cfg.tinhViPhamHetHan),
        "evaluatedAt": eval_now,
    }


def get_accountability_policy(db: Session) -> dict[str, Any]:
    cfg = _get_validated_accountability_config(db)
    return {
        "windowHours": int(cfg.khoangThongKeGio),
        "warningThreshold": int(cfg.nguongCanhBao),
        "finalWarningThreshold": max(int(cfg.nguongCanhBao), int(cfg.nguongKhoaTaiKhoan) - 1),
        "lockThreshold": int(cfg.nguongKhoaTaiKhoan),
        "automaticLockEnabled": bool(cfg.tuDongKhoa),
        "expirationCountsAsViolation": bool(cfg.tinhViPhamHetHan),
        "autoUnlockEnabled": False,
        "onlyAdminCanUnlock": True,
    }


def list_violations(
    db: Session,
    *,
    expert_id: int | None = None,
    status: str | None = None,
    cycle: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ViPhamChuyenGia]:
    stmt = select(ViPhamChuyenGia)
    if expert_id is not None:
        stmt = stmt.where(ViPhamChuyenGia.maChuyenGia == expert_id)
    if status:
        stmt = stmt.where(ViPhamChuyenGia.trangThaiXuLy == status)
    if cycle is not None:
        stmt = stmt.where(ViPhamChuyenGia.chuKyKyLuatSo == cycle)
    return list(
        db.scalars(
            stmt.order_by(ViPhamChuyenGia.ngayViPham.desc(), ViPhamChuyenGia.maViPham.desc())
            .offset(offset)
            .limit(min(limit, 100))
        ).all()
    )


def list_audit_logs(
    db: Session,
    *,
    expert_id: int | None = None,
    action: str | None = None,
    cycle: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[NhatKyKyLuatChuyenGia]:
    stmt = select(NhatKyKyLuatChuyenGia)
    if expert_id is not None:
        stmt = stmt.where(NhatKyKyLuatChuyenGia.maChuyenGia == expert_id)
    if action:
        stmt = stmt.where(NhatKyKyLuatChuyenGia.hanhDong == action)
    if cycle is not None:
        stmt = stmt.where(NhatKyKyLuatChuyenGia.chuKyKyLuatSo == cycle)
    return list(
        db.scalars(
            stmt.order_by(NhatKyKyLuatChuyenGia.ngayTao.desc(), NhatKyKyLuatChuyenGia.maNhatKy.desc())
            .offset(offset)
            .limit(min(limit, 100))
        ).all()
    )


def admin_list_experts_accountability(
    db: Session, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    eval_now = now or _utc_now()
    experts = list(
        db.scalars(
            select(ChuyenGia)
            .options(joinedload(ChuyenGia.nguoiDung).joinedload(NguoiDung.vaiTro))
            .order_by(ChuyenGia.maChuyenGia.asc())
        ).unique().all()
    )
    items = []
    for e in experts:
        if e.nguoiDung is None or (e.nguoiDung.vaiTro and e.nguoiDung.vaiTro.tenVaiTro != "EXPERT"):
            continue
        s = get_expert_accountability_summary(db, expert_id=int(e.maChuyenGia), now=eval_now)
        items.append(
            {
                "maChuyenGia": int(e.maChuyenGia),
                "maNguoiDung": int(e.maNguoiDung),
                "hoTen": e.nguoiDung.hoTen,
                "trangThaiTaiKhoan": e.nguoiDung.trangThai,
                "trangThaiHoSo": e.trangThaiHoSo,
                "currentCycle": s["currentCycle"],
                "confirmedViolationsInWindow": s["confirmedViolationsInWindow"],
                "pendingReviewCount": s["pendingReviewCount"],
                "disciplineLevel": s["disciplineLevel"],
            }
        )
    return items


def admin_update_accountability_config(
    db: Session,
    *,
    admin_user_id: int,
    updates: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Update singleton CauHinhPhanCong accountability fields without retroactive locking."""
    ts = now or _utc_now()
    cfg = db.scalars(
        select(CauHinhPhanCong)
        .where(CauHinhPhanCong.maCauHinh == 1)
        .with_for_update()
    ).first()
    if cfg is None:
        raise AssignmentConfigurationError("CauHinhPhanCong singleton is missing.")

    new_warn = updates.get("nguongCanhBao", cfg.nguongCanhBao)
    new_lock = updates.get("nguongKhoaTaiKhoan", cfg.nguongKhoaTaiKhoan)
    if new_lock <= new_warn:
        raise WorkflowConflictError("nguongKhoaTaiKhoan phải lớn hơn nguongCanhBao.")

    for field in ("khoangThongKeGio", "nguongCanhBao", "nguongKhoaTaiKhoan", "tinhViPhamHetHan", "tuDongKhoa"):
        if field in updates and updates[field] is not None:
            setattr(cfg, field, updates[field])
    cfg.maNguoiCapNhat = admin_user_id
    cfg.ngayCapNhat = ts
    db.commit()
    return get_accountability_policy(db)
