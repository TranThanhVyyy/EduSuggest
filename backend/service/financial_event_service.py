"""GĐ4.7A.2 Append-Only Financial Event Log & Durable Reconciliation Queue Helpers.

- Never stores secrets, OTP, CVV, card numbers, or passwords in SuKienThanhToan.
- Uses PostgreSQL ON CONFLICT DO NOTHING on khoaChongTrung for idempotent recording.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from models import SuKienThanhToan, TacVuDoiSoatThanhToan

_SENSITIVE_KEY_FRAGMENTS = (
    "secret",
    "password",
    "matkhau",
    "otp",
    "cvv",
    "cvc",
    "cardnumber",
    "sothe",
    "securehash",
    "token",
)


def _sanitize_event_payload(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for k, v in data.items():
        lk = str(k).lower()
        if any(frag in lk for frag in _SENSITIVE_KEY_FRAGMENTS):
            continue
        if isinstance(v, dict):
            cleaned[str(k)] = _sanitize_event_payload(v)
        elif isinstance(v, list):
            cleaned[str(k)] = [
                _sanitize_event_payload(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            cleaned[str(k)] = v
    return cleaned


def record_payment_event(
    db: Session,
    *,
    order_id: int,
    event_type: str,
    source: str,
    safe_data: dict[str, Any] | None = None,
    payment_id: int | None = None,
    refund_id: int | None = None,
    idempotency_key: str | None = None,
    now: datetime | None = None,
) -> None:
    """Append an immutable financial event into SuKienThanhToan (idempotent if key provided)."""
    ts = now or datetime.now(UTC).replace(tzinfo=None)
    stmt = pg_insert(SuKienThanhToan).values(
        maDonHang=int(order_id),
        maThanhToan=int(payment_id) if payment_id is not None else None,
        maHoanTien=int(refund_id) if refund_id is not None else None,
        loaiSuKien=str(event_type)[:50],
        nguonSuKien=str(source)[:40],
        khoaChongTrung=idempotency_key[:128] if idempotency_key else None,
        duLieuAnToan=_sanitize_event_payload(safe_data),
        ngayTao=ts,
    )
    if idempotency_key:
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["khoaChongTrung"],
            index_where=SuKienThanhToan.khoaChongTrung.is_not(None),
        )
    db.execute(stmt)


def enqueue_reconciliation_task(
    db: Session,
    *,
    task_type: str,
    order_id: int,
    payment_id: int,
    idempotency_key: str,
    refund_id: int | None = None,
    run_at: datetime | None = None,
    max_retries: int = 6,
    now: datetime | None = None,
) -> None:
    """Idempotently enqueue a durable reconciliation task into TacVuDoiSoatThanhToan."""
    ts = now or datetime.now(UTC).replace(tzinfo=None)
    stmt = (
        pg_insert(TacVuDoiSoatThanhToan)
        .values(
            loaiTacVu=task_type,
            maDonHang=int(order_id),
            maThanhToan=int(payment_id),
            maHoanTien=int(refund_id) if refund_id is not None else None,
            khoaChongTrung=idempotency_key[:128],
            trangThai="PENDING",
            soLanThu=0,
            soLanThuToiDa=max(1, int(max_retries)),
            thoiDiemChayTiepTheo=run_at or ts,
            leaseGeneration=0,
            ngayTao=ts,
            ngayCapNhat=ts,
        )
        .on_conflict_do_nothing(index_elements=["khoaChongTrung"])
    )
    db.execute(stmt)
