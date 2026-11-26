"""GĐ4.3 Order, Checkout, and Mock Payment Sandbox business logic.

Enforces strict deadlock-free locking order:
  DonHang (FOR UPDATE) -> ThanhToan (FOR UPDATE) -> KhoaHoc (ASC maKhoaHoc) -> DangKyKhoaHoc (ASC maKhoaHoc)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import math
import secrets
import uuid

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config.config import get_settings
from models import ChiTietDonHang, DangKyKhoaHoc, DonHang, NguoiDung, ThanhToan
from repository import commerce_repository
from schemas.commerce import (
    CommerceCapabilitiesResponse,
    MockPaymentCallbackRequest,
    MockPaymentSessionDetailResponse,
    MockPaymentSimulateRequest,
    OrderCancelRequest,
    OrderCreateRequest,
    OrderItemResponse,
    OrderListResponse,
    OrderPreviewItemResponse,
    OrderPreviewRequest,
    OrderPreviewResponse,
    OrderResponse,
    OrderStatusResponse,
    PaymentAttemptResponse,
    PaymentCallbackResponse,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    VNPayIpnResponse,
    VNPayReturnVerifyResponse,
)
from service import commerce_service, financial_event_service, notification_service
from service.commerce_service import (
    CommerceBadRequestError,
    CommerceConflictError,
    CommerceForbiddenError,
    CommerceNotFoundError,
    _assert_active_learner,
    _evaluate_purchasability,
    _lock_user_course,
    _provider_display_name,
)
from service.payment_providers import (
    CallbackVerificationResult,
    PaymentProviderError,
    PaymentSignatureError,
    compute_mock_callback_signature,
    get_payment_provider,
    is_vnpay_sandbox_configured,
)


_MOCK_PAYMENT_ALLOWED_TEST_DBS = frozenset({"EduSuggest_phase4_test"})


def get_commerce_capabilities() -> CommerceCapabilitiesResponse:
    """Zero-DB-query runtime capability check so Production EduSuggest (24 tables) stays 100% safe."""
    settings = get_settings()
    enrollment_gate = bool(settings.commerce_enrollment_gate_enabled)
    mock_enabled = (
        bool(settings.mock_payment_enabled)
        and (settings.app_env or "").strip().lower() != "production"
    )
    return CommerceCapabilitiesResponse(
        marketplaceEnabled=enrollment_gate,
        enrollmentGateEnabled=enrollment_gate,
        mockPaymentEnabled=mock_enabled,
        vnpaySandboxEnabled=is_vnpay_sandbox_configured(),
        orderTtlMinutes=int(settings.order_payment_ttl_minutes),
    )


def _assert_vnpay_sandbox_allowed(db: Session) -> None:
    """Hard safety guard: VNPay Sandbox is OFF by default and NEVER runs against Production EduSuggest."""
    if not is_vnpay_sandbox_configured():
        raise CommerceForbiddenError(
            "VNPay Sandbox chưa được bật hoặc chưa được cấu hình trên môi trường này."
        )
    current_db = str(db.execute(text("SELECT current_database()")).scalar_one() or "")
    if current_db == "EduSuggest" or current_db not in _MOCK_PAYMENT_ALLOWED_TEST_DBS:
        raise CommerceForbiddenError(
            "VNPay Sandbox chỉ được phép hoạt động trên cơ sở dữ liệu kiểm thử được cho phép."
        )


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _order_ttl_minutes() -> int:
    return int(get_settings().order_payment_ttl_minutes)


def _generate_order_number(now: datetime) -> str:
    return f"ORD-{now.strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"


def _generate_internal_txn_ref(order_id: int, now: datetime) -> str:
    return f"TXN-{now.strftime('%Y%m%d%H%M%S')}-{order_id}-{uuid.uuid4().hex[:6].upper()}"


def _assert_mock_payment_allowed(db: Session) -> None:
    """Hard safety guard: Mock Payment is disabled by default and NEVER runs on Production EduSuggest."""
    settings = get_settings()
    if not settings.mock_payment_enabled:
        raise CommerceForbiddenError(
            "Thanh toán mô phỏng (Mock Payment Sandbox) đang tắt trên môi trường này."
        )
    if (settings.app_env or "").strip().lower() == "production":
        raise CommerceForbiddenError(
            "Không được phép sử dụng Mock Payment trên môi trường Production."
        )
    current_db = str(db.execute(text("SELECT current_database()")).scalar_one() or "")
    if current_db == "EduSuggest" or current_db not in _MOCK_PAYMENT_ALLOWED_TEST_DBS:
        raise CommerceForbiddenError(
            "Mock Payment chỉ được phép hoạt động trên cơ sở dữ liệu kiểm thử được cho phép."
        )


def _to_payment_response(p: ThanhToan) -> PaymentAttemptResponse:
    safe_data = p.duLieuPhanHoiAnToan if isinstance(p.duLieuPhanHoiAnToan, dict) else {}
    return PaymentAttemptResponse(
        maThanhToan=p.maThanhToan,
        maDonHang=p.maDonHang,
        congThanhToan=p.congThanhToan,
        laThanhToanMoPhong=(p.congThanhToan == "MOCK_SANDBOX"),
        maGiaoDichNoiBo=p.maGiaoDichNoiBo,
        maGiaoDichCong=p.maGiaoDichCong,
        soTien=Decimal(p.soTien),
        donViTienTe=p.donViTienTe,
        trangThai=p.trangThai,
        maPhanHoiCong=p.maPhanHoiCong,
        daXacMinhChuKy=bool(p.daXacMinhChuKy),
        canDoiSoat=bool(safe_data.get("reconciliationRequired", False)),
        ngayThanhToan=p.ngayThanhToan,
        ngayTao=p.ngayTao,
    )


def _to_order_response(order: DonHang) -> OrderResponse:
    sorted_items = sorted(order.chiTiets or [], key=lambda x: x.maChiTietDonHang)
    sorted_payments = sorted(
        order.thanhToans or [],
        key=lambda x: (x.ngayTao, x.maThanhToan),
        reverse=True,
    )
    return OrderResponse(
        maDonHang=order.maDonHang,
        maSoDonHang=order.maSoDonHang,
        nguonTao=order.nguonTao,
        tongTien=Decimal(order.tongTien),
        donViTienTe=order.donViTienTe,
        trangThai=order.trangThai,
        hanThanhToan=order.hanThanhToan,
        ngayThanhToan=order.ngayThanhToan,
        ngayHuy=order.ngayHuy,
        lyDoHuyHoacHoan=order.lyDoHuyHoacHoan,
        ngayTao=order.ngayTao,
        items=[
            OrderItemResponse(
                maChiTietDonHang=item.maChiTietDonHang,
                maKhoaHoc=item.maKhoaHoc,
                maNhaCungCap=item.maNhaCungCap,
                tieuDeSnapshot=item.tieuDeSnapshot,
                giaTaiThoiDiemMua=Decimal(item.giaTaiThoiDiemMua),
                donViTienTe=order.donViTienTe,
                ngayTao=item.ngayTao,
            )
            for item in sorted_items
        ],
        thanhToans=[_to_payment_response(p) for p in sorted_payments],
    )


def _expire_order_if_past_ttl(order: DonHang, now: datetime) -> bool:
    """Transition stale PENDING/FAILED orders to EXPIRED once hanThanhToan has passed."""
    if order.trangThai in {"PENDING", "FAILED"} and now >= order.hanThanhToan:
        order.trangThai = "EXPIRED"
        order.ngayHuy = order.ngayHuy or now
        order.lyDoHuyHoacHoan = order.lyDoHuyHoacHoan or "Đơn hàng quá hạn thanh toán."
        order.ngayCapNhat = now
        for pay in order.thanhToans or []:
            if pay.trangThai == "PENDING":
                pay.trangThai = "EXPIRED"
                pay.ngayCapNhat = now
        return True
    return False


def _resolve_checkout_course_ids(
    db: Session,
    user: NguoiDung,
    *,
    source: str,
    course_ids: list[int] | None,
    single_course_id: int | None,
) -> list[int]:
    if source == "BUY_NOW":
        if single_course_id is None:
            raise CommerceBadRequestError("Mua ngay yêu cầu cung cấp maKhoaHoc.")
        return [int(single_course_id)]

    # source == "CART"
    cart = commerce_repository.get_cart_by_user(db, user.maNguoiDung)
    if cart is None:
        raise CommerceBadRequestError("Giỏ hàng của bạn đang trống.")
    cart_rows = commerce_repository.list_cart_items(db, cart.maGioHang)
    cart_course_ids = [int(r.maKhoaHoc) for r in cart_rows]
    if not cart_course_ids:
        raise CommerceBadRequestError("Giỏ hàng của bạn đang trống.")

    if course_ids is None:
        return sorted(set(cart_course_ids))

    requested = sorted({int(cid) for cid in course_ids})
    missing = [cid for cid in requested if cid not in set(cart_course_ids)]
    if missing:
        raise CommerceBadRequestError(
            f"Một số khóa học được chọn không có trong giỏ hàng của bạn: {missing}."
        )
    return requested


# ---------------------------------------------------------------------------
# 1. Order Preview
# ---------------------------------------------------------------------------
def preview_order(
    db: Session, user: NguoiDung, payload: OrderPreviewRequest
) -> OrderPreviewResponse:
    _assert_active_learner(user)
    target_ids = _resolve_checkout_course_ids(
        db,
        user,
        source=payload.nguonTao,
        course_ids=payload.courseIds,
        single_course_id=payload.maKhoaHoc,
    )

    items: list[OrderPreviewItemResponse] = []
    total = Decimal("0")
    enrollments = commerce_repository.list_user_enrollments_map(
        db, user.maNguoiDung, set(target_ids)
    )

    for cid in target_ids:
        course = commerce_repository.get_course_with_relations(db, cid)
        enrollment = enrollments.get(cid)
        purchasable, reason, price, is_repurchase = _evaluate_purchasability(
            course, enrollment
        )
        if not purchasable or price is None or course is None:
            if enrollment is not None and enrollment.trangThaiQuyenHoc == "ACTIVE":
                raise CommerceConflictError(reason or "Bạn đã sở hữu khóa học này.")
            if course is None or course.trangThaiDuyet != "APPROVED" or course.trangThaiHienThi != "VISIBLE":
                raise CommerceNotFoundError(reason or "Khóa học không khả dụng.")
            raise CommerceBadRequestError(reason or "Khóa học không đủ điều kiện thanh toán.")
        if course.maNhaCungCap is None:
            raise CommerceConflictError(f"Khóa học #{cid} thiếu thông tin nhà cung cấp.")

        total += price
        items.append(
            OrderPreviewItemResponse(
                maKhoaHoc=course.maKhoaHoc,
                tieuDe=course.tieuDe or f"Khóa học #{course.maKhoaHoc}",
                hinhAnh=course.hinhAnh,
                maNhaCungCap=course.maNhaCungCap,
                tenNhaCungCap=_provider_display_name(course),
                giaHienTai=price,
                donViTienTe="VND",
                muaLaiSauHoanTien=is_repurchase,
            )
        )

    return OrderPreviewResponse(
        nguonTao=payload.nguonTao,
        items=items,
        tongSoLuong=len(items),
        tongTien=total,
        donViTienTe="VND",
        thoiHanThanhToanPhut=_order_ttl_minutes(),
    )


# ---------------------------------------------------------------------------
# 2. Order Creation (Idempotent + Price Snapshot + Price-Change Guard)
# ---------------------------------------------------------------------------
def create_order(
    db: Session,
    user: NguoiDung,
    payload: OrderCreateRequest,
    *,
    idempotency_key: str,
) -> tuple[OrderResponse, bool]:
    """Create a PENDING order with immutable snapshots. Returns (OrderResponse, created_new)."""
    _assert_active_learner(user)
    clean_key = (idempotency_key or "").strip()
    if len(clean_key) < 4 or len(clean_key) > 72:
        raise CommerceBadRequestError("Header Idempotency-Key hợp lệ là bắt buộc (4–72 ký tự).")

    scoped_idem_key = f"ord:u{user.maNguoiDung}:{clean_key}"

    # Fast-path idempotency replay WITH request fingerprint verification (GĐ4.7A HARDEN-02)
    existing_order = commerce_repository.get_order_by_idempotency_key(db, scoped_idem_key)
    if existing_order is not None:
        existing_cids = sorted(int(item.maKhoaHoc) for item in (existing_order.chiTiets or []))
        req_cids: list[int] | None = None
        if payload.nguonTao == "BUY_NOW" and payload.maKhoaHoc is not None:
            req_cids = [int(payload.maKhoaHoc)]
        elif payload.nguonTao == "CART" and payload.courseIds is not None:
            req_cids = sorted({int(c) for c in payload.courseIds})
        if existing_order.nguonTao != payload.nguonTao or (
            req_cids is not None and existing_cids != req_cids
        ):
            raise CommerceConflictError(
                "Idempotency-Key đã được sử dụng cho yêu cầu tạo đơn hàng khác (request fingerprint mismatch)."
            )
        return _to_order_response(existing_order), False

    target_ids = _resolve_checkout_course_ids(
        db,
        user,
        source=payload.nguonTao,
        course_ids=payload.courseIds,
        single_course_id=payload.maKhoaHoc,
    )

    # Lock KhoaHoc rows in strict ascending maKhoaHoc order to prevent deadlocks
    locked_courses = commerce_repository.lock_courses_ordered(db, target_ids)
    course_by_id = {int(c.maKhoaHoc): c for c in locked_courses}
    enrollments = commerce_repository.list_user_enrollments_map(
        db, user.maNguoiDung, set(target_ids)
    )

    total = Decimal("0")
    snapshot_specs: list[tuple[int, int, str, Decimal]] = []

    for cid in target_ids:
        course = course_by_id.get(cid)
        enrollment = enrollments.get(cid)
        purchasable, reason, price, _ = _evaluate_purchasability(course, enrollment)
        if not purchasable or price is None or course is None:
            if enrollment is not None and enrollment.trangThaiQuyenHoc == "ACTIVE":
                raise CommerceConflictError(reason or "Bạn đã sở hữu khóa học này.")
            if course is None or course.trangThaiDuyet != "APPROVED" or course.trangThaiHienThi != "VISIBLE":
                raise CommerceNotFoundError(reason or "Khóa học không khả dụng.")
            raise CommerceBadRequestError(reason or "Khóa học không đủ điều kiện đặt hàng.")
        if course.maNhaCungCap is None:
            raise CommerceConflictError(f"Khóa học #{cid} thiếu thông tin nhà cung cấp.")

        total += price
        snapshot_specs.append(
            (
                course.maKhoaHoc,
                int(course.maNhaCungCap),
                course.tieuDe or f"Khóa học #{course.maKhoaHoc}",
                price,
            )
        )

    # Detect price change between preview and create (never trust client total as billed price)
    if payload.tongTienXacNhan is not None and Decimal(payload.tongTienXacNhan) != total:
        raise CommerceConflictError(
            f"Giá khóa học đã thay đổi kể từ lúc xem trước (tổng mới: {total} VND). "
            "Vui lòng xác nhận lại đơn hàng."
        )

    now = _utc_now()
    ttl = now + timedelta(minutes=_order_ttl_minutes())
    order = DonHang(
        maSoDonHang=_generate_order_number(now),
        maNguoiDung=user.maNguoiDung,
        nguonTao=payload.nguonTao,
        tongTien=total,
        donViTienTe="VND",
        trangThai="PENDING",
        khoaChongTrung=scoped_idem_key,
        hanThanhToan=ttl,
        ngayTao=now,
        ngayCapNhat=now,
    )
    try:
        db.add(order)
        db.flush()
        for cid, provider_id, title_snap, price_snap in snapshot_specs:
            db.add(
                ChiTietDonHang(
                    maDonHang=order.maDonHang,
                    maKhoaHoc=cid,
                    maNhaCungCap=provider_id,
                    tieuDeSnapshot=title_snap,
                    giaTaiThoiDiemMua=price_snap,
                    ngayTao=now,
                )
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        # Concurrent duplicate request with same Idempotency-Key -> replay existing order cleanly
        replay = commerce_repository.get_order_by_idempotency_key(db, scoped_idem_key)
        if replay is not None:
            return _to_order_response(replay), False
        raise
    except Exception:
        db.rollback()
        raise

    loaded = commerce_repository.get_order_by_id(db, order.maDonHang)
    assert loaded is not None
    return _to_order_response(loaded), True


# ---------------------------------------------------------------------------
# 3. Order Read, History, Status, Cancel, Expiry
# ---------------------------------------------------------------------------
def _get_owned_order_or_raise(
    db: Session, user: NguoiDung, order_id: int, *, for_update: bool = False
) -> DonHang:
    _assert_active_learner(user)
    order = commerce_repository.get_order_by_id(db, order_id, for_update=for_update)
    if order is None or int(order.maNguoiDung) != int(user.maNguoiDung):
        raise CommerceNotFoundError("Không tìm thấy đơn hàng.")
    return order


def list_my_orders(
    db: Session,
    user: NguoiDung,
    *,
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
) -> OrderListResponse:
    _assert_active_learner(user)
    safe_page = max(1, page)
    safe_size = max(1, min(page_size, 100))

    # Expire any stale PENDING/FAILED orders belonging to this user on read
    now = _utc_now()
    rows = commerce_repository.list_user_orders(
        db,
        user.maNguoiDung,
        offset=(safe_page - 1) * safe_size,
        limit=safe_size,
        status_filter=status_filter,
    )
    changed = any(_expire_order_if_past_ttl(r, now) for r in rows)
    if changed:
        db.commit()

    total = commerce_repository.count_user_orders(
        db, user.maNguoiDung, status_filter=status_filter
    )
    total_pages = max(1, math.ceil(total / safe_size)) if total else 0
    return OrderListResponse(
        items=[_to_order_response(r) for r in rows],
        total=total,
        page=safe_page,
        pageSize=safe_size,
        totalPages=total_pages,
    )


def get_my_order_detail(
    db: Session, user: NguoiDung, order_id: int
) -> OrderResponse:
    order = _get_owned_order_or_raise(db, user, order_id, for_update=True)
    if _expire_order_if_past_ttl(order, _utc_now()):
        db.commit()
    return _to_order_response(order)


def get_my_order_status(
    db: Session, user: NguoiDung, order_id: int
) -> OrderStatusResponse:
    order = _get_owned_order_or_raise(db, user, order_id, for_update=True)
    now = _utc_now()
    if _expire_order_if_past_ttl(order, now):
        db.commit()
    latest_payment = None
    if order.thanhToans:
        sorted_p = sorted(
            order.thanhToans, key=lambda x: (x.ngayTao, x.maThanhToan), reverse=True
        )
        latest_payment = _to_payment_response(sorted_p[0])
    return OrderStatusResponse(
        maDonHang=order.maDonHang,
        maSoDonHang=order.maSoDonHang,
        trangThai=order.trangThai,
        tongTien=Decimal(order.tongTien),
        donViTienTe=order.donViTienTe,
        hanThanhToan=order.hanThanhToan,
        daHetHan=(order.trangThai == "EXPIRED" or now >= order.hanThanhToan),
        ngayThanhToan=order.ngayThanhToan,
        giaoDichGanNhat=latest_payment,
    )


def cancel_my_order(
    db: Session, user: NguoiDung, order_id: int, payload: OrderCancelRequest | None = None
) -> OrderResponse:
    order = _get_owned_order_or_raise(db, user, order_id, for_update=True)
    now = _utc_now()
    if _expire_order_if_past_ttl(order, now):
        db.commit()
        raise CommerceConflictError("Đơn hàng đã hết hạn thanh toán nên không thể hủy.")

    if order.trangThai == "PAID":
        raise CommerceConflictError("Không thể hủy đơn hàng đã thanh toán thành công.")
    if order.trangThai == "CANCELLED":
        return _to_order_response(order)
    if order.trangThai not in {"PENDING", "FAILED"}:
        raise CommerceConflictError(
            f"Không thể hủy đơn hàng đang ở trạng thái {order.trangThai}."
        )

    order.trangThai = "CANCELLED"
    order.ngayHuy = now
    order.lyDoHuyHoacHoan = (
        payload.lyDo.strip() if payload and payload.lyDo and payload.lyDo.strip() else "Người dùng hủy đơn hàng."
    )
    order.ngayCapNhat = now
    for pay in order.thanhToans or []:
        if pay.trangThai == "PENDING":
            pay.trangThai = "CANCELLED"
            pay.ngayCapNhat = now
    db.commit()
    return _to_order_response(order)


# ---------------------------------------------------------------------------
# 4. Payment Initiation (Mock Sandbox — Idempotent + Pre-Payment Re-Validation)
# ---------------------------------------------------------------------------
def initiate_payment(
    db: Session,
    user: NguoiDung,
    order_id: int,
    payload: PaymentInitiateRequest,
    *,
    idempotency_key: str,
    client_ip: str = "127.0.0.1",
) -> PaymentInitiateResponse:
    _assert_active_learner(user)
    clean_key = (idempotency_key or "").strip()
    if len(clean_key) < 4 or len(clean_key) > 72:
        raise CommerceBadRequestError("Header Idempotency-Key hợp lệ là bắt buộc (4–72 ký tự).")

    if payload.congThanhToan == "MOCK_SANDBOX":
        _assert_mock_payment_allowed(db)
    elif payload.congThanhToan == "VNPAY_SANDBOX":
        _assert_vnpay_sandbox_allowed(db)

    try:
        provider = get_payment_provider(payload.congThanhToan)
    except PaymentProviderError as exc:
        raise CommerceBadRequestError(str(exc)) from exc

    scoped_pay_key = f"pay:u{user.maNguoiDung}:o{order_id}:{clean_key}"

    # Lock order FIRST (deadlock-free ordering)
    order = _get_owned_order_or_raise(db, user, order_id, for_update=True)
    now = _utc_now()
    if _expire_order_if_past_ttl(order, now):
        db.commit()
        raise CommerceConflictError("Đơn hàng đã hết hạn thanh toán. Vui lòng tạo đơn hàng mới.")

    # Replay if same payment idempotency key already created WITH gateway fingerprint check (GĐ4.7A HARDEN-02)
    existing_pay = commerce_repository.get_payment_by_idempotency_key(db, scoped_pay_key)
    if existing_pay is not None:
        if existing_pay.congThanhToan != provider.gateway_code:
            raise CommerceConflictError(
                "Idempotency-Key đã được sử dụng cho cổng thanh toán khác (request fingerprint mismatch)."
            )
        session = provider.create_session(
            order_id=order.maDonHang,
            order_number=order.maSoDonHang,
            internal_txn_ref=existing_pay.maGiaoDichNoiBo,
            amount=Decimal(existing_pay.soTien),
            currency=existing_pay.donViTienTe,
            client_ip=client_ip,
            created_at_utc=existing_pay.ngayTao,
            expires_at_utc=order.hanThanhToan,
        )
        gateway_note = (
            "Giao dịch thanh toán mô phỏng (Sandbox) — không phát sinh tiền thật."
            if provider.is_simulated
            else "Chuyển hướng tới cổng thử nghiệm VNPay Sandbox — không phát sinh giao dịch tiền thật."
        )
        return PaymentInitiateResponse(
            maThanhToan=existing_pay.maThanhToan,
            maDonHang=order.maDonHang,
            maSoDonHang=order.maSoDonHang,
            congThanhToan=existing_pay.congThanhToan,
            laThanhToanMoPhong=provider.is_simulated,
            maGiaoDichNoiBo=existing_pay.maGiaoDichNoiBo,
            soTien=Decimal(existing_pay.soTien),
            donViTienTe=existing_pay.donViTienTe,
            trangThai=existing_pay.trangThai,
            paymentUrl=session.payment_url,
            hanThanhToan=order.hanThanhToan,
            ghiChu=gateway_note,
        )

    if order.trangThai == "PAID":
        raise CommerceConflictError("Đơn hàng này đã được thanh toán thành công.")
    if order.trangThai not in {"PENDING", "FAILED"}:
        raise CommerceConflictError(
            f"Đơn hàng ở trạng thái {order.trangThai} không thể khởi tạo thanh toán."
        )

    # Re-validate all courses in order before starting payment (lock courses ASC)
    course_ids = sorted({int(item.maKhoaHoc) for item in order.chiTiets or []})
    locked_courses = commerce_repository.lock_courses_ordered(db, course_ids)
    course_by_id = {int(c.maKhoaHoc): c for c in locked_courses}
    enrollments = commerce_repository.list_user_enrollments_map(
        db, user.maNguoiDung, set(course_ids)
    )
    for item in order.chiTiets or []:
        c = course_by_id.get(int(item.maKhoaHoc))
        if c is None or c.trangThaiDuyet != "APPROVED" or c.trangThaiHienThi != "VISIBLE":
            raise CommerceConflictError(
                f"Khóa học '{item.tieuDeSnapshot}' hiện không còn hiển thị công khai nên không thể thanh toán."
            )
        enr = enrollments.get(int(item.maKhoaHoc))
        if enr is not None and enr.trangThaiQuyenHoc == "ACTIVE":
            raise CommerceConflictError(
                f"Bạn đã sở hữu khóa học '{item.tieuDeSnapshot}'. Không thể thanh toán trùng."
            )

    # Allow retry from FAILED back to PENDING within TTL
    if order.trangThai == "FAILED":
        order.trangThai = "PENDING"
        order.ngayCapNhat = now

    txn_ref = _generate_internal_txn_ref(order.maDonHang, now)
    payment = ThanhToan(
        maDonHang=order.maDonHang,
        maNguoiDung=user.maNguoiDung,
        congThanhToan=provider.gateway_code,
        maGiaoDichNoiBo=txn_ref,
        soTien=Decimal(order.tongTien),
        donViTienTe=order.donViTienTe,
        trangThai="PENDING",
        khoaChongTrung=scoped_pay_key,
        daXacMinhChuKy=False,
        duLieuPhanHoiAnToan={"isSimulated": provider.is_simulated, "stage": "INITIATED"},
        ngayTao=now,
        ngayCapNhat=now,
    )
    try:
        db.add(payment)
        db.flush()
        financial_event_service.record_payment_event(
            db,
            order_id=order.maDonHang,
            payment_id=payment.maThanhToan,
            event_type="PAYMENT_INITIATED",
            source=provider.gateway_code,
            safe_data={
                "maGiaoDichNoiBo": payment.maGiaoDichNoiBo,
                "soTien": str(payment.soTien),
                "congThanhToan": provider.gateway_code,
                "isSimulated": provider.is_simulated,
            },
            idempotency_key=f"init:{payment.maGiaoDichNoiBo}",
            now=now,
        )
        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        replay = commerce_repository.get_payment_by_idempotency_key(db, scoped_pay_key)
        if replay is not None:
            payment = replay
        else:
            raise

    session = provider.create_session(
        order_id=order.maDonHang,
        order_number=order.maSoDonHang,
        internal_txn_ref=payment.maGiaoDichNoiBo,
        amount=Decimal(payment.soTien),
        currency=payment.donViTienTe,
        client_ip=client_ip,
        created_at_utc=payment.ngayTao,
        expires_at_utc=order.hanThanhToan,
    )
    gateway_note = (
        "Giao dịch thanh toán mô phỏng (Sandbox) — không phát sinh tiền thật."
        if provider.is_simulated
        else "Chuyển hướng tới cổng thử nghiệm VNPay Sandbox — không phát sinh giao dịch tiền thật."
    )
    return PaymentInitiateResponse(
        maThanhToan=payment.maThanhToan,
        maDonHang=order.maDonHang,
        maSoDonHang=order.maSoDonHang,
        congThanhToan=payment.congThanhToan,
        laThanhToanMoPhong=provider.is_simulated,
        maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
        soTien=Decimal(payment.soTien),
        donViTienTe=payment.donViTienTe,
        trangThai=payment.trangThai,
        paymentUrl=session.payment_url,
        hanThanhToan=order.hanThanhToan,
        ghiChu=gateway_note,
    )


# ---------------------------------------------------------------------------
# 5. Atomic Mock Payment Callback & 10-Step Enrollment Activation
# ---------------------------------------------------------------------------
def _apply_verified_callback(
    db: Session,
    verified: CallbackVerificationResult,
    *,
    expected_gateway: str,
    _post_payment_hook=None,
) -> PaymentCallbackResponse:
    """Shared 10-step atomic callback processor used by BOTH Mock Sandbox and VNPay Sandbox IPN."""
    # Locate payment first (unlocked) to discover order_id, then lock DonHang -> ThanhToan in strict order
    payment_ref = commerce_repository.get_payment_by_internal_ref(
        db, verified.internal_txn_ref, for_update=False
    )
    if payment_ref is None:
        raise CommerceNotFoundError("Không tìm thấy mã giao dịch thanh toán.")
    if payment_ref.congThanhToan != expected_gateway:
        raise CommerceBadRequestError("Cổng thanh toán không khớp với giao dịch đã khởi tạo.")
    if verified.order_id is not None and int(payment_ref.maDonHang) != int(verified.order_id):
        raise CommerceBadRequestError("Mã đơn hàng trong callback không khớp với mã giao dịch.")

    # Step 1: Strict deadlock-free row locking: DonHang FIRST, then ThanhToan
    order = commerce_repository.get_order_by_id(
        db, int(payment_ref.maDonHang), for_update=True
    )
    payment = commerce_repository.get_payment_by_internal_ref(
        db, verified.internal_txn_ref, for_update=True
    )
    if order is None or payment is None:
        raise CommerceNotFoundError("Không tìm thấy đơn hàng hoặc giao dịch.")

    now = _utc_now()

    # Step 2a: Idempotent replay if already processed identically
    if payment.trangThai == "PAID" and order.trangThai == "PAID" and verified.outcome == "PAID":
        return PaymentCallbackResponse(
            maDonHang=order.maDonHang,
            maSoDonHang=order.maSoDonHang,
            maThanhToan=payment.maThanhToan,
            maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
            trangThaiDonHang=order.trangThai,
            trangThaiThanhToan=payment.trangThai,
            daCapQuyenHoc=True,
            soKhoaHocKichHoat=0,
            idempotentReplay=True,
            canDoiSoat=False,
            thongDiep="Callback trùng lặp đã được xử lý idempotent (đơn hàng đã thanh toán).",
        )

    if payment.trangThai != "PENDING" and payment.trangThai == verified.outcome:
        return PaymentCallbackResponse(
            maDonHang=order.maDonHang,
            maSoDonHang=order.maSoDonHang,
            maThanhToan=payment.maThanhToan,
            maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
            trangThaiDonHang=order.trangThai,
            trangThaiThanhToan=payment.trangThai,
            daCapQuyenHoc=(order.trangThai == "PAID"),
            soKhoaHocKichHoat=0,
            idempotentReplay=True,
            canDoiSoat=False,
            thongDiep="Callback trùng lặp đã được bỏ qua an toàn.",
        )

    # Step 2b: Verify amount & currency strictly against DB snapshot
    if (
        verified.currency != order.donViTienTe
        or verified.amount != Decimal(order.tongTien)
        or verified.amount != Decimal(payment.soTien)
    ):
        payment.maPhanHoiCong = "04_AMOUNT_MISMATCH"
        payment.duLieuPhanHoiAnToan = {
            **verified.safe_payload,
            "reconciliationRequired": True,
            "reason": "AMOUNT_OR_CURRENCY_MISMATCH",
            "expectedAmount": str(order.tongTien),
            "expectedCurrency": order.donViTienTe,
        }
        payment.ngayCapNhat = now
        db.commit()
        raise CommerceBadRequestError(
            "Số tiền hoặc đơn vị tiền tệ trong callback không khớp với đơn hàng."
        )

    # Step 2c: Non-PAID outcomes (FAILED / CANCELLED / EXPIRED)
    if verified.outcome != "PAID":
        existing_meta = dict(payment.duLieuPhanHoiAnToan) if isinstance(payment.duLieuPhanHoiAnToan, dict) else {}
        if (
            order.trangThai in {"PAID", "REFUNDED"}
            or payment.trangThai in {"PAID", "REFUNDED"}
            or bool(existing_meta.get("fundsCaptured", False))
        ):
            # GĐ4.7A HARDEN-03: NEVER downgrade PAID/REFUNDED or clobber captured-funds reconciliation evidence
            return PaymentCallbackResponse(
                maDonHang=order.maDonHang,
                maSoDonHang=order.maSoDonHang,
                maThanhToan=payment.maThanhToan,
                maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
                trangThaiDonHang=order.trangThai,
                trangThaiThanhToan=payment.trangThai,
                daCapQuyenHoc=(order.trangThai == "PAID"),
                soKhoaHocKichHoat=0,
                idempotentReplay=True,
                canDoiSoat=bool(existing_meta.get("reconciliationRequired", False)),
                thongDiep="Giao dịch đã ghi nhận thu tiền hoặc hoàn tất trước đó; bỏ qua callback thất bại/hủy muộn.",
            )
        payment.trangThai = verified.outcome
        payment.maGiaoDichCong = verified.gateway_txn_id
        payment.daXacMinhChuKy = True
        payment.maPhanHoiCong = verified.response_code
        payment.duLieuPhanHoiAnToan = {**existing_meta, **verified.safe_payload}
        payment.ngayCapNhat = now

        if order.trangThai in {"PENDING", "FAILED"}:
            if verified.outcome == "EXPIRED" or now >= order.hanThanhToan:
                order.trangThai = "EXPIRED"
                order.ngayHuy = now
                order.lyDoHuyHoacHoan = "Giao dịch thanh toán đã hết hạn."
            elif verified.outcome == "FAILED":
                order.trangThai = "FAILED"
            # On user-cancelled gateway attempt within TTL, keep order PENDING so user can retry or cancel
            order.ngayCapNhat = now

        db.commit()
        return PaymentCallbackResponse(
            maDonHang=order.maDonHang,
            maSoDonHang=order.maSoDonHang,
            maThanhToan=payment.maThanhToan,
            maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
            trangThaiDonHang=order.trangThai,
            trangThaiThanhToan=payment.trangThai,
            daCapQuyenHoc=False,
            soKhoaHocKichHoat=0,
            idempotentReplay=False,
            canDoiSoat=False,
            thongDiep=f"Đã ghi nhận kết quả thanh toán mô phỏng: {verified.outcome}.",
        )

    # ------------------------------------------------------------------
    # Verified PAID outcome — Check conflict / late callback / eligibility
    # ------------------------------------------------------------------
    def _record_reconciliation(reason: str, code: str, message: str) -> PaymentCallbackResponse:
        existing_meta = dict(payment.duLieuPhanHoiAnToan) if isinstance(payment.duLieuPhanHoiAnToan, dict) else {}
        audit_trail = list(existing_meta.get("auditTrail") or [])
        audit_trail.append(
            {
                "at": now.isoformat(),
                "action": "CAPTURED_RECONCILIATION_OPENED",
                "reason": reason,
                "gatewayTxnId": verified.gateway_txn_id,
                "capturedAmountVnd": str(verified.amount),
            }
        )
        payment.trangThai = "CAPTURED_UNAPPLIED"
        payment.daThuTien = True
        payment.soTienDaThuThucTe = Decimal(verified.amount)
        payment.maGiaoDichCong = verified.gateway_txn_id
        payment.daXacMinhChuKy = True
        payment.maPhanHoiCong = code
        payment.duLieuPhanHoiAnToan = {
            **existing_meta,
            **verified.safe_payload,
            "fundsCaptured": True,
            "capturedAmountVnd": str(verified.amount),
            "reconciliationRequired": True,
            "reconciliationStatus": "OPEN",
            "reason": reason,
            "orderStatusAtCallback": order.trangThai,
            "auditTrail": audit_trail,
        }
        payment.ngayCapNhat = now
        financial_event_service.record_payment_event(
            db,
            order_id=order.maDonHang,
            payment_id=payment.maThanhToan,
            event_type="CAPTURED_UNAPPLIED",
            source=expected_gateway,
            safe_data={
                "reason": reason,
                "code": code,
                "gatewayTxnId": verified.gateway_txn_id,
                "capturedAmountVnd": str(verified.amount),
                "orderStatus": order.trangThai,
            },
            idempotency_key=f"cap_unapplied:{payment.maThanhToan}:{reason}",
            now=now,
        )
        financial_event_service.enqueue_reconciliation_task(
            db,
            task_type="RETRY_CAPTURED_UNAPPLIED",
            order_id=order.maDonHang,
            payment_id=payment.maThanhToan,
            idempotency_key=f"recon:cap_unapplied:{payment.maThanhToan}",
            now=now,
        )
        db.commit()
        return PaymentCallbackResponse(
            maDonHang=order.maDonHang,
            maSoDonHang=order.maSoDonHang,
            maThanhToan=payment.maThanhToan,
            maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
            trangThaiDonHang=order.trangThai,
            trangThaiThanhToan=payment.trangThai,
            daCapQuyenHoc=(order.trangThai == "PAID"),
            soKhoaHocKichHoat=0,
            idempotentReplay=False,
            canDoiSoat=True,
            thongDiep=message,
        )

    # Case A: Second payment attempt succeeds on an already PAID order
    if order.trangThai == "PAID":
        return _record_reconciliation(
            "DUPLICATE_PAID_ATTEMPT_ON_PAID_ORDER",
            "CONFLICT_ALREADY_PAID",
            "Đơn hàng đã có giao dịch thanh toán thành công trước đó. Đã lưu bằng chứng đối soát.",
        )

    # Case B: Late callback arriving after CANCELLED or EXPIRED (or past TTL)
    if order.trangThai in {"CANCELLED", "EXPIRED"} or now >= order.hanThanhToan:
        if order.trangThai in {"PENDING", "FAILED"}:
            order.trangThai = "EXPIRED"
            order.ngayHuy = order.ngayHuy or now
            order.lyDoHuyHoacHoan = order.lyDoHuyHoacHoan or "Đơn hàng hết hạn trước khi nhận callback thanh toán."
            order.ngayCapNhat = now
        return _record_reconciliation(
            f"LATE_CALLBACK_AFTER_{order.trangThai}",
            "LATE_RECONCILIATION",
            "Callback thanh toán đến sau khi đơn hàng đã hủy hoặc hết hạn. Đã lưu bằng chứng đối soát, không tự cấp quyền học.",
        )

    # Step 3a: Verify buyer account is still ACTIVE
    buyer = db.get(NguoiDung, order.maNguoiDung)
    if buyer is None or (buyer.trangThai or "ACTIVE").upper() != "ACTIVE":
        return _record_reconciliation(
            "BUYER_ACCOUNT_LOCKED",
            "ACCOUNT_LOCKED",
            "Tài khoản người mua hiện đang bị khóa. Đã lưu bằng chứng đối soát, không tự cấp quyền học.",
        )

    # Step 3b: Lock KhoaHoc rows ASC and re-verify course visibility/approval
    course_ids = sorted({int(item.maKhoaHoc) for item in order.chiTiets or []})
    locked_courses = commerce_repository.lock_courses_ordered(db, course_ids)
    course_by_id = {int(c.maKhoaHoc): c for c in locked_courses}
    for item in order.chiTiets or []:
        c = course_by_id.get(int(item.maKhoaHoc))
        if c is None or c.trangThaiDuyet != "APPROVED" or c.trangThaiHienThi != "VISIBLE":
            return _record_reconciliation(
                "COURSE_UNAVAILABLE_AT_ACTIVATION",
                "COURSE_UNAVAILABLE",
                f"Khóa học '{item.tieuDeSnapshot}' không còn khả dụng. Đã lưu bằng chứng đối soát.",
            )

    # Step 3c: Lock per-(user, course) in ASC order and verify no ACTIVE enrollment conflict
    existing_enrollments: dict[int, DangKyKhoaHoc | None] = {}
    for cid in course_ids:
        _lock_user_course(db, order.maNguoiDung, cid)
        enr = commerce_repository.get_enrollment_for_update(db, order.maNguoiDung, cid)
        if enr is not None and enr.trangThaiQuyenHoc == "ACTIVE":
            return _record_reconciliation(
                "CONFLICT_ALREADY_OWNED_ACTIVE",
                "ALREADY_OWNED",
                "Người dùng đã sở hữu quyền học ACTIVE cho khóa học trong đơn. Không ghi đè quyền học hiện có; đã lưu đối soát.",
            )
        existing_enrollments[cid] = enr

    # Steps 4–10: Single atomic transaction (Payment PAID -> Order PAID -> Enrollments -> Cart prune -> Notification -> Commit)
    activated_count = 0
    try:
        existing_meta = dict(payment.duLieuPhanHoiAnToan) if isinstance(payment.duLieuPhanHoiAnToan, dict) else {}
        payment.trangThai = "PAID"
        payment.daThuTien = True
        payment.soTienDaThuThucTe = Decimal(verified.amount)
        payment.maGiaoDichCong = verified.gateway_txn_id
        payment.daXacMinhChuKy = True
        payment.maPhanHoiCong = verified.response_code
        payment.duLieuPhanHoiAnToan = {**existing_meta, **verified.safe_payload}
        payment.ngayThanhToan = now
        payment.ngayCapNhat = now

        order.trangThai = "PAID"
        order.ngayThanhToan = now
        order.ngayCapNhat = now
        db.flush()

        # Optional test hook to prove full transaction rollback on mid-flight error
        if _post_payment_hook is not None:
            _post_payment_hook()

        for cid in course_ids:
            enr = existing_enrollments[cid]
            if enr is not None and enr.trangThaiQuyenHoc == "REVOKED":
                # Reactivate REVOKED enrollment while strictly preserving tienDo and LichSuHocTap
                enr.trangThaiQuyenHoc = "ACTIVE"
                enr.maDonHang = order.maDonHang
                enr.nguonCapQuyen = "PURCHASE"
                enr.ngayThuHoi = None
                enr.lyDoThuHoi = None
            else:
                db.add(
                    DangKyKhoaHoc(
                        maNguoiDung=order.maNguoiDung,
                        maKhoaHoc=cid,
                        ngayDangKy=now,
                        tienDo=Decimal("0"),
                        maDonHang=order.maDonHang,
                        nguonCapQuyen="PURCHASE",
                        trangThaiQuyenHoc="ACTIVE",
                    )
                )
            activated_count += 1

        # Remove ONLY the purchased courses from user's cart
        commerce_repository.delete_cart_items_by_course_ids(
            db, order.maNguoiDung, course_ids
        )

        # Step 9: Idempotent in-app notification (GĐ4.7A HARDEN-05: accurate gateway label)
        gw_label = "mô phỏng" if verified.is_simulated else "VNPay Sandbox"
        notification_service.create_notification_idempotent(
            db,
            recipient_user_id=order.maNguoiDung,
            notification_type="ORDER_PAID",
            title=f"Thanh toán thành công đơn {order.maSoDonHang}",
            body=(
                f"Giao dịch {gw_label} {order.tongTien:,.0f} VND đã được xác nhận. "
                f"Bạn đã được cấp quyền học cho {activated_count} khóa học."
            ),
            event_key=f"order_paid:{order.maDonHang}",
            payload={
                "maDonHang": order.maDonHang,
                "maSoDonHang": order.maSoDonHang,
                "courseIds": course_ids,
                "isSimulated": bool(verified.is_simulated),
            },
            now=now,
        )

        financial_event_service.record_payment_event(
            db,
            order_id=order.maDonHang,
            payment_id=payment.maThanhToan,
            event_type="ENTITLEMENT_ACTIVATED",
            source=expected_gateway,
            safe_data={
                "gatewayTxnId": verified.gateway_txn_id,
                "capturedAmountVnd": str(verified.amount),
                "activatedCount": activated_count,
                "courseIds": course_ids,
            },
            idempotency_key=f"activated:{order.maDonHang}:{payment.maThanhToan}",
            now=now,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return PaymentCallbackResponse(
        maDonHang=order.maDonHang,
        maSoDonHang=order.maSoDonHang,
        maThanhToan=payment.maThanhToan,
        maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
        trangThaiDonHang=order.trangThai,
        trangThaiThanhToan=payment.trangThai,
        daCapQuyenHoc=True,
        soKhoaHocKichHoat=activated_count,
        idempotentReplay=False,
        canDoiSoat=False,
        thongDiep=(
            "Thanh toán mô phỏng thành công và đã cấp quyền học nguyên tử."
            if verified.is_simulated
            else "Thanh toán VNPay Sandbox thành công và đã cấp quyền học nguyên tử."
        ),
    )


def process_mock_payment_callback(
    db: Session,
    payload: MockPaymentCallbackRequest,
    *,
    _post_payment_hook=None,
) -> PaymentCallbackResponse:
    """Process server-signed Mock Payment Sandbox callback atomically."""
    _assert_mock_payment_allowed(db)
    provider = get_payment_provider("MOCK_SANDBOX")
    try:
        verified = provider.verify_callback(payload.model_dump())
    except PaymentSignatureError as exc:
        raise CommerceForbiddenError(str(exc)) from exc
    except PaymentProviderError as exc:
        raise CommerceBadRequestError(str(exc)) from exc
    return _apply_verified_callback(
        db, verified, expected_gateway="MOCK_SANDBOX", _post_payment_hook=_post_payment_hook
    )


# ---------------------------------------------------------------------------
# 5b. GĐ4.5 VNPay Sandbox IPN (Authoritative) & Return URL (Read-Only)
# ---------------------------------------------------------------------------
def process_vnpay_ipn(
    db: Session,
    query_params: dict[str, str],
    *,
    _post_payment_hook=None,
) -> VNPayIpnResponse:
    """Official VNPay v2.1.0 IPN handler returning standard RspCode/Message JSON."""
    try:
        _assert_vnpay_sandbox_allowed(db)
    except CommerceForbiddenError:
        return VNPayIpnResponse(RspCode="99", Message="VNPay sandbox disabled")

    provider = get_payment_provider("VNPAY_SANDBOX")
    try:
        verified = provider.verify_callback(query_params)
    except PaymentSignatureError:
        return VNPayIpnResponse(RspCode="97", Message="Invalid signature")
    except PaymentProviderError:
        return VNPayIpnResponse(RspCode="99", Message="Invalid request parameters")

    try:
        res = _apply_verified_callback(
            db, verified, expected_gateway="VNPAY_SANDBOX", _post_payment_hook=_post_payment_hook
        )
    except CommerceNotFoundError:
        return VNPayIpnResponse(RspCode="01", Message="Order not found")
    except CommerceBadRequestError as exc:
        msg = str(exc).lower()
        if "số tiền" in msg or "tiền tệ" in msg or "amount" in msg:
            return VNPayIpnResponse(RspCode="04", Message="Invalid amount")
        return VNPayIpnResponse(RspCode="99", Message="Invalid transaction")
    except Exception:
        return VNPayIpnResponse(RspCode="99", Message="Unknown error")

    if res.idempotentReplay:
        return VNPayIpnResponse(RspCode="02", Message="Order already confirmed")
    return VNPayIpnResponse(RspCode="00", Message="Confirm Success")


def verify_vnpay_return_readonly(
    db: Session,
    user: NguoiDung,
    query_params: dict[str, str],
) -> VNPayReturnVerifyResponse:
    """Read-only Return URL verification for Frontend UX.
    STRICTLY NEVER modifies DonHang, ThanhToan, or DangKyKhoaHoc!
    """
    _assert_active_learner(user)
    _assert_vnpay_sandbox_allowed(db)
    provider = get_payment_provider("VNPAY_SANDBOX")
    try:
        verified = provider.verify_callback(query_params)
    except PaymentSignatureError:
        return VNPayReturnVerifyResponse(
            signatureValid=False,
            thongDiep="Chữ ký trên URL trả về từ VNPay không hợp lệ (có dấu hiệu bị thay đổi).",
        )
    except PaymentProviderError as exc:
        return VNPayReturnVerifyResponse(
            signatureValid=False,
            thongDiep=str(exc),
        )

    payment = commerce_repository.get_payment_by_internal_ref(
        db, verified.internal_txn_ref, for_update=False
    )
    if payment is None or int(payment.maNguoiDung) != int(user.maNguoiDung):
        return VNPayReturnVerifyResponse(
            signatureValid=True,
            maGiaoDichNoiBo=verified.internal_txn_ref,
            vnpResponseCode=verified.response_code,
            thongDiep="Không tìm thấy giao dịch thuộc tài khoản của bạn.",
        )

    order = commerce_repository.get_order_by_id(db, int(payment.maDonHang), for_update=False)
    return VNPayReturnVerifyResponse(
        signatureValid=True,
        maDonHang=payment.maDonHang,
        maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
        vnpResponseCode=verified.response_code,
        trangThaiDonHangHienTai=order.trangThai if order else None,
        thongDiep=(
            "Đã xác minh chữ ký URL trả về. Trạng thái chính thức luôn được lấy từ hệ thống Backend (IPN)."
        ),
    )


# ---------------------------------------------------------------------------
# 6. Server-Signed Mock Sandbox Simulator (Test-DB Allowlisted, Owner-Scoped)
# ---------------------------------------------------------------------------
def get_mock_payment_session_detail(
    db: Session, user: NguoiDung, internal_txn_ref: str
) -> MockPaymentSessionDetailResponse:
    _assert_active_learner(user)
    _assert_mock_payment_allowed(db)
    payment = commerce_repository.get_payment_by_internal_ref(
        db, internal_txn_ref.strip(), for_update=False
    )
    if payment is None or int(payment.maNguoiDung) != int(user.maNguoiDung):
        raise CommerceNotFoundError("Không tìm thấy phiên giao dịch thanh toán mô phỏng.")
    order = commerce_repository.get_order_by_id(db, int(payment.maDonHang), for_update=True)
    if order is None or int(order.maNguoiDung) != int(user.maNguoiDung):
        raise CommerceNotFoundError("Không tìm thấy đơn hàng liên kết.")
    now = _utc_now()
    if _expire_order_if_past_ttl(order, now):
        db.commit()
    db.refresh(payment)
    sorted_items = sorted(order.chiTiets or [], key=lambda x: x.maChiTietDonHang)
    return MockPaymentSessionDetailResponse(
        maThanhToan=payment.maThanhToan,
        maDonHang=order.maDonHang,
        maSoDonHang=order.maSoDonHang,
        maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
        soTien=Decimal(payment.soTien),
        donViTienTe=payment.donViTienTe,
        trangThaiThanhToan=payment.trangThai,
        trangThaiDonHang=order.trangThai,
        hanThanhToan=order.hanThanhToan,
        daHetHan=(order.trangThai == "EXPIRED" or now >= order.hanThanhToan),
        laThanhToanMoPhong=True,
        items=[
            OrderItemResponse(
                maChiTietDonHang=item.maChiTietDonHang,
                maKhoaHoc=item.maKhoaHoc,
                maNhaCungCap=item.maNhaCungCap,
                tieuDeSnapshot=item.tieuDeSnapshot,
                giaTaiThoiDiemMua=Decimal(item.giaTaiThoiDiemMua),
                donViTienTe=order.donViTienTe,
                ngayTao=item.ngayTao,
            )
            for item in sorted_items
        ],
    )


def simulate_mock_payment_outcome(
    db: Session,
    user: NguoiDung,
    internal_txn_ref: str,
    payload: MockPaymentSimulateRequest,
) -> PaymentCallbackResponse:
    """Test-only simulator: verifies ownership on server, computes HMAC on server,
    and delegates strictly through process_mock_payment_callback. Never exposes secrets to Frontend.
    """
    _assert_active_learner(user)
    _assert_mock_payment_allowed(db)
    payment = commerce_repository.get_payment_by_internal_ref(
        db, internal_txn_ref.strip(), for_update=False
    )
    if payment is None or int(payment.maNguoiDung) != int(user.maNguoiDung):
        raise CommerceNotFoundError("Không tìm thấy phiên giao dịch thanh toán mô phỏng.")
    if payment.congThanhToan != "MOCK_SANDBOX":
        raise CommerceBadRequestError("Giao dịch này không sử dụng cổng thanh toán mô phỏng.")

    gw_txn_id = f"MOCK-SIM-{uuid.uuid4().hex[:10].upper()}"
    amount = Decimal(payment.soTien)
    sig = compute_mock_callback_signature(
        internal_txn_ref=payment.maGiaoDichNoiBo,
        order_id=int(payment.maDonHang),
        amount=amount,
        currency=payment.donViTienTe,
        outcome=payload.ketQua,
        gateway_txn_id=gw_txn_id,
    )
    cb_req = MockPaymentCallbackRequest(
        maGiaoDichNoiBo=payment.maGiaoDichNoiBo,
        maGiaoDichCong=gw_txn_id,
        maDonHang=int(payment.maDonHang),
        soTien=amount,
        donViTienTe=payment.donViTienTe,
        ketQua=payload.ketQua,
        signature=sig,
    )
    return process_mock_payment_callback(db, cb_req)
