from contextvars import ContextVar
from typing import Any

from fastapi import HTTPException, status

request_id: ContextVar[str] = ContextVar("request_id", default="SYSTEM")

current_email: ContextVar[str | None] = ContextVar("current_email", default=None)
current_user: ContextVar[dict[str, Any] | None] = ContextVar(
    "current_user", default=None
)
lang_var: ContextVar[str] = ContextVar("lang", default="en")
token_user: ContextVar[dict[str, Any] | None] = ContextVar(
    "token_user", default=None
)


def get_current_lang() -> str:
    return lang_var.get()


def get_current_user() -> dict:
    user = current_user.get()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return user