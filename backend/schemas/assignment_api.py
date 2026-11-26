"""Pydantic request/response schemas for GĐ3.3 EXPERT & ADMIN Assignment APIs.

All request schemas use `extra="forbid"` to block mass-assignment attacks
(e.g., client attempting to inject maChuyenGia, soVongKiemDuyet, or phuongThucPhanCong).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DeclineReasonCode = Literal[
    "WORKLOAD_PERSONAL",
    "CONFLICT_OF_INTEREST",
    "SYSTEM_MISASSIGNMENT",
    "TECHNICAL_ISSUE",
    "OTHER",
]


class DeclineAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maLyDoTuChoi: DeclineReasonCode
    lyDoTuChoi: str = Field(min_length=5, max_length=1000)

    @field_validator("lyDoTuChoi")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Lý do từ chối phải có ít nhất 5 ký tự.")
        return s


class SaveDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    banNhapDanhGia: dict[str, Any]


class AssignmentDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trangThai: Literal["APPROVED", "REJECTED", "NEEDS_REVISION"]
    noiDungDanhGia: str | None = Field(default=None, max_length=5000)
    ghiChu: str | None = Field(default=None, max_length=2000)
    diemKyThuat: Decimal | None = Field(default=None, ge=0, le=10)
    diemNoiDung: Decimal | None = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def require_note_on_non_approval(self) -> "AssignmentDecisionRequest":
        note = (self.ghiChu or "").strip() or (self.noiDungDanhGia or "").strip()
        if self.trangThai != "APPROVED" and not note:
            raise ValueError(
                "Bắt buộc nhập nhận xét hoặc ghi chú khi từ chối hoặc yêu cầu chỉnh sửa."
            )
        return self


class AdminCancelAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lyDoHuy: str = Field(min_length=5, max_length=1000)
    requeue: bool = True

    @field_validator("lyDoHuy")
    @classmethod
    def strip_cancel_reason(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Lý do thu hồi phải có ít nhất 5 ký tự.")
        return s


class AdminManualAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaiDoiTuong: Literal["COURSE", "MATERIAL"]
    maDoiTuong: int = Field(ge=1)
    maChuyenGia: int = Field(ge=1)
    lyDoPhanCong: str = Field(min_length=5, max_length=1000)

    @field_validator("lyDoPhanCong")
    @classmethod
    def strip_manual_reason(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Lý do phân công thủ công phải có ít nhất 5 ký tự.")
        return s


class ExpertAssignmentSummaryResponse(BaseModel):
    maPhanCong: int
    loaiDoiTuong: Literal["COURSE", "MATERIAL"]
    maDoiTuong: int
    tieuDeDoiTuong: str | None = None
    maDanhMuc: int
    soVongKiemDuyet: int
    trangThai: str
    phuongThucPhanCong: str
    diemPhuHop: float | None = None
    lyDoPhanCong: str | None = None
    ngayPhanCong: datetime
    hanTiepNhan: datetime
    hanKiemDuyet: datetime | None = None
    ngayChapNhan: datetime | None = None
    ngayBatDau: datetime | None = None
    ngayHoanThanh: datetime | None = None
    isOverdueReview: bool = False
    allowedActions: list[str] = Field(default_factory=list)


class ExpertAssignmentDetailResponse(ExpertAssignmentSummaryResponse):
    chiTietDiem: dict[str, Any] | None = None
    banNhapDanhGia: dict[str, Any] | None = None
    noiDungKiemDuyet: dict[str, Any] | None = None
    ketQuaDanhGia: dict[str, Any] | None = None


class AdminAssignmentResponse(BaseModel):
    maPhanCong: int
    loaiDoiTuong: Literal["COURSE", "MATERIAL"]
    maDoiTuong: int
    tieuDeDoiTuong: str | None = None
    maChuyenGia: int
    tenChuyenGia: str | None = None
    maDanhMuc: int
    tenDanhMuc: str | None = None
    maChuyenMonKhop: int | None = None
    soVongKiemDuyet: int
    phuongThucPhanCong: str
    trangThai: str
    diemPhuHop: float | None = None
    chiTietDiem: dict[str, Any] | None = None
    lyDoPhanCong: str | None = None
    ngayPhanCong: datetime
    hanTiepNhan: datetime
    hanKiemDuyet: datetime | None = None
    ngayChapNhan: datetime | None = None
    ngayBatDau: datetime | None = None
    ngayHoanThanh: datetime | None = None
    maLyDoTuChoi: str | None = None
    lyDoTuChoi: str | None = None
    lyDoHuy: str | None = None
    isOverdueReview: bool = False


class AdminAssignmentConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maCauHinh: int
    gioiHanTaiToiDa: int
    hanTiepNhanGio: int
    hanKiemDuyetGio: int
    soLanTaiPhanCongToiDa: int
    khoangThongKeGio: int
    nguongCanhBao: int
    nguongKhoaTaiKhoan: int
    thoiGianTamNgungToiDaNgay: int
    tinhViPhamHetHan: bool
    tuDongKhoa: bool
    uuTienTuyetDoiChuyenMonChinh: bool
    maNguoiCapNhat: int | None = None
    ngayCapNhat: datetime


class AdminAssignmentConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gioiHanTaiToiDa: int | None = Field(default=None, ge=1, le=50)
    hanTiepNhanGio: int | None = Field(default=None, ge=1, le=168)
    hanKiemDuyetGio: int | None = Field(default=None, ge=1, le=720)
    soLanTaiPhanCongToiDa: int | None = Field(default=None, ge=1, le=20)
    khoangThongKeGio: int | None = Field(default=None, ge=24, le=2160)
    nguongCanhBao: int | None = Field(default=None, ge=1, le=20)
    nguongKhoaTaiKhoan: int | None = Field(default=None, ge=2, le=50)
    thoiGianTamNgungToiDaNgay: int | None = Field(default=None, ge=1, le=180)
    tinhViPhamHetHan: bool | None = None
    tuDongKhoa: bool | None = None
    uuTienTuyetDoiChuyenMonChinh: bool | None = None

    @model_validator(mode="after")
    def validate_config_bounds(self) -> "AdminAssignmentConfigUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Phải cung cấp ít nhất một thông số cấu hình cần cập nhật.")
        if (
            self.nguongCanhBao is not None
            and self.nguongKhoaTaiKhoan is not None
            and self.nguongKhoaTaiKhoan <= self.nguongCanhBao
        ):
            raise ValueError("Ngưỡng khóa tài khoản phải lớn hơn ngưỡng cảnh báo.")
        return self


class AdminExpertOverviewResponse(BaseModel):
    totalExperts: int
    verifiedExperts: int
    pendingVerificationExperts: int
    activeWorkingExperts: int
    pausedExperts: int
    lockedExperts: int
    activeAssignments: int
    overdueAssignments: int
    pendingQueueJobs: int
    pendingViolations: int
    pendingAvailabilityRequests: int
    assignmentStatusBreakdown: dict[str, int]
    queueStatusBreakdown: dict[str, int]
    disciplineLevelBreakdown: dict[str, int]
    evaluatedAt: datetime


class AdminQueueJobResponse(BaseModel):
    maCongViec: int
    loaiDoiTuong: str
    maKhoaHoc: int | None = None
    maTaiLieu: int | None = None
    soVongKiemDuyet: int
    loaiSuKien: str
    maPhanCongNguon: int | None = None
    khoaChongTrung: str
    trangThai: str
    uuTien: int
    soLanThu: int
    soLanThuToiDa: int
    thoiDiemChayTiepTheo: datetime
    maWorker: str | None = None
    leaseGeneration: int
    hanXuLy: datetime | None = None
    lyDoCho: str | None = None
    loiGanNhat: str | None = None
    ngayTao: datetime
    ngayCapNhat: datetime


class AdminExpertWorkloadItem(BaseModel):
    maChuyenGia: int
    maNguoiDung: int
    hoTen: str | None = None
    trangThaiTaiKhoan: str
    trangThaiHoSo: str
    activeAssignments: int
    maxAssignments: int
