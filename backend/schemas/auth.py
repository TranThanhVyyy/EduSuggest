from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from models import NguoiDung
from utils.usernames import normalize_username


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenTaiKhoan: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9._-]{3,50}$",
    )
    hoTen: str = Field(min_length=1, max_length=255)
    email: EmailStr
    matKhau: str = Field(min_length=8, max_length=128)
    soDienThoai: str | None = Field(default=None, max_length=20)

    @field_validator("tenTaiKhoan", mode="before")
    @classmethod
    def normalize_username_value(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return normalize_username(value)

    @field_validator("hoTen")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("hoTen must not be blank.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenTaiKhoan: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9._-]{3,50}$",
    )
    matKhau: str = Field(min_length=1, max_length=128)

    @field_validator("tenTaiKhoan", mode="before")
    @classmethod
    def normalize_username_value(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return normalize_username(value)


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hoTen: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    soDienThoai: str | None = Field(default=None, max_length=20)

    @field_validator("hoTen")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("hoTen must not be blank.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @model_validator(mode="after")
    def require_update_fields(self) -> "UpdateProfileRequest":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided.")
        if "hoTen" in self.model_fields_set and self.hoTen is None:
            raise ValueError("hoTen cannot be null.")
        if "email" in self.model_fields_set and self.email is None:
            raise ValueError("email cannot be null.")
        return self


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matKhauHienTai: str = Field(min_length=1, max_length=128)
    matKhauMoi: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    maNguoiDung: int
    maVaiTro: int | None
    tenVaiTro: str | None
    tenTaiKhoan: str
    hoTen: str
    email: EmailStr
    soDienThoai: str | None
    trangThai: str = "ACTIVE"
    batBuocDoiMatKhau: bool = False

    @classmethod
    def from_user(cls, user: NguoiDung) -> "UserResponse":
        return cls(
            maNguoiDung=user.maNguoiDung,
            maVaiTro=user.maVaiTro,
            tenVaiTro=user.vaiTro.tenVaiTro if user.vaiTro else None,
            tenTaiKhoan=user.tenTaiKhoan,
            hoTen=user.hoTen or "",
            email=user.email or "",
            soDienThoai=user.soDienThoai,
            trangThai=getattr(user, "trangThai", None) or "ACTIVE",
            batBuocDoiMatKhau=bool(getattr(user, "batBuocDoiMatKhau", False)),
        )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PasswordChangeResponse(BaseModel):
    message: str
