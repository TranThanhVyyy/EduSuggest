"""Shared guardrails and paths for the long-lived EduSuggest official dataset.

The helpers in this module never mutate a database on import.  Every writer must
call :func:`assert_database_target` on the same connection that performs writes.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url

PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_DIR / "backend"
DATASET_DIR = BACKEND_DIR / "database" / "official_dataset"
GENERATED_DIR = DATASET_DIR / "generated"
SOURCE_MANIFEST = DATASET_DIR / "sources.json"
DATASET_MANIFEST = GENERATED_DIR / "dataset.json"
COVER_DIR = GENERATED_DIR / "course-covers"
MATERIAL_DIR = GENERATED_DIR / "materials"
REPORT_DIR = GENERATED_DIR / "reports"
BACKUP_DIR = BACKEND_DIR / "database" / "backups" / "official-dataset"

PRODUCTION_DATABASE = "EduSuggest"
DATASET_STAGING_DATABASE = "EduSuggest_dataset_staging"
TEST_DATABASE = "EduSuggest_phase3_test"
EXPECTED_REVISION = "c3d4e5f6a7b8"


def configured_database_url() -> URL:
    """Read DATABASE_URL without loading or modifying process-wide settings."""
    raw = os.getenv("DATABASE_URL")
    if not raw:
        values = dotenv_values(BACKEND_DIR / ".env")
        raw = values.get("DATABASE_URL")
    if not raw:
        raise RuntimeError("DATABASE_URL was not found in the process or backend/.env")
    return make_url(str(raw))


def database_url(database: str) -> URL:
    return configured_database_url().set(database=database)


def create_database_engine(database: str) -> Engine:
    return create_engine(database_url(database), pool_pre_ping=True)


def database_identity(connection) -> tuple[str, str]:
    database = connection.execute(text("select current_database()")).scalar_one()
    revision = connection.execute(
        text("select version_num from alembic_version")
    ).scalar_one()
    return str(database), str(revision)


def assert_database_target(
    connection,
    *,
    expected_database: str,
    expected_revision: str = EXPECTED_REVISION,
) -> None:
    actual_database, actual_revision = database_identity(connection)
    if actual_database != expected_database:
        raise RuntimeError(
            f"Database guard failed: expected {expected_database!r}, got {actual_database!r}."
        )
    if actual_revision != expected_revision:
        raise RuntimeError(
            f"Revision guard failed: expected {expected_revision!r}, got {actual_revision!r}."
        )


def assert_dataset_writer_target(connection) -> None:
    """The official importer is intentionally unable to write Production or test DB."""
    assert_database_target(connection, expected_database=DATASET_STAGING_DATABASE)


def ensure_generated_directories() -> None:
    for path in (GENERATED_DIR, COVER_DIR, MATERIAL_DIR, REPORT_DIR, BACKUP_DIR):
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temp.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
