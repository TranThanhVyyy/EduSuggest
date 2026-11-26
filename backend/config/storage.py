"""Filesystem locations with process-only staging overrides.

Production behaviour is unchanged when no override is supplied.  Dataset
staging can point the public course-cover mount at an isolated directory
without editing .env or exposing private material storage.
"""

from __future__ import annotations

import os
from pathlib import Path

from config.config import BACKEND_DIR


def course_media_directory() -> Path:
    configured = os.getenv("EDUSUGGEST_COURSE_MEDIA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (BACKEND_DIR.parent / "media" / "courses").resolve()
