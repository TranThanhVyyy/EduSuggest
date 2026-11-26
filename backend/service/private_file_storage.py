"""Private local file storage with an object-storage-shaped interface.

Files live outside every StaticFiles mount. Database names form isolated namespaces,
so staging and production cannot resolve each other's object identifiers.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from config.config import BACKEND_DIR

INTERNAL_SCHEME = "private://materials/"
MAX_PRIVATE_FILE_BYTES = 25 * 1024 * 1024
_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_SAFE_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_FORBIDDEN_FILENAME_CHARS = re.compile(r"[\\/\x00-\x1f]")

_ALLOWED_TYPES: dict[str, tuple[str, ...]] = {
    ".pdf": ("application/pdf",),
    ".txt": ("text/plain",),
    ".csv": ("text/csv", "application/csv", "text/plain"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation",),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
    ".webp": ("image/webp",),
}
_OOXML_MARKERS = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
}


class PrivateFileValidationError(ValueError):
    pass


class PrivateFileNotFoundError(FileNotFoundError):
    pass


@dataclass(frozen=True)
class StoredPrivateFile:
    reference: str
    object_id: str
    path: Path
    original_name: str
    content_type: str
    size: int


def is_internal_reference(value: str | None) -> bool:
    return bool(value and value.startswith(INTERNAL_SCHEME))


def protected_material_url(material_id: int) -> str:
    return f"/api/materials/{int(material_id)}/file"


def validate_external_or_empty_reference(value: str | None) -> None:
    """Client JSON may keep legacy http(s) URLs but may never forge private keys."""
    if value is None:
        return
    normalized = value.strip()
    if normalized.startswith(INTERNAL_SCHEME):
        raise PrivateFileValidationError("Internal file references can only be created by the upload API.")
    if not normalized.lower().startswith(("https://", "http://")):
        raise PrivateFileValidationError("Material references must be an HTTP(S) URL or an uploaded private file.")


class LocalPrivateFileStorage:
    """Local implementation that can later be replaced by an object storage adapter."""

    def __init__(self, database_namespace: str, root: Path | None = None) -> None:
        if not _SAFE_NAMESPACE_RE.fullmatch(database_namespace):
            raise PrivateFileValidationError("Invalid storage namespace.")
        self.database_namespace = database_namespace
        self.root = (root or (BACKEND_DIR / "private_storage")).resolve()
        self.objects_dir = (self.root / database_namespace / "materials").resolve()
        if self.root not in self.objects_dir.parents:
            raise PrivateFileValidationError("Private storage path escaped its configured root.")
        self.objects_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _object_id(reference: str) -> str:
        if not reference.startswith(INTERNAL_SCHEME):
            raise PrivateFileValidationError("Not an internal material reference.")
        object_id = reference.removeprefix(INTERNAL_SCHEME)
        if not _OBJECT_ID_RE.fullmatch(object_id):
            raise PrivateFileValidationError("Invalid private file identifier.")
        return object_id

    def _paths(self, object_id: str) -> tuple[Path, Path]:
        if not _OBJECT_ID_RE.fullmatch(object_id):
            raise PrivateFileValidationError("Invalid private file identifier.")
        data_path = (self.objects_dir / f"{object_id}.bin").resolve()
        metadata_path = (self.objects_dir / f"{object_id}.json").resolve()
        if self.objects_dir not in data_path.parents or self.objects_dir not in metadata_path.parents:
            raise PrivateFileValidationError("Private file path escaped storage.")
        return data_path, metadata_path

    async def save_upload(self, upload: UploadFile) -> StoredPrivateFile:
        original_name = (upload.filename or "").strip()
        if not original_name or len(original_name) > 255 or _FORBIDDEN_FILENAME_CHARS.search(original_name):
            raise PrivateFileValidationError("Invalid file name.")
        suffix = Path(original_name).suffix.lower()
        content_type = (upload.content_type or "").lower().strip()
        allowed_mime = _ALLOWED_TYPES.get(suffix)
        if not allowed_mime or content_type not in allowed_mime:
            raise PrivateFileValidationError("Unsupported file type or mismatched content type.")

        object_id = uuid.uuid4().hex
        data_path, metadata_path = self._paths(object_id)
        temp_fd, temp_name = tempfile.mkstemp(prefix="upload-", suffix=".tmp", dir=self.objects_dir)
        os.close(temp_fd)
        temp_path = Path(temp_name)
        size = 0
        try:
            # Local private storage is intentionally bounded at 25 MB; UploadFile reads
            # remain chunked and the storage adapter can later be replaced by object storage.
            with temp_path.open("wb") as stream:  # noqa: ASYNC230
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_PRIVATE_FILE_BYTES:
                        raise PrivateFileValidationError("File exceeds the 25 MB limit.")
                    stream.write(chunk)
            if size == 0:
                raise PrivateFileValidationError("Uploaded file is empty.")
            self._validate_content(temp_path, suffix)
            temp_path.replace(data_path)
            metadata_temp = metadata_path.with_suffix(".json.tmp")
            metadata_temp.write_text(
                json.dumps(
                    {
                        "object_id": object_id,
                        "original_name": original_name,
                        "content_type": content_type,
                        "size": size,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            metadata_temp.replace(metadata_path)
            return StoredPrivateFile(
                reference=f"{INTERNAL_SCHEME}{object_id}",
                object_id=object_id,
                path=data_path,
                original_name=original_name,
                content_type=content_type,
                size=size,
            )
        except Exception:
            temp_path.unlink(missing_ok=True)
            data_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)
            metadata_path.with_suffix(".json.tmp").unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    @staticmethod
    def _validate_content(path: Path, suffix: str) -> None:
        with path.open("rb") as stream:
            header = stream.read(16)
        if suffix == ".pdf" and not header.startswith(b"%PDF-"):
            raise PrivateFileValidationError("The uploaded content is not a valid PDF.")
        if suffix == ".png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise PrivateFileValidationError("The uploaded content is not a valid PNG.")
        if suffix in (".jpg", ".jpeg") and not header.startswith(b"\xff\xd8\xff"):
            raise PrivateFileValidationError("The uploaded content is not a valid JPEG.")
        if suffix == ".webp" and not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
            raise PrivateFileValidationError("The uploaded content is not a valid WEBP file.")
        if suffix in (".txt", ".csv"):
            with path.open("rb") as stream:
                sample = stream.read(65536)
            if b"\x00" in sample:
                raise PrivateFileValidationError("Text files may not contain binary executable content.")
            try:
                sample.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise PrivateFileValidationError("Text files must use UTF-8 encoding.") from exc
        if suffix in _OOXML_MARKERS:
            try:
                with zipfile.ZipFile(path) as archive:
                    names = archive.namelist()
                    if _OOXML_MARKERS[suffix] not in names or "[Content_Types].xml" not in names:
                        raise PrivateFileValidationError("Invalid Office Open XML document.")
                    if any(
                        name.startswith(("/", "\\"))
                        or ".." in Path(name.replace("\\", "/")).parts
                        or name.lower().endswith(("vbaproject.bin", ".exe", ".dll", ".js", ".html"))
                        for name in names
                    ):
                        raise PrivateFileValidationError("The Office document contains unsafe embedded content.")
            except zipfile.BadZipFile as exc:
                raise PrivateFileValidationError("Invalid Office Open XML document.") from exc

    def open(self, reference: str) -> StoredPrivateFile:
        object_id = self._object_id(reference)
        data_path, metadata_path = self._paths(object_id)
        if not data_path.is_file() or not metadata_path.is_file():
            raise PrivateFileNotFoundError("Private file was not found.")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise PrivateFileNotFoundError("Private file metadata is unavailable.") from exc
        if metadata.get("object_id") != object_id:
            raise PrivateFileNotFoundError("Private file metadata is invalid.")
        return StoredPrivateFile(
            reference=reference,
            object_id=object_id,
            path=data_path,
            original_name=str(metadata.get("original_name") or "material"),
            content_type=str(metadata.get("content_type") or "application/octet-stream"),
            size=int(metadata.get("size") or data_path.stat().st_size),
        )

    def delete(self, reference: str | None) -> None:
        if not is_internal_reference(reference):
            return
        object_id = self._object_id(str(reference))
        data_path, metadata_path = self._paths(object_id)
        data_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
