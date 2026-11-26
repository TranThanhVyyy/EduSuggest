"""Business logic for GĐ4.2 Wishlist, Shopping Cart, and Buy Now preparation."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import DangKyKhoaHoc, KhoaHoc, NguoiDung
from repository import commerce_repository
from schemas.commerce import (
    BuyNowValidationResponse,
    CartClearResponse,
    CartCountResponse,
    CartItemResponse,
    CartResponse,
    MoveWishlistToCartResponse,
    WishlistCountResponse,
    WishlistItemResponse,
    WishlistListResponse,
    WishlistStatusResponse,
)

_LOCK_NAMESPACE_COMMERCE = 4201


class CommerceError(Exception):
    pass


class CommerceNotFoundError(CommerceError):
    pass


class CommerceBadRequestError(CommerceError):
    pass


class CommerceConflictError(CommerceError):
    pass


class CommerceForbiddenError(CommerceError):
    pass


@dataclass(frozen=True)
class BuyNowEligibilityResult:
    course: KhoaHoc
    current_price: Decimal
    is_repurchase_after_refund: bool


def _lock_user_course(db: Session, user_id: int, course_id: int) -> None:
    """Serialize per-(user, course) commerce writes inside the current DB transaction.

    Uses PostgreSQL's native (int4, int4) advisory lock keyspace (supports 2.1B x 2.1B IDs
    without the int4 overflow caused by user_id * 1_000_000 + course_id at user_id >= 2148).
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(CAST(:u AS integer), CAST(:c AS integer))"),
        {"u": int(user_id), "c": int(course_id)},
    )


def _assert_active_learner(user: NguoiDung) -> None:
    if (getattr(user, "trangThai", "ACTIVE") or "ACTIVE").upper() != "ACTIVE":
        raise CommerceForbiddenError("Tài khoản của bạn không ở trạng thái hoạt động.")
    role = user.vaiTro.tenVaiTro.upper() if user.vaiTro and user.vaiTro.tenVaiTro else ""
    if role != "USER":
        raise CommerceForbiddenError("Chỉ tài khoản người học (USER) được sử dụng chức năng này.")


def _provider_display_name(course: KhoaHoc) -> str | None:
    provider = course.nhaCungCap
    if provider is None:
        return None
    if provider.nguoiDung and provider.nguoiDung.hoTen:
        return provider.nguoiDung.hoTen
    if provider.nguoiDung and provider.nguoiDung.tenTaiKhoan:
        return provider.nguoiDung.tenTaiKhoan
    return None


def _evaluate_purchasability(
    course: KhoaHoc | None,
    enrollment: DangKyKhoaHoc | None,
) -> tuple[bool, str | None, Decimal | None, bool]:
    """Return (purchasable, unavailable_reason, current_price_vnd, is_repurchase_after_refund)."""
    if course is None:
        return False, "Khóa học không còn tồn tại.", None, False

    current_price = Decimal(course.gia) if course.gia is not None else None

    if course.trangThaiDuyet != "APPROVED" or course.trangThaiHienThi != "VISIBLE":
        return False, "Khóa học hiện tạm ẩn hoặc chưa được phê duyệt công khai.", current_price, False

    if enrollment is not None and enrollment.trangThaiQuyenHoc == "ACTIVE":
        return False, "Bạn đã sở hữu khóa học này.", current_price, False

    if current_price is None:
        return False, "Khóa học chưa được thiết lập học phí hợp lệ.", None, False

    if current_price < Decimal("0"):
        return False, "Học phí khóa học không hợp lệ.", current_price, False

    if current_price == Decimal("0"):
        return False, "Khóa học miễn phí — vui lòng đăng ký học trực tiếp.", current_price, False

    is_repurchase = enrollment is not None and enrollment.trangThaiQuyenHoc == "REVOKED"
    return True, None, current_price, is_repurchase


def _evaluate_wishlist_availability(
    course: KhoaHoc | None,
    enrollment: DangKyKhoaHoc | None,
) -> tuple[bool, str | None, Decimal | None]:
    """Wishlist allows both free and paid APPROVED+VISIBLE courses, while flagging hidden/owned."""
    if course is None:
        return False, "Khóa học không còn tồn tại.", None
    current_price = Decimal(course.gia) if course.gia is not None else None
    if course.trangThaiDuyet != "APPROVED" or course.trangThaiHienThi != "VISIBLE":
        return False, "Khóa học hiện tạm ẩn hoặc chưa được phê duyệt công khai.", current_price
    if current_price is None or current_price < Decimal("0"):
        return False, "Khóa học chưa được thiết lập học phí hợp lệ.", current_price
    if enrollment is not None and enrollment.trangThaiQuyenHoc == "ACTIVE":
        return True, None, current_price
    return True, None, current_price


