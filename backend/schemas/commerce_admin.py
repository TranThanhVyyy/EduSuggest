"""Pydantic schemas for GĐ4.6 ADMIN Commerce Management, Exception Refunds, Incidents & PROVIDER Sales."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentIncidentReportRequest(BaseModel):
    """USER reports a payment issue on their own order. Never accepts card/OTP/password fields."""

    model_config = ConfigDict(extra="forbid")

    loaiSuCo: str = Field(
        pattern="^(DUPLICATE_CHARGE|CHARGED_NO_ACCESS|WRONG_AMOUNT|CANCELLED_OR_EXPIRED_CHARGED|OTHER_PAYMENT_ERROR)$"
    )
    moTa: str = Field(min_length=10, max_length=1000)


class PaymentIncidentReportResponse(BaseModel):
    maSuCo: str
    maDonHang: int
    maSoDonHang: str
    maThanhToan: int | None = None
    maNguoiBaoCao: int
    loaiSuCo: str
    moTa: str
    trangThai: str
    ngayBaoCao: str


class AdminReconciliationActivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lyDo: str = Field(min_length=5, max_length=500)


class AdminExceptionRefundCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maDonHang: int = Field(gt=0)
    maThanhToan: int = Field(gt=0)
    soTienHoan: Decimal = Field(gt=0)
    loaiSuCo: str = Field(
        pattern="^(DUPLICATE_CHARGE|WRONG_AMOUNT|CANNOT_PROVISION_COURSE|LATE_AFTER_CANCEL|LATE_AFTER_EXPIRE|SYSTEM_ERROR|REGULATORY)$"
    )
    phamViHoan: str = Field(pattern="^(EXCESS_PAYMENT|FULL_ORDER|PARTIAL_OVERCHARGE)$")
    lyDo: str = Field(min_length=5, max_length=1000)


class AdminRefundVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ghiChuXacMinh: str = Field(min_length=5, max_length=500)


class AdminRefundExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Test-only fault injection outcome for MOCK_SANDBOX; ignored/blocked for real gateways
    mockOutcome: str = Field(default="REFUNDED", pattern="^(REFUNDED|REFUND_FAILED|UNKNOWN)$")


class AdminRefundReconcileUnknownRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ketQuaDoiSoat: str = Field(pattern="^(REFUNDED|REFUND_FAILED)$")
    maGiaoDichHoanCong: str | None = Field(default=None, max_length=100)
    ghiChuBangChung: str = Field(min_length=5, max_length=500)


class ExceptionRefundRecordResponse(BaseModel):
    refundId: str
    idempotencyKey: str
    maDonHang: int
    maSoDonHang: str
    maThanhToan: int
    congThanhToan: str
    soTienDaThu: Decimal
    soTienHoan: Decimal
    donViTienTe: str = "VND"
    phamViHoan: str
    loaiSuCo: str
    lyDo: str
    trangThai: str
    maGiaoDichHoanCong: str | None = None
    maNguoiXuLy: int | None = None
    ngayCapNhat: str
    lichSuTrangThai: list[dict] = []


class AdminCommerceOverviewResponse(BaseModel):
    donThanhCong: int
    donChuaHoanTat: int
    donHuyHoacHetHan: int
    donHoanTien: int
    giaoDichCanDoiSoat: int
    giaoDichChuaXacDinh: int
    suCoChuaXuLy: int
    tienThuDuChoHoan: Decimal
    tienDangChoHoan: Decimal
    tienDaHoanXacNhan: Decimal
    doanhThuGhiNhan: Decimal
    hoanTienSuCo: Decimal
    doanhThuThuanHopLe: Decimal
    giaTriDonTrungBinh: Decimal
    donViTienTe: str = "VND"
    phanBoCongThanhToan: dict[str, dict[str, str | int]] = {}


class AdminOrderSummaryItem(BaseModel):
    maDonHang: int
    maSoDonHang: str
    maNguoiDung: int
    tenNguoiMua: str | None = None
    nguonTao: str
    tongTien: Decimal
    donViTienTe: str = "VND"
    trangThai: str
    soKhoaHoc: int
    canDoiSoat: bool = False
    coSuCoNguoiDung: bool = False
    trangThaiHoanTien: str | None = None
    hanThanhToan: datetime
    ngayThanhToan: datetime | None = None
    ngayTao: datetime


class AdminOrderListResponse(BaseModel):
    items: list[AdminOrderSummaryItem]
    total: int
    page: int
    pageSize: int
    totalPages: int


class AdminTransactionItem(BaseModel):
    maThanhToan: int
    maDonHang: int
    maSoDonHang: str
    maNguoiDung: int
    congThanhToan: str
    laThanhToanMoPhong: bool
    maGiaoDichNoiBo: str
    maGiaoDichCong: str | None = None
    soTien: Decimal
    soTienDaThuThucTe: Decimal
    daThuTien: bool
    donViTienTe: str = "VND"
    trangThai: str
    maPhanHoiCong: str | None = None
    daXacMinhChuKy: bool
    canDoiSoat: bool
    trangThaiDoiSoat: str | None = None
    lyDoDoiSoat: str | None = None
    trangThaiHoanTien: str | None = None
    ngayThanhToan: datetime | None = None
    ngayTao: datetime


class RevenuePointResponse(BaseModel):
    ngay: str
    doanhThuGhiNhan: Decimal
    hoanTienSuCo: Decimal
    doanhThuThuan: Decimal
    soDonThanhCong: int


class TopCourseRevenueResponse(BaseModel):
    maKhoaHoc: int
    tieuDe: str
    soLuotBan: int
    doanhThuGhiNhan: Decimal
    doanhThuThuan: Decimal


class AdminRevenueDashboardResponse(BaseModel):
    doanhThuGhiNhan: Decimal
    hoanTienSuCo: Decimal
    doanhThuThuanHopLe: Decimal
    tienThuDuChoXuLy: Decimal
    tongLuotBan: int
    soDonThanhCong: int
    giaTriDonTrungBinh: Decimal
    donViTienTe: str = "VND"
    chuoiDoanhThuTheoNgay: list[RevenuePointResponse]
    topKhoaHoc: list[TopCourseRevenueResponse]
    phanBoCongThanhToan: dict[str, dict[str, str | int]]
    ghiChuChinhSach: str


class ProviderSalesSummaryResponse(BaseModel):
    maNhaCungCap: int
    doanhThuGhiNhan: Decimal
    hoanTienSuCo: Decimal
    doanhThuThuan: Decimal
    tongLuotBan: int
    soKhoaHocCoDoanhThu: int
    donViTienTe: str = "VND"
    chuoiDoanhThuTheoNgay: list[RevenuePointResponse]
    hieuQuaTheoKhoaHoc: list[TopCourseRevenueResponse]
    ghiChuPayout: str


class ProviderSaleItemResponse(BaseModel):
    maChiTietDonHang: int
    maDonHang: int
    maSoDonHang: str
    maKhoaHoc: int
    tieuDeSnapshot: str
    giaTaiThoiDiemMua: Decimal
    donViTienTe: str = "VND"
    trangThaiDonHang: str
    ngayThanhToan: datetime | None = None
    ngayTao: datetime
