"""Pydantic request/response schemas for GĐ3.5 Expert Availability & Notification Center."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


class CreateAvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ngayBatDau: datetime
    ngayKetThuc: datetime
    lyDo: str = Field(min_length=5, max_length=1000)

    @field_validator("ngayBatDau", "ngayKetThuc")
    @classmethod
    def normalize_utc_naive(cls, v: datetime) -> datetime:
        return _to_utc_naive(v)

    @field_validator("lyDo")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Lý do tạm ngừng phải có ít nhất 5 ký tự.")
        return s

    @model_validator(mode="after")
    def validate_range(self) -> "CreateAvailabilityRequest":
        if self.ngayKetThuc <= self.ngayBatDau:
            raise ValueError("Thời điểm kết thúc phải lớn hơn thời điểm bắt đầu.")
        return self


class CancelAvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lyDoHuy: str = Field(min_length=5, max_length=1000)

    @field_validator("lyDoHuy")
    @classmethod
    def strip_cancel_reason(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Lý do hủy phải có ít nhất 5 ký tự.")
        return s


class AdminApproveAvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ghiChuXuLy: str | None = Field(default=None, max_length=1000)


class AdminRejectAvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ghiChuXuLy: str = Field(min_length=5, max_length=1000)

    @field_validator("ghiChuXuLy")
    @classmethod
    def strip_reject_note(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Bắt buộc nhập lý do từ chối (tối thiểu 5 ký tự).")
        return s


class AvailabilityRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maYeuCau: int
    maChuyenGia: int
    ngayBatDau: datetime
    ngayKetThuc: datetime
    lyDo: str
    trangThai: str
    ngayGuiYeuCau: datetime
    maNguoiXuLy: int | None = None
    ngayXuLy: datetime | None = None
    ghiChuXuLy: str | None = None
    ngayHuy: datetime | None = None
    lyDoHuy: str | None = None
    ngayCapNhat: datetime


class NotificationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maThongBao: int
    maNguoiNhan: int
    loaiThongBao: str
    tieuDe: str
    noiDung: str
    duLieuLienKet: dict[str, Any] | None = None
    daDoc: bool
    ngayTao: datetime
    ngayDoc: datetime | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationItemResponse]
    total: int
    unreadCount: int
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    unreadCount: int


class MarkAllReadResponse(BaseModel):
    updatedCount: int
