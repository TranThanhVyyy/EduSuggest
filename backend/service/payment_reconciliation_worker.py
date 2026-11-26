"""GĐ4.7A.2 Durable Payment Reconciliation Worker (PostgreSQL SKIP LOCKED + Fencing Token).

Strictly separated from GĐ3 AssignmentQueueWorker (HangDoiPhanCong).
Enforces 3-phase execution so NO DB lock/transaction is ever held during network gateway calls:
  Phase 1 (Short TX): Claim task via FOR UPDATE SKIP LOCKED + increment leaseGeneration + claimToken.
  Phase 2 (No DB Lock): Execute gateway QueryDR / evaluation via injectable GatewayQueryClient.
  Phase 3 (Fenced TX): Re-verify (maTacVu, claimToken, leaseGeneration) before committing results.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import uuid
from typing import Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from config.config import get_settings
from models import (
    DangKyKhoaHoc,
    DonHang,
    HoanTienNgoaiLe,
    LanThuHoanTien,
    NguoiDung,
    TacVuDoiSoatThanhToan,
    ThanhToan,
)
from repository import commerce_repository
from service import commerce_admin_service, financial_event_service, order_payment_service
from service.payment_providers import CallbackVerificationResult

BACKOFF_SECONDS: tuple[int, ...] = (60, 180, 600, 1800, 3600)


@dataclass(frozen=True)
class ClaimedReconTask:
    maTacVu: int
    loaiTacVu: str
    maDonHang: int
    maThanhToan: int
    maHoanTien: int | None
    claimToken: str
    leaseGeneration: int
    soLanThu: int
    soLanThuToiDa: int


@dataclass(frozen=True)
class GatewayQueryOutcome:
    """Normalized outcome of a read-only QueryDR call against the payment gateway."""

    status: str  # "CAPTURED" | "FAILED" | "CANCELLED" | "PENDING" | "UNKNOWN" | "REFUNDED" | "NOT_REFUNDED"
    gateway_txn_id: str | None = None
    amount_vnd: Decimal | None = None
    response_code: str = "00"
    note: str = ""


class GatewayQueryClient(Protocol):
    def query_payment(self, payment_snapshot: dict) -> GatewayQueryOutcome: ...
    def query_refund(self, refund_snapshot: dict) -> GatewayQueryOutcome: ...


class FailClosedGatewayQueryClient:
    """Default production-safe client: fails closed unless live QueryDR is explicitly configured."""

    def query_payment(self, payment_snapshot: dict) -> GatewayQueryOutcome:
        settings = get_settings()
        if not settings.payment_auto_gateway_query_enabled:
            return GatewayQueryOutcome(
                status="UNKNOWN",
                response_code="DISABLED",
                note="PAYMENT_AUTO_GATEWAY_QUERY_ENABLED=False (fail-closed).",
            )
        return GatewayQueryOutcome(
            status="UNKNOWN",
            response_code="UNCONFIGURED",
            note="VNPay live QueryDR transport is not configured on this environment (fail-closed).",
        )

    def query_refund(self, refund_snapshot: dict) -> GatewayQueryOutcome:
        return self.query_payment(refund_snapshot)


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def sweep_stale_payment_tasks(
    db: Session,
    *,
    pending_age_minutes: int = 5,
    now: datetime | None = None,
) -> int:
    """Discover stale PENDING payments, CAPTURED_UNAPPLIED payments, and UNKNOWN refunds."""
    ts = now or _utc_now()
    enqueued = 0

    # 1. Stale PENDING payments past age threshold (NEVER mark FAILED without gateway check!)
    cutoff = ts - timedelta(minutes=pending_age_minutes)
    stale_pending = list(
        db.scalars(
            select(ThanhToan).where(
                ThanhToan.trangThai == "PENDING",
                ThanhToan.ngayTao <= cutoff,
            )
        ).all()
    )
    for p in stale_pending:
        financial_event_service.enqueue_reconciliation_task(
            db,
            task_type="QUERY_PENDING_PAYMENT",
            order_id=p.maDonHang,
            payment_id=p.maThanhToan,
            idempotency_key=f"recon:pending:{p.maThanhToan}",
            now=ts,
        )
        enqueued += 1

    # 2. CAPTURED_UNAPPLIED payments awaiting auto-restore or ADMIN escalation
    unapplied = list(
        db.scalars(
            select(ThanhToan).where(ThanhToan.trangThai == "CAPTURED_UNAPPLIED")
        ).all()
    )
    for p in unapplied:
        financial_event_service.enqueue_reconciliation_task(
            db,
            task_type="RETRY_CAPTURED_UNAPPLIED",
            order_id=p.maDonHang,
            payment_id=p.maThanhToan,
            idempotency_key=f"recon:cap_unapplied:{p.maThanhToan}",
            now=ts,
        )
        enqueued += 1

    # 3. Refunds stuck in REFUND_PENDING / UNKNOWN (NEVER blind-retry refund; QueryDR only!)
    unk_refunds = list(
        db.scalars(
            select(HoanTienNgoaiLe).where(
                HoanTienNgoaiLe.trangThai.in_(("REFUND_PENDING", "UNKNOWN"))
            )
        ).all()
    )
    for r in unk_refunds:
        financial_event_service.enqueue_reconciliation_task(
            db,
            task_type="QUERY_UNKNOWN_REFUND",
            order_id=r.maDonHang,
            payment_id=r.maThanhToan,
            refund_id=r.maHoanTien,
            idempotency_key=f"recon:ref_unk_sweep:{r.maHoanTien}",
            now=ts,
        )
        enqueued += 1

    db.commit()
    return enqueued


class PaymentReconciliationWorker:
    """Durable PostgreSQL reconciliation worker with lease expiration & fencing tokens."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        worker_id: str,
        lease_seconds: int = 60,
        gateway_client: GatewayQueryClient | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.worker_id = worker_id
        self.lease_seconds = max(5, int(lease_seconds))
        self.gateway_client: GatewayQueryClient = gateway_client or FailClosedGatewayQueryClient()

    def claim_next_task(self, *, now: datetime | None = None) -> ClaimedReconTask | None:
        """Phase 1 (Short TX): Claim 1 due or stale-leased task with FOR UPDATE SKIP LOCKED."""
        ts = now or _utc_now()
        with self.session_factory() as db:
            stmt = (
                select(TacVuDoiSoatThanhToan)
                .where(
                    or_(
                        (
                            TacVuDoiSoatThanhToan.trangThai.in_(("PENDING", "RETRY_WAIT"))
                            & (TacVuDoiSoatThanhToan.thoiDiemChayTiepTheo <= ts)
                        ),
                        (
                            (TacVuDoiSoatThanhToan.trangThai == "PROCESSING")
                            & (TacVuDoiSoatThanhToan.hanLease <= ts)
                        ),
                    )
                )
                .order_by(
                    TacVuDoiSoatThanhToan.thoiDiemChayTiepTheo.asc(),
                    TacVuDoiSoatThanhToan.maTacVu.asc(),
                )
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            task = db.scalars(stmt).first()
            if task is None:
                return None

            token = uuid.uuid4().hex
            task.trangThai = "PROCESSING"
            task.maWorker = self.worker_id
            task.claimToken = token
            task.leaseGeneration = int(task.leaseGeneration) + 1
            task.hanLease = ts + timedelta(seconds=self.lease_seconds)
            task.soLanThu = int(task.soLanThu) + 1
            task.ngayCapNhat = ts
            db.commit()
            return ClaimedReconTask(
                maTacVu=int(task.maTacVu),
                loaiTacVu=str(task.loaiTacVu),
                maDonHang=int(task.maDonHang),
                maThanhToan=int(task.maThanhToan),
                maHoanTien=int(task.maHoanTien) if task.maHoanTien is not None else None,
                claimToken=token,
                leaseGeneration=int(task.leaseGeneration),
                soLanThu=int(task.soLanThu),
                soLanThuToiDa=int(task.soLanThuToiDa),
            )

    def _load_snapshots_unlocked(self, claimed: ClaimedReconTask) -> tuple[dict | None, dict | None]:
        with self.session_factory() as db:
            p = db.get(ThanhToan, claimed.maThanhToan)
            pay_snap = (
                {
                    "maThanhToan": p.maThanhToan,
                    "maDonHang": p.maDonHang,
                    "congThanhToan": p.congThanhToan,
                    "maGiaoDichNoiBo": p.maGiaoDichNoiBo,
                    "maGiaoDichCong": p.maGiaoDichCong,
                    "soTien": Decimal(p.soTien),
                    "trangThai": p.trangThai,
                    "ngayTao": p.ngayTao,
                }
                if p is not None
                else None
            )
            ref_snap = None
            if claimed.maHoanTien is not None:
                r = db.get(HoanTienNgoaiLe, claimed.maHoanTien)
                if r is not None:
                    ref_snap = {
                        "maHoanTien": r.maHoanTien,
                        "maSoHoanTien": r.maSoHoanTien,
                        "maThanhToan": r.maThanhToan,
                        "soTienHoan": Decimal(r.soTienHoan),
                        "trangThai": r.trangThai,
                    }
            return pay_snap, ref_snap

    def apply_fenced_outcome(
        self,
        claimed: ClaimedReconTask,
        outcome: GatewayQueryOutcome,
        *,
        now: datetime | None = None,
        _before_commit_hook=None,
    ) -> str:
        """Phase 3 (Fenced TX): Only commit if (claimToken, leaseGeneration) still matches!"""
        ts = now or _utc_now()
        with self.session_factory() as db:
            task = db.scalars(
                select(TacVuDoiSoatThanhToan)
                .where(
                    TacVuDoiSoatThanhToan.maTacVu == claimed.maTacVu,
                    TacVuDoiSoatThanhToan.claimToken == claimed.claimToken,
                    TacVuDoiSoatThanhToan.leaseGeneration == claimed.leaseGeneration,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            ).first()
            if task is None:
                # Fencing token rejected: another worker already reclaimed stale lease!
                return "STALE_LEASE_IGNORED"

            payment = db.get(ThanhToan, claimed.maThanhToan)
            order = commerce_repository.get_order_by_id(db, claimed.maDonHang, for_update=True)
            if payment is None or order is None:
                task.trangThai = "ESCALATED_ADMIN"
                task.loiGanNhat = "Missing order or payment row."
                task.ngayCapNhat = ts
                db.commit()
                return "ESCALATED_ADMIN"

            if claimed.loaiTacVu in {"QUERY_PENDING_PAYMENT", "VERIFY_EXPIRED_ORDER"}:
                if outcome.status == "CAPTURED":
                    amt = outcome.amount_vnd if outcome.amount_vnd is not None else Decimal(payment.soTien)
                    verified = CallbackVerificationResult(
                        gateway=payment.congThanhToan,
                        is_simulated=(payment.congThanhToan == "MOCK_SANDBOX"),
                        internal_txn_ref=payment.maGiaoDichNoiBo,
                        gateway_txn_id=outcome.gateway_txn_id or f"QDR-{payment.maThanhToan}",
                        order_id=order.maDonHang,
                        amount=amt,
                        currency="VND",
                        outcome="PAID",
                        response_code=outcome.response_code,
                        signature_valid=True,
                        safe_payload={"source": "QUERYDR_RECONCILE", "note": outcome.note},
                    )
                    if _before_commit_hook is not None:
                        _before_commit_hook()
                    order_payment_service._apply_verified_callback(
                        db, verified, expected_gateway=payment.congThanhToan
                    )
                    # Re-lock task after _apply_verified_callback committed
                    t2 = db.get(TacVuDoiSoatThanhToan, claimed.maTacVu)
                    if t2 is not None and t2.claimToken == claimed.claimToken and t2.leaseGeneration == claimed.leaseGeneration:
                        t2.trangThai = "DONE"
                        t2.ngayCapNhat = ts
                        db.commit()
                    return "DONE_CAPTURED"
                if outcome.status in {"FAILED", "CANCELLED"}:
                    if not payment.daThuTien and payment.trangThai == "PENDING":
                        payment.trangThai = outcome.status
                        payment.maPhanHoiCong = outcome.response_code
                        payment.ngayCapNhat = ts
                    task.trangThai = "DONE"
                    task.ngayCapNhat = ts
                    if _before_commit_hook is not None:
                        _before_commit_hook()
                    db.commit()
                    return f"DONE_{outcome.status}"
                # PENDING or UNKNOWN -> retry with backoff, NEVER falsely mark FAILED!
                return self._schedule_retry_or_escalate(db, task, outcome.note or outcome.status, ts)

            if claimed.loaiTacVu == "RETRY_CAPTURED_UNAPPLIED":
                settings = get_settings()
                if (
                    settings.payment_auto_restore_enabled
                    and payment.trangThai == "CAPTURED_UNAPPLIED"
                    and payment.daThuTien
                    and order.trangThai != "PAID"
                ):
                    buyer = db.get(NguoiDung, order.maNguoiDung)
                    course_ids = sorted({int(i.maKhoaHoc) for i in order.chiTiets or []})
                    courses = commerce_repository.lock_courses_ordered(db, course_ids)
                    all_ok = (
                        buyer is not None
                        and (buyer.trangThai or "ACTIVE").upper() == "ACTIVE"
                        and len(courses) == len(course_ids)
                        and all(c.trangThaiDuyet == "APPROVED" and c.trangThaiHienThi == "VISIBLE" for c in courses)
                    )
                    if all_ok:
                        existing_enr = [
                            commerce_repository.get_enrollment_for_update(db, order.maNguoiDung, cid)
                            for cid in course_ids
                        ]
                        if not any(e is not None and e.trangThaiQuyenHoc == "ACTIVE" for e in existing_enr):
                            payment.trangThai = "PAID"
                            payment.ngayThanhToan = payment.ngayThanhToan or ts
                            order.trangThai = "PAID"
                            order.ngayThanhToan = order.ngayThanhToan or ts
                            for cid, enr in zip(course_ids, existing_enr, strict=True):
                                if enr is not None and enr.trangThaiQuyenHoc == "REVOKED":
                                    enr.trangThaiQuyenHoc = "ACTIVE"
                                    enr.maDonHang = order.maDonHang
                                    enr.nguonCapQuyen = "PURCHASE"
                                else:
                                    db.add(
                                        DangKyKhoaHoc(
                                            maNguoiDung=order.maNguoiDung,
                                            maKhoaHoc=cid,
                                            ngayDangKy=ts,
                                            tienDo=Decimal("0"),
                                            maDonHang=order.maDonHang,
                                            nguonCapQuyen="PURCHASE",
                                            trangThaiQuyenHoc="ACTIVE",
                                        )
                                    )
                            task.trangThai = "DONE"
                            task.ngayCapNhat = ts
                            financial_event_service.record_payment_event(
                                db,
                                order_id=order.maDonHang,
                                payment_id=payment.maThanhToan,
                                event_type="AUTO_RECONCILE_ACTIVATED",
                                source="RECONCILIATION_WORKER",
                                safe_data={"workerId": self.worker_id},
                                idempotency_key=f"auto_act:{order.maDonHang}:{payment.maThanhToan}",
                                now=ts,
                            )
                            if _before_commit_hook is not None:
                                _before_commit_hook()
                            db.commit()
                            return "DONE_AUTO_RESTORED"

                task.trangThai = "ESCALATED_ADMIN"
                task.loiGanNhat = "Yêu cầu ADMIN đối soát (thu trùng / khóa ẩn / auto-restore đang tắt)."
                task.ngayCapNhat = ts
                financial_event_service.record_payment_event(
                    db,
                    order_id=order.maDonHang,
                    payment_id=payment.maThanhToan,
                    event_type="RECONCILE_ESCALATED_ADMIN",
                    source="RECONCILIATION_WORKER",
                    safe_data={"workerId": self.worker_id, "maTacVu": claimed.maTacVu},
                    now=ts,
                )
                if _before_commit_hook is not None:
                    _before_commit_hook()
                db.commit()
                return "ESCALATED_ADMIN"

            if claimed.loaiTacVu == "QUERY_UNKNOWN_REFUND":
                refund_row = db.get(HoanTienNgoaiLe, claimed.maHoanTien) if claimed.maHoanTien else None
                if refund_row is None or refund_row.trangThai not in {"REFUND_PENDING", "UNKNOWN"}:
                    task.trangThai = "DONE"
                    task.ngayCapNhat = ts
                    db.commit()
                    return "DONE_ALREADY_RESOLVED"

                if outcome.status == "REFUNDED":
                    rec = commerce_admin_service._refund_record(payment) or {
                        "refundId": refund_row.maSoHoanTien,
                        "idempotencyKey": refund_row.khoaChongTrung,
                        "maDonHang": order.maDonHang,
                        "maSoDonHang": order.maSoDonHang,
                        "maThanhToan": payment.maThanhToan,
                        "congThanhToan": payment.congThanhToan,
                        "soTienDaThu": str(refund_row.soTienDaThu),
                        "soTienHoan": str(refund_row.soTienHoan),
                        "phamViHoan": refund_row.phamViHoan,
                        "loaiSuCo": refund_row.loaiSuCo,
                        "lyDo": refund_row.lyDo,
                        "trangThai": refund_row.trangThai,
                        "lichSuTrangThai": list(refund_row.lichSuTrangThai or []),
                    }
                    commerce_admin_service._finalize_confirmed_refund(
                        db,
                        order=order,
                        payment=payment,
                        rec=rec,
                        gateway_refund_txn_id=outcome.gateway_txn_id or f"QDR-REF-{refund_row.maHoanTien}",
                        actor_admin_id=refund_row.maNguoiXuLy or 0,
                        evidence_note=outcome.note or "Xác nhận hoàn tiền qua Durable Reconciliation Worker (QueryDR).",
                        now=ts,
                    )
                    task.trangThai = "DONE"
                    task.ngayCapNhat = ts
                    if _before_commit_hook is not None:
                        _before_commit_hook()
                    db.commit()
                    return "DONE_REFUND_CONFIRMED"

                if outcome.status == "NOT_REFUNDED":
                    refund_row.trangThai = "REFUND_FAILED"
                    refund_row.ngayCapNhat = ts
                    latest_attempt = db.scalars(
                        select(LanThuHoanTien)
                        .where(LanThuHoanTien.maHoanTien == refund_row.maHoanTien)
                        .order_by(LanThuHoanTien.thuTuLanThu.desc())
                    ).first()
                    if latest_attempt is not None and latest_attempt.trangThai in {"SENT", "UNKNOWN"}:
                        latest_attempt.trangThai = "FAILED"
                        latest_attempt.ngayPhanHoi = ts
                    meta = commerce_admin_service._safe_meta(payment)
                    if isinstance(meta.get("exceptionRefund"), dict):
                        meta["exceptionRefund"]["trangThai"] = "REFUND_FAILED"
                        payment.duLieuPhanHoiAnToan = meta
                    task.trangThai = "ESCALATED_ADMIN"
                    task.loiGanNhat = "QueryDR xác nhận cổng chưa hoàn tiền; chuyển ADMIN quyết định thử lại."
                    task.ngayCapNhat = ts
                    if _before_commit_hook is not None:
                        _before_commit_hook()
                    db.commit()
                    return "ESCALATED_REFUND_FAILED"

                # Still UNKNOWN -> backoff retry, NEVER send a new Refund request!
                return self._schedule_retry_or_escalate(db, task, outcome.note or "UNKNOWN_REFUND", ts)

            task.trangThai = "ESCALATED_ADMIN"
            task.ngayCapNhat = ts
            db.commit()
            return "ESCALATED_ADMIN"

    def _schedule_retry_or_escalate(
        self,
        db: Session,
        task: TacVuDoiSoatThanhToan,
        reason: str,
        ts: datetime,
    ) -> str:
        task.loiGanNhat = reason[:500]
        task.ngayCapNhat = ts
        if int(task.soLanThu) >= int(task.soLanThuToiDa):
            task.trangThai = "ESCALATED_ADMIN"
            db.commit()
            return "ESCALATED_ADMIN"
        idx = min(max(0, int(task.soLanThu) - 1), len(BACKOFF_SECONDS) - 1)
        task.trangThai = "RETRY_WAIT"
        task.thoiDiemChayTiepTheo = ts + timedelta(seconds=BACKOFF_SECONDS[idx])
        task.hanLease = None
        db.commit()
        return "RETRY_WAIT"

    def run_once(self, *, now: datetime | None = None, _before_commit_hook=None) -> str | None:
        """Execute 1 full 3-phase reconciliation cycle (Claim -> Unlocked Gateway Call -> Fenced Apply)."""
        claimed = self.claim_next_task(now=now)
        if claimed is None:
            return None

        # Phase 2: Unlocked read + gateway call (ZERO DB locks held!)
        pay_snap, ref_snap = self._load_snapshots_unlocked(claimed)
        if claimed.loaiTacVu in {"QUERY_PENDING_PAYMENT", "VERIFY_EXPIRED_ORDER"}:
            outcome = (
                self.gateway_client.query_payment(pay_snap)
                if pay_snap is not None
                else GatewayQueryOutcome(status="UNKNOWN", note="Missing payment snapshot")
            )
        elif claimed.loaiTacVu == "QUERY_UNKNOWN_REFUND":
            outcome = (
                self.gateway_client.query_refund(ref_snap or {})
                if ref_snap is not None
                else GatewayQueryOutcome(status="UNKNOWN", note="Missing refund snapshot")
            )
        else:
            outcome = GatewayQueryOutcome(status="CAPTURED", note="Local CAPTURED_UNAPPLIED evaluation")

        # Phase 3: Fenced commit
        return self.apply_fenced_outcome(
            claimed, outcome, now=now, _before_commit_hook=_before_commit_hook
        )
