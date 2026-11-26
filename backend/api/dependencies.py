from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from config.database import get_db
from models import NguoiDung
from repository import token_repository, user_repository
from utils.security import (
    InvalidAccessTokenError,
    VerifiedAccessToken,
    extract_unverified_subject_id,
    verify_access_token,
)

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user: NguoiDung
    token: VerifiedAccessToken


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_principal(
    authorization: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> AuthenticatedPrincipal:
    if authorization is None or authorization.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        user_id = extract_unverified_subject_id(authorization.credentials)
    except InvalidAccessTokenError as exc:
        raise _unauthorized() from exc

    user = user_repository.get_by_id(db, user_id)
    if user is None or not user.matKhau:
        raise _unauthorized()
    if (getattr(user, "trangThai", "ACTIVE") or "ACTIVE").upper() == "LOCKED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị khóa bởi Quản trị viên.",
        )

    try:
        token = verify_access_token(
            authorization.credentials,
            user.matKhau,
            expected_user_id=user.maNguoiDung,
        )
    except InvalidAccessTokenError as exc:
        raise _unauthorized() from exc

    if token_repository.is_revoked(db, token.jti):
        raise _unauthorized()

    # ACC-09: Reject pre-lock JWTs after ADMIN unlock (requires fresh login after unlock)
    role_name = user.vaiTro.tenVaiTro if getattr(user, "vaiTro", None) else None
    if role_name == "EXPERT" and token.issued_at is not None:
        from sqlalchemy import select
        from models import ChuyenGia

        cycle_anchor = db.scalar(
            select(ChuyenGia.mocChuKyKyLuat).where(ChuyenGia.maNguoiDung == user.maNguoiDung)
        )
        if cycle_anchor is not None:
            # ACC-09: Reject pre-lock & same-ms tokens; fail-closed on legacy tokens lacking iat_ms
            stale = (
                token.issued_at <= cycle_anchor
                if token.has_ms_precision
                else token.issued_at <= cycle_anchor.replace(microsecond=0)
            )
            if stale:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Phiên đăng nhập trước khi mở khóa đã hết hiệu lực. Vui lòng đăng nhập lại.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    return AuthenticatedPrincipal(user=user, token=token)


def get_optional_current_principal(
    request: Request,
    authorization: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> AuthenticatedPrincipal | None:
    """Return authenticated principal when a valid Bearer token is provided.

    - Missing Authorization header -> anonymous (returns None).
    - Present Authorization header (even malformed, invalid, expired, or revoked)
      -> delegates to get_current_principal and raises 401 Unauthorized.
    """
    if request.headers.get("authorization") is None:
        return None
    return get_current_principal(authorization=authorization, db=db)


def get_optional_current_user(
    principal: Annotated[
        AuthenticatedPrincipal | None,
        Depends(get_optional_current_principal),
    ],
) -> NguoiDung | None:
    return principal.user if principal is not None else None


def require_roles(*allowed_roles: str, allow_password_change_pending: bool = False):
    normalized_roles = {role.strip().upper() for role in allowed_roles}
    if not normalized_roles:
        raise ValueError("At least one role must be specified.")

    def role_dependency(
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(get_current_principal),
        ],
    ) -> NguoiDung:
        role_name = principal.user.vaiTro.tenVaiTro if principal.user.vaiTro else None
        if role_name is None or role_name.upper() not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        if not allow_password_change_pending and bool(
            getattr(principal.user, "batBuocDoiMatKhau", False)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn cần đổi mật khẩu lần đầu trước khi sử dụng các chức năng nghiệp vụ.",
            )
        return principal.user

    return role_dependency
