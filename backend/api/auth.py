from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from api.dependencies import AuthenticatedPrincipal, get_current_principal
from config.database import get_db
from repository import token_repository
from schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from service.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    UsernameAlreadyRegisteredError,
    UserRoleNotConfiguredError,
    login_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Username or email is already registered."
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Default USER role is not configured."
        },
    },
)
def register(
    payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    try:
        user = register_user(db, payload)
    except UsernameAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this username already exists.",
        ) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    except UserRoleNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Default USER role is not configured.",
        ) from exc

    return UserResponse.from_user(user)


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid username or password."}
    },
)
def login(
    payload: LoginRequest, db: Annotated[Session, Depends(get_db)]
) -> LoginResponse:
    try:
        user, token = login_user(db, payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return LoginResponse(
        access_token=token.encoded,
        expires_in=token.expires_in,
        user=UserResponse.from_user(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(get_current_principal),
    ],
) -> UserResponse:
    return UserResponse.from_user(principal.user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid, expired, or revoked access token."
        }
    },
)
def logout(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(get_current_principal),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    token_repository.revoke(
        db,
        principal.token.jti,
        principal.token.expires_at,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
