"""Event-scoped Durable Queue Service (HangDoiPhanCong) for GĐ3.3.

Provides:
- Deterministic idempotency keys (<= 150 chars, zero dynamic timestamps):
    SUBMIT:{type}:{id}:R{round}
    REASSIGN:{type}:{id}:R{round}:FROM:{source_assignment_id}
    ADMIN_RETRY:{type}:{id}:R{round}:AT:{attempt_seq}
- Source consistency validation for REASSIGN_* events (fail-closed).
- One open job per target enforcement compatible with uq_hangdoi_open_course/material.
- Safe WAITING_ELIGIBLE wake-up without lock inversion.
- Never commits on its own — participates atomically in caller's transaction.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import HangDoiPhanCong, PhanCongKiemDuyet
from repository import assignment_repository
from schemas.assignment import TargetType

OPEN_QUEUE_STATUSES = ("PENDING", "PROCESSING", "RETRYING", "WAITING_ELIGIBLE")

EXPECTED_SOURCE_STATUS_BY_EVENT = {
    "REASSIGN_DECLINED": "DECLINED",
    "REASSIGN_EXPIRED": "EXPIRED",
    "REASSIGN_CANCELLED": "CANCELLED",
}


class QueueValidationError(ValueError):
    """Raised when an enqueue request violates queue/source consistency invariants."""


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def build_event_idempotency_key(
    *,
    target_type: TargetType,
    target_id: int,
    review_round: int,
    event_type: str,
    source_assignment_id: int | None = None,
    attempt_seq: int | None = None,
) -> str:
    if event_type == "SUBMIT":
        key = f"SUBMIT:{target_type}:{target_id}:R{review_round}"
    elif event_type in EXPECTED_SOURCE_STATUS_BY_EVENT:
        if source_assignment_id is None:
            raise QueueValidationError(
                f"{event_type} requires a valid source_assignment_id."
            )
        key = (
            f"REASSIGN:{target_type}:{target_id}:R{review_round}"
            f":FROM:{source_assignment_id}"
        )
    elif event_type == "ADMIN_RETRY":
        if attempt_seq is None or attempt_seq < 1:
            raise QueueValidationError("ADMIN_RETRY requires attempt_seq >= 1.")
        key = (
            f"ADMIN_RETRY:{target_type}:{target_id}:R{review_round}"
            f":AT:{attempt_seq}"
        )
    else:
        raise QueueValidationError(f"Unsupported queue event_type: {event_type!r}")

    if len(key) > 150:
        raise QueueValidationError(f"Queue idempotency key exceeds 150 chars: {len(key)}")
    return key


def validate_reassign_source(
    db: Session,
    *,
    target_type: TargetType,
    target_id: int,
    review_round: int,
    event_type: str,
    source_assignment_id: int | None,
) -> PhanCongKiemDuyet:
    """Section 21: Strict source consistency validation for REASSIGN_* events."""
    expected_status = EXPECTED_SOURCE_STATUS_BY_EVENT.get(event_type)
    if expected_status is None:
        raise QueueValidationError(f"Not a reassign event: {event_type!r}")
    if source_assignment_id is None:
        raise QueueValidationError(
            f"maPhanCongNguon is required for {event_type} (fail-closed)."
        )

    src = db.get(PhanCongKiemDuyet, source_assignment_id)
    if src is None:
        raise QueueValidationError(
            f"Source assignment #{source_assignment_id} does not exist."
        )
    if target_type == "COURSE" and src.maKhoaHoc != target_id:
        raise QueueValidationError(
            f"Source assignment #{source_assignment_id} does not belong to COURSE #{target_id}."
        )
    if target_type == "MATERIAL" and src.maTaiLieu != target_id:
        raise QueueValidationError(
            f"Source assignment #{source_assignment_id} does not belong to MATERIAL #{target_id}."
        )
    if src.soVongKiemDuyet != review_round:
        raise QueueValidationError(
            f"Source assignment #{source_assignment_id} belongs to round {src.soVongKiemDuyet}, "
            f"not current round {review_round}."
        )
    if src.trangThai == "COMPLETED":
        raise QueueValidationError(
            f"Cannot reassign from COMPLETED assignment #{source_assignment_id}."
        )
    if src.trangThai != expected_status:
        raise QueueValidationError(
            f"Source assignment #{source_assignment_id} has status {src.trangThai}, "
            f"expected {expected_status} for {event_type}."
        )
    return src


def next_admin_retry_attempt_seq(
    db: Session,
    *,
    target_type: TargetType,
    target_id: int,
    review_round: int,
) -> int:
    """Compute next deterministic ADMIN_RETRY attempt_seq under target FOR UPDATE lock."""
    col = (
        HangDoiPhanCong.maKhoaHoc
        if target_type == "COURSE"
        else HangDoiPhanCong.maTaiLieu
    )
    cnt = db.scalar(
        select(func.count(HangDoiPhanCong.maCongViec)).where(
            col == target_id,
            HangDoiPhanCong.soVongKiemDuyet == review_round,
            HangDoiPhanCong.loaiSuKien == "ADMIN_RETRY",
        )
    )
    return int(cnt or 0) + 1


def enqueue_assignment_job(
    db: Session,
    *,
    target_type: TargetType,
    target_id: int,
    review_round: int,
    event_type: str,
    source_assignment_id: int | None = None,
    attempt_seq: int | None = None,
    priority: int = 0,
    now: datetime | None = None,
) -> tuple[HangDoiPhanCong, bool]:
    """Enqueue an event-scoped durable job atomically inside caller's transaction.

    Caller MUST hold FOR UPDATE lock on the target (KhoaHoc / TaiLieu) so concurrent
    enqueues for the same target serialize cleanly without losing events.

    Returns: (job, created_new_bool)
    """
    ts = now or _utc_now()
    if review_round < 1:
        raise QueueValidationError(f"review_round must be >= 1, got {review_round}.")

    if event_type in EXPECTED_SOURCE_STATUS_BY_EVENT:
        validate_reassign_source(
            db,
            target_type=target_type,
            target_id=target_id,
            review_round=review_round,
            event_type=event_type,
            source_assignment_id=source_assignment_id,
        )

    if event_type == "ADMIN_RETRY" and attempt_seq is None:
        attempt_seq = next_admin_retry_attempt_seq(
            db,
            target_type=target_type,
            target_id=target_id,
            review_round=review_round,
        )

    idem_key = build_event_idempotency_key(
        target_type=target_type,
        target_id=target_id,
        review_round=review_round,
        event_type=event_type,
        source_assignment_id=source_assignment_id,
        attempt_seq=attempt_seq,
    )

    # 1. Event-scoped idempotency (ENG-02): if this exact event already exists (even if DONE), return it!
    existing_by_key = db.scalars(
        select(HangDoiPhanCong)
        .where(HangDoiPhanCong.khoaChongTrung == idem_key)
        .execution_options(populate_existing=True)
    ).first()
    if existing_by_key is not None:
        return existing_by_key, False

    # 2. Check existing open job on this target (uq_hangdoi_open_course / material)
    col = (
        HangDoiPhanCong.maKhoaHoc
        if target_type == "COURSE"
        else HangDoiPhanCong.maTaiLieu
    )
    open_job = db.scalars(
        select(HangDoiPhanCong)
        .where(
            col == target_id,
            HangDoiPhanCong.trangThai.in_(OPEN_QUEUE_STATUSES),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()

    if open_job is not None:
        if open_job.soVongKiemDuyet < review_round:
            # Stale round job -> cancel cleanly before inserting new round job
            open_job.trangThai = "CANCELLED"
            open_job.maWorker = None
            open_job.claimToken = None
            open_job.hanXuLy = None
            open_job.lyDoCho = f"Superseded by review round {review_round}"
            open_job.ngayCapNhat = ts
            db.flush()
        else:
            # Same-round open job already exists: wake it up if WAITING_ELIGIBLE/RETRYING
            if open_job.trangThai in ("WAITING_ELIGIBLE", "RETRYING"):
                open_job.trangThai = "PENDING"
                open_job.thoiDiemChayTiepTheo = ts
                open_job.lyDoCho = None
                open_job.ngayCapNhat = ts
                db.flush()
            return open_job, False

    # 3. Respect reassignment cap before creating new REASSIGN/ADMIN_RETRY jobs
    if event_type != "SUBMIT":
        cfg = assignment_repository.get_singleton_config(db)
        max_in_round = 1 + int(cfg.soLanTaiPhanCongToiDa)
        current_count = assignment_repository.count_round_assignments(
            db, target_type, target_id, review_round
        )
        if current_count >= max_in_round:
            raise QueueValidationError(
                f"Reassignment limit reached ({current_count}/{max_in_round}) for round {review_round}."
            )

    job = HangDoiPhanCong(
        loaiDoiTuong=target_type,
        maKhoaHoc=target_id if target_type == "COURSE" else None,
        maTaiLieu=target_id if target_type == "MATERIAL" else None,
        soVongKiemDuyet=review_round,
        loaiSuKien=event_type,
        maPhanCongNguon=source_assignment_id,
        khoaChongTrung=idem_key,
        trangThai="PENDING",
        uuTien=priority,
        soLanThu=0,
        soLanThuToiDa=5,
        thoiDiemChayTiepTheo=ts,
        ngayTao=ts,
        ngayCapNhat=ts,
    )
    db.add(job)
    db.flush()
    return job, True


def cancel_open_jobs_for_target(
    db: Session,
    *,
    target_type: TargetType,
    target_id: int,
    reason: str,
    now: datetime | None = None,
) -> int:
    """Cancel any open queue jobs for a target (e.g., when review completes or content leaves PENDING)."""
    ts = now or _utc_now()
    col = (
        HangDoiPhanCong.maKhoaHoc
        if target_type == "COURSE"
        else HangDoiPhanCong.maTaiLieu
    )
    jobs = list(
        db.scalars(
            select(HangDoiPhanCong)
            .where(
                col == target_id,
                HangDoiPhanCong.trangThai.in_(OPEN_QUEUE_STATUSES),
            )
            .with_for_update()
        ).all()
    )
    for j in jobs:
        j.trangThai = "CANCELLED"
        j.maWorker = None
        j.claimToken = None
        j.hanXuLy = None
        j.lyDoCho = reason[:500]
        j.ngayCapNhat = ts
    if jobs:
        db.flush()
    return len(jobs)


def wake_waiting_eligible_jobs(
    db: Session,
    *,
    limit: int = 50,
    now: datetime | None = None,
) -> int:
    """Safely wake WAITING_ELIGIBLE jobs using SKIP LOCKED (zero lock inversion)."""
    ts = now or _utc_now()
    jobs = list(
        db.scalars(
            select(HangDoiPhanCong)
            .where(HangDoiPhanCong.trangThai == "WAITING_ELIGIBLE")
            .order_by(HangDoiPhanCong.ngayCapNhat.asc(), HangDoiPhanCong.maCongViec.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        ).all()
    )
    for j in jobs:
        j.trangThai = "PENDING"
        j.thoiDiemChayTiepTheo = ts
        j.lyDoCho = None
        j.ngayCapNhat = ts
    if jobs:
        db.flush()
    return len(jobs)
