"""GĐ4.6 ADMIN Commerce Management, Reconciliation, Exception Refunds, Incident Reports & PROVIDER Sales.

Zero new database migrations: persists auditable reconciliation/refund/incident ledgers
atomically inside row-locked PostgreSQL ThanhToan.duLieuPhanHoiAnToan (JSONB) + ThongBao.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models import (
    BaoCaoSuCoThanhToan,
    ChiTietDonHang,
    DangKyKhoaHoc,
    DonHang,
    HoanTienNgoaiLe,
    KhoaHoc,
    LanThuHoanTien,
    NguoiDung,
    NhaCungCapKhoaHoc,
    ThanhToan,
)
from repository import commerce_repository
from schemas.commerce import OrderResponse
from schemas.commerce_admin import (
    AdminCommerceOverviewResponse,
    AdminExceptionRefundCreateRequest,
    AdminOrderListResponse,
    AdminOrderSummaryItem,
    AdminReconciliationActivateRequest,
    AdminRefundExecuteRequest,
    AdminRefundReconcileUnknownRequest,
    AdminRefundVerifyRequest,
    AdminRevenueDashboardResponse,
    AdminTransactionItem,
    ExceptionRefundRecordResponse,
    PaymentIncidentReportRequest,
    PaymentIncidentReportResponse,
    ProviderSaleItemResponse,
    ProviderSalesSummaryResponse,
    RevenuePointResponse,
    TopCourseRevenueResponse,
)
from service import financial_event_service, notification_service, order_payment_service
from service.commerce_service import (
    CommerceBadRequestError,
    CommerceConflictError,
    CommerceForbiddenError,
    CommerceNotFoundError,
    _assert_active_learner,
    _lock_user_course,
)
from service.order_payment_service import (
    _assert_mock_payment_allowed,
    _assert_vnpay_sandbox_allowed,
    _to_order_response,
)


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _safe_meta(payment: ThanhToan) -> dict:
    return dict(payment.duLieuPhanHoiAnToan) if isinstance(payment.duLieuPhanHoiAnToan, dict) else {}


def _is_funds_captured(payment: ThanhToan) -> bool:
    meta = _safe_meta(payment)
    return (
        bool(getattr(payment, "daThuTien", False))
        or payment.trangThai in {"PAID", "REFUNDED", "CAPTURED_UNAPPLIED", "PARTIALLY_REFUNDED"}
        or bool(meta.get("fundsCaptured", False))
    )


def _captured_amount(payment: ThanhToan) -> Decimal:
    if not _is_funds_captured(payment):
        return Decimal("0")
    col_amt = getattr(payment, "soTienDaThuThucTe", None)
    if col_amt is not None and Decimal(col_amt) > 0:
        return Decimal(col_amt)
    meta = _safe_meta(payment)
    raw = meta.get("capturedAmountVnd")
    if raw is not None:
        return Decimal(str(raw))
    return Decimal(payment.soTien)


def _is_reconciliation_open(payment: ThanhToan) -> bool:
    meta = _safe_meta(payment)
    if not meta.get("reconciliationRequired"):
        return False
    return str(meta.get("reconciliationStatus") or "OPEN").upper() == "OPEN"


def _refund_record(payment: ThanhToan) -> dict | None:
    meta = _safe_meta(payment)
    rec = meta.get("exceptionRefund")
    return dict(rec) if isinstance(rec, dict) else None


def _to_refund_response(rec: dict) -> ExceptionRefundRecordResponse:
    return ExceptionRefundRecordResponse(
        refundId=str(rec["refundId"]),
        idempotencyKey=str(rec["idempotencyKey"]),
        maDonHang=int(rec["maDonHang"]),
        maSoDonHang=str(rec["maSoDonHang"]),
        maThanhToan=int(rec["maThanhToan"]),
        congThanhToan=str(rec["congThanhToan"]),
        soTienDaThu=Decimal(str(rec["soTienDaThu"])),
        soTienHoan=Decimal(str(rec["soTienHoan"])),
        donViTienTe=str(rec.get("donViTienTe", "VND")),
        phamViHoan=str(rec["phamViHoan"]),
        loaiSuCo=str(rec["loaiSuCo"]),
        lyDo=str(rec["lyDo"]),
        trangThai=str(rec["trangThai"]),
        maGiaoDichHoanCong=rec.get("maGiaoDichHoanCong"),
        maNguoiXuLy=rec.get("maNguoiXuLy"),
        ngayCapNhat=str(rec["ngayCapNhat"]),
        lichSuTrangThai=list(rec.get("lichSuTrangThai") or []),
    )


# ---------------------------------------------------------------------------
# 1. USER Payment Incident Report (Owner-Scoped, No General Refund Button)
# ---------------------------------------------------------------------------
def report_payment_incident(
    db: Session,
    user: NguoiDung,
    order_id: int,
    payload: PaymentIncidentReportRequest,
) -> PaymentIncidentReportResponse:
    _assert_active_learner(user)
    order = commerce_repository.get_order_by_id(db, order_id, for_update=True)
    if order is None or int(order.maNguoiDung) != int(user.maNguoiDung):
        raise CommerceNotFoundError("Không tìm thấy đơn hàng của bạn.")

    payments = sorted(
        order.thanhToans or [],
        key=lambda p: (p.ngayTao, p.maThanhToan),
        reverse=True,
    )
    if not payments:
        raise CommerceBadRequestError(
            "Đơn hàng chưa có giao dịch thanh toán nào để báo cáo sự cố."
        )

    target_payment = commerce_repository.get_payment_by_internal_ref(
        db, payments[0].maGiaoDichNoiBo, for_update=True
    )
    assert target_payment is not None
    now = _utc_now()
    incident_id = f"INC-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    incident = {
        "maSuCo": incident_id,
        "maDonHang": order.maDonHang,
        "maSoDonHang": order.maSoDonHang,
        "maThanhToan": target_payment.maThanhToan,
        "maNguoiBaoCao": user.maNguoiDung,
        "loaiSuCo": payload.loaiSuCo,
        "moTa": payload.moTa.strip(),
        "trangThai": "OPEN",
        "ngayBaoCao": now.isoformat(),
    }

    meta = _safe_meta(target_payment)
    incidents = list(meta.get("incidentReports") or [])
    incidents.append(incident)
    audit = list(meta.get("auditTrail") or [])
    audit.append(
        {
            "at": now.isoformat(),
            "action": "USER_INCIDENT_REPORTED",
            "incidentId": incident_id,
            "loaiSuCo": payload.loaiSuCo,
            "userId": user.maNguoiDung,
        }
    )
    meta["incidentReports"] = incidents
    meta["reconciliationRequired"] = True
    if not meta.get("reconciliationStatus") or meta.get("reconciliationStatus") == "DISMISSED":
        meta["reconciliationStatus"] = "OPEN"
    meta["auditTrail"] = audit
    target_payment.duLieuPhanHoiAnToan = meta
    target_payment.ngayCapNhat = now

    # GĐ4.7A.2: Persist normalized BaoCaoSuCoThanhToan + append-only SuKienThanhToan
    db.add(
        BaoCaoSuCoThanhToan(
            maSoSuCo=incident_id,
            maDonHang=order.maDonHang,
            maThanhToan=target_payment.maThanhToan,
            maNguoiBaoCao=user.maNguoiDung,
            loaiSuCo=payload.loaiSuCo,
            moTa=payload.moTa.strip(),
            trangThai="OPEN",
            ngayBaoCao=now,
            ngayCapNhat=now,
        )
    )
    financial_event_service.record_payment_event(
        db,
        order_id=order.maDonHang,
        payment_id=target_payment.maThanhToan,
        event_type="USER_INCIDENT_REPORTED",
        source="USER_UI",
        safe_data={"maSuCo": incident_id, "loaiSuCo": payload.loaiSuCo, "userId": user.maNguoiDung},
        idempotency_key=f"inc:{incident_id}",
        now=now,
    )
    db.commit()

    return PaymentIncidentReportResponse(**incident)


def list_user_order_incidents(
    db: Session,
    user: NguoiDung,
    order_id: int,
) -> list[PaymentIncidentReportResponse]:
    """USER tracks status of their own submitted payment incident reports (owner-scoped)."""
    _assert_active_learner(user)
    order = commerce_repository.get_order_by_id(db, order_id, for_update=False)
    if order is None or int(order.maNguoiDung) != int(user.maNguoiDung):
        raise CommerceNotFoundError("Không tìm thấy đơn hàng của bạn.")
    rows = list(
        db.scalars(
            select(BaoCaoSuCoThanhToan)
            .where(
                BaoCaoSuCoThanhToan.maDonHang == order.maDonHang,
                BaoCaoSuCoThanhToan.maNguoiBaoCao == user.maNguoiDung,
            )
            .order_by(BaoCaoSuCoThanhToan.ngayBaoCao.desc())
        ).all()
    )
    return [
        PaymentIncidentReportResponse(
            maSuCo=r.maSoSuCo,
            maDonHang=r.maDonHang,
            maSoDonHang=order.maSoDonHang,
            maThanhToan=r.maThanhToan,
            maNguoiBaoCao=r.maNguoiBaoCao,
            loaiSuCo=r.loaiSuCo,
            moTa=r.moTa,
            trangThai=r.trangThai,
            ngayBaoCao=r.ngayBaoCao.isoformat(),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 2. ADMIN Commerce Overview, Orders, Transactions, Reconciliation & Incidents
# ---------------------------------------------------------------------------
def _load_all_orders_and_payments(db: Session) -> tuple[list[DonHang], list[ThanhToan]]:
    orders = list(
        db.scalars(
            select(DonHang)
            .options(
                joinedload(DonHang.chiTiets),
                joinedload(DonHang.thanhToans),
                joinedload(DonHang.nguoiDung),
            )
            .order_by(DonHang.ngayTao.desc(), DonHang.maDonHang.desc())
        )
        .unique()
        .all()
    )
    payments = list(
        db.scalars(
            select(ThanhToan)
            .options(joinedload(ThanhToan.donHang))
            .order_by(ThanhToan.ngayTao.desc(), ThanhToan.maThanhToan.desc())
        )
        .unique()
        .all()
    )
    return orders, payments


def _compute_revenue_metrics(
    orders: list[DonHang], payments: list[ThanhToan]
) -> dict:
    """Financial invariant:
    - Recognized Gross Revenue = sum(DonHang.tongTien) for orders with trangThai in ('PAID', 'REFUNDED').
      (LEGACY enrollments have no DonHang -> NEVER counted in revenue!)
    - Incident Refunded Revenue = sum(DonHang.tongTien) for orders with trangThai == 'REFUNDED'
      (FULL_ORDER refunds). Excess duplicate payments were NEVER counted in Gross Revenue,
      so refunding an EXCESS_PAYMENT NEVER subtracts from Gross Sales!
    - Net Valid Revenue = Gross - Incident Refunded (= sum(tongTien) of PAID orders).
    """
    gross_recognized = Decimal("0")
    incident_refunded = Decimal("0")
    excess_pending_refund = Decimal("0")
    pending_refund_amount = Decimal("0")
    confirmed_refunded_total = Decimal("0")
    paid_order_count = 0
    total_sold_items = 0

    gateway_breakdown: dict[str, dict] = {}
    daily_map: dict[str, dict] = defaultdict(
        lambda: {
            "gross": Decimal("0"),
            "refunded": Decimal("0"),
            "orders": 0,
        }
    )
    course_map: dict[int, dict] = {}

    for order in orders:
        if order.trangThai not in {"PAID", "REFUNDED"}:
            continue
        order_amt = Decimal(order.tongTien)
        gross_recognized += order_amt
        day_key = (order.ngayThanhToan or order.ngayTao).strftime("%Y-%m-%d")
        daily_map[day_key]["gross"] += order_amt

        if order.trangThai == "PAID":
            paid_order_count += 1
            total_sold_items += len(order.chiTiets or [])
            daily_map[day_key]["orders"] += 1
        elif order.trangThai == "REFUNDED":
            incident_refunded += order_amt
            daily_map[day_key]["refunded"] += order_amt

        for item in order.chiTiets or []:
            cid = int(item.maKhoaHoc)
            entry = course_map.setdefault(
                cid,
                {
                    "maKhoaHoc": cid,
                    "tieuDe": item.tieuDeSnapshot,
                    "soLuotBan": 0,
                    "gross": Decimal("0"),
                    "net": Decimal("0"),
                },
            )
            item_price = Decimal(item.giaTaiThoiDiemMua)
            entry["gross"] += item_price
            if order.trangThai == "PAID":
                entry["soLuotBan"] += 1
                entry["net"] += item_price

        # Attribute gateway from primary PAID/REFUNDED payment
        primary_pay = next(
            (p for p in (order.thanhToans or []) if p.trangThai in {"PAID", "REFUNDED"}),
            None,
        )
        gw = primary_pay.congThanhToan if primary_pay else "UNKNOWN"
        gw_stat = gateway_breakdown.setdefault(
            gw,
            {"soDon": 0, "doanhThuGhiNhan": Decimal("0"), "doanhThuThuan": Decimal("0")},
        )
        gw_stat["soDon"] += 1
        gw_stat["doanhThuGhiNhan"] += order_amt
        if order.trangThai == "PAID":
            gw_stat["doanhThuThuan"] += order_amt

    reconciliation_open_cnt = 0
    unknown_cnt = 0
    unresolved_incidents_cnt = 0

    for p in payments:
        meta = _safe_meta(p)
        if _is_reconciliation_open(p):
            reconciliation_open_cnt += 1
        if p.trangThai == "PENDING":
            unknown_cnt += 1

        for inc in meta.get("incidentReports") or []:
            if str(inc.get("trangThai") or "OPEN").upper() == "OPEN":
                unresolved_incidents_cnt += 1

        ref = _refund_record(p)
        if ref:
            st = str(ref.get("trangThai") or "")
            amt = Decimal(str(ref.get("soTienHoan") or "0"))
            if st in {"PENDING_REVIEW", "VERIFIED", "REFUND_PENDING", "UNKNOWN"}:
                pending_refund_amount += amt
            if st == "UNKNOWN":
                unknown_cnt += 1
            if st == "REFUNDED":
                confirmed_refunded_total += amt
        elif p.trangThai != "PAID" and _is_funds_captured(p) and _is_reconciliation_open(p):
            # Captured excess/late funds not yet refunded
            excess_pending_refund += _captured_amount(p)

    net_valid = gross_recognized - incident_refunded
    aov = (
        (net_valid / Decimal(paid_order_count)).quantize(Decimal("1"))
        if paid_order_count > 0
        else Decimal("0")
    )

    return {
        "gross_recognized": gross_recognized,
        "incident_refunded": incident_refunded,
        "net_valid": net_valid,
        "excess_pending_refund": excess_pending_refund,
        "pending_refund_amount": pending_refund_amount,
        "confirmed_refunded_total": confirmed_refunded_total,
        "paid_order_count": paid_order_count,
        "total_sold_items": total_sold_items,
        "aov": aov,
        "reconciliation_open_cnt": reconciliation_open_cnt,
        "unknown_cnt": unknown_cnt,
        "unresolved_incidents_cnt": unresolved_incidents_cnt,
        "gateway_breakdown": {
            gw: {
                "soDon": v["soDon"],
                "doanhThuGhiNhan": str(v["doanhThuGhiNhan"]),
                "doanhThuThuan": str(v["doanhThuThuan"]),
            }
            for gw, v in gateway_breakdown.items()
        },
        "daily_series": [
            RevenuePointResponse(
                ngay=day,
                doanhThuGhiNhan=vals["gross"],
                hoanTienSuCo=vals["refunded"],
                doanhThuThuan=vals["gross"] - vals["refunded"],
                soDonThanhCong=vals["orders"],
            )
            for day, vals in sorted(daily_map.items())[-30:]
        ],
        "top_courses": [
            TopCourseRevenueResponse(
                maKhoaHoc=c["maKhoaHoc"],
                tieuDe=c["tieuDe"],
                soLuotBan=c["soLuotBan"],
                doanhThuGhiNhan=c["gross"],
                doanhThuThuan=c["net"],
            )
            for c in sorted(course_map.values(), key=lambda x: x["net"], reverse=True)[:10]
        ],
    }


def admin_commerce_overview(db: Session) -> AdminCommerceOverviewResponse:
    orders, payments = _load_all_orders_and_payments(db)
    m = _compute_revenue_metrics(orders, payments)
    return AdminCommerceOverviewResponse(
        donThanhCong=sum(1 for o in orders if o.trangThai == "PAID"),
        donChuaHoanTat=sum(1 for o in orders if o.trangThai in {"PENDING", "FAILED"}),
        donHuyHoacHetHan=sum(1 for o in orders if o.trangThai in {"CANCELLED", "EXPIRED"}),
        donHoanTien=sum(1 for o in orders if o.trangThai == "REFUNDED"),
        giaoDichCanDoiSoat=m["reconciliation_open_cnt"],
        giaoDichChuaXacDinh=m["unknown_cnt"],
        suCoChuaXuLy=m["unresolved_incidents_cnt"],
        tienThuDuChoHoan=m["excess_pending_refund"],
        tienDangChoHoan=m["pending_refund_amount"],
        tienDaHoanXacNhan=m["confirmed_refunded_total"],
        doanhThuGhiNhan=m["gross_recognized"],
        hoanTienSuCo=m["incident_refunded"],
        doanhThuThuanHopLe=m["net_valid"],
        giaTriDonTrungBinh=m["aov"],
        donViTienTe="VND",
        phanBoCongThanhToan=m["gateway_breakdown"],
    )


def admin_revenue_dashboard(db: Session) -> AdminRevenueDashboardResponse:
    orders, payments = _load_all_orders_and_payments(db)
    m = _compute_revenue_metrics(orders, payments)
    return AdminRevenueDashboardResponse(
        doanhThuGhiNhan=m["gross_recognized"],
        hoanTienSuCo=m["incident_refunded"],
        doanhThuThuanHopLe=m["net_valid"],
        tienThuDuChoXuLy=m["excess_pending_refund"],
        tongLuotBan=m["total_sold_items"],
        soDonThanhCong=m["paid_order_count"],
        giaTriDonTrungBinh=m["aov"],
        donViTienTe="VND",
        chuoiDoanhThuTheoNgay=m["daily_series"],
        topKhoaHoc=m["top_courses"],
        phanBoCongThanhToan=m["gateway_breakdown"],
        ghiChuChinhSach=(
            "Chỉ ghi nhận doanh thu từ đơn hàng thanh toán hợp lệ (không tính 150 lượt LEGACY, "
            "không tính khoản thu dư trùng lặp vào doanh thu bán hàng; chưa bật chi trả/payout)."
        ),
    )


def admin_list_orders(
    db: Session, *, page: int = 1, page_size: int = 20, status_filter: str | None = None, q: str | None = None
) -> AdminOrderListResponse:
    orders, _ = _load_all_orders_and_payments(db)
    filtered = orders
    if status_filter:
        sf = status_filter.strip().upper()
        filtered = [o for o in filtered if o.trangThai == sf]
    if q and q.strip():
        needle = q.strip().lower()
        filtered = [
            o
            for o in filtered
            if needle in (o.maSoDonHang or "").lower()
            or needle in ((o.nguoiDung.hoTen or "") if o.nguoiDung else "").lower()
            or needle in ((o.nguoiDung.tenTaiKhoan or "") if o.nguoiDung else "").lower()
        ]

    total = len(filtered)
    safe_size = max(1, min(page_size, 100))
    safe_page = max(1, page)
    total_pages = max(1, math.ceil(total / safe_size)) if total else 0
    slice_rows = filtered[(safe_page - 1) * safe_size : safe_page * safe_size]

    items: list[AdminOrderSummaryItem] = []
    for o in slice_rows:
        pays = o.thanhToans or []
        need_rec = any(_is_reconciliation_open(p) for p in pays)
        has_inc = any(bool(_safe_meta(p).get("incidentReports")) for p in pays)
        ref_status = next(
            (_refund_record(p)["trangThai"] for p in pays if _refund_record(p)), None
        )
        items.append(
            AdminOrderSummaryItem(
                maDonHang=o.maDonHang,
                maSoDonHang=o.maSoDonHang,
                maNguoiDung=o.maNguoiDung,
                tenNguoiMua=(
                    o.nguoiDung.hoTen or o.nguoiDung.tenTaiKhoan if o.nguoiDung else None
                ),
                nguonTao=o.nguonTao,
                tongTien=Decimal(o.tongTien),
                donViTienTe=o.donViTienTe,
                trangThai=o.trangThai,
                soKhoaHoc=len(o.chiTiets or []),
                canDoiSoat=need_rec,
                coSuCoNguoiDung=has_inc,
                trangThaiHoanTien=ref_status,
                hanThanhToan=o.hanThanhToan,
                ngayThanhToan=o.ngayThanhToan,
                ngayTao=o.ngayTao,
            )
        )

    return AdminOrderListResponse(
        items=items,
        total=total,
        page=safe_page,
        pageSize=safe_size,
        totalPages=total_pages,
    )


def admin_get_order_detail(db: Session, order_id: int) -> OrderResponse:
    order = commerce_repository.get_order_by_id(db, order_id, for_update=False)
    if order is None:
        raise CommerceNotFoundError("Không tìm thấy đơn hàng.")
    return _to_order_response(order)


def _to_admin_txn(p: ThanhToan) -> AdminTransactionItem:
    meta = _safe_meta(p)
    ref = _refund_record(p)
    return AdminTransactionItem(
        maThanhToan=p.maThanhToan,
        maDonHang=p.maDonHang,
        maSoDonHang=p.donHang.maSoDonHang if p.donHang else f"ORD-{p.maDonHang}",
        maNguoiDung=p.maNguoiDung,
        congThanhToan=p.congThanhToan,
        laThanhToanMoPhong=(p.congThanhToan == "MOCK_SANDBOX"),
        maGiaoDichNoiBo=p.maGiaoDichNoiBo,
        maGiaoDichCong=p.maGiaoDichCong,
        soTien=Decimal(p.soTien),
        soTienDaThuThucTe=_captured_amount(p),
        daThuTien=_is_funds_captured(p),
        donViTienTe=p.donViTienTe,
        trangThai=p.trangThai,
        maPhanHoiCong=p.maPhanHoiCong,
        daXacMinhChuKy=bool(p.daXacMinhChuKy),
        canDoiSoat=_is_reconciliation_open(p),
        trangThaiDoiSoat=meta.get("reconciliationStatus"),
        lyDoDoiSoat=meta.get("reason"),
        trangThaiHoanTien=ref.get("trangThai") if ref else None,
        ngayThanhToan=p.ngayThanhToan,
        ngayTao=p.ngayTao,
    )


def admin_list_transactions(
    db: Session, *, reconciliation_only: bool = False
) -> list[AdminTransactionItem]:
    _, payments = _load_all_orders_and_payments(db)
    if reconciliation_only:
        payments = [
            p
            for p in payments
            if _is_reconciliation_open(p)
            or _refund_record(p) is not None
            or bool(_safe_meta(p).get("incidentReports"))
        ]
    return [_to_admin_txn(p) for p in payments]


def admin_list_incidents(db: Session) -> list[PaymentIncidentReportResponse]:
    rows = list(
        db.scalars(
            select(BaoCaoSuCoThanhToan)
            .options(joinedload(BaoCaoSuCoThanhToan.donHang))
            .order_by(BaoCaoSuCoThanhToan.ngayBaoCao.desc())
        )
        .unique()
        .all()
    )
    seen_codes: set[str] = set()
    result: list[PaymentIncidentReportResponse] = []
    for r in rows:
        seen_codes.add(r.maSoSuCo)
        result.append(
            PaymentIncidentReportResponse(
                maSuCo=r.maSoSuCo,
                maDonHang=r.maDonHang,
                maSoDonHang=r.donHang.maSoDonHang if r.donHang else f"ORD-{r.maDonHang}",
                maThanhToan=r.maThanhToan,
                maNguoiBaoCao=r.maNguoiBaoCao,
                loaiSuCo=r.loaiSuCo,
                moTa=r.moTa,
                trangThai=r.trangThai,
                ngayBaoCao=r.ngayBaoCao.isoformat(),
            )
        )
    # Include any legacy JSONB-only entries not yet in BaoCaoSuCoThanhToan
    _, payments = _load_all_orders_and_payments(db)
    for p in payments:
        for inc in _safe_meta(p).get("incidentReports") or []:
            if inc.get("maSuCo") not in seen_codes:
                result.append(PaymentIncidentReportResponse(**inc))
    result.sort(key=lambda x: x.ngayBaoCao, reverse=True)
    return result


# ---------------------------------------------------------------------------
# 3. ADMIN Reconciliation: Priority #1 Restore Learning Entitlement if Valid
# ---------------------------------------------------------------------------
def admin_resolve_reconciliation_activate(
    db: Session,
    admin_user: NguoiDung,
    payment_id: int,
    payload: AdminReconciliationActivateRequest,
) -> OrderResponse:
    """Restore learning entitlement from a verified captured payment (e.g. late IPN on valid course)."""
    pay_ref = db.get(ThanhToan, payment_id)
    if pay_ref is None:
        raise CommerceNotFoundError("Không tìm thấy giao dịch thanh toán.")

    order = commerce_repository.get_order_by_id(db, int(pay_ref.maDonHang), for_update=True)
    payment = commerce_repository.get_payment_by_internal_ref(
        db, pay_ref.maGiaoDichNoiBo, for_update=True
    )
    if order is None or payment is None:
        raise CommerceNotFoundError("Không tìm thấy đơn hàng hoặc giao dịch.")

    if not _is_funds_captured(payment) or not payment.daXacMinhChuKy:
        raise CommerceConflictError(
            "Chỉ có thể khôi phục quyền học từ giao dịch đã có bằng chứng thu tiền và xác minh chữ ký."
        )
    if order.trangThai == "PAID":
        raise CommerceConflictError(
            "Đơn hàng này đã được thanh toán thành công bởi giao dịch khác; vui lòng xử lý hoàn tiền khoản thu dư."
        )
    if _refund_record(payment) and _refund_record(payment)["trangThai"] in {"REFUND_PENDING", "REFUNDED"}:
        raise CommerceConflictError("Giao dịch đã hoặc đang được hoàn tiền nên không thể kích hoạt quyền học.")

    buyer = db.get(NguoiDung, order.maNguoiDung)
    if buyer is None or (buyer.trangThai or "ACTIVE").upper() != "ACTIVE":
        raise CommerceConflictError("Tài khoản người mua đang bị khóa.")

    course_ids = sorted({int(i.maKhoaHoc) for i in order.chiTiets or []})
    locked_courses = commerce_repository.lock_courses_ordered(db, course_ids)
    course_by_id = {int(c.maKhoaHoc): c for c in locked_courses}
    for cid in course_ids:
        c = course_by_id.get(cid)
        if c is None or c.trangThaiDuyet != "APPROVED" or c.trangThaiHienThi != "VISIBLE":
            raise CommerceConflictError(
                "Một số khóa học trong đơn không còn khả dụng; vui lòng thực hiện hoàn tiền ngoại lệ thay vì cấp quyền."
            )

    existing_map: dict[int, DangKyKhoaHoc | None] = {}
    for cid in course_ids:
        _lock_user_course(db, order.maNguoiDung, cid)
        enr = commerce_repository.get_enrollment_for_update(db, order.maNguoiDung, cid)
        if enr is not None and enr.trangThaiQuyenHoc == "ACTIVE":
            raise CommerceConflictError(
                "Người dùng đã sở hữu quyền học ACTIVE cho khóa học trong đơn; vui lòng hoàn tiền khoản thu dư."
            )
        existing_map[cid] = enr

    now = _utc_now()
    meta = _safe_meta(payment)
    audit = list(meta.get("auditTrail") or [])
    audit.append(
        {
            "at": now.isoformat(),
            "action": "ADMIN_RECONCILE_ACTIVATE_ENTITLEMENT",
            "adminId": admin_user.maNguoiDung,
            "reason": payload.lyDo.strip(),
        }
    )
    meta["reconciliationStatus"] = "RESOLVED_ACTIVATED"
    meta["auditTrail"] = audit
    for inc in meta.get("incidentReports") or []:
        inc["trangThai"] = "RESOLVED"

    try:
        payment.trangThai = "PAID"
        payment.daThuTien = True
        payment.soTienDaThuThucTe = _captured_amount(payment)
        payment.ngayThanhToan = payment.ngayThanhToan or now
        payment.duLieuPhanHoiAnToan = meta
        payment.ngayCapNhat = now

        order.trangThai = "PAID"
        order.ngayThanhToan = order.ngayThanhToan or now
        order.ngayCapNhat = now
        db.flush()

        # Resolve normalized BaoCaoSuCoThanhToan rows for this payment/order
        open_incs = list(
            db.scalars(
                select(BaoCaoSuCoThanhToan).where(
                    BaoCaoSuCoThanhToan.maDonHang == order.maDonHang,
                    BaoCaoSuCoThanhToan.trangThai.in_(("OPEN", "IN_REVIEW")),
                )
            ).all()
        )
        for inc_row in open_incs:
            inc_row.trangThai = "RESOLVED"
            inc_row.maAdminPhuTrach = admin_user.maNguoiDung
            inc_row.ghiChuXuLy = payload.lyDo.strip()
            inc_row.ngayCapNhat = now

        financial_event_service.record_payment_event(
            db,
            order_id=order.maDonHang,
            payment_id=payment.maThanhToan,
            event_type="RECONCILE_ACTIVATED",
            source="ADMIN_UI",
            safe_data={"adminId": admin_user.maNguoiDung, "reason": payload.lyDo.strip()},
            idempotency_key=f"recon_act:{order.maDonHang}:{payment.maThanhToan}",
            now=now,
        )

        for cid in course_ids:
            enr = existing_map[cid]
            if enr is not None and enr.trangThaiQuyenHoc == "REVOKED":
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

        commerce_repository.delete_cart_items_by_course_ids(db, order.maNguoiDung, course_ids)
        notification_service.create_notification_idempotent(
            db,
            recipient_user_id=order.maNguoiDung,
            notification_type="RECONCILIATION_ACTIVATED",
            title=f"Đã khôi phục quyền học cho đơn {order.maSoDonHang}",
            body="Quản trị viên đã xác minh giao dịch của bạn và kích hoạt quyền học thành công.",
            event_key=f"reconcile_activate:{order.maDonHang}:{payment.maThanhToan}",
            payload={"maDonHang": order.maDonHang, "maThanhToan": payment.maThanhToan},
            now=now,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _to_order_response(order)


# ---------------------------------------------------------------------------
# 4. ADMIN Exception Refund State Machine
#    PENDING_REVIEW -> VERIFIED -> REFUND_PENDING -> REFUNDED | REFUND_FAILED | UNKNOWN
# ---------------------------------------------------------------------------
def admin_create_exception_refund(
    db: Session,
    admin_user: NguoiDung,
    payload: AdminExceptionRefundCreateRequest,
    *,
    idempotency_key: str,
) -> ExceptionRefundRecordResponse:
    clean_key = (idempotency_key or "").strip()
    if len(clean_key) < 4 or len(clean_key) > 72:
        raise CommerceBadRequestError("Header Idempotency-Key hợp lệ là bắt buộc.")

    order = commerce_repository.get_order_by_id(db, payload.maDonHang, for_update=True)
    if order is None:
        raise CommerceNotFoundError("Không tìm thấy đơn hàng.")

    pay_ref = db.get(ThanhToan, payload.maThanhToan)
    if pay_ref is None or int(pay_ref.maDonHang) != int(order.maDonHang):
        raise CommerceNotFoundError("Không tìm thấy giao dịch thuộc đơn hàng này.")

    payment = commerce_repository.get_payment_by_internal_ref(
        db, pay_ref.maGiaoDichNoiBo, for_update=True
    )
    assert payment is not None

    existing_ref = _refund_record(payment)
    if existing_ref is not None:
        if existing_ref.get("idempotencyKey") == clean_key:
            return _to_refund_response(existing_ref)
        raise CommerceConflictError(
            f"Giao dịch #{payment.maThanhToan} đã có yêu cầu hoàn tiền ngoại lệ ({existing_ref['trangThai']})."
        )

    if not _is_funds_captured(payment):
        raise CommerceConflictError(
            "Không thể tạo hoàn tiền cho giao dịch chưa có bằng chứng đã thu tiền."
        )

    captured = _captured_amount(payment)
    req_amount = Decimal(payload.soTienHoan)
    if req_amount > captured:
        raise CommerceBadRequestError(
            f"Số tiền hoàn ({req_amount} VND) không được vượt quá số tiền thực tế đã thu ({captured} VND)."
        )

    # GĐ4.7A.2: Guard total refunded + requested <= captured amount across HoanTienNgoaiLe
    already_refunded = db.scalar(
        select(func.coalesce(func.sum(HoanTienNgoaiLe.soTienHoan), 0)).where(
            HoanTienNgoaiLe.maThanhToan == payment.maThanhToan,
            HoanTienNgoaiLe.trangThai == "REFUNDED",
        )
    ) or Decimal("0")
    if Decimal(already_refunded) + req_amount > captured:
        raise CommerceBadRequestError(
            f"Tổng số tiền hoàn ({Decimal(already_refunded) + req_amount} VND) vượt quá số tiền đã thu ({captured} VND)."
        )

    if payload.phamViHoan == "PARTIAL_OVERCHARGE" and req_amount >= captured:
        raise CommerceBadRequestError(
            "Hoàn tiền một phần do thu sai số tiền (PARTIAL_OVERCHARGE) phải nhỏ hơn tổng số tiền đã thu."
        )

    now = _utc_now()
    refund_code = f"REF-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    history = [
        {
            "at": now.isoformat(),
            "from": None,
            "to": "PENDING_REVIEW",
            "actorAdminId": admin_user.maNguoiDung,
            "note": payload.lyDo.strip(),
        }
    ]
    refund_row = HoanTienNgoaiLe(
        maSoHoanTien=refund_code,
        maDonHang=order.maDonHang,
        maThanhToan=payment.maThanhToan,
        khoaChongTrung=clean_key,
        phamViHoan=payload.phamViHoan,
        loaiSuCo=payload.loaiSuCo,
        soTienDaThu=captured,
        soTienHoan=req_amount,
        donViTienTe="VND",
        trangThai="PENDING_REVIEW",
        lyDo=payload.lyDo.strip(),
        maNguoiTao=admin_user.maNguoiDung,
        maNguoiXuLy=admin_user.maNguoiDung,
        lichSuTrangThai=history,
        ngayTao=now,
        ngayCapNhat=now,
    )
    db.add(refund_row)
    db.flush()

    rec = {
        "refundId": refund_code,
        "idempotencyKey": clean_key,
        "maDonHang": order.maDonHang,
        "maSoDonHang": order.maSoDonHang,
        "maThanhToan": payment.maThanhToan,
        "congThanhToan": payment.congThanhToan,
        "soTienDaThu": str(captured),
        "soTienHoan": str(req_amount),
        "donViTienTe": "VND",
        "phamViHoan": payload.phamViHoan,
        "loaiSuCo": payload.loaiSuCo,
        "lyDo": payload.lyDo.strip(),
        "trangThai": "PENDING_REVIEW",
        "maGiaoDichHoanCong": None,
        "maNguoiXuLy": admin_user.maNguoiDung,
        "ngayCapNhat": now.isoformat(),
        "lichSuTrangThai": history,
    }
    meta = _safe_meta(payment)
    meta["exceptionRefund"] = rec
    payment.duLieuPhanHoiAnToan = meta
    payment.ngayCapNhat = now
    financial_event_service.record_payment_event(
        db,
        order_id=order.maDonHang,
        payment_id=payment.maThanhToan,
        refund_id=refund_row.maHoanTien,
        event_type="REFUND_CREATED",
        source="ADMIN_UI",
        safe_data={
            "refundId": refund_code,
            "phamViHoan": payload.phamViHoan,
            "soTienHoan": str(req_amount),
            "adminId": admin_user.maNguoiDung,
        },
        idempotency_key=f"ref_created:{clean_key}",
        now=now,
    )
    db.commit()
    return _to_refund_response(rec)


def admin_verify_exception_refund(
    db: Session,
    admin_user: NguoiDung,
    payment_id: int,
    payload: AdminRefundVerifyRequest,
) -> ExceptionRefundRecordResponse:
    pay_ref = db.get(ThanhToan, payment_id)
    if pay_ref is None:
        raise CommerceNotFoundError("Không tìm thấy giao dịch thanh toán.")
    order = commerce_repository.get_order_by_id(db, int(pay_ref.maDonHang), for_update=True)
    payment = commerce_repository.get_payment_by_internal_ref(
        db, pay_ref.maGiaoDichNoiBo, for_update=True
    )
    assert order is not None and payment is not None

    rec = _refund_record(payment)
    if rec is None:
        raise CommerceNotFoundError("Giao dịch chưa có yêu cầu hoàn tiền ngoại lệ.")
    if rec["trangThai"] != "PENDING_REVIEW":
        raise CommerceConflictError(
            f"Chỉ có thể xác minh yêu cầu đang ở trạng thái PENDING_REVIEW (hiện tại: {rec['trangThai']})."
        )

    now = _utc_now()
    rec["trangThai"] = "VERIFIED"
    rec["maNguoiXuLy"] = admin_user.maNguoiDung
    rec["ngayCapNhat"] = now.isoformat()
    rec["lichSuTrangThai"] = list(rec.get("lichSuTrangThai") or []) + [
        {
            "at": now.isoformat(),
            "from": "PENDING_REVIEW",
            "to": "VERIFIED",
            "actorAdminId": admin_user.maNguoiDung,
            "note": payload.ghiChuXacMinh.strip(),
        }
    ]
    meta = _safe_meta(payment)
    meta["exceptionRefund"] = rec
    payment.duLieuPhanHoiAnToan = meta
    payment.ngayCapNhat = now

    refund_row = db.scalars(
        select(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maSoHoanTien == rec["refundId"])
    ).first()
    if refund_row is not None:
        refund_row.trangThai = "VERIFIED"
        refund_row.ghiChuXacMinh = payload.ghiChuXacMinh.strip()
        refund_row.maNguoiXacMinh = admin_user.maNguoiDung
        refund_row.maNguoiXuLy = admin_user.maNguoiDung
        refund_row.lichSuTrangThai = rec["lichSuTrangThai"]
        refund_row.ngayCapNhat = now
        financial_event_service.record_payment_event(
            db,
            order_id=order.maDonHang,
            payment_id=payment.maThanhToan,
            refund_id=refund_row.maHoanTien,
            event_type="REFUND_VERIFIED",
            source="ADMIN_UI",
            safe_data={"refundId": rec["refundId"], "adminId": admin_user.maNguoiDung},
            idempotency_key=f"ref_verified:{rec['refundId']}",
            now=now,
        )
    db.commit()
    return _to_refund_response(rec)


def _finalize_confirmed_refund(
    db: Session,
    *,
    order: DonHang,
    payment: ThanhToan,
    rec: dict,
    gateway_refund_txn_id: str,
    actor_admin_id: int,
    evidence_note: str,
    now: datetime,
) -> None:
    """Apply confirmed REFUNDED state atomically:
    - EXCESS_PAYMENT: NEVER revokes valid enrollment, NEVER marks valid PAID order as REFUNDED.
    - FULL_ORDER: Marks DonHang & ThanhToan REFUNDED, revokes ONLY DangKyKhoaHoc linked to this maDonHang,
      strictly preserves DangKyKhoaHoc rows (no DELETE) and LichSuHocTap (no DELETE).
    """
    prev_state = rec["trangThai"]
    rec["trangThai"] = "REFUNDED"
    rec["maGiaoDichHoanCong"] = gateway_refund_txn_id
    rec["maNguoiXuLy"] = actor_admin_id
    rec["ngayCapNhat"] = now.isoformat()
    rec["lichSuTrangThai"] = list(rec.get("lichSuTrangThai") or []) + [
        {
            "at": now.isoformat(),
            "from": prev_state,
            "to": "REFUNDED",
            "actorAdminId": actor_admin_id,
            "gatewayRefundTxnId": gateway_refund_txn_id,
            "note": evidence_note,
        }
    ]

    meta = _safe_meta(payment)
    meta["exceptionRefund"] = rec
    meta["reconciliationStatus"] = "RESOLVED_REFUNDED"
    for inc in meta.get("incidentReports") or []:
        inc["trangThai"] = "RESOLVED"
    payment.duLieuPhanHoiAnToan = meta
    payment.ngayCapNhat = now

    # Sync normalized HoanTienNgoaiLe & BaoCaoSuCoThanhToan
    refund_row = db.scalars(
        select(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maSoHoanTien == rec["refundId"])
    ).first()
    if refund_row is not None:
        refund_row.trangThai = "REFUNDED"
        refund_row.maGiaoDichHoanCong = gateway_refund_txn_id
        refund_row.maNguoiXuLy = actor_admin_id
        refund_row.lichSuTrangThai = rec["lichSuTrangThai"]
        refund_row.ngayCapNhat = now
        refund_row.ngayHoanTat = now
        # Close any inflight UNKNOWN/SENT attempt row
        latest_attempt = db.scalars(
            select(LanThuHoanTien)
            .where(LanThuHoanTien.maHoanTien == refund_row.maHoanTien)
            .order_by(LanThuHoanTien.thuTuLanThu.desc())
        ).first()
        if latest_attempt is not None and latest_attempt.trangThai in {"SENT", "UNKNOWN"}:
            latest_attempt.trangThai = "SUCCEEDED"
            latest_attempt.maGiaoDichHoanCong = gateway_refund_txn_id
            latest_attempt.ngayPhanHoi = now

    open_incs = list(
        db.scalars(
            select(BaoCaoSuCoThanhToan).where(
                BaoCaoSuCoThanhToan.maDonHang == order.maDonHang,
                BaoCaoSuCoThanhToan.trangThai.in_(("OPEN", "IN_REVIEW")),
            )
        ).all()
    )
    for inc_row in open_incs:
        inc_row.trangThai = "RESOLVED"
        inc_row.maAdminPhuTrach = actor_admin_id
        inc_row.ghiChuXuLy = evidence_note
        inc_row.ngayCapNhat = now

    if rec["phamViHoan"] == "PARTIAL_OVERCHARGE":
        # Partial overcharge refund: keep PAID order & ACTIVE enrollment untouched!
        payment.trangThai = "PARTIALLY_REFUNDED"
    elif rec["phamViHoan"] == "FULL_ORDER":
        payment.trangThai = "REFUNDED"
        order.trangThai = "REFUNDED"
        order.ngayHoanTien = now
        order.lyDoHuyHoacHoan = rec["lyDo"]
        order.ngayCapNhat = now

        # Revoke ONLY enrollments granted specifically by THIS order (never LEGACY/FREE/other orders!)
        course_ids = sorted({int(i.maKhoaHoc) for i in order.chiTiets or []})
        for cid in course_ids:
            _lock_user_course(db, order.maNguoiDung, cid)
            enr = commerce_repository.get_enrollment_for_update(db, order.maNguoiDung, cid)
            if (
                enr is not None
                and enr.maDonHang == order.maDonHang
                and enr.nguonCapQuyen == "PURCHASE"
                and enr.trangThaiQuyenHoc == "ACTIVE"
            ):
                enr.trangThaiQuyenHoc = "REVOKED"
                enr.ngayThuHoi = now
                enr.lyDoThuHoi = f"Thu hồi do hoàn tiền ngoại lệ ({rec['refundId']})"

    notification_service.create_notification_idempotent(
        db,
        recipient_user_id=order.maNguoiDung,
        notification_type="EXCEPTION_REFUND_CONFIRMED",
        title=f"Hoàn tiền ngoại lệ thành công ({order.maSoDonHang})",
        body=(
            f"Khoản hoàn {Decimal(str(rec['soTienHoan'])):,.0f} VND đã được xác nhận "
            f"(mã hoàn: {gateway_refund_txn_id})."
        ),
        event_key=f"exception_refund:{rec['refundId']}",
        payload={
            "maDonHang": order.maDonHang,
            "refundId": rec["refundId"],
            "phamViHoan": rec["phamViHoan"],
        },
        now=now,
    )


def admin_execute_exception_refund(
    db: Session,
    admin_user: NguoiDung,
    payment_id: int,
    payload: AdminRefundExecuteRequest,
) -> ExceptionRefundRecordResponse:
    pay_ref = db.get(ThanhToan, payment_id)
    if pay_ref is None:
        raise CommerceNotFoundError("Không tìm thấy giao dịch thanh toán.")

    order = commerce_repository.get_order_by_id(db, int(pay_ref.maDonHang), for_update=True)
    payment = commerce_repository.get_payment_by_internal_ref(
        db, pay_ref.maGiaoDichNoiBo, for_update=True
    )
    assert order is not None and payment is not None

    rec = _refund_record(payment)
    if rec is None:
        raise CommerceNotFoundError("Giao dịch chưa có yêu cầu hoàn tiền ngoại lệ.")

    # Idempotent replay if already REFUNDED
    if rec["trangThai"] == "REFUNDED":
        return _to_refund_response(rec)

    # Strict timeout/unknown safety guard: MUST reconcile UNKNOWN before retrying!
    if rec["trangThai"] == "UNKNOWN":
        raise CommerceConflictError(
            "Giao dịch hoàn tiền đang ở trạng thái UNKNOWN (timeout). "
            "Phải đối soát kết quả với cổng thanh toán trước khi thử lại để tránh hoàn tiền trùng."
        )

    if rec["trangThai"] not in {"VERIFIED", "REFUND_FAILED"}:
        raise CommerceConflictError(
            f"Yêu cầu hoàn tiền phải ở trạng thái VERIFIED hoặc REFUND_FAILED mới được thực thi (hiện tại: {rec['trangThai']})."
        )

    if payment.congThanhToan == "VNPAY_SANDBOX":
        _assert_vnpay_sandbox_allowed(db)
        raise CommerceConflictError(
            "Hoàn tiền trực tiếp qua VNPay Sandbox API chưa được kích hoạt trong runtime do thiếu môi trường Sandbox trực tuyến; không giả lập thành công."
        )

    # MOCK_SANDBOX execution (strictly allowlisted test DB & flag)
    _assert_mock_payment_allowed(db)
    now = _utc_now()
    prev = rec["trangThai"]
    rec["trangThai"] = "REFUND_PENDING"
    rec["maNguoiXuLy"] = admin_user.maNguoiDung
    rec["ngayCapNhat"] = now.isoformat()
    rec["lichSuTrangThai"] = list(rec.get("lichSuTrangThai") or []) + [
        {
            "at": now.isoformat(),
            "from": prev,
            "to": "REFUND_PENDING",
            "actorAdminId": admin_user.maNguoiDung,
            "note": "Bắt đầu gọi cổng hoàn tiền mô phỏng (Mock Sandbox).",
        }
    ]

    if payload.mockOutcome == "UNKNOWN":
        rec["trangThai"] = "UNKNOWN"
        rec["lichSuTrangThai"].append(
            {
                "at": now.isoformat(),
                "from": "REFUND_PENDING",
                "to": "UNKNOWN",
                "actorAdminId": admin_user.maNguoiDung,
                "note": "Timeout khi chờ phản hồi từ cổng thanh toán; yêu cầu đối soát trước khi thử lại.",
            }
        )
        meta = _safe_meta(payment)
        meta["exceptionRefund"] = rec
        payment.duLieuPhanHoiAnToan = meta
        payment.ngayCapNhat = now

        refund_row = db.scalars(
            select(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maSoHoanTien == rec["refundId"])
        ).first()
        if refund_row is not None:
            refund_row.trangThai = "UNKNOWN"
            refund_row.maNguoiXuLy = admin_user.maNguoiDung
            refund_row.lichSuTrangThai = rec["lichSuTrangThai"]
            refund_row.ngayCapNhat = now
            seq = (
                db.scalar(
                    select(func.coalesce(func.max(LanThuHoanTien.thuTuLanThu), 0)).where(
                        LanThuHoanTien.maHoanTien == refund_row.maHoanTien
                    )
                )
                or 0
            ) + 1
            db.add(
                LanThuHoanTien(
                    maHoanTien=refund_row.maHoanTien,
                    thuTuLanThu=seq,
                    maYeuCauCong=f"REQ-MOCK-{refund_row.maHoanTien}-{seq}-{uuid.uuid4().hex[:6].upper()}",
                    soTienYeuCau=Decimal(str(rec["soTienHoan"])),
                    trangThai="UNKNOWN",
                    maPhanHoiCong="TIMEOUT",
                    phanHoiAnToan={"outcome": "UNKNOWN", "isSimulated": True},
                    maNguoiThucThi=admin_user.maNguoiDung,
                    ngayGui=now,
                )
            )
            financial_event_service.record_payment_event(
                db,
                order_id=order.maDonHang,
                payment_id=payment.maThanhToan,
                refund_id=refund_row.maHoanTien,
                event_type="REFUND_UNKNOWN",
                source="MOCK_SANDBOX",
                safe_data={"refundId": rec["refundId"], "attemptSeq": seq},
                now=now,
            )
            financial_event_service.enqueue_reconciliation_task(
                db,
                task_type="QUERY_UNKNOWN_REFUND",
                order_id=order.maDonHang,
                payment_id=payment.maThanhToan,
                refund_id=refund_row.maHoanTien,
                idempotency_key=f"recon:ref_unk:{refund_row.maHoanTien}:{seq}",
                now=now,
            )
        db.commit()
        return _to_refund_response(rec)

    if payload.mockOutcome == "REFUND_FAILED":
        rec["trangThai"] = "REFUND_FAILED"
        rec["lichSuTrangThai"].append(
            {
                "at": now.isoformat(),
                "from": "REFUND_PENDING",
                "to": "REFUND_FAILED",
                "actorAdminId": admin_user.maNguoiDung,
                "note": "Cổng mô phỏng từ chối yêu cầu hoàn tiền.",
            }
        )
        meta = _safe_meta(payment)
        meta["exceptionRefund"] = rec
        payment.duLieuPhanHoiAnToan = meta
        payment.ngayCapNhat = now
        refund_row = db.scalars(
            select(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maSoHoanTien == rec["refundId"])
        ).first()
        if refund_row is not None:
            refund_row.trangThai = "REFUND_FAILED"
            refund_row.maNguoiXuLy = admin_user.maNguoiDung
            refund_row.lichSuTrangThai = rec["lichSuTrangThai"]
            refund_row.ngayCapNhat = now
            seq = (
                db.scalar(
                    select(func.coalesce(func.max(LanThuHoanTien.thuTuLanThu), 0)).where(
                        LanThuHoanTien.maHoanTien == refund_row.maHoanTien
                    )
                )
                or 0
            ) + 1
            db.add(
                LanThuHoanTien(
                    maHoanTien=refund_row.maHoanTien,
                    thuTuLanThu=seq,
                    maYeuCauCong=f"REQ-MOCK-{refund_row.maHoanTien}-{seq}-{uuid.uuid4().hex[:6].upper()}",
                    soTienYeuCau=Decimal(str(rec["soTienHoan"])),
                    trangThai="FAILED",
                    maPhanHoiCong="99",
                    phanHoiAnToan={"outcome": "REFUND_FAILED", "isSimulated": True},
                    maNguoiThucThi=admin_user.maNguoiDung,
                    ngayGui=now,
                    ngayPhanHoi=now,
                )
            )
        db.commit()
        return _to_refund_response(rec)

    # Confirmed REFUNDED on Mock Sandbox
    gw_ref_id = f"MOCK-REF-{uuid.uuid4().hex[:10].upper()}"
    refund_row = db.scalars(
        select(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maSoHoanTien == rec["refundId"])
    ).first()
    if refund_row is not None:
        seq = (
            db.scalar(
                select(func.coalesce(func.max(LanThuHoanTien.thuTuLanThu), 0)).where(
                    LanThuHoanTien.maHoanTien == refund_row.maHoanTien
                )
            )
            or 0
        ) + 1
        db.add(
            LanThuHoanTien(
                maHoanTien=refund_row.maHoanTien,
                thuTuLanThu=seq,
                maYeuCauCong=f"REQ-MOCK-{refund_row.maHoanTien}-{seq}-{uuid.uuid4().hex[:6].upper()}",
                maGiaoDichHoanCong=gw_ref_id,
                soTienYeuCau=Decimal(str(rec["soTienHoan"])),
                trangThai="SUCCEEDED",
                maPhanHoiCong="00",
                phanHoiAnToan={"outcome": "REFUNDED", "isSimulated": True},
                maNguoiThucThi=admin_user.maNguoiDung,
                ngayGui=now,
                ngayPhanHoi=now,
            )
        )
        financial_event_service.record_payment_event(
            db,
            order_id=order.maDonHang,
            payment_id=payment.maThanhToan,
            refund_id=refund_row.maHoanTien,
            event_type="REFUND_CONFIRMED",
            source="MOCK_SANDBOX",
            safe_data={
                "refundId": rec["refundId"],
                "gatewayRefundTxnId": gw_ref_id,
                "soTienHoan": str(rec["soTienHoan"]),
                "phamViHoan": rec["phamViHoan"],
            },
            idempotency_key=f"ref_confirmed:{rec['refundId']}",
            now=now,
        )
    _finalize_confirmed_refund(
        db,
        order=order,
        payment=payment,
        rec=rec,
        gateway_refund_txn_id=gw_ref_id,
        actor_admin_id=admin_user.maNguoiDung,
        evidence_note="Xác nhận hoàn tiền mô phỏng (Mock Sandbox) thành công.",
        now=now,
    )
    db.commit()
    return _to_refund_response(rec)


def admin_reconcile_unknown_refund(
    db: Session,
    admin_user: NguoiDung,
    payment_id: int,
    payload: AdminRefundReconcileUnknownRequest,
) -> ExceptionRefundRecordResponse:
    pay_ref = db.get(ThanhToan, payment_id)
    if pay_ref is None:
        raise CommerceNotFoundError("Không tìm thấy giao dịch thanh toán.")
    order = commerce_repository.get_order_by_id(db, int(pay_ref.maDonHang), for_update=True)
    payment = commerce_repository.get_payment_by_internal_ref(
        db, pay_ref.maGiaoDichNoiBo, for_update=True
    )
    assert order is not None and payment is not None

    rec = _refund_record(payment)
    if rec is None or rec["trangThai"] != "UNKNOWN":
        raise CommerceConflictError("Chỉ có thể đối soát yêu cầu hoàn tiền đang ở trạng thái UNKNOWN.")

    now = _utc_now()
    if payload.ketQuaDoiSoat == "REFUNDED":
        if not payload.maGiaoDichHoanCong or not payload.maGiaoDichHoanCong.strip():
            raise CommerceBadRequestError(
                "Bắt buộc cung cấp mã giao dịch hoàn tiền từ cổng thanh toán để xác nhận REFUNDED."
            )
        _finalize_confirmed_refund(
            db,
            order=order,
            payment=payment,
            rec=rec,
            gateway_refund_txn_id=payload.maGiaoDichHoanCong.strip(),
            actor_admin_id=admin_user.maNguoiDung,
            evidence_note=payload.ghiChuBangChung.strip(),
            now=now,
        )
    else:
        rec["trangThai"] = "REFUND_FAILED"
        rec["maNguoiXuLy"] = admin_user.maNguoiDung
        rec["ngayCapNhat"] = now.isoformat()
        rec["lichSuTrangThai"] = list(rec.get("lichSuTrangThai") or []) + [
            {
                "at": now.isoformat(),
                "from": "UNKNOWN",
                "to": "REFUND_FAILED",
                "actorAdminId": admin_user.maNguoiDung,
                "note": payload.ghiChuBangChung.strip(),
            }
        ]
        meta = _safe_meta(payment)
        meta["exceptionRefund"] = rec
        payment.duLieuPhanHoiAnToan = meta
        payment.ngayCapNhat = now

        refund_row = db.scalars(
            select(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maSoHoanTien == rec["refundId"])
        ).first()
        if refund_row is not None:
            refund_row.trangThai = "REFUND_FAILED"
            refund_row.maNguoiXuLy = admin_user.maNguoiDung
            refund_row.lichSuTrangThai = rec["lichSuTrangThai"]
            refund_row.ngayCapNhat = now
            latest_attempt = db.scalars(
                select(LanThuHoanTien)
                .where(LanThuHoanTien.maHoanTien == refund_row.maHoanTien)
                .order_by(LanThuHoanTien.thuTuLanThu.desc())
            ).first()
            if latest_attempt is not None and latest_attempt.trangThai in {"SENT", "UNKNOWN"}:
                latest_attempt.trangThai = "FAILED"
                latest_attempt.ngayPhanHoi = now

    db.commit()
    return _to_refund_response(rec)


# ---------------------------------------------------------------------------
# 5. PROVIDER Sales Dashboard & History (Strictly Owner-Scoped)
# ---------------------------------------------------------------------------
def _require_provider_profile(db: Session, user: NguoiDung) -> NhaCungCapKhoaHoc:
    profile = db.scalars(
        select(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNguoiDung == user.maNguoiDung)
    ).first()
    if profile is None:
        raise CommerceForbiddenError("Tài khoản chưa được thiết lập hồ sơ Nhà cung cấp.")
    return profile


def provider_sales_summary(db: Session, user: NguoiDung) -> ProviderSalesSummaryResponse:
    provider = _require_provider_profile(db, user)
    rows = list(
        db.scalars(
            select(ChiTietDonHang)
            .join(DonHang, ChiTietDonHang.maDonHang == DonHang.maDonHang)
            .options(joinedload(ChiTietDonHang.donHang))
            .where(
                ChiTietDonHang.maNhaCungCap == provider.maNhaCungCap,
                DonHang.trangThai.in_(("PAID", "REFUNDED")),
            )
            .order_by(ChiTietDonHang.ngayTao.desc())
        )
        .unique()
        .all()
    )

    gross = Decimal("0")
    refunded = Decimal("0")
    sold_count = 0
    daily_map: dict[str, dict] = defaultdict(
        lambda: {"gross": Decimal("0"), "refunded": Decimal("0"), "orders": set()}
    )
    course_map: dict[int, dict] = {}

    for item in rows:
        order = item.donHang
        amt = Decimal(item.giaTaiThoiDiemMua)
        gross += amt
        day_key = (order.ngayThanhToan or order.ngayTao).strftime("%Y-%m-%d")
        daily_map[day_key]["gross"] += amt

        entry = course_map.setdefault(
            int(item.maKhoaHoc),
            {
                "maKhoaHoc": int(item.maKhoaHoc),
                "tieuDe": item.tieuDeSnapshot,
                "soLuotBan": 0,
                "gross": Decimal("0"),
                "net": Decimal("0"),
            },
        )
        entry["gross"] += amt

        if order.trangThai == "PAID":
            sold_count += 1
            entry["soLuotBan"] += 1
            entry["net"] += amt
            daily_map[day_key]["orders"].add(order.maDonHang)
        elif order.trangThai == "REFUNDED":
            refunded += amt
            daily_map[day_key]["refunded"] += amt

    return ProviderSalesSummaryResponse(
        maNhaCungCap=provider.maNhaCungCap,
        doanhThuGhiNhan=gross,
        hoanTienSuCo=refunded,
        doanhThuThuan=gross - refunded,
        tongLuotBan=sold_count,
        soKhoaHocCoDoanhThu=len([c for c in course_map.values() if c["soLuotBan"] > 0]),
        donViTienTe="VND",
        chuoiDoanhThuTheoNgay=[
            RevenuePointResponse(
                ngay=day,
                doanhThuGhiNhan=v["gross"],
                hoanTienSuCo=v["refunded"],
                doanhThuThuan=v["gross"] - v["refunded"],
                soDonThanhCong=len(v["orders"]),
            )
            for day, v in sorted(daily_map.items())[-30:]
        ],
        hieuQuaTheoKhoaHoc=[
            TopCourseRevenueResponse(
                maKhoaHoc=c["maKhoaHoc"],
                tieuDe=c["tieuDe"],
                soLuotBan=c["soLuotBan"],
                doanhThuGhiNhan=c["gross"],
                doanhThuThuan=c["net"],
            )
            for c in sorted(course_map.values(), key=lambda x: x["net"], reverse=True)
        ],
        ghiChuPayout="Hệ thống hiện chỉ ghi nhận doanh thu bán hàng; chưa kích hoạt chia hoa hồng hoặc chi trả tự động (payout).",
    )


def provider_sales_items(db: Session, user: NguoiDung) -> list[ProviderSaleItemResponse]:
    provider = _require_provider_profile(db, user)
    rows = list(
        db.scalars(
            select(ChiTietDonHang)
            .join(DonHang, ChiTietDonHang.maDonHang == DonHang.maDonHang)
            .options(joinedload(ChiTietDonHang.donHang))
            .where(
                ChiTietDonHang.maNhaCungCap == provider.maNhaCungCap,
                DonHang.trangThai.in_(("PAID", "REFUNDED")),
            )
            .order_by(ChiTietDonHang.ngayTao.desc(), ChiTietDonHang.maChiTietDonHang.desc())
        )
        .unique()
        .all()
    )
    return [
        ProviderSaleItemResponse(
            maChiTietDonHang=item.maChiTietDonHang,
            maDonHang=item.maDonHang,
            maSoDonHang=item.donHang.maSoDonHang,
            maKhoaHoc=item.maKhoaHoc,
            tieuDeSnapshot=item.tieuDeSnapshot,
            giaTaiThoiDiemMua=Decimal(item.giaTaiThoiDiemMua),
            donViTienTe=item.donHang.donViTienTe,
            trangThaiDonHang=item.donHang.trangThai,
            ngayThanhToan=item.donHang.ngayThanhToan,
            ngayTao=item.ngayTao,
        )
        for item in rows
    ]