# ---------------------------------------------------------------------------
# Wishlist Services
# ---------------------------------------------------------------------------
def list_wishlist(
    db: Session,
    user: NguoiDung,
    *,
    page: int = 1,
    page_size: int = 20,
) -> WishlistListResponse:
    _assert_active_learner(user)
    safe_page = max(1, page)
    safe_size = max(1, min(page_size, 100))
    total = commerce_repository.count_wishlist(db, user.maNguoiDung)
    total_pages = max(1, math.ceil(total / safe_size)) if total else 0
    offset = (safe_page - 1) * safe_size

    rows = commerce_repository.list_wishlist_items(
        db, user.maNguoiDung, offset=offset, limit=safe_size
    )
    course_ids = {int(r.maKhoaHoc) for r in rows}
    enrollments = commerce_repository.list_user_enrollments_map(
        db, user.maNguoiDung, course_ids
    )
    cart_course_ids = commerce_repository.list_cart_course_ids(db, user.maNguoiDung)

    items: list[WishlistItemResponse] = []
    for row in rows:
        course = row.khoaHoc
        enrollment = enrollments.get(int(row.maKhoaHoc))
        available, reason, current_price = _evaluate_wishlist_availability(course, enrollment)
        items.append(
            WishlistItemResponse(
                maYeuThich=row.maYeuThich,
                maKhoaHoc=row.maKhoaHoc,
                tieuDe=course.tieuDe or f"Khóa học #{row.maKhoaHoc}" if course else f"Khóa học #{row.maKhoaHoc}",
                hinhAnh=course.hinhAnh if course else None,
                maDanhMuc=course.maDanhMuc if course else None,
                tenDanhMuc=course.danhMuc.tenDanhMuc if course and course.danhMuc else None,
                maNhaCungCap=course.maNhaCungCap if course else None,
                tenNhaCungCap=_provider_display_name(course) if course else None,
                giaHienTai=current_price,
                donViTienTe="VND",
                khaDung=available,
                lyDoKhongKhaDung=reason,
                daSoHuu=bool(enrollment and enrollment.trangThaiQuyenHoc == "ACTIVE"),
                trangThaiQuyenHoc=enrollment.trangThaiQuyenHoc if enrollment else None,
                trongGioHang=int(row.maKhoaHoc) in cart_course_ids,
                ngayTao=row.ngayTao,
            )
        )

    return WishlistListResponse(
        items=items,
        total=total,
        page=safe_page,
        pageSize=safe_size,
        totalPages=total_pages,
    )


