from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import AuthenticatedPrincipal, get_current_principal
from config.database import get_db
from schemas.auth import (
    ChangePasswordRequest,
    PasswordChangeResponse,
    UpdateProfileRequest,
    UserResponse,
)
from service.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCurrentPasswordError,
    NewPasswordUnchangedError,
    change_user_password,
    update_user_profile,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.put(
    "/me",
    response_model=UserResponse,
    responses={
        status.HTTP_409_CONFLICT: {"description": "Email is already registered."}
    },
)
def update_me(
    payload: UpdateProfileRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(get_current_principal),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    try:
        user = update_user_profile(db, principal.user, payload)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    return UserResponse.from_user(user)


@router.put(
    "/change-password",
    response_model=PasswordChangeResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Current password is incorrect or unchanged."
        }
    },
)
def change_password(
    payload: ChangePasswordRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(get_current_principal),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PasswordChangeResponse:
    try:
        change_user_password(db, principal.user, payload)
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        ) from exc
    except NewPasswordUnchangedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current password.",
        ) from exc
    return PasswordChangeResponse(message="Password changed successfully.")
