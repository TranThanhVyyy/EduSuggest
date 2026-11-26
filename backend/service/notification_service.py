"""Minimal idempotent In-app Notification Service for GĐ3.3 Assignment Lifecycle.

Enforces recipient-scoped idempotency key convention:
  {event_key}:TO:{user_id}
so multiple recipients (EXPERT, ADMINs, PROVIDER) each receive their own notification
without colliding on ThongBao.khoaChongTrung UNIQUE constraint.
Never commits on its own — participates atomically in the caller's transaction.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from models import NguoiDung, ThongBao, VaiTro
from service.workflow_service import WorkflowNotFoundError


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def build_notification_key(event_key: str, recipient_user_id: int) -> str:
    key = f"{event_key}:TO:{recipient_user_id}"
    if len(key) > 150:
        raise ValueError(f"Notification idempotency key exceeds 150 chars: {len(key)}")
    return key


def create_notification_idempotent(
    db: Session,
    *,
    recipient_user_id: int,
    notification_type: str,
    title: str,
    body: str,
    event_key: str,
    payload: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> bool:
    """Insert ThongBao idempotently inside caller's transaction (ON CONFLICT DO NOTHING).

    Returns True if a new row was inserted, False if duplicate was safely ignored.
    """
    idem_key = build_notification_key(event_key, recipient_user_id)
    ts = now or _utc_now()
    stmt = (
        pg_insert(ThongBao)
        .values(
            maNguoiNhan=recipient_user_id,
            loaiThongBao=notification_type,
            tieuDe=title,
            noiDung=body,
            duLieuLienKet=payload,
            daDoc=False,
            khoaChongTrung=idem_key,
            ngayTao=ts,
        )
        .on_conflict_do_nothing(index_elements=["khoaChongTrung"])
        .returning(ThongBao.maThongBao)
    )
    inserted_id = db.execute(stmt).scalar_one_or_none()
    return inserted_id is not None


def notify_active_admins(
    db: Session,
    *,
    notification_type: str,
    title: str,
    body: str,
    event_key: str,
    payload: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> int:
    """Send recipient-scoped idempotent notifications to all ACTIVE ADMIN accounts."""
    admin_ids = list(
        db.scalars(
            select(NguoiDung.maNguoiDung)
            .join(VaiTro, VaiTro.maVaiTro == NguoiDung.maVaiTro)
            .where(VaiTro.tenVaiTro == "ADMIN", NguoiDung.trangThai == "ACTIVE")
            .order_by(NguoiDung.maNguoiDung.asc())
        ).all()
    )
    created = 0
    for admin_uid in admin_ids:
        if create_notification_idempotent(
            db,
            recipient_user_id=int(admin_uid),
            notification_type=notification_type,
            title=title,
            body=body,
            event_key=event_key,
            payload=payload,
            now=now,
        ):
            created += 1
    return created


def list_user_notifications(
    db: Session,
    *,
    user_id: int,
    is_read: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List authenticated user's own notifications with pagination & unread count."""
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)

    base_cond = [ThongBao.maNguoiNhan == user_id]
    filtered_cond = list(base_cond)
    if is_read is not None:
        filtered_cond.append(ThongBao.daDoc == is_read)

    total = int(
        db.scalar(select(func.count(ThongBao.maThongBao)).where(*filtered_cond)) or 0
    )
    unread_count = int(
        db.scalar(
            select(func.count(ThongBao.maThongBao)).where(
                ThongBao.maNguoiNhan == user_id,
                ThongBao.daDoc.is_(False),
            )
        )
        or 0
    )
    items = list(
        db.scalars(
            select(ThongBao)
            .where(*filtered_cond)
            .order_by(ThongBao.ngayTao.desc(), ThongBao.maThongBao.desc())
            .offset(safe_offset)
            .limit(safe_limit)
        ).all()
    )
    return {
        "items": items,
        "total": total,
        "unreadCount": unread_count,
        "limit": safe_limit,
        "offset": safe_offset,
    }


def count_unread_notifications(db: Session, *, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(ThongBao.maThongBao)).where(
                ThongBao.maNguoiNhan == user_id,
                ThongBao.daDoc.is_(False),
            )
        )
        or 0
    )


def mark_notification_read(
    db: Session,
    *,
    user_id: int,
    notification_id: int,
    now: datetime | None = None,
) -> ThongBao:
    """Mark one notification as read; strictly enforces ownership (maNguoiNhan == user_id)."""
    ts = now or _utc_now()
    notif = db.scalars(
        select(ThongBao)
        .where(
            ThongBao.maThongBao == notification_id,
            ThongBao.maNguoiNhan == user_id,
        )
        .with_for_update()
    ).first()
    if notif is None:
        raise WorkflowNotFoundError("Không tìm thấy thông báo.")
    if not notif.daDoc:
        notif.daDoc = True
        notif.ngayDoc = ts
        db.commit()
        db.refresh(notif)
    return notif


def mark_all_notifications_read(
    db: Session,
    *,
    user_id: int,
    now: datetime | None = None,
) -> int:
    """Mark all unread notifications belonging ONLY to user_id as read."""
    ts = now or _utc_now()
    res = db.execute(
        update(ThongBao)
        .where(ThongBao.maNguoiNhan == user_id, ThongBao.daDoc.is_(False))
        .values(daDoc=True, ngayDoc=ts)
    )
    db.commit()
    return int(res.rowcount or 0)
