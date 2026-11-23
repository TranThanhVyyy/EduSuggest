from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank.")
    return normalized


class ProviderApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    soDienThoai: str = Field(min_length=7, max_length=20)
    toChuc: str = Field(min_length=1, max_length=255)
    chuyenMon: str = Field(min_length=1, max_length=255)
    kinhNghiem: str = Field(min_length=1)
    gioiThieu: str | None = None
    lyDoDangKy: str = Field(min_length=1)

    @field_validator("soDienThoai")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return _required_text(value, "soDienThoai")

    @field_validator("toChuc", "kinhNghiem", "lyDoDangKy")
    @classmethod
    def normalize_required_fields(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator("chuyenMon")
    @classmethod
    def normalize_expertise(cls, value: str) -> str:
        return _required_text(value, "chuyenMon")

    @field_validator("gioiThieu")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ProviderApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maDon: int
    maNguoiDung: int
    toChuc: str
    kinhNghiem: str
    lyDoDangKy: str
    chuyenMon: str | None
    gioiThieu: str | None
    trangThai: str
    lyDoTuChoi: str | None
    ngayGui: datetime
    ngayXuLy: datetime | None


class AdminProviderApplicationResponse(ProviderApplicationResponse):
    hoTen: str | None
    email: str | None
    soDienThoai: str | None


class RejectProviderApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lyDoTuChoi: str = Field(min_length=1)

    @field_validator("lyDoTuChoi")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return _required_text(value, "lyDoTuChoi")


class AdminUserResponse(BaseModel):
    maNguoiDung: int
    hoTen: str | None
    email: str | None
    soDienThoai: str | None
    tenVaiTro: str | None


class GrantExpertRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chuyenMon: str | None = Field(default=None, max_length=255)
    tieuSu: str | None = None


class ExpertProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chuyenMon: str | None = Field(default=None, max_length=255)
    tieuSu: str | None = None

    @model_validator(mode="after")
    def require_update_fields(self) -> "ExpertProfileUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided.")
        return self


class ProviderProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tieuSu: str | None = None
    chuyenMon: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_update_fields(self) -> "ProviderProfileUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided.")
        return self


class ProviderProfileResponse(BaseModel):
    maNhaCungCap: int
    maNguoiDung: int | None
    tieuSu: str | None
    chuyenMon: str | None


class ExpertProfileResponse(BaseModel):
    maChuyenGia: int
    maNguoiDung: int | None
    tieuSu: str | None
    chuyenMon: str | None


class CategoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenDanhMuc: str = Field(min_length=1, max_length=255)
    moTa: str | None = None

    @field_validator("tenDanhMuc")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _required_text(value, "tenDanhMuc")


class CategoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenDanhMuc: str | None = Field(default=None, min_length=1, max_length=255)
    moTa: str | None = None

    @field_validator("tenDanhMuc")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value, "tenDanhMuc")

    @model_validator(mode="after")
    def require_update_fields(self) -> "CategoryUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one category field must be provided.")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maDanhMuc: int
    tenDanhMuc: str | None
    moTa: str | None


class CourseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maDanhMuc: int
    tieuDe: str = Field(min_length=1, max_length=255)
    moTa: str | None = None
    gia: Decimal | None = Field(default=None, ge=0)
    trinhDo: str | None = Field(default=None, max_length=100)
    thoiLuong: int | None = Field(default=None, ge=0)

    @field_validator("tieuDe")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return _required_text(value, "tieuDe")


class CourseUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maDanhMuc: int | None = None
    tieuDe: str | None = Field(default=None, min_length=1, max_length=255)
    moTa: str | None = None
    gia: Decimal | None = Field(default=None, ge=0)
    trinhDo: str | None = Field(default=None, max_length=100)
    thoiLuong: int | None = Field(default=None, ge=0)

    @field_validator("tieuDe")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value, "tieuDe")

    @model_validator(mode="after")
    def require_update_fields(self) -> "CourseUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one course field must be provided.")
        return self


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maKhoaHoc: int
    maNhaCungCap: int | None
    maDanhMuc: int | None
    maNguoiDuyet: int | None
    tieuDe: str | None
    moTa: str | None
    gia: Decimal | None
    trinhDo: str | None
    thoiLuong: int | None
    trangThaiDuyet: str | None
    trangThaiHienThi: str | None
    lyDoTuChoi: str | None
    ngayDuyet: datetime | None
    ngayTao: datetime | None
    ngayCapNhat: datetime | None


class VisibilityUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trangThaiHienThi: Literal["VISIBLE", "HIDDEN"]


class LessonCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tieuDe: str = Field(min_length=1, max_length=255)
    noiDung: str | None = None
    duongDanVideo: str | None = Field(default=None, max_length=500)
    thoiLuong: int | None = Field(default=None, ge=0)
    thuTu: int | None = Field(default=None, ge=0)

    @field_validator("tieuDe")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return _required_text(value, "tieuDe")


class LessonUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tieuDe: str | None = Field(default=None, min_length=1, max_length=255)
    noiDung: str | None = None
    duongDanVideo: str | None = Field(default=None, max_length=500)
    thoiLuong: int | None = Field(default=None, ge=0)
    thuTu: int | None = Field(default=None, ge=0)

    @field_validator("tieuDe")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value, "tieuDe")

    @model_validator(mode="after")
    def require_update_fields(self) -> "LessonUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one lesson field must be provided.")
        return self


class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maBaiHoc: int
    maKhoaHoc: int | None
    tieuDe: str | None
    noiDung: str | None
    duongDanVideo: str | None
    thoiLuong: int | None
    thuTu: int | None
    ngayTao: datetime | None


class MaterialCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tieuDe: str = Field(min_length=1, max_length=255)
    duongDanTep: str = Field(min_length=1, max_length=500)
    loai: str | None = Field(default=None, max_length=100)
    moTa: str | None = None

    @field_validator("tieuDe", "duongDanTep")
    @classmethod
    def normalize_required_fields(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)


class MaterialUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tieuDe: str | None = Field(default=None, min_length=1, max_length=255)
    duongDanTep: str | None = Field(default=None, min_length=1, max_length=500)
    loai: str | None = Field(default=None, max_length=100)
    moTa: str | None = None

    @field_validator("tieuDe", "duongDanTep")
    @classmethod
    def normalize_optional_fields(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return _required_text(value, info.field_name)

    @model_validator(mode="after")
    def require_update_fields(self) -> "MaterialUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one material field must be provided.")
        return self


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maTaiLieu: int
    maBaiHoc: int | None
    tieuDe: str | None
    duongDanTep: str | None
    loai: str | None
    moTa: str | None
    ngayTao: datetime | None


class CourseLessonDetailResponse(LessonResponse):
    taiLieus: list[MaterialResponse]


class CourseDetailResponse(CourseResponse):
    baiHocs: list[CourseLessonDetailResponse]


class EnrollmentResponse(BaseModel):
    maDangKy: int
    maKhoaHoc: int
    ngayDangKy: datetime | None
    tienDo: Decimal | None
    ngayHoanThanh: datetime | None
    khoaHoc: CourseResponse
    tongBaiHoc: int
    baiHocHoanThanh: int


class LearningLessonResponse(CourseLessonDetailResponse):
    daHoanThanh: bool


class LearningCourseResponse(BaseModel):
    khoaHoc: CourseResponse
    baiHocs: list[LearningLessonResponse]


class LearningProgressResponse(BaseModel):
    maKhoaHoc: int
    tongBaiHoc: int
    baiHocHoanThanh: int
    tienDo: Decimal
    ngayHoatDongGanNhat: datetime | None


class LearningHistoryResponse(BaseModel):
    maLichSu: int
    maKhoaHoc: int
    maBaiHoc: int
    tienDo: str | None
    thoiGianXem: int | None
    ngayTao: datetime | None
    khoaHoc: CourseResponse
    baiHoc: LessonResponse


class CourseDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trangThai: Literal["APPROVED", "REJECTED", "NEEDS_REVISION"]
    noiDungDanhGia: str | None = None
    diemKyThuat: Decimal | None = None
    diemNoiDung: Decimal | None = None
    ghiChu: str | None = None

    @model_validator(mode="after")
    def require_feedback_for_non_approval(self) -> "CourseDecisionRequest":
        if self.trangThai != "APPROVED" and not (self.ghiChu or self.noiDungDanhGia or "").strip():
            raise ValueError("A review note is required for rejection or revision.")
        return self


class ExpertReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maDanhGia: int
    maKhoaHoc: int | None
    maChuyenGia: int | None
    noiDungDanhGia: str | None
    diemKyThuat: Decimal | None
    diemNoiDung: Decimal | None
    ghiChu: str | None
    trangThai: str | None
    ngayTao: datetime | None
