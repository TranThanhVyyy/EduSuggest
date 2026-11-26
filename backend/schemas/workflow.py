from datetime import datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from utils.usernames import normalize_username


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank.")
    return normalized


def _external_material_reference(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    if normalized.startswith("private://"):
        raise ValueError("Internal file references can only be created by the upload API.")
    parsed = urlsplit(normalized)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Material reference must be an HTTP(S) URL or an uploaded file.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Material URLs may not contain embedded credentials.")
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
    tenTaiKhoan: str | None = None
    hoTen: str | None
    email: str | None
    soDienThoai: str | None
    tenVaiTro: str | None
    trangThai: str = "ACTIVE"


class AdminUserStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trangThai: Literal["ACTIVE", "LOCKED"]


class AdminResetExpertPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matKhauMoi: str | None = Field(default=None, min_length=8, max_length=128)


class AdminResetExpertPasswordResponse(BaseModel):
    maNguoiDung: int
    tenTaiKhoan: str
    matKhauMoi: str
    message: str


class SpecialtyCategoryRef(BaseModel):
    maDanhMuc: int
    tenDanhMuc: str | None = None


class SpecialtyResponse(BaseModel):
    maChuyenMon: int
    tenChuyenMon: str
    nhomChuyenMon: str
    moTa: str | None = None
    trangThai: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"
    maNguoiTao: int | None = None
    ngayTao: datetime | None = None
    ngayCapNhat: datetime | None = None
    danhMucs: list[SpecialtyCategoryRef] = Field(default_factory=list)
    soChuyenGiaDangSuDung: int = 0


class SpecialtyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenChuyenMon: str = Field(min_length=1, max_length=255)
    nhomChuyenMon: str = Field(min_length=1, max_length=100)
    moTa: str | None = None
    danhMucIds: list[int] = Field(default_factory=list)

    @field_validator("tenChuyenMon", "nhomChuyenMon")
    @classmethod
    def normalize_required_specialty_fields(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator("moTa")
    @classmethod
    def normalize_optional_desc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("danhMucIds")
    @classmethod
    def dedupe_category_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class SpecialtyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenChuyenMon: str | None = Field(default=None, min_length=1, max_length=255)
    nhomChuyenMon: str | None = Field(default=None, min_length=1, max_length=100)
    moTa: str | None = None
    danhMucIds: list[int] | None = None

    @field_validator("tenChuyenMon", "nhomChuyenMon")
    @classmethod
    def normalize_optional_specialty_fields(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return _required_text(value, info.field_name)

    @field_validator("moTa")
    @classmethod
    def normalize_optional_desc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("danhMucIds")
    @classmethod
    def dedupe_category_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def require_update_fields(self) -> "SpecialtyUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật chuyên môn.")
        return self


class SpecialtyStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trangThai: Literal["ACTIVE", "INACTIVE"]


class ExpertSpecialtyItem(BaseModel):
    maChuyenMon: int
    tenChuyenMon: str
    nhomChuyenMon: str
    moTa: str | None = None
    trangThai: str = "ACTIVE"
    laChuyenMonChinh: bool = False


class AdminCreateExpertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenTaiKhoan: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9._-]{3,50}$",
    )
    hoTen: str = Field(min_length=1, max_length=255)
    email: EmailStr
    soDienThoai: str | None = Field(default=None, max_length=20)
    matKhauTamThoi: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("tenTaiKhoan", mode="before")
    @classmethod
    def normalize_username_value(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return normalize_username(value)

    @field_validator("hoTen")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _required_text(value, "hoTen")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class AdminCreateExpertResponse(BaseModel):
    maNguoiDung: int
    maChuyenGia: int
    tenTaiKhoan: str
    hoTen: str
    email: str
    matKhauTamThoi: str
    batBuocDoiMatKhau: bool = True
    message: str


class AdminVerifyExpertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trangThaiHoSo: Literal["VERIFIED", "NEEDS_UPDATE"]
    ghiChuXacMinh: str | None = None

    @field_validator("ghiChuXacMinh")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_note_for_needs_update(self) -> "AdminVerifyExpertRequest":
        if self.trangThaiHoSo == "NEEDS_UPDATE" and not self.ghiChuXacMinh:
            raise ValueError(
                "Vui lòng nhập ghi chú yêu cầu bổ sung khi chuyển hồ sơ sang trạng thái Cần bổ sung."
            )
        return self


class AdminExpertSummaryResponse(AdminUserResponse):
    maChuyenGia: int | None = None
    chuyenMon: str | None = None
    tieuSu: str | None = None
    soNamKinhNghiem: int | None = None
    trangThaiHoSo: str = "DRAFT"
    ghiChuXacMinh: str | None = None
    ngayXacMinh: datetime | None = None
    batBuocDoiMatKhau: bool = False
    primarySpecialty: ExpertSpecialtyItem | None = None
    secondarySpecialties: list[ExpertSpecialtyItem] = Field(default_factory=list)
    hoSoHoanThien: bool = False
    duDieuKienPhanCong: bool = False


class AdminExpertCandidateResponse(BaseModel):
    maNguoiDung: int
    maChuyenGia: int
    hoTen: str | None = None
    email: str | None = None
    soNamKinhNghiem: int | None = None
    primarySpecialty: ExpertSpecialtyItem | None = None
    secondarySpecialties: list[ExpertSpecialtyItem] = Field(default_factory=list)
    soCongViecDangXuLy: int = 0
    diemPhuHop: int = 0
    lyDoDeXuat: list[str] = Field(default_factory=list)


class GrantExpertRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chuyenMon: str | None = Field(default=None, max_length=255)
    tieuSu: str | None = None


class ExpertProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chuyenMon: str | None = Field(default=None, max_length=255)
    tieuSu: str | None = None
    soNamKinhNghiem: int | None = Field(default=None, ge=0, le=60)
    primarySpecialtyId: int | None = None
    secondarySpecialtyIds: list[int] | None = None

    @model_validator(mode="after")
    def validate_profile_update(self) -> "ExpertProfileUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật hồ sơ.")
        if self.secondarySpecialtyIds is not None:
            if len(self.secondarySpecialtyIds) != len(set(self.secondarySpecialtyIds)):
                raise ValueError("Danh sách chuyên môn phụ không được chứa giá trị trùng lặp.")
            if (
                self.primarySpecialtyId is not None
                and self.primarySpecialtyId in self.secondarySpecialtyIds
            ):
                raise ValueError(
                    "Chuyên môn chính không được đồng thời xuất hiện trong danh sách chuyên môn phụ."
                )
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
    soNamKinhNghiem: int | None = None
    trangThaiHoSo: str = "DRAFT"
    ghiChuXacMinh: str | None = None
    ngayXacMinh: datetime | None = None
    primarySpecialty: ExpertSpecialtyItem | None = None
    secondarySpecialties: list[ExpertSpecialtyItem] = Field(default_factory=list)
    duDieuKienPhanCong: bool = False
    batBuocDoiMatKhau: bool = False


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
    hinhAnh: str | None = Field(default=None, max_length=500)
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
    hinhAnh: str | None = Field(default=None, max_length=500)
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
    hinhAnh: str | None = None
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
    duongDanTep: str | None = Field(default=None, min_length=1, max_length=500)
    loai: str | None = Field(default=None, max_length=100)
    moTa: str | None = None
    maDanhMuc: int | None = None
    maKhoaHoc: int | None = None
    maBaiHoc: int | None = None

    @field_validator("tieuDe")
    @classmethod
    def normalize_required_fields(cls, value: str, info) -> str:
        return _required_text(value, info.field_name)

    @field_validator("duongDanTep")
    @classmethod
    def normalize_file_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _external_material_reference(value, "duongDanTep")


class MaterialUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tieuDe: str | None = Field(default=None, min_length=1, max_length=255)
    duongDanTep: str | None = Field(default=None, min_length=1, max_length=500)
    loai: str | None = Field(default=None, max_length=100)
    moTa: str | None = None
    maDanhMuc: int | None = None
    maKhoaHoc: int | None = None
    maBaiHoc: int | None = None

    @field_validator("tieuDe", "duongDanTep")
    @classmethod
    def normalize_optional_fields(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        if info.field_name == "duongDanTep":
            return _external_material_reference(value, info.field_name)
        return _required_text(value, info.field_name)

    @model_validator(mode="after")
    def require_update_fields(self) -> "MaterialUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one material field must be provided.")
        return self


class MaterialDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trangThai: Literal["APPROVED", "REJECTED", "NEEDS_REVISION"]
    ghiChu: str | None = None
    noiDungDanhGia: str | None = None

    @field_validator("ghiChu", "noiDungDanhGia")
    @classmethod
    def normalize_optional_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_feedback_for_non_approval(self) -> "MaterialDecisionRequest":
        if self.trangThai != "APPROVED" and not (self.ghiChu or self.noiDungDanhGia):
            raise ValueError(
                "A review note or reason is required when rejecting or requesting revision."
            )
        return self


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maTaiLieu: int
    maNhaCungCap: int | None = None
    maKhoaHoc: int | None = None
    maBaiHoc: int | None = None
    maDanhMuc: int | None = None
    tenDanhMuc: str | None = None
    tieuDe: str | None = None
    duongDanTep: str | None = None
    loai: str | None = None
    moTa: str | None = None
    trangThaiDuyet: str | None = None
    trangThaiHienThi: str | None = None
    lyDoTuChoi: str | None = None
    maNguoiDuyet: int | None = None
    ngayDuyet: datetime | None = None
    nguonPheDuyet: Literal["EXPERT_REVIEW", "LEGACY_BACKFILL", "UNAPPROVED"] | None = None
    ngayTao: datetime | None = None
    ngayCapNhat: datetime | None = None

    @model_validator(mode="after")
    def protect_internal_file_reference(self) -> "MaterialResponse":
        if self.duongDanTep and self.duongDanTep.startswith("private://materials/"):
            self.duongDanTep = f"/api/materials/{self.maTaiLieu}/file"
        return self


class PublicSyllabusLessonResponse(BaseModel):
    """Publicly visible syllabus metadata (NEVER exposes paid noiDung, duongDanVideo, or private files)."""
    maBaiHoc: int
    tieuDe: str
    thuTu: int | None = None
    thoiLuong: int | None = None


class CourseLessonDetailResponse(LessonResponse):
    taiLieus: list[MaterialResponse]


class CourseDetailResponse(CourseResponse):
    tenNhaCungCap: str | None = None
    soLuongBaiHoc: int = 0
    deCuongCongKhai: list[PublicSyllabusLessonResponse] = Field(default_factory=list)
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
    maKhoaHoc: int | None = None
    maTaiLieu: int | None = None
    loaiDoiTuong: Literal["COURSE", "MATERIAL"] | None = None
    tenDoiTuong: str | None = None
    maChuyenGia: int | None = None
    noiDungDanhGia: str | None = None
    diemKyThuat: Decimal | None = None
    diemNoiDung: Decimal | None = None
    ghiChu: str | None = None
    trangThai: str | None = None
    ngayTao: datetime | None = None


class PaginatedMaterialResponse(BaseModel):
    items: list[MaterialResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminAnalyticsSummaryResponse(BaseModel):
    total_users: int
    total_courses: int
    total_lessons: int
    total_enrollments: int
    completed_enrollments: int
    completion_rate: float
