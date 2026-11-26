"""Database repository for GĐ4.2 Wishlist, Shopping Cart, and Buy Now preparation."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from models import (
    ChiTietDonHang,
    ChiTietGioHang,
    DangKyKhoaHoc,
    DonHang,
    GioHang,
    KhoaHoc,
    NhaCungCapKhoaHoc,
    ThanhToan,
    YeuThich,
)


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_course_with_relations(
    db: Session, course_id: int, *, for_update: bool = False
) -> KhoaHoc | None:
    statement = (
        select(KhoaHoc)
        .options(
            joinedload(KhoaHoc.danhMuc),
            joinedload(KhoaHoc.nhaCungCap).joinedload(NhaCungCapKhoaHoc.nguoiDung),
        )
        .where(KhoaHoc.maKhoaHoc == course_id)
    )
    if for_update:
        statement = statement.with_for_update(of=KhoaHoc)
    return db.scalars(statement).unique().first()


def list_user_enrollments_map(
    db: Session, user_id: int, course_ids: set[int]
) -> dict[int, DangKyKhoaHoc]:
    if not course_ids:
        return {}
    rows = db.scalars(
        select(DangKyKhoaHoc).where(
            DangKyKhoaHoc.maNguoiDung == user_id,
            DangKyKhoaHoc.maKhoaHoc.in_(course_ids),
        )
    ).all()
    return {
        int(row.maKhoaHoc): row for row in rows if row.maKhoaHoc is not None
    }


def get_user_enrollment_any_status(
    db: Session, user_id: int, course_id: int
) -> DangKyKhoaHoc | None:
    return db.scalars(
        select(DangKyKhoaHoc).where(
            DangKyKhoaHoc.maNguoiDung == user_id,
            DangKyKhoaHoc.maKhoaHoc == course_id,
        )
    ).first()


# ---------------------------------------------------------------------------
# Wishlist (YeuThich)
# ---------------------------------------------------------------------------
def get_wishlist_item(
    db: Session, user_id: int, course_id: int, *, for_update: bool = False
) -> YeuThich | None:
    statement = select(YeuThich).where(
        YeuThich.maNguoiDung == user_id,
        YeuThich.maKhoaHoc == course_id,
    )
    if for_update:
        statement = statement.with_for_update().execution_options(
            populate_existing=True
        )
    return db.scalars(statement).first()


def count_wishlist(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(YeuThich.maYeuThich)).where(
                YeuThich.maNguoiDung == user_id
            )
        )
        or 0
    )


def list_wishlist_items(
    db: Session, user_id: int, *, offset: int, limit: int
) -> list[YeuThich]:
    statement = (
        select(YeuThich)
        .options(
            joinedload(YeuThich.khoaHoc).joinedload(KhoaHoc.danhMuc),
            joinedload(YeuThich.khoaHoc)
            .joinedload(KhoaHoc.nhaCungCap)
            .joinedload(NhaCungCapKhoaHoc.nguoiDung),
        )
        .where(YeuThich.maNguoiDung == user_id)
        .order_by(YeuThich.ngayTao.desc(), YeuThich.maYeuThich.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def insert_wishlist_idempotent(db: Session, user_id: int, course_id: int) -> bool:
    """Insert into YeuThich with ON CONFLICT DO NOTHING. Returns True if newly inserted."""
    stmt = (
        pg_insert(YeuThich)
        .values(
            maNguoiDung=user_id,
            maKhoaHoc=course_id,
            ngayTao=_utc_now(),
        )
        .on_conflict_do_nothing(constraint="uq_YeuThich_user_course")
        .returning(YeuThich.maYeuThich)
    )
    inserted_id = db.scalar(stmt)
    return inserted_id is not None


def delete_wishlist_item(db: Session, user_id: int, course_id: int) -> bool:
    result = db.execute(
        delete(YeuThich).where(
            YeuThich.maNguoiDung == user_id,
            YeuThich.maKhoaHoc == course_id,
        )
    )
    return (result.rowcount or 0) > 0


# ---------------------------------------------------------------------------
# Shopping Cart (GioHang, ChiTietGioHang)
# ---------------------------------------------------------------------------
def get_cart_by_user(
    db: Session, user_id: int, *, for_update: bool = False
) -> GioHang | None:
    statement = select(GioHang).where(GioHang.maNguoiDung == user_id)
    if for_update:
        statement = statement.with_for_update().execution_options(
            populate_existing=True
        )
    return db.scalars(statement).first()


def get_or_create_cart(db: Session, user_id: int) -> GioHang:
    """Concurrency-safe cart creation (1 cart per USER via uq_GioHang_maNguoiDung)."""
    now = _utc_now()
    db.execute(
        pg_insert(GioHang)
        .values(maNguoiDung=user_id, ngayTao=now, ngayCapNhat=now)
        .on_conflict_do_nothing(constraint="uq_GioHang_maNguoiDung")
    )
    cart = get_cart_by_user(db, user_id)
    assert cart is not None
    return cart


def list_cart_items(db: Session, cart_id: int) -> list[ChiTietGioHang]:
    statement = (
        select(ChiTietGioHang)
        .options(
            joinedload(ChiTietGioHang.khoaHoc).joinedload(KhoaHoc.danhMuc),
            joinedload(ChiTietGioHang.khoaHoc)
            .joinedload(KhoaHoc.nhaCungCap)
            .joinedload(NhaCungCapKhoaHoc.nguoiDung),
        )
        .where(ChiTietGioHang.maGioHang == cart_id)
        .order_by(ChiTietGioHang.ngayTao.desc(), ChiTietGioHang.maChiTietGioHang.desc())
    )
    return list(db.scalars(statement).unique().all())


def list_cart_course_ids(db: Session, user_id: int) -> set[int]:
    cart = get_cart_by_user(db, user_id)
    if cart is None:
        return set()
    rows = db.scalars(
        select(ChiTietGioHang.maKhoaHoc).where(
            ChiTietGioHang.maGioHang == cart.maGioHang
        )
    ).all()
    return {int(cid) for cid in rows if cid is not None}


def insert_cart_item_idempotent(
    db: Session, cart_id: int, course_id: int, price_snapshot: Decimal
) -> bool:
    """Insert into ChiTietGioHang with ON CONFLICT DO NOTHING. Returns True if newly added."""
    now = _utc_now()
    stmt = (
        pg_insert(ChiTietGioHang)
        .values(
            maGioHang=cart_id,
            maKhoaHoc=course_id,
            giaLucThem=price_snapshot,
            ngayTao=now,
        )
        .on_conflict_do_nothing(constraint="uq_ChiTietGioHang_cart_course")
        .returning(ChiTietGioHang.maChiTietGioHang)
    )
    inserted_id = db.scalar(stmt)
    if inserted_id is not None:
        cart = db.get(GioHang, cart_id)
        if cart is not None:
            cart.ngayCapNhat = now
    return inserted_id is not None


def delete_cart_item(db: Session, cart_id: int, course_id: int) -> bool:
    result = db.execute(
        delete(ChiTietGioHang).where(
            ChiTietGioHang.maGioHang == cart_id,
            ChiTietGioHang.maKhoaHoc == course_id,
        )
    )
    deleted = (result.rowcount or 0) > 0
    if deleted:
        cart = db.get(GioHang, cart_id)
        if cart is not None:
            cart.ngayCapNhat = _utc_now()
    return deleted


def clear_cart_items(db: Session, cart_id: int) -> int:
    result = db.execute(
        delete(ChiTietGioHang).where(ChiTietGioHang.maGioHang == cart_id)
    )
    removed = int(result.rowcount or 0)
    if removed:
        cart = db.get(GioHang, cart_id)
        if cart is not None:
            cart.ngayCapNhat = _utc_now()
    return removed


# ---------------------------------------------------------------------------
# GĐ4.3 Orders (DonHang, ChiTietDonHang) & Payments (ThanhToan)
# ---------------------------------------------------------------------------
def lock_courses_ordered(db: Session, course_ids: list[int]) -> list[KhoaHoc]:
    """Lock KhoaHoc rows in strict ascending maKhoaHoc order to prevent deadlocks."""
    unique_sorted = sorted({int(cid) for cid in course_ids})
    if not unique_sorted:
        return []
    statement = (
        select(KhoaHoc)
        .options(
            joinedload(KhoaHoc.danhMuc),
            joinedload(KhoaHoc.nhaCungCap).joinedload(NhaCungCapKhoaHoc.nguoiDung),
        )
        .where(KhoaHoc.maKhoaHoc.in_(unique_sorted))
        .order_by(KhoaHoc.maKhoaHoc.asc())
        .with_for_update(of=KhoaHoc)
    )
    return list(db.scalars(statement).unique().all())


def get_order_by_id(
    db: Session, order_id: int, *, for_update: bool = False
) -> DonHang | None:
    statement = (
        select(DonHang)
        .options(
            joinedload(DonHang.chiTiets),
            joinedload(DonHang.thanhToans),
        )
        .where(DonHang.maDonHang == order_id)
    )
    if for_update:
        statement = statement.with_for_update(of=DonHang).execution_options(
            populate_existing=True
        )
    return db.scalars(statement).unique().first()


def get_order_by_idempotency_key(db: Session, idem_key: str) -> DonHang | None:
    statement = (
        select(DonHang)
        .options(
            joinedload(DonHang.chiTiets),
            joinedload(DonHang.thanhToans),
        )
        .where(DonHang.khoaChongTrung == idem_key)
    )
    return db.scalars(statement).unique().first()


def count_user_orders(
    db: Session, user_id: int, *, status_filter: str | None = None
) -> int:
    statement = select(func.count(DonHang.maDonHang)).where(
        DonHang.maNguoiDung == user_id
    )
    if status_filter:
        statement = statement.where(DonHang.trangThai == status_filter)
    return int(db.scalar(statement) or 0)


def list_user_orders(
    db: Session,
    user_id: int,
    *,
    offset: int,
    limit: int,
    status_filter: str | None = None,
) -> list[DonHang]:
    statement = (
        select(DonHang)
        .options(
            joinedload(DonHang.chiTiets),
            joinedload(DonHang.thanhToans),
        )
        .where(DonHang.maNguoiDung == user_id)
    )
    if status_filter:
        statement = statement.where(DonHang.trangThai == status_filter)
    statement = (
        statement.order_by(DonHang.ngayTao.desc(), DonHang.maDonHang.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())


def get_payment_by_idempotency_key(db: Session, idem_key: str) -> ThanhToan | None:
    return db.scalars(
        select(ThanhToan).where(ThanhToan.khoaChongTrung == idem_key)
    ).first()


def get_payment_by_internal_ref(
    db: Session, internal_txn_ref: str, *, for_update: bool = False
) -> ThanhToan | None:
    statement = select(ThanhToan).where(
        ThanhToan.maGiaoDichNoiBo == internal_txn_ref
    )
    if for_update:
        statement = statement.with_for_update().execution_options(
            populate_existing=True
        )
    return db.scalars(statement).first()


def delete_cart_items_by_course_ids(
    db: Session, user_id: int, course_ids: list[int]
) -> int:
    if not course_ids:
        return 0
    cart = get_cart_by_user(db, user_id)
    if cart is None:
        return 0
    result = db.execute(
        delete(ChiTietGioHang).where(
            ChiTietGioHang.maGioHang == cart.maGioHang,
            ChiTietGioHang.maKhoaHoc.in_(course_ids),
        )
    )
    removed = int(result.rowcount or 0)
    if removed:
        cart.ngayCapNhat = _utc_now()
    return removed


def get_enrollment_for_update(
    db: Session, user_id: int, course_id: int
) -> DangKyKhoaHoc | None:
    return db.scalars(
        select(DangKyKhoaHoc)
        .where(
            DangKyKhoaHoc.maNguoiDung == user_id,
            DangKyKhoaHoc.maKhoaHoc == course_id,
        )
        .with_for_update()
    ).first()
