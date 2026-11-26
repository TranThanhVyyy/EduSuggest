"""Standalone PostgreSQL Durable Queue Worker for GĐ3.3.

Features:
- SKIP LOCKED atomic batch claim in a short separate transaction.
- ARCH-06 Fencing: verifies (trangThai == 'PROCESSING', maWorker, claimToken,
  leaseGeneration, hanXuLy > clock_timestamp() AT TIME ZONE 'UTC') BOTH before
  running the assignment engine AND right before commit.
- Crash recovery via `reclaim_stale_processing_jobs()` using PostgreSQL `clock_timestamp()`.
- Exponential backoff [5, 15, 30, 60]s with bounded retry budget (`soLanThuToiDa`).
- Acceptance expiration sweep (`expire_overdue_assignments()`).
- Fail-closed: NEVER auto-started on import or FastAPI lifespan.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models import HangDoiPhanCong, PhanCongKiemDuyet
from repository import assignment_repository
from schemas.assignment import (
    AssignmentStatusCode,
    TargetType,
    WorkerJobContext,
)
from service import (
    assignment_queue_service,
    assignment_service,
    notification_service,
)

DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_LEASE_SECONDS = 60
DEFAULT_BATCH_SIZE = 10
DEFAULT_WAITING_FALLBACK_SECONDS = 300
RETRY_BACKOFF_SECONDS = (5, 15, 30, 60)


@dataclass(frozen=True)
class WorkerProcessOutcome:
    jobId: int
    finalQueueStatus: str
    assignmentStatus: str | None = None
    assignmentId: int | None = None
    fencedOut: bool = False
    errorSummary: str | None = None


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _pg_clock_utc(db: Session) -> datetime:
    """Real PostgreSQL wall-clock UTC timestamp (NOT transaction-start now())."""
    return db.execute(text("SELECT (clock_timestamp() AT TIME ZONE 'UTC')")).scalar_one()


def _backoff_seconds(attempt_index: int) -> int:
    idx = max(0, min(attempt_index, len(RETRY_BACKOFF_SECONDS) - 1))
    return RETRY_BACKOFF_SECONDS[idx]


def _sanitize_error(exc: Exception) -> str:
    """Strip sensitive SQL/credentials; keep concise diagnostic type + message."""
    msg = f"{type(exc).__name__}: {str(exc)}"
    return msg[:300]


class AssignmentQueueWorker:
    """Independent PostgreSQL durable queue worker (NOT auto-started on Production)."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        worker_id: str | None = None,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        waiting_fallback_seconds: int = DEFAULT_WAITING_FALLBACK_SECONDS,
        expected_db_name: str | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.lease_seconds = lease_seconds
        self.batch_size = batch_size
        self.waiting_fallback_seconds = waiting_fallback_seconds
        self.expected_db_name = expected_db_name

    def _open_session(self) -> Session:
        db = self.session_factory()
        if self.expected_db_name:
            cur = db.execute(text("SELECT current_database()")).scalar()
            if cur != self.expected_db_name:
                db.close()
                raise RuntimeError(
                    f"WORKER SAFETY GUARD ABORT: expected DB {self.expected_db_name!r}, got {cur!r}"
                )
        return db

    def claim_next_jobs(self, *, now: datetime | None = None) -> list[WorkerJobContext]:
        """Claim up to batch_size due jobs using FOR UPDATE SKIP LOCKED in a short transaction."""
        with self._open_session() as db:
            ts = now or _pg_clock_utc(db)
            lease_until = ts + timedelta(seconds=self.lease_seconds)

            jobs = list(
                db.scalars(
                    select(HangDoiPhanCong)
                    .where(
                        HangDoiPhanCong.trangThai.in_(("PENDING", "RETRYING")),
                        HangDoiPhanCong.thoiDiemChayTiepTheo <= ts,
                    )
                    .order_by(
                        HangDoiPhanCong.uuTien.desc(),
                        HangDoiPhanCong.thoiDiemChayTiepTheo.asc(),
                        HangDoiPhanCong.maCongViec.asc(),
                    )
                    .with_for_update(skip_locked=True)
                    .limit(self.batch_size)
                ).all()
            )

            contexts: list[WorkerJobContext] = []
            for job in jobs:
                token = uuid.uuid4()
                job.trangThai = "PROCESSING"
                job.maWorker = self.worker_id
                job.claimToken = token
                job.leaseGeneration = int(job.leaseGeneration or 0) + 1
                job.thoiDiemBatDauXuLy = ts
                job.hanXuLy = lease_until
                job.ngayCapNhat = ts
                contexts.append(
                    WorkerJobContext(
                        maCongViec=int(job.maCongViec),
                        claimToken=token,
                        leaseGeneration=int(job.leaseGeneration),
                        maWorker=self.worker_id,
                        loaiSuKien=job.loaiSuKien,
                        maPhanCongNguon=job.maPhanCongNguon,
                    )
                )

            db.commit()
            return contexts

    def reclaim_stale_processing_jobs(self, *, now: datetime | None = None) -> int:
        """Crash recovery: reclaim PROCESSING jobs whose lease hanXuLy <= real clock_timestamp()."""
        with self._open_session() as db:
            ts = now or _pg_clock_utc(db)
            stale_jobs = list(
                db.scalars(
                    select(HangDoiPhanCong)
                    .where(
                        HangDoiPhanCong.trangThai == "PROCESSING",
                        HangDoiPhanCong.hanXuLy <= ts,
                    )
                    .with_for_update(skip_locked=True)
                    .limit(self.batch_size)
                ).all()
            )
            reclaimed = 0
            for job in stale_jobs:
                next_attempt = int(job.soLanThu or 0) + 1
                job.maWorker = None
                job.claimToken = None
                job.hanXuLy = None
                job.ngayCapNhat = ts
                if next_attempt >= int(job.soLanThuToiDa):
                    job.soLanThu = int(job.soLanThuToiDa)
                    job.trangThai = "FAILED"
                    job.loiGanNhat = "Worker lease expired and retry budget exhausted."
                else:
                    job.soLanThu = next_attempt
                    job.trangThai = "RETRYING"
                    job.thoiDiemChayTiepTheo = ts + timedelta(
                        seconds=_backoff_seconds(next_attempt - 1)
                    )
                    job.loiGanNhat = "Reclaimed after worker lease expiration."
                reclaimed += 1
            db.commit()
            return reclaimed

    def _verify_lease_under_lock(
        self,
        db: Session,
        ctx: WorkerJobContext,
        *,
        override_now: datetime | None = None,
    ) -> HangDoiPhanCong | None:
        """ARCH-06 Fencing check using PostgreSQL real wall-clock clock_timestamp()."""
        job = db.scalars(
            select(HangDoiPhanCong)
            .where(HangDoiPhanCong.maCongViec == ctx.maCongViec)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).first()
        if job is None:
            return None
        real_now = override_now or _pg_clock_utc(db)
        if (
            job.trangThai != "PROCESSING"
            or job.maWorker != ctx.maWorker
            or job.claimToken != ctx.claimToken
            or int(job.leaseGeneration) != ctx.leaseGeneration
            or job.hanXuLy is None
            or job.hanXuLy <= real_now
        ):
            return None
        return job

    def process_claimed_job(
        self,
        ctx: WorkerJobContext,
        *,
        now: datetime | None = None,
        before_commit_hook: Callable[[Session], None] | None = None,
    ) -> WorkerProcessOutcome:
        """Process a single claimed job with strict ARCH-06 fencing & atomic commit.

        before_commit_hook is an optional test hook (e.g., to simulate stale-worker pause
        or crash right before commit during crash-recovery tests).
        """
        with self._open_session() as db:
            try:
                # 1. Pre-execution fencing check (ARCH-05 Step 1: lock HangDoiPhanCong first!)
                job = self._verify_lease_under_lock(db, ctx, override_now=now)
                if job is None:
                    db.rollback()
                    return WorkerProcessOutcome(
                        jobId=ctx.maCongViec,
                        finalQueueStatus="FENCED_OUT",
                        fencedOut=True,
                    )

                eval_now = now or _pg_clock_utc(db)
                target_type: TargetType = job.loaiDoiTuong  # type: ignore[assignment]
                target_id = (
                    int(job.maKhoaHoc)
                    if target_type == "COURSE"
                    else int(job.maTaiLieu)
                )
                review_round = int(job.soVongKiemDuyet)

                # 2. Validate REASSIGN source consistency before executing engine
                if job.loaiSuKien in assignment_queue_service.EXPECTED_SOURCE_STATUS_BY_EVENT:
                    try:
                        assignment_queue_service.validate_reassign_source(
                            db,
                            target_type=target_type,
                            target_id=target_id,
                            review_round=review_round,
                            event_type=job.loaiSuKien,
                            source_assignment_id=job.maPhanCongNguon,
                        )
                    except assignment_queue_service.QueueValidationError as qerr:
                        job.trangThai = "FAILED"
                        job.maWorker = None
                        job.claimToken = None
                        job.hanXuLy = None
                        job.loiGanNhat = _sanitize_error(qerr)
                        job.ngayCapNhat = eval_now
                        db.commit()
                        return WorkerProcessOutcome(
                            jobId=ctx.maCongViec,
                            finalQueueStatus="FAILED",
                            errorSummary=job.loiGanNhat,
                        )

                # 3. Call Assignment Engine inside THIS transaction (commit=False!)
                res = assignment_service.assign_best_expert(
                    db,
                    target_type,
                    target_id,
                    expected_review_round=review_round,
                    now=eval_now,
                    worker_context=ctx,
                    commit=False,
                )

                # Optional hook for deterministic crash/fencing tests
                if before_commit_hook is not None:
                    before_commit_hook(db)

                # 4. Final fencing check RIGHT BEFORE finalization & commit!
                job_recheck = self._verify_lease_under_lock(db, ctx, override_now=now)
                if job_recheck is None:
                    db.rollback()
                    return WorkerProcessOutcome(
                        jobId=ctx.maCongViec,
                        finalQueueStatus="FENCED_OUT",
                        fencedOut=True,
                    )

                # 5. Map engine outcome to durable queue state + idempotent notifications
                job_recheck.maWorker = None
                job_recheck.claimToken = None
                job_recheck.hanXuLy = None
                job_recheck.ngayCapNhat = eval_now

                if res.status == AssignmentStatusCode.ASSIGNED:
                    job_recheck.trangThai = "DONE"
                    job_recheck.lyDoCho = None
                    job_recheck.loiGanNhat = None
                    if res.assignedUserId is not None and res.assignmentId is not None:
                        notification_service.create_notification_idempotent(
                            db,
                            recipient_user_id=res.assignedUserId,
                            notification_type="ASSIGNMENT_ASSIGNED",
                            title="Bạn được phân công kiểm duyệt mới",
                            body=res.message,
                            event_key=f"ASSIGN_CREATED:{res.assignmentId}",
                            payload={
                                "maPhanCong": res.assignmentId,
                                "loaiDoiTuong": target_type,
                                "maDoiTuong": target_id,
                                "soVongKiemDuyet": review_round,
                            },
                            now=eval_now,
                        )
                elif res.status == AssignmentStatusCode.ALREADY_ASSIGNED:
                    job_recheck.trangThai = "DONE"
                    job_recheck.lyDoCho = None
                    job_recheck.loiGanNhat = None
                elif res.status == AssignmentStatusCode.NO_ELIGIBLE_EXPERT:
                    job_recheck.trangThai = "WAITING_ELIGIBLE"
                    job_recheck.lyDoCho = res.message
                    job_recheck.thoiDiemChayTiepTheo = eval_now + timedelta(
                        seconds=self.waiting_fallback_seconds
                    )
                    notification_service.notify_active_admins(
                        db,
                        notification_type="ASSIGNMENT_WAITING_ELIGIBLE",
                        title="Nội dung đang chờ chuyên gia kiểm duyệt phù hợp",
                        body=f"{target_type} #{target_id} (vòng {review_round}): {res.message}",
                        event_key=f"WAITING_ELIGIBLE:{target_type}:{target_id}:R{review_round}",
                        payload={
                            "loaiDoiTuong": target_type,
                            "maDoiTuong": target_id,
                            "soVongKiemDuyet": review_round,
                        },
                        now=eval_now,
                    )
                elif res.status == AssignmentStatusCode.STALE_REVIEW_ROUND:
                    job_recheck.trangThai = "CANCELLED"
                    job_recheck.lyDoCho = res.message
                elif res.status in (
                    AssignmentStatusCode.INVALID_TARGET,
                    AssignmentStatusCode.REASSIGNMENT_LIMIT_REACHED,
                    AssignmentStatusCode.CONFIGURATION_ERROR,
                ):
                    job_recheck.trangThai = "FAILED"
                    job_recheck.loiGanNhat = res.message[:300]
                    if res.status == AssignmentStatusCode.REASSIGNMENT_LIMIT_REACHED:
                        notification_service.notify_active_admins(
                            db,
                            notification_type="ASSIGNMENT_REASSIGN_LIMIT",
                            title="Đạt giới hạn tái phân công kiểm duyệt",
                            body=f"{target_type} #{target_id} (vòng {review_round}): {res.message}",
                            event_key=f"REASSIGN_LIMIT:{target_type}:{target_id}:R{review_round}",
                            payload={
                                "loaiDoiTuong": target_type,
                                "maDoiTuong": target_id,
                                "soVongKiemDuyet": review_round,
                            },
                            now=eval_now,
                        )
                elif res.status == AssignmentStatusCode.RETRYABLE_CONFLICT:
                    next_attempt = int(job_recheck.soLanThu or 0) + 1
                    if next_attempt >= int(job_recheck.soLanThuToiDa):
                        job_recheck.soLanThu = int(job_recheck.soLanThuToiDa)
                        job_recheck.trangThai = "FAILED"
                        job_recheck.loiGanNhat = res.message[:300]
                    else:
                        job_recheck.soLanThu = next_attempt
                        job_recheck.trangThai = "RETRYING"
                        job_recheck.thoiDiemChayTiepTheo = eval_now + timedelta(
                            seconds=_backoff_seconds(next_attempt - 1)
                        )
                        job_recheck.loiGanNhat = res.message[:300]

                final_status = job_recheck.trangThai
                db.commit()
                return WorkerProcessOutcome(
                    jobId=ctx.maCongViec,
                    finalQueueStatus=final_status,
                    assignmentStatus=res.status.value,
                    assignmentId=res.assignmentId,
                )
            except Exception as exc:
                db.rollback()
                # Record retry/failure safely ONLY if this worker still owns the lease
                with self._open_session() as err_db:
                    err_job = self._verify_lease_under_lock(err_db, ctx, override_now=now)
                    if err_job is None:
                        err_db.rollback()
                        return WorkerProcessOutcome(
                            jobId=ctx.maCongViec,
                            finalQueueStatus="FENCED_OUT",
                            fencedOut=True,
                            errorSummary=_sanitize_error(exc),
                        )
                    ts = now or _pg_clock_utc(err_db)
                    next_attempt = int(err_job.soLanThu or 0) + 1
                    err_job.maWorker = None
                    err_job.claimToken = None
                    err_job.hanXuLy = None
                    err_job.loiGanNhat = _sanitize_error(exc)
                    err_job.ngayCapNhat = ts
                    if next_attempt >= int(err_job.soLanThuToiDa):
                        err_job.soLanThu = int(err_job.soLanThuToiDa)
                        err_job.trangThai = "FAILED"
                    else:
                        err_job.soLanThu = next_attempt
                        err_job.trangThai = "RETRYING"
                        err_job.thoiDiemChayTiepTheo = ts + timedelta(
                            seconds=_backoff_seconds(next_attempt - 1)
                        )
                    final_st = err_job.trangThai
                    err_db.commit()
                    return WorkerProcessOutcome(
                        jobId=ctx.maCongViec,
                        finalQueueStatus=final_st,
                        errorSummary=err_job.loiGanNhat,
                    )

    def expire_overdue_assignments(self, *, now: datetime | None = None) -> int:
        """Sweep ASSIGNED assignments with hanTiepNhan <= now -> EXPIRED + REASSIGN_EXPIRED."""
        with self._open_session() as db:
            ts = now or _pg_clock_utc(db)
            candidate_ids = list(
                db.scalars(
                    select(PhanCongKiemDuyet.maPhanCong)
                    .where(
                        PhanCongKiemDuyet.trangThai == "ASSIGNED",
                        PhanCongKiemDuyet.hanTiepNhan <= ts,
                    )
                    .order_by(PhanCongKiemDuyet.hanTiepNhan.asc())
                    .limit(self.batch_size)
                ).all()
            )

        expired_count = 0
        for pc_id in candidate_ids:
            with self._open_session() as db:
                pc = db.get(PhanCongKiemDuyet, pc_id)
                if pc is None or pc.trangThai != "ASSIGNED":
                    continue
                target_type: TargetType = "COURSE" if pc.maKhoaHoc is not None else "MATERIAL"
                target_id = int(pc.maKhoaHoc if target_type == "COURSE" else pc.maTaiLieu)

                # ARCH-05: Lock target BEFORE assignment
                target, _ = assignment_repository.get_target(
                    db, target_type, target_id, for_update=True
                )
                locked_pc = db.scalars(
                    select(PhanCongKiemDuyet)
                    .where(PhanCongKiemDuyet.maPhanCong == pc_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                ).first()
                ts_check = now or _pg_clock_utc(db)
                if (
                    locked_pc is None
                    or locked_pc.trangThai != "ASSIGNED"
                    or locked_pc.hanTiepNhan > ts_check
                ):
                    db.rollback()
                    continue

                locked_pc.trangThai = "EXPIRED"
                locked_pc.ngayCapNhat = ts_check
                # Preserve immutable terminal evidence + policySnapshot (ACC-11) for GĐ3.4/3.5 Accountability
                cfg_snap = assignment_repository.get_singleton_config(db)
                details = dict(locked_pc.chiTietDiem or {})
                details["accountabilityEvent"] = {
                    "eventType": "EXPIRED_ACCEPTANCE",
                    "occurredAt": ts_check.isoformat(),
                    "deadlineAt": locked_pc.hanTiepNhan.isoformat(),
                    "expertId": int(locked_pc.maChuyenGia),
                    "policySnapshot": {
                        "tinhViPhamHetHan": bool(cfg_snap.tinhViPhamHetHan),
                        "khoangThongKeGio": int(cfg_snap.khoangThongKeGio),
                        "nguongCanhBao": int(cfg_snap.nguongCanhBao),
                        "nguongKhoaTaiKhoan": int(cfg_snap.nguongKhoaTaiKhoan),
                        "tuDongKhoa": bool(cfg_snap.tuDongKhoa),
                    },
                }
                locked_pc.chiTietDiem = details
                db.flush()

                # Enqueue REASSIGN_EXPIRED if target still PENDING on same review round
                if (
                    target is not None
                    and target.trangThaiDuyet == "PENDING"
                    and int(target.soVongKiemDuyetHienTai or 0) == int(locked_pc.soVongKiemDuyet)
                ):
                    try:
                        assignment_queue_service.enqueue_assignment_job(
                            db,
                            target_type=target_type,
                            target_id=target_id,
                            review_round=int(locked_pc.soVongKiemDuyet),
                            event_type="REASSIGN_EXPIRED",
                            source_assignment_id=int(locked_pc.maPhanCong),
                            now=ts_check,
                        )
                    except assignment_queue_service.QueueValidationError:
                        # Reassignment limit reached -> notify admins cleanly
                        notification_service.notify_active_admins(
                            db,
                            notification_type="ASSIGNMENT_REASSIGN_LIMIT",
                            title="Hết hạn tiếp nhận và đạt giới hạn tái phân công",
                            body=f"{target_type} #{target_id} vòng {locked_pc.soVongKiemDuyet} đã đạt trần tái phân công.",
                            event_key=f"REASSIGN_LIMIT:{target_type}:{target_id}:R{locked_pc.soVongKiemDuyet}",
                            now=ts_check,
                        )

                # Notify expert that assignment expired
                if locked_pc.chuyenGia and locked_pc.chuyenGia.maNguoiDung:
                    notification_service.create_notification_idempotent(
                        db,
                        recipient_user_id=int(locked_pc.chuyenGia.maNguoiDung),
                        notification_type="ASSIGNMENT_EXPIRED",
                        title="Nhiệm vụ kiểm duyệt đã hết hạn tiếp nhận",
                        body=f"Nhiệm vụ #{locked_pc.maPhanCong} đã quá hạn tiếp nhận và được thu hồi để phân công lại.",
                        event_key=f"ASSIGN_EXPIRED:{locked_pc.maPhanCong}",
                        payload={"maPhanCong": int(locked_pc.maPhanCong)},
                        now=ts_check,
                    )

                db.commit()
                expired_count += 1

                # GĐ3.4 fail-closed Accountability hook: record EXPIRED_ACCEPTANCE & durable revocation
                from service import accountability_service

                if accountability_service.is_accountability_enabled():
                    acc_res = accountability_service.record_violation_for_assignment(
                        db,
                        assignment_id=int(locked_pc.maPhanCong),
                        violation_type="EXPIRED_ACCEPTANCE",
                        now=ts_check,
                        commit=True,
                    )
                    if acc_res.autoLocked:
                        accountability_service.reconcile_locked_expert_assignments(
                            db, expert_id=int(locked_pc.maChuyenGia), now=ts_check, commit=True
                        )
        return expired_count

    def run_once(self, *, now: datetime | None = None) -> dict[str, int | list[WorkerProcessOutcome]]:
        """Execute one deterministic worker tick: reclaim -> expire -> availability -> accountability -> claim -> process."""
        reclaimed = self.reclaim_stale_processing_jobs(now=now)
        expired = self.expire_overdue_assignments(now=now)
        ended_pauses = 0
        recovered_violations = 0
        revoked = 0

        from service import accountability_service, availability_service

        with self._open_session() as av_db:
            ended_pauses = availability_service.complete_ended_availability_requests(
                av_db, now=now, commit=True
            )

        if accountability_service.is_accountability_enabled():
            with self._open_session() as rdb:
                recovered_violations = accountability_service.reconcile_unrecorded_accountability_events(
                    rdb, now=now, commit=True
                )
                revoked = accountability_service.reconcile_locked_expert_assignments(
                    rdb, now=now, commit=True
                )
        claimed = self.claim_next_jobs(now=now)
        outcomes = [self.process_claimed_job(ctx, now=now) for ctx in claimed]
        return {
            "reclaimed": reclaimed,
            "expired": expired,
            "ended_pauses": ended_pauses,
            "recovered_violations": recovered_violations,
            "revoked": revoked,
            "claimed": len(claimed),
            "outcomes": outcomes,
        }
