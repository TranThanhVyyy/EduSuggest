from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.dependencies import AuthenticatedPrincipal, get_current_principal
from api.workflows import _course_detail
from config.database import get_db
from main import app
from models import (
    BaiHoc,
    ChuyenGia,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    TaiLieu,
    VaiTro,
)
from schemas.workflow import MaterialDecisionRequest, MaterialUpdateRequest
from service import workflow_service
from service.content_recommendation import MaterialFeatures, rank_materials
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)


def _make_user(user_id: int, role_name: str) -> NguoiDung:
    return NguoiDung(
        maNguoiDung=user_id,
        tenTaiKhoan=f"{role_name.lower()}_{user_id}",
        hoTen=f"{role_name} User",
        email=f"{role_name.lower()}_{user_id}@test.local",
        vaiTro=VaiTro(maVaiTro=1, tenVaiTro=role_name),
    )


def _make_material(
    material_id: int,
    *,
    provider_id: int = 6,
    course_id: int | None = 1,
    lesson_id: int | None = 10,
    review_status: str = "DRAFT",
    visibility: str = "HIDDEN",
) -> TaiLieu:
    return TaiLieu(
        maTaiLieu=material_id,
        maNhaCungCap=provider_id,
        maKhoaHoc=course_id,
        maBaiHoc=lesson_id,
        maDanhMuc=1,
        tieuDe=f"Material #{material_id}",
        duongDanTep=f"https://example.com/materials/{material_id}.pdf",
        loai="DOCUMENT",
        moTa="Sample description",
        trangThaiDuyet=review_status,
        trangThaiHienThi=visibility,
        ngayTao=datetime(2026, 11, 24, 10, 0, 0),
        ngayCapNhat=datetime(2026, 11, 24, 10, 0, 0),
    )


# ---------------------------------------------------------------------------
# C-01: Provider ownership uses user_id (maNguoiDung), not maNhaCungCap
# ---------------------------------------------------------------------------
def test_c01_provider_service_passes_user_id_not_provider_id():
    mock_db = MagicMock()
    provider_profile = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)
    owned_material = _make_material(101, provider_id=6, review_status="DRAFT")

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider_profile,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "list_owned_materials",
            return_value=[owned_material],
        ) as mock_list,
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material_by_id",
            return_value=owned_material,
        ) as mock_get,
    ):
        listed = workflow_service.list_provider_materials(mock_db, 28)
        fetched = workflow_service.get_provider_material(mock_db, 28, 101)
        submitted = workflow_service.submit_provider_material(mock_db, 28, 101)

    assert listed == [owned_material]
    assert fetched is owned_material
    assert submitted.trangThaiDuyet == "PENDING"
    mock_list.assert_called_once_with(mock_db, 28)
    assert mock_get.call_args_list[0].args == (mock_db, 28, 101)
    assert mock_get.call_args_list[1].args == (mock_db, 28, 101)
    assert mock_get.call_args_list[1].kwargs == {"for_update": True}


def test_c01_provider_idor_blocked_when_material_not_owned():
    mock_db = MagicMock()
    provider_profile = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider_profile,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material_by_id",
            return_value=None,
        ),
    ):
        with pytest.raises(WorkflowNotFoundError):
            workflow_service.get_provider_material(mock_db, 28, 999)
        with pytest.raises(WorkflowNotFoundError):
            workflow_service.update_provider_material_by_id(
                mock_db, 28, 999, MaterialUpdateRequest(tieuDe="Hacked")
            )
        with pytest.raises(WorkflowNotFoundError):
            workflow_service.delete_provider_material_by_id(mock_db, 28, 999)
        with pytest.raises(WorkflowNotFoundError):
            workflow_service.submit_provider_material(mock_db, 28, 999)


