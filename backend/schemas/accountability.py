"""Pydantic request/response schemas for GĐ3.4 Expert Accountability & Auto-Lock APIs.

All request schemas enforce `extra="forbid"` to prevent mass-assignment attacks.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AdminViolationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ghiChuXuLy: str = Field(min_length=5, max_length=1000)

    @field_validator("ghiChuXuLy")
    @classmethod
    def strip_note(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Ghi chú xử lý phải có ít nhất 5 ký tự.")
        return s


class AdminLockUnlockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lyDo: str = Field(min_length=5, max_length=1000)

    @field_validator("lyDo")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Lý do phải có ít nhất 5 ký tự.")
        return s


class AdminAccountabilityConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    khoangThongKeGio: int | None = Field(default=None, ge=24, le=2160)
    nguongCanhBao: int | None = Field(default=None, ge=1)
    nguongKhoaTaiKhoan: int | None = Field(default=None, ge=2)
    tinhViPhamHetHan: bool | None = None
    tuDongKhoa: bool | None = None

    @model_validator(mode="after")
    def validate_thresholds(self) -> "AdminAccountabilityConfigUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Phải cung cấp ít nhất một trường cấu hình cần cập nhật.")
        if (
            self.nguongCanhBao is not None
            and self.nguongKhoaTaiKhoan is not None
            and self.nguongKhoaTaiKhoan <= self.nguongCanhBao
        ):
            raise ValueError("nguongKhoaTaiKhoan phải lớn hơn nguongCanhBao.")
        return self


class ExpertAccountabilitySummaryResponse(BaseModel):
    maChuyenGia: int
    confirmedViolationsInWindow: int
    pendingReviewCount: int
    exemptedCount: int
    warningThreshold: int
    finalWarningThreshold: int
    lockThreshold: int
    remainingBeforeLock: int
    disciplineLevel: str
    windowHours: int
    currentCycle: int
    cycleStartedAt: datetime | None = None
    accountStatus: str
    automaticLockEnabled: bool
    expirationCountsAsViolation: bool
    evaluatedAt: datetime


class ExpertAccountabilityPolicyResponse(BaseModel):
    windowHours: int
    warningThreshold: int
    finalWarningThreshold: int
    lockThreshold: int
    automaticLockEnabled: bool
    expirationCountsAsViolation: bool
    autoUnlockEnabled: bool = False
    onlyAdminCanUnlock: bool = True


class ViolationResponse(BaseModel):
    maViPham: int
    maChuyenGia: int
    maPhanCong: int
    loaiViPham: str
    maLyDoTuChoi: str | None = None
    lyDo: str | None = None
    trangThaiXuLy: str
    chuKyKyLuatSo: int
    mocChuKyApDung: datetime | None = None
    ngayViPham: datetime
    maNguoiXuLy: int | None = None
    ngayXuLy: datetime | None = None
    ghiChuXuLy: str | None = None


class AuditLogResponse(BaseModel):
    maNhatKy: int
    maChuyenGia: int
    maNguoiDung: int
    hanhDong: str
    nguonThucHien: str
    maNguoiThucHien: int | None = None
    chuKyKyLuatSo: int
    trangThaiTruoc: str | None = None
    trangThaiSau: str | None = None
    soViPhamTaiThoiDiem: int | None = None
    lyDo: str
    chinhSachSnapshot: dict[str, Any] | None = None
    ngayTao: datetime


class AdminExpertAccountabilityItem(BaseModel):
    maChuyenGia: int
    maNguoiDung: int
    hoTen: str | None = None
    trangThaiTaiKhoan: str
    trangThaiHoSo: str
    currentCycle: int
    confirmedViolationsInWindow: int
    pendingReviewCount: int
    disciplineLevel: str
