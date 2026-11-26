from sqlalchemy import text
from sqlalchemy.orm import Session

from models import NguoiDung
from repository import role_repository, user_repository
from schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from utils.security import (
    CreatedAccessToken,
    create_access_token,
    hash_password,
    verify_password,
    verify_unknown_user_password,
)


class EmailAlreadyRegisteredError(Exception):
    pass


class UsernameAlreadyRegisteredError(Exception):
    pass


class UserRoleNotConfiguredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AccountLockedError(Exception):
    pass


class InvalidCurrentPasswordError(Exception):
    pass


class NewPasswordUnchangedError(Exception):
    pass


def register_user(db: Session, payload: RegisterRequest) -> NguoiDung:
    username = payload.tenTaiKhoan
    email = str(payload.email).strip().lower()
    for lock_key in sorted((email, f"username:{username}")):
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": lock_key},
        )

    if user_repository.get_by_username(db, username) is not None:
        raise UsernameAlreadyRegisteredError
    if user_repository.get_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError

    user_role = role_repository.get_by_name(db, "USER")
    if user_role is None:
        raise UserRoleNotConfiguredError

    user = NguoiDung(
        maVaiTro=user_role.maVaiTro,
        tenTaiKhoan=username,
        hoTen=payload.hoTen,
        email=email,
        matKhau=hash_password(payload.matKhau),
        soDienThoai=payload.soDienThoai,
    )
    db.add(user)
    db.commit()
    return user_repository.get_by_id(db, user.maNguoiDung) or user


def login_user(
    db: Session,
    payload: LoginRequest,
) -> tuple[NguoiDung, CreatedAccessToken]:
    username = payload.tenTaiKhoan
    user = user_repository.get_by_username(db, username)
    if user is None:
        verify_unknown_user_password(payload.matKhau)
        raise InvalidCredentialsError

    if not user.matKhau:
        verify_unknown_user_password(payload.matKhau)
        raise InvalidCredentialsError

    if not verify_password(payload.matKhau, user.matKhau):
        raise InvalidCredentialsError

    if (getattr(user, "trangThai", "ACTIVE") or "ACTIVE").upper() == "LOCKED":
        raise AccountLockedError

    return user, create_access_token(user.maNguoiDung, user.matKhau)


def update_user_profile(
    db: Session,
    user: NguoiDung,
    payload: UpdateProfileRequest,
) -> NguoiDung:
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes:
        email = str(changes["email"]).strip().lower()
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))"),
            {"email": email},
        )
        existing_user = user_repository.get_by_email(db, email)
        if existing_user is not None and existing_user.maNguoiDung != user.maNguoiDung:
            raise EmailAlreadyRegisteredError
        changes["email"] = email

    for field, value in changes.items():
        setattr(user, field, value)

    db.commit()
    return user_repository.get_by_id(db, user.maNguoiDung) or user


def change_user_password(
    db: Session,
    user: NguoiDung,
    payload: ChangePasswordRequest,
) -> NguoiDung:
    if not user.matKhau or not verify_password(payload.matKhauHienTai, user.matKhau):
        raise InvalidCurrentPasswordError

    if verify_password(payload.matKhauMoi, user.matKhau):
        raise NewPasswordUnchangedError

    user.matKhau = hash_password(payload.matKhauMoi)
    user.batBuocDoiMatKhau = False
    db.commit()
    return user_repository.get_by_id(db, user.maNguoiDung) or user