# ---------------------------------------------------------------------------
# C-02: Admin Analytics Summary RBAC
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("role_name", ["USER", "PROVIDER", "EXPERT"])
def test_c02_admin_analytics_rejects_non_admin_roles(role_name: str):
    client = TestClient(app)
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        user=_make_user(50, role_name), token=MagicMock()
    )
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        response = client.get("/api/admin/analytics/summary")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# H-02: Unapproved / Hidden materials must not leak in course/learning/rec
# ---------------------------------------------------------------------------
def test_h02_course_detail_filters_non_public_materials_for_users():
    approved_visible = _make_material(1, review_status="APPROVED", visibility="VISIBLE")
    pending_hidden = _make_material(2, review_status="PENDING", visibility="HIDDEN")
    approved_hidden = _make_material(3, review_status="APPROVED", visibility="HIDDEN")
    draft_hidden = _make_material(4, review_status="DRAFT", visibility="HIDDEN")

    lesson = BaiHoc(
        maBaiHoc=10,
        maKhoaHoc=1,
        tieuDe="Lesson 1",
        taiLieus=[approved_visible, pending_hidden, approved_hidden, draft_hidden],
    )
    course = KhoaHoc(
        maKhoaHoc=1,
        tieuDe="Course 1",
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        baiHocs=[lesson],
    )

    public_detail = _course_detail(
        course, include_learning_content=True, public_only_materials=True
    )
    assert [m.maTaiLieu for m in public_detail.baiHocs[0].taiLieus] == [1]

    provider_detail = _course_detail(
        course, include_learning_content=True, public_only_materials=False
    )
    assert [m.maTaiLieu for m in provider_detail.baiHocs[0].taiLieus] == [1, 2, 3, 4]


def test_h02_rank_materials_excludes_unapproved_or_hidden():
    context = {"title": ("Vue 3 Composition API",)}
    candidates = [
        MaterialFeatures(
            material_id=1,
            title="Vue 3 Composition API Guide",
            review_status="APPROVED",
            visibility="VISIBLE",
        ),
        MaterialFeatures(
            material_id=2,
            title="Vue 3 Composition API Draft",
            review_status="DRAFT",
            visibility="HIDDEN",
        ),
        MaterialFeatures(
            material_id=3,
            title="Vue 3 Composition API Hidden",
            review_status="APPROVED",
            visibility="HIDDEN",
        ),
    ]
    ranked = rank_materials(context, candidates, limit=10)
    assert [item.item.material_id for item in ranked] == [1]


# ---------------------------------------------------------------------------
# H-03: Provider cannot set trangThaiHienThi or link mismatched/unowned lesson
# ---------------------------------------------------------------------------
def test_h03_material_update_request_forbids_visibility_field():
    with pytest.raises(ValidationError):
        MaterialUpdateRequest(tieuDe="Updated", trangThaiHienThi="VISIBLE")


def test_h03_update_material_rejects_lesson_not_in_selected_course():
    mock_db = MagicMock()
    provider_profile = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)
    material = _make_material(101, provider_id=6, course_id=1, lesson_id=None, review_status="DRAFT")
    owned_course = KhoaHoc(maKhoaHoc=1, maNhaCungCap=6)

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider_profile,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material_by_id",
            return_value=material,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_course",
            return_value=owned_course,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_lesson",
            return_value=None,
        ),
    ):
        with pytest.raises(WorkflowConflictError, match="does not belong"):
            workflow_service.update_provider_material_by_id(
                mock_db,
                28,
                101,
                MaterialUpdateRequest(maKhoaHoc=1, maBaiHoc=999),
            )


def test_h03_update_material_rejects_detaching_course_while_lesson_linked():
    mock_db = MagicMock()
    provider_profile = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)
    material = _make_material(101, provider_id=6, course_id=1, lesson_id=10, review_status="DRAFT")

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider_profile,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material_by_id",
            return_value=material,
        ),
    ):
        with pytest.raises(WorkflowConflictError, match="Cannot detach course"):
            workflow_service.update_provider_material_by_id(
                mock_db,
                28,
                101,
                MaterialUpdateRequest(maKhoaHoc=None),
            )


