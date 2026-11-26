"""Pydantic schemas for GĐ4.2 Wishlist, Shopping Cart, and Buy Now validation APIs."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CartItemAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maKhoaHoc: int = Field(gt=0)


class WishlistItemResponse(BaseModel):
    maYeuThich: int
    maKhoaHoc: int
    tieuDe: str
    hinhAnh: str | None = None
    maDanhMuc: int | None = None
    tenDanhMuc: str | None = None
    maNhaCungCap: int | None = None
    tenNhaCungCap: str | None = None
    giaHienTai: Decimal | None = None
    donViTienTe: str = "VND"
    khaDung: bool
    lyDoKhongKhaDung: str | None = None
    daSoHuu: bool
    trangThaiQuyenHoc: str | None = None
    trongGioHang: bool
    ngayTao: datetime


class WishlistListResponse(BaseModel):
    items: list[WishlistItemResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int


class WishlistStatusResponse(BaseModel):
    maKhoaHoc: int
    trongYeuThich: bool
    tongSoYeuThich: int


class WishlistCountResponse(BaseModel):
    tongSoYeuThich: int


class CartItemResponse(BaseModel):
    maChiTietGioHang: int
    maKhoaHoc: int
    tieuDe: str
    hinhAnh: str | None = None
    maDanhMuc: int | None = None
    tenDanhMuc: str | None = None
    maNhaCungCap: int | None = None
    tenNhaCungCap: str | None = None
    giaLucThem: Decimal
    giaHienTai: Decimal | None = None
    giaThayDoi: bool
    donViTienTe: str = "VND"
    khaDung: bool
    lyDoKhongKhaDung: str | None = None
    daSoHuu: bool
    trangThaiQuyenHoc: str | None = None
    ngayTao: datetime


class CartResponse(BaseModel):
    maGioHang: int | None = None
    items: list[CartItemResponse]
    tongSoLuong: int
    soLuongHopLe: int
    soLuongKhongHopLe: int
    tongTien: Decimal
    donViTienTe: str = "VND"
    coThayDoiGia: bool
    coMucKhongHopLe: bool


class CartCountResponse(BaseModel):
    tongSoLuong: int
    soLuongHopLe: int


class CartClearResponse(BaseModel):
    daXoaSoLuong: int
    tongSoLuong: int = 0


class MoveWishlistToCartResponse(BaseModel):
    maKhoaHoc: int
    daChuyenVaoGioHang: bool
    daXoaKhoiYeuThich: bool
    tongSoYeuThich: int
    tongSoGioHang: int
    tongTienGioHang: Decimal
    donViTienTe: str = "VND"


class BuyNowValidationResponse(BaseModel):
    maKhoaHoc: int
    tieuDe: str
    hinhAnh: str | None = None
    maDanhMuc: int | None = None
    tenDanhMuc: str | None = None
    maNhaCungCap: int | None = None
    tenNhaCungCap: str | None = None
    giaHienTai: Decimal
    donViTienTe: str = "VND"
    muaLaiSauHoanTien: bool
    hopLe: bool = True


# ---------------------------------------------------------------------------
# GĐ4.3 Order, Checkout & Mock Payment Schemas (extra="forbid" on all inputs)
# ---------------------------------------------------------------------------
class OrderPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nguonTao: str = Field(default="CART", pattern="^(CART|BUY_NOW)$")
    courseIds: list[int] | None = Field(default=None, min_length=1, max_length=50)
    maKhoaHoc: int | None = Field(default=None, gt=0)


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nguonTao: str = Field(default="CART", pattern="^(CART|BUY_NOW)$")
    courseIds: list[int] | None = Field(default=None, min_length=1, max_length=50)
    maKhoaHoc: int | None = Field(default=None, gt=0)
    # Optional client confirmation check ONLY (never trusted as billed price)
    tongTienXacNhan: Decimal | None = Field(default=None, gt=0)


class OrderCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lyDo: str | None = Field(default=None, max_length=500)


class PaymentInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    congThanhToan: str = Field(default="MOCK_SANDBOX", pattern="^(MOCK_SANDBOX|VNPAY_SANDBOX)$")


class MockPaymentCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maGiaoDichNoiBo: str = Field(min_length=4, max_length=64)
    maGiaoDichCong: str | None = Field(default=None, max_length=100)
    maDonHang: int = Field(gt=0)
    soTien: Decimal = Field(gt=0)
    donViTienTe: str = Field(default="VND", min_length=3, max_length=3)
    ketQua: str = Field(pattern="^(PAID|FAILED|CANCELLED|EXPIRED)$")
    signature: str = Field(min_length=16, max_length=256)


class OrderPreviewItemResponse(BaseModel):
    maKhoaHoc: int
    tieuDe: str
    hinhAnh: str | None = None
    maNhaCungCap: int | None = None
    tenNhaCungCap: str | None = None
    giaHienTai: Decimal
    donViTienTe: str = "VND"
    muaLaiSauHoanTien: bool = False


class OrderPreviewResponse(BaseModel):
    nguonTao: str
    items: list[OrderPreviewItemResponse]
    tongSoLuong: int
    tongTien: Decimal
    donViTienTe: str = "VND"
    thoiHanThanhToanPhut: int


class OrderItemResponse(BaseModel):
    maChiTietDonHang: int
    maKhoaHoc: int
    maNhaCungCap: int
    tieuDeSnapshot: str
    giaTaiThoiDiemMua: Decimal
    donViTienTe: str = "VND"
    ngayTao: datetime


class PaymentAttemptResponse(BaseModel):
    maThanhToan: int
    maDonHang: int
    congThanhToan: str
    laThanhToanMoPhong: bool
    maGiaoDichNoiBo: str
    maGiaoDichCong: str | None = None
    soTien: Decimal
    donViTienTe: str = "VND"
    trangThai: str
    maPhanHoiCong: str | None = None
    daXacMinhChuKy: bool
    canDoiSoat: bool = False
    ngayThanhToan: datetime | None = None
    ngayTao: datetime


class OrderResponse(BaseModel):
    maDonHang: int
    maSoDonHang: str
    nguonTao: str
    tongTien: Decimal
    donViTienTe: str = "VND"
    trangThai: str
    hanThanhToan: datetime
    ngayThanhToan: datetime | None = None
    ngayHuy: datetime | None = None
    lyDoHuyHoacHoan: str | None = None
    ngayTao: datetime
    items: list[OrderItemResponse]
    thanhToans: list[PaymentAttemptResponse] = []


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int


class OrderStatusResponse(BaseModel):
    maDonHang: int
    maSoDonHang: str
    trangThai: str
    tongTien: Decimal
    donViTienTe: str = "VND"
    hanThanhToan: datetime
    daHetHan: bool
    ngayThanhToan: datetime | None = None
    giaoDichGanNhat: PaymentAttemptResponse | None = None


class PaymentInitiateResponse(BaseModel):
    maThanhToan: int
    maDonHang: int
    maSoDonHang: str
    congThanhToan: str
    laThanhToanMoPhong: bool
    maGiaoDichNoiBo: str
    soTien: Decimal
    donViTienTe: str = "VND"
    trangThai: str
    paymentUrl: str
    hanThanhToan: datetime
    ghiChu: str


class PaymentCallbackResponse(BaseModel):
    maDonHang: int
    maSoDonHang: str
    maThanhToan: int
    maGiaoDichNoiBo: str
    trangThaiDonHang: str
    trangThaiThanhToan: str
    daCapQuyenHoc: bool
    soKhoaHocKichHoat: int
    idempotentReplay: bool = False
    canDoiSoat: bool = False
    thongDiep: str


class CommerceCapabilitiesResponse(BaseModel):
    marketplaceEnabled: bool
    enrollmentGateEnabled: bool
    mockPaymentEnabled: bool
    vnpaySandboxEnabled: bool = False
    orderTtlMinutes: int


class VNPayIpnResponse(BaseModel):
    RspCode: str
    Message: str


class VNPayReturnVerifyResponse(BaseModel):
    signatureValid: bool
    maDonHang: int | None = None
    maGiaoDichNoiBo: str | None = None
    vnpResponseCode: str | None = None
    trangThaiDonHangHienTai: str | None = None
    thongDiep: str


class MockPaymentSimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ketQua: str = Field(pattern="^(PAID|FAILED|CANCELLED|EXPIRED)$")


class MockPaymentSessionDetailResponse(BaseModel):
    maThanhToan: int
    maDonHang: int
    maSoDonHang: str
    maGiaoDichNoiBo: str
    soTien: Decimal
    donViTienTe: str = "VND"
    trangThaiThanhToan: str
    trangThaiDonHang: str
    hanThanhToan: datetime
    daHetHan: bool
    laThanhToanMoPhong: bool = True
    items: list[OrderItemResponse]
