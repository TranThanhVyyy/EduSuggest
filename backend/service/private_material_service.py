"""Authorization and transaction coordination for private material files."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models import (
    ChuyenGia,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    PhanCongKiemDuyet,
    TaiLieu,
)
from repository import workflow_repository
from service import assignment_lifecycle_service, eligibility_service
from service.private_file_storage import (
    LocalPrivateFileStorage,
    PrivateFileNotFoundError,
    StoredPrivateFile,
    is_internal_reference,
)
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)


def _database_namespace(db: Session) -> str:
    return str(db.execute(text("SELECT current_database()")).scalar_one())


def _storage(db: Session) -> LocalPrivateFileStorage:
    return LocalPrivateFileStorage(_database_namespace(db))


def delete_managed_reference(db: Session, reference: str | None) -> None:
    _storage(db).delete(reference)


def _role_name(user: NguoiDung) -> str:
    return ((user.vaiTro.tenVaiTro if user.vaiTro else None) or "").upper()


def _get_material(db: Session, material_id: int, *, for_update: bool = False) -> TaiLieu:
    statement = select(TaiLieu).where(TaiLieu.maTaiLieu == material_id)
    if for_update:
        statement = statement.with_for_update(of=TaiLieu)
    material = db.scalars(statement).first()
    if material is None:
        raise WorkflowNotFoundError("Material was not found.")
    return material

def _assert_expert_current_eligibility(
    db: Session,
    *,
    expert_id: int,
    target_type: str,
    target_id: int,
    category_id: int | None,
) -> None:
    """ACC-15 read-time eligibility gates for private review content."""
    if category_id is None:
        raise WorkflowForbiddenError("The review target has no category.")
    eligibility_service.lock_expert_eligibility(db, expert_id)
    reasons = eligibility_service.current_assignment_ineligibility_reasons(
        db,
        expert_id=expert_id,
        target_type=target_type,  # type: ignore[arg-type]
        target_id=target_id,
        category_id=int(category_id),
    )
    if reasons:
        raise WorkflowForbiddenError(
            "Expert eligibility is no longer valid: " + ", ".join(reasons)
        )


def authorize_private_file(
    db: Session, *, user: NguoiDung, material_id: int
) -> tuple[TaiLieu, StoredPrivateFile]:
    material = _get_material(db, material_id)
    if not is_internal_reference(material.duongDanTep):
        raise WorkflowNotFoundError("This material does not use managed private storage.")

    role = _role_name(user)
    if role == "ADMIN":
        pass
    elif role == "PROVIDER":
        provider_id = db.scalar(
            select(NhaCungCapKhoaHoc.maNhaCungCap).where(
                NhaCungCapKhoaHoc.maNguoiDung == user.maNguoiDung
            )
        )
        if provider_id is None or int(provider_id) != int(material.maNhaCungCap or -1):
            raise WorkflowForbiddenError("Provider does not own this material.")
    elif role == "EXPERT":
        expert_id = db.scalar(
            select(ChuyenGia.maChuyenGia).where(
                ChuyenGia.maNguoiDung == user.maNguoiDung
            )
        )
        if expert_id is None:
            raise WorkflowForbiddenError("Expert profile is unavailable.")
        material_assignment_exists = db.scalar(
            select(PhanCongKiemDuyet.maPhanCong)
            .where(
                PhanCongKiemDuyet.maChuyenGia == expert_id,
                PhanCongKiemDuyet.maTaiLieu == material_id,
                PhanCongKiemDuyet.trangThai.in_(("ACCEPTED", "IN_PROGRESS")),
            )
            .limit(1)
        )
        target_type = "MATERIAL" if material_assignment_exists is not None else "COURSE"
        target_id = material_id if target_type == "MATERIAL" else material.maKhoaHoc
        if target_id is None:
            raise WorkflowForbiddenError("Expert does not own an active assignment for this material.")
        if target_type == "COURSE":
            course = db.get(KhoaHoc, int(target_id))
            category_id = course.maDanhMuc if course is not None else None
        else:
            category_id = material.maDanhMuc
        expert, assignment, _ = assignment_lifecycle_service.require_owned_review_assignment(
            db,
            user_id=int(user.maNguoiDung),
            target_type=target_type,
            target_id=int(target_id),
            allowed_states={"ACCEPTED", "IN_PROGRESS"},
            require_current_round=True,
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        if assignment.hanKiemDuyet is not None and now >= assignment.hanKiemDuyet:
            raise WorkflowForbiddenError("The review assignment has expired.")
        _assert_expert_current_eligibility(
            db,
            expert_id=int(expert.maChuyenGia),
            target_type=target_type,
            target_id=int(target_id),
            category_id=category_id,
        )
    elif role == "USER":
        if material.trangThaiDuyet != "APPROVED" or material.trangThaiHienThi != "VISIBLE":
            raise WorkflowForbiddenError("Material is not approved and visible.")
        if material.maKhoaHoc is not None:
            course = db.get(KhoaHoc, material.maKhoaHoc)
            if (
                course is None
                or course.trangThaiDuyet != "APPROVED"
                or course.trangThaiHienThi != "VISIBLE"
                or workflow_repository.get_enrollment(
                    db, int(user.maNguoiDung), int(material.maKhoaHoc)
                )
                is None
            ):
                raise WorkflowForbiddenError("Enroll in the approved visible course before accessing this file.")
    else:
        raise WorkflowForbiddenError("This role cannot access private material files.")

    try:
        stored = _storage(db).open(str(material.duongDanTep))
    except PrivateFileNotFoundError as exc:
        raise WorkflowNotFoundError("The private material file is unavailable.") from exc
    return material, stored


async def replace_provider_file(
    db: Session,
    *,
    user_id: int,
    material_id: int,
    upload: UploadFile,
) -> TaiLieu:
    provider_id = db.scalar(
        select(NhaCungCapKhoaHoc.maNhaCungCap).where(
            NhaCungCapKhoaHoc.maNguoiDung == user_id
        )
    )
    if provider_id is None:
        raise WorkflowForbiddenError("Provider profile is not configured.")
    material = _get_material(db, material_id, for_update=True)
    if int(material.maNhaCungCap or -1) != int(provider_id):
        raise WorkflowNotFoundError("Material was not found for this provider.")
    if material.trangThaiDuyet not in {"DRAFT", "REJECTED", "NEEDS_REVISION"}:
        raise WorkflowConflictError("Only editable materials can replace their file.")

    storage = _storage(db)
    old_reference = material.duongDanTep
    stored = await storage.save_upload(upload)
    try:
        material.duongDanTep = stored.reference
        material.ngayCapNhat = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
        db.refresh(material)
    except Exception:
        db.rollback()
        storage.delete(stored.reference)
        raise
    storage.delete(old_reference)
    return material
