from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models import (
    BaiHoc,
    DanhGiaChuyenGia,
    KhoaHoc,
    NhaCungCapKhoaHoc,
    TaiLieu,
)
from schemas.workflow import MaterialCreateRequest, MaterialResponse
from service import workflow_service
from service.workflow_service import WorkflowConflictError, WorkflowNotFoundError


def _make_material(
    material_id: int,
    *,
    provider_id: int = 6,
    course_id: int | None = None,
    lesson_id: int | None = None,
    review_status: str = "DRAFT",
    visibility: str = "HIDDEN",
    approver_id: int | None = None,
    approved_at: datetime | None = None,
    reviews: list[DanhGiaChuyenGia] | None = None,
) -> TaiLieu:
    mat = TaiLieu(
        maTaiLieu=material_id,
        maNhaCungCap=provider_id,
        maKhoaHoc=course_id,
        maBaiHoc=lesson_id,
        maDanhMuc=1,
        tieuDe=f"Material #{material_id}",
        duongDanTep=f"https://example.com/m/{material_id}.pdf",
        loai="DOCUMENT",
        moTa="Desc",
        trangThaiDuyet=review_status,
        trangThaiHienThi=visibility,
        maNguoiDuyet=approver_id,
        ngayDuyet=approved_at,
        ngayTao=datetime(2026, 11, 24, 10, 0, 0),
        ngayCapNhat=datetime(2026, 11, 24, 10, 0, 0),
    )
    if reviews is not None:
        mat.danhGiaChuyenGias = reviews
    return mat


# ---------------------------------------------------------------------------
# M-01: Approval provenance distinguishes LEGACY_BACKFILL vs EXPERT_REVIEW vs UNAPPROVED
# ---------------------------------------------------------------------------
def test_m01_legacy_backfill_provenance_without_fabricating_approver():
    backfilled = _make_material(
        2,
        review_status="APPROVED",
        visibility="VISIBLE",
        approver_id=None,
        approved_at=None,
    )
    resp = MaterialResponse.model_validate(backfilled)
    assert resp.nguonPheDuyet == "LEGACY_BACKFILL"
    assert resp.maNguoiDuyet is None
    assert resp.ngayDuyet is None


def test_m01_expert_reviewed_and_unapproved_provenance():
    reviewed = _make_material(
        3,
        review_status="APPROVED",
        visibility="VISIBLE",
        approver_id=33,
        approved_at=datetime(2026, 11, 24, 15, 0, 0),
    )
    draft = _make_material(4, review_status="DRAFT", visibility="HIDDEN")

    assert MaterialResponse.model_validate(reviewed).nguonPheDuyet == "EXPERT_REVIEW"
    assert MaterialResponse.model_validate(draft).nguonPheDuyet == "UNAPPROVED"


# ---------------------------------------------------------------------------
# M-03: Additive migration file integrity & 3-level linking validation
# ---------------------------------------------------------------------------
def test_m03_additive_migration_module_structure():
    mig_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "f1a2b3c4d5e6_add_tailieu_constraints_and_restrict_review_delete.py"
    )
    assert mig_path.exists()
    spec = spec_from_file_location("mig_f1a2b3c4d5e6", mig_path)
    mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    assert mod.revision == "f1a2b3c4d5e6"
    assert mod.down_revision == "e5b72183d29a"
    assert callable(mod.upgrade)
    assert callable(mod.downgrade)


def test_m03_three_level_material_creation_standalone_course_lesson():
    mock_db = MagicMock()
    mock_db.get.return_value = MagicMock()  # Category exists
    provider = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)
    course = KhoaHoc(maKhoaHoc=1, maNhaCungCap=6, maDanhMuc=1)
    lesson = BaiHoc(maBaiHoc=10, maKhoaHoc=1)

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_course",
            return_value=course,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_lesson",
            return_value=lesson,
        ),
    ):
        # 1. Standalone
        m_standalone = workflow_service.create_provider_standalone_material(
            mock_db,
            28,
            MaterialCreateRequest(
                tieuDe="Standalone Guide",
                duongDanTep="https://example.com/s.pdf",
                maDanhMuc=1,
            ),
        )
        assert m_standalone.maKhoaHoc is None and m_standalone.maBaiHoc is None

        # 2. Course-level
        m_course = workflow_service.create_provider_standalone_material(
            mock_db,
            28,
            MaterialCreateRequest(
                tieuDe="Course Handbook",
                duongDanTep="https://example.com/c.pdf",
                maKhoaHoc=1,
            ),
        )
        assert m_course.maKhoaHoc == 1 and m_course.maBaiHoc is None

        # 3. Lesson-level
        m_lesson = workflow_service.create_provider_standalone_material(
            mock_db,
            28,
            MaterialCreateRequest(
                tieuDe="Lesson Slides",
                duongDanTep="https://example.com/l.pdf",
                maKhoaHoc=1,
                maBaiHoc=10,
            ),
        )
        assert m_lesson.maKhoaHoc == 1 and m_lesson.maBaiHoc == 10


# ---------------------------------------------------------------------------
# M-06: Deleting materials with expert review history is blocked
# ---------------------------------------------------------------------------
def test_m06_delete_material_blocked_when_expert_review_exists():
    mock_db = MagicMock()
    mock_db.scalar.return_value = 501  # DanhGiaChuyenGia.maDanhGia exists
    provider = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)
    review = DanhGiaChuyenGia(maDanhGia=501, maTaiLieu=101, trangThai="REJECTED")
    material = _make_material(
        101,
        provider_id=6,
        review_status="REJECTED",
        visibility="HIDDEN",
        reviews=[review],
    )

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material_by_id",
            return_value=material,
        ),
    ):
        with pytest.raises(WorkflowConflictError, match="expert review history"):
            workflow_service.delete_provider_material_by_id(mock_db, 28, 101)

    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()


def test_m06_delete_nested_lesson_material_blocked_when_review_exists():
    mock_db = MagicMock()
    mock_db.scalar.return_value = 502
    provider = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)
    course = KhoaHoc(maKhoaHoc=1, maNhaCungCap=6, trangThaiDuyet="REJECTED")
    material = _make_material(102, provider_id=6, course_id=1, lesson_id=10, review_status="REJECTED")

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_course",
            return_value=course,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material",
            return_value=material,
        ),
    ):
        with pytest.raises(WorkflowConflictError, match="expert review history"):
            workflow_service.delete_provider_material(mock_db, 28, 1, 10, 102)

    mock_db.delete.assert_not_called()


def test_m06_delete_unreviewed_draft_material_allowed_for_owner_and_blocked_for_other():
    mock_db = MagicMock()
    mock_db.scalar.return_value = None  # No review history
    provider = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)
    draft = _make_material(103, provider_id=6, review_status="DRAFT", visibility="HIDDEN", reviews=[])

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material_by_id",
            return_value=draft,
        ),
    ):
        workflow_service.delete_provider_material_by_id(mock_db, 28, 103)

    mock_db.delete.assert_called_once_with(draft)
    mock_db.commit.assert_called_once()

    # Cross-provider delete blocked
    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=NhaCungCapKhoaHoc(maNhaCungCap=7, maNguoiDung=29),
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material_by_id",
            return_value=None,
        ),
    ):
        with pytest.raises(WorkflowNotFoundError):
            workflow_service.delete_provider_material_by_id(mock_db, 29, 103)
