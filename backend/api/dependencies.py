from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
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

    return AuthenticatedPrincipal(user=user, token=token)


def require_roles(*allowed_roles: str):
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
        return principal.user

    return role_dependency