def test_h03_update_material_rejects_unowned_course():
    mock_db = MagicMock()
    provider_profile = NhaCungCapKhoaHoc(maNhaCungCap=6, maNguoiDung=28)
    material = _make_material(101, provider_id=6, course_id=None, lesson_id=None, review_status="DRAFT")

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_provider_profile",
            return_value=provider_profile,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_material_by_id",
            return_value=material,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_owned_course",
            return_value=None,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_course",
            return_value=KhoaHoc(maKhoaHoc=2, maNhaCungCap=7),
        ),
    ):
        with pytest.raises(WorkflowForbiddenError):
            workflow_service.update_provider_material_by_id(
                mock_db,
                28,
                101,
                MaterialUpdateRequest(maKhoaHoc=2),
            )


# ---------------------------------------------------------------------------
# H-04: REJECTED / NEEDS_REVISION require feedback + decide_material locks row
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("decision", ["REJECTED", "NEEDS_REVISION"])
@pytest.mark.parametrize("note", [None, "", "   "])
def test_h04_material_decision_requires_non_blank_feedback(decision: str, note: str | None):
    with pytest.raises(ValidationError):
        MaterialDecisionRequest(trangThai=decision, ghiChu=note, noiDungDanhGia=note)


def _make_verified_expert_db_mock(user_id: int = 33, expert_id: int = 3):
    """Build a mock Session that satisfies the real SEC-01 _require_verified_expert() guard."""
    from models import VaiTro

    mock_db = MagicMock()
    verified_user = NguoiDung(
        maNguoiDung=user_id,
        tenTaiKhoan=f"expert_{user_id}",
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    verified_user.vaiTro = VaiTro(maVaiTro=4, tenVaiTro="EXPERT")
    verified_profile = ChuyenGia(
        maChuyenGia=expert_id,
        maNguoiDung=user_id,
        trangThaiHoSo="VERIFIED",
    )
    mock_db.scalars.return_value.unique.return_value.first.side_effect = [
        verified_user,
        verified_profile,
    ]
    return mock_db, verified_profile


def test_h04_material_decision_allows_approved_without_note_and_uses_for_update():
    payload = MaterialDecisionRequest(trangThai="APPROVED")
    assert payload.ghiChu is None

    mock_db, expert_profile = _make_verified_expert_db_mock(user_id=33, expert_id=3)
    pending_material = _make_material(55, review_status="PENDING", visibility="HIDDEN")

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_expert_profile",
            return_value=expert_profile,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_expert_material",
            return_value=pending_material,
        ) as mock_get_mat,
    ):
        material, review = workflow_service.decide_material(mock_db, 33, 55, payload)

    mock_get_mat.assert_called_once_with(mock_db, 55, for_update=True)
    assert material.trangThaiDuyet == "APPROVED"
    assert material.trangThaiHienThi == "VISIBLE"
    assert material.maNguoiDuyet == 33
    assert review.maTaiLieu == 55


# ---------------------------------------------------------------------------
# H-05: Expert detail endpoint only allows PENDING materials
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("status_val", ["DRAFT", "APPROVED", "REJECTED", "NEEDS_REVISION"])
def test_h05_expert_cannot_view_non_pending_material(status_val: str):
    mock_db, expert_profile = _make_verified_expert_db_mock(user_id=33, expert_id=3)
    non_pending = _make_material(55, review_status=status_val, visibility="HIDDEN")

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_expert_profile",
            return_value=expert_profile,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_expert_material",
            return_value=non_pending,
        ),
    ):
        with pytest.raises(WorkflowNotFoundError):
            workflow_service.get_expert_material(mock_db, 33, 55)


def test_h05_expert_can_view_pending_material():
    mock_db, expert_profile = _make_verified_expert_db_mock(user_id=33, expert_id=3)
    pending = _make_material(55, review_status="PENDING", visibility="HIDDEN")

    with (
        patch.object(
            workflow_service.workflow_repository,
            "get_expert_profile",
            return_value=expert_profile,
        ),
        patch.object(
            workflow_service.workflow_repository,
            "get_expert_material",
            return_value=pending,
        ),
    ):
        result = workflow_service.get_expert_material(mock_db, 33, 55)
    assert result is pending
