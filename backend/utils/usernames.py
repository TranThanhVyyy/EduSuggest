import re

_USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,50}\Z")


def normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Username must contain 3-50 ASCII letters, digits, dots, underscores, or hyphens."
        )
    return normalized
