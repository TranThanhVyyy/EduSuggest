import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from config.config import get_settings

JWT_ALGORITHM = "HS256"
_password_hasher = PasswordHasher()
_dummy_password_hash = _password_hasher.hash("EduSuggest-invalid-user-dummy")
_settings = get_settings()


class InvalidAccessTokenError(Exception):
    pass


@dataclass(frozen=True)
class CreatedAccessToken:
    encoded: str
    jti: str
    expires_at: datetime
    expires_in: int


@dataclass(frozen=True)
class VerifiedAccessToken:
    subject_id: int
    jti: str
    expires_at: datetime
    issued_at: datetime | None = None
    has_ms_precision: bool = False


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerificationError:
        return False


def verify_unknown_user_password(password: str) -> None:
    verify_password(password, _dummy_password_hash)


def _jwt_signing_key(password_hash: str) -> bytes:
    secret = _settings.secret_key.get_secret_value().encode("utf-8")
    material = b"EduSuggest access token v1:" + password_hash.encode("utf-8")
    return hmac.new(secret, material, hashlib.sha256).digest()


def create_access_token(user_id: int, password_hash: str) -> CreatedAccessToken:
    now = datetime.now(UTC)
    expires_in = _settings.access_token_expire_seconds
    expires_at = now + timedelta(seconds=expires_in)
    jti = str(uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iat": now,
        "iat_ms": int(now.timestamp() * 1000),
        "exp": expires_at,
        "iss": _settings.app_name,
    }
    encoded = jwt.encode(
        payload,
        _jwt_signing_key(password_hash),
        algorithm=JWT_ALGORITHM,
    )
    return CreatedAccessToken(
        encoded=encoded,
        jti=jti,
        expires_at=expires_at.replace(tzinfo=None),
        expires_in=expires_in,
    )


def extract_unverified_subject_id(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            algorithms=[JWT_ALGORITHM],
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "verify_iss": False,
                "verify_aud": False,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidAccessTokenError from exc

    if not isinstance(payload, dict):
        raise InvalidAccessTokenError

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdecimal():
        raise InvalidAccessTokenError

    try:
        subject_id = int(subject)
    except ValueError as exc:
        raise InvalidAccessTokenError from exc
    if subject_id <= 0:
        raise InvalidAccessTokenError
    return subject_id


def verify_access_token(
    token: str,
    password_hash: str,
    expected_user_id: int,
) -> VerifiedAccessToken:
    try:
        payload = jwt.decode(
            token,
            _jwt_signing_key(password_hash),
            algorithms=[JWT_ALGORITHM],
            issuer=_settings.app_name,
            options={
                "require": ["exp", "iat", "iss", "jti", "sub"],
                "verify_aud": False,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidAccessTokenError from exc

    subject = payload.get("sub")
    jti = payload.get("jti")
    expiration = payload.get("exp")
    if (
        not isinstance(subject, str)
        or not subject.isdecimal()
        or int(subject) != expected_user_id
        or not isinstance(jti, str)
        or not jti
        or len(jti) > 255
        or not isinstance(expiration, (int, float))
    ):
        raise InvalidAccessTokenError

    issued_at_ms = payload.get("iat_ms")
    issued_at_raw = payload.get("iat")
    has_ms_precision = False
    try:
        expires_at = datetime.fromtimestamp(expiration, UTC).replace(tzinfo=None)
        if isinstance(issued_at_ms, (int, float)):
            issued_at = datetime.fromtimestamp(issued_at_ms / 1000.0, UTC).replace(tzinfo=None)
            has_ms_precision = True
        elif isinstance(issued_at_raw, (int, float)):
            issued_at = datetime.fromtimestamp(issued_at_raw, UTC).replace(tzinfo=None)
        else:
            issued_at = None
    except (OverflowError, OSError, ValueError) as exc:
        raise InvalidAccessTokenError from exc

    return VerifiedAccessToken(
        subject_id=expected_user_id,
        jti=jti,
        expires_at=expires_at,
        issued_at=issued_at,
        has_ms_precision=has_ms_precision,
    )