def add_to_wishlist(
    db: Session, user: NguoiDung, course_id: int
) -> WishlistStatusResponse:
    _assert_active_learner(user)
    _lock_user_course(db, user.maNguoiDung, course_id)

    course = commerce_repository.get_course_with_relations(db, course_id)
    if (
        course is None
        or course.trangThaiDuyet != "APPROVED"
        or course.trangThaiHienThi != "VISIBLE"
    ):
        raise CommerceNotFoundError("Không tìm thấy khóa học công khai để thêm vào danh sách yêu thích.")

    try:
        commerce_repository.insert_wishlist_idempotent(db, user.maNguoiDung, course_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return WishlistStatusResponse(
        maKhoaHoc=course_id,
        trongYeuThich=True,
        tongSoYeuThich=commerce_repository.count_wishlist(db, user.maNguoiDung),
    )


def remove_from_wishlist(
    db: Session, user: NguoiDung, course_id: int
) -> WishlistStatusResponse:
    _assert_active_learner(user)
    _lock_user_course(db, user.maNguoiDung, course_id)
    try:
        commerce_repository.delete_wishlist_item(db, user.maNguoiDung, course_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return WishlistStatusResponse(
        maKhoaHoc=course_id,
        trongYeuThich=False,
        tongSoYeuThich=commerce_repository.count_wishlist(db, user.maNguoiDung),
    )


def get_wishlist_status(
    db: Session, user: NguoiDung, course_id: int
) -> WishlistStatusResponse:
    _assert_active_learner(user)
    exists = commerce_repository.get_wishlist_item(db, user.maNguoiDung, course_id) is not None
    return WishlistStatusResponse(
        maKhoaHoc=course_id,
        trongYeuThich=exists,
        tongSoYeuThich=commerce_repository.count_wishlist(db, user.maNguoiDung),
    )


def get_wishlist_count(db: Session, user: NguoiDung) -> WishlistCountResponse:
    _assert_active_learner(user)
    return WishlistCountResponse(
        tongSoYeuThich=commerce_repository.count_wishlist(db, user.maNguoiDung)
    )


# ---------------------------------------------------------------------------
# Shopping Cart Services
# ---------------------------------------------------------------------------
def _build_cart_response(db: Session, user_id: int) -> CartResponse:
    cart = commerce_repository.get_cart_by_user(db, user_id)
    if cart is None:
        return CartResponse(
            maGioHang=None,
            items=[],
            tongSoLuong=0,
            soLuongHopLe=0,
            soLuongKhongHopLe=0,
            tongTien=Decimal("0"),
            donViTienTe="VND",
            coThayDoiGia=False,
            coMucKhongHopLe=False,
        )

    rows = commerce_repository.list_cart_items(db, cart.maGioHang)
    course_ids = {int(r.maKhoaHoc) for r in rows}
    enrollments = commerce_repository.list_user_enrollments_map(db, user_id, course_ids)

    items: list[CartItemResponse] = []
    valid_total = Decimal("0")
    valid_count = 0
    invalid_count = 0
    any_price_changed = False

    for row in rows:
        course = row.khoaHoc
        enrollment = enrollments.get(int(row.maKhoaHoc))
        purchasable, reason, current_price, _ = _evaluate_purchasability(course, enrollment)
        added_price = Decimal(row.giaLucThem)
        price_changed = current_price is not None and current_price != added_price

        if purchasable and current_price is not None:
            valid_total += current_price
            valid_count += 1
            if price_changed:
                any_price_changed = True
        else:
            invalid_count += 1

        items.append(
            CartItemResponse(
                maChiTietGioHang=row.maChiTietGioHang,
                maKhoaHoc=row.maKhoaHoc,
                tieuDe=course.tieuDe or f"Khóa học #{row.maKhoaHoc}" if course else f"Khóa học #{row.maKhoaHoc}",
                hinhAnh=course.hinhAnh if course else None,
                maDanhMuc=course.maDanhMuc if course else None,
                tenDanhMuc=course.danhMuc.tenDanhMuc if course and course.danhMuc else None,
                maNhaCungCap=course.maNhaCungCap if course else None,
                tenNhaCungCap=_provider_display_name(course) if course else None,
                giaLucThem=added_price,
                giaHienTai=current_price,
                giaThayDoi=price_changed,
                donViTienTe="VND",
                khaDung=purchasable,
                lyDoKhongKhaDung=reason,
                daSoHuu=bool(enrollment and enrollment.trangThaiQuyenHoc == "ACTIVE"),
                trangThaiQuyenHoc=enrollment.trangThaiQuyenHoc if enrollment else None,
                ngayTao=row.ngayTao,
            )
        )

    return CartResponse(
        maGioHang=cart.maGioHang,
        items=items,
        tongSoLuong=len(items),
        soLuongHopLe=valid_count,
        soLuongKhongHopLe=invalid_count,
        tongTien=valid_total,
        donViTienTe="VND",
        coThayDoiGia=any_price_changed,
        coMucKhongHopLe=invalid_count > 0,
    )


def get_cart(db: Session, user: NguoiDung) -> CartResponse:
    _assert_active_learner(user)
    return _build_cart_response(db, user.maNguoiDung)


def get_cart_count(db: Session, user: NguoiDung) -> CartCountResponse:
    _assert_active_learner(user)
    cart_res = _build_cart_response(db, user.maNguoiDung)
    return CartCountResponse(
        tongSoLuong=cart_res.tongSoLuong,
        soLuongHopLe=cart_res.soLuongHopLe,
    )


def _validate_purchasable_or_raise(
    db: Session, user: NguoiDung, course_id: int, *, for_update: bool = False
) -> BuyNowEligibilityResult:
    _assert_active_learner(user)
    course = commerce_repository.get_course_with_relations(
        db, course_id, for_update=for_update
    )
    if (
        course is None
        or course.trangThaiDuyet != "APPROVED"
        or course.trangThaiHienThi != "VISIBLE"
    ):
        raise CommerceNotFoundError("Khóa học không tồn tại hoặc chưa được mở bán công khai.")

    enrollment = commerce_repository.get_user_enrollment_any_status(
        db, user.maNguoiDung, course_id
    )
    purchasable, reason, current_price, is_repurchase = _evaluate_purchasability(
        course, enrollment
    )
    if not purchasable or current_price is None:
        if enrollment is not None and enrollment.trangThaiQuyenHoc == "ACTIVE":
            raise CommerceConflictError(reason or "Bạn đã sở hữu khóa học này.")
        raise CommerceBadRequestError(reason or "Khóa học không đủ điều kiện thêm vào giỏ hàng.")

    return BuyNowEligibilityResult(
        course=course,
        current_price=current_price,
        is_repurchase_after_refund=is_repurchase,
    )


def add_to_cart(db: Session, user: NguoiDung, course_id: int) -> CartResponse:
    _assert_active_learner(user)
    _lock_user_course(db, user.maNguoiDung, course_id)

    eligibility = _validate_purchasable_or_raise(db, user, course_id, for_update=True)
    try:
        cart = commerce_repository.get_or_create_cart(db, user.maNguoiDung)
        commerce_repository.insert_cart_item_idempotent(
            db, cart.maGioHang, course_id, eligibility.current_price
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _build_cart_response(db, user.maNguoiDung)


def remove_from_cart(db: Session, user: NguoiDung, course_id: int) -> CartResponse:
    _assert_active_learner(user)
    _lock_user_course(db, user.maNguoiDung, course_id)
    try:
        cart = commerce_repository.get_cart_by_user(db, user.maNguoiDung)
        if cart is not None:
            commerce_repository.delete_cart_item(db, cart.maGioHang, course_id)
            db.commit()
    except Exception:
        db.rollback()
        raise

    return _build_cart_response(db, user.maNguoiDung)


def clear_cart(db: Session, user: NguoiDung) -> CartClearResponse:
    _assert_active_learner(user)
    removed = 0
    try:
        cart = commerce_repository.get_cart_by_user(db, user.maNguoiDung, for_update=True)
        if cart is not None:
            removed = commerce_repository.clear_cart_items(db, cart.maGioHang)
            db.commit()
    except Exception:
        db.rollback()
        raise

    return CartClearResponse(daXoaSoLuong=removed, tongSoLuong=0)


def move_wishlist_to_cart(
    db: Session, user: NguoiDung, course_id: int
) -> MoveWishlistToCartResponse:
    """Atomic transfer: validate purchasability -> insert cart item -> remove wishlist item -> commit.
    If cart validation or insert fails, wishlist item is strictly preserved (rollback).
    """
    _assert_active_learner(user)
    _lock_user_course(db, user.maNguoiDung, course_id)

    wishlist_row = commerce_repository.get_wishlist_item(
        db, user.maNguoiDung, course_id, for_update=True
    )
    if wishlist_row is None:
        raise CommerceNotFoundError("Khóa học không có trong danh sách yêu thích của bạn.")

    # Validate BEFORE touching wishlist so failure never removes wishlist item
    eligibility = _validate_purchasable_or_raise(db, user, course_id, for_update=True)

    try:
        cart = commerce_repository.get_or_create_cart(db, user.maNguoiDung)
        commerce_repository.insert_cart_item_idempotent(
            db, cart.maGioHang, course_id, eligibility.current_price
        )
        removed = commerce_repository.delete_wishlist_item(db, user.maNguoiDung, course_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    cart_res = _build_cart_response(db, user.maNguoiDung)
    wishlist_total = commerce_repository.count_wishlist(db, user.maNguoiDung)
    return MoveWishlistToCartResponse(
        maKhoaHoc=course_id,
        daChuyenVaoGioHang=True,
        daXoaKhoiYeuThich=removed,
        tongSoYeuThich=wishlist_total,
        tongSoGioHang=cart_res.tongSoLuong,
        tongTienGioHang=cart_res.tongTien,
        donViTienTe="VND",
    )


# ---------------------------------------------------------------------------
# Buy Now Preparation (Reusable by GĐ4.3 Checkout & Order Creation)
# ---------------------------------------------------------------------------
def prepare_buy_now(
    db: Session, user: NguoiDung, course_id: int, *, for_update: bool = False
) -> BuyNowEligibilityResult:
    """Validate whether a USER can initiate a Buy Now order directly without adding to cart.
    Does NOT create orders, payments, or enrollments.
    """
    return _validate_purchasable_or_raise(db, user, course_id, for_update=for_update)


def validate_buy_now_response(
    db: Session, user: NguoiDung, course_id: int
) -> BuyNowValidationResponse:
    result = prepare_buy_now(db, user, course_id, for_update=False)
    course = result.course
    return BuyNowValidationResponse(
        maKhoaHoc=course.maKhoaHoc,
        tieuDe=course.tieuDe or f"Khóa học #{course.maKhoaHoc}",
        hinhAnh=course.hinhAnh,
        maDanhMuc=course.maDanhMuc,
        tenDanhMuc=course.danhMuc.tenDanhMuc if course.danhMuc else None,
        maNhaCungCap=course.maNhaCungCap,
        tenNhaCungCap=_provider_display_name(course),
        giaHienTai=result.current_price,
        donViTienTe="VND",
        muaLaiSauHoanTien=result.is_repurchase_after_refund,
        hopLe=True,
    )
