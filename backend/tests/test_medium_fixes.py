from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies import AuthenticatedPrincipal, get_current_principal
from api.workflows import _expert_review_response
from config.database import get_db
from main import app
from models import (
    BaiHoc,
    ChuyenGia,
    DanhGiaChuyenGia,
    DanhMuc,
    KhoaHoc,
    NguoiDung,
    TaiLieu,
    VaiTro,
)
from repository import workflow_repository
from service import recommendation_service, workflow_service
from service.workflow_service import WorkflowForbiddenError


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
    course_id: int | None = None,
    lesson_id: int | None = None,
    title: str | None = None,
    review_status: str = "APPROVED",
    visibility: str = "VISIBLE",
) -> TaiLieu:
    return TaiLieu(
        maTaiLieu=material_id,
        maNhaCungCap=6,
        maKhoaHoc=course_id,
        maBaiHoc=lesson_id,
        maDanhMuc=1,
        tieuDe=title or f"Material #{material_id}",
        duongDanTep=f"https://example.com/m/{material_id}.pdf",
        loai="DOCUMENT",
        moTa="Vue 3 composition api tutorial",
        trangThaiDuyet=review_status,
        trangThaiHienThi=visibility,
        ngayTao=datetime(2026, 11, 24, 10, 0, 0),
        ngayCapNhat=datetime(2026, 11, 24, 10, 0, 0),
    )


# ---------------------------------------------------------------------------
# M-02: ExpertReviewResponse includes maTaiLieu, loaiDoiTuong, tenDoiTuong
# ---------------------------------------------------------------------------
def test_m02_expert_review_response_distinguishes_course_and_material():
    course = KhoaHoc(maKhoaHoc=10, tieuDe="Vue 3 Masterclass")
    material = _make_material(42, title="Vue 3 Reactivity Cheatsheet")

    course_review = DanhGiaChuyenGia(
        maDanhGia=1,
        maKhoaHoc=10,
        maTaiLieu=None,
        maChuyenGia=3,
        trangThai="APPROVED",
        ghiChu="Good course",
        ngayTao=datetime(2026, 11, 24, 11, 0, 0),
        khoaHoc=course,
        taiLieu=None,
    )
    material_review = DanhGiaChuyenGia(
        maDanhGia=2,
        maKhoaHoc=None,
        maTaiLieu=42,
        maChuyenGia=3,
        trangThai="NEEDS_REVISION",
        ghiChu="Please add examples",
        ngayTao=datetime(2026, 11, 24, 12, 0, 0),
        khoaHoc=None,
        taiLieu=material,
    )

    c_resp = _expert_review_response(course_review)
    m_resp = _expert_review_response(material_review)

    assert c_resp.maKhoaHoc == 10
    assert c_resp.maTaiLieu is None
    assert c_resp.loaiDoiTuong == "COURSE"
    assert c_resp.tenDoiTuong == "Vue 3 Masterclass"

    assert m_resp.maTaiLieu == 42
    assert m_resp.maKhoaHoc is None
    assert m_resp.loaiDoiTuong == "MATERIAL"
    assert m_resp.tenDoiTuong == "Vue 3 Reactivity Cheatsheet"


def test_m02_expert_review_history_endpoint_returns_material_and_course():
    client = TestClient(app)
    expert_user = _make_user(33, "EXPERT")
    course = KhoaHoc(maKhoaHoc=10, tieuDe="Python Backend")
    material = _make_material(99, title="FastAPI Security Guide")

    reviews = [
        DanhGiaChuyenGia(
            maDanhGia=101,
            maKhoaHoc=None,
            maTaiLieu=99,
            maChuyenGia=3,
            trangThai="APPROVED",
            ghiChu="Solid guide",
            ngayTao=datetime(2026, 11, 24, 13, 0, 0),
            taiLieu=material,
        ),
        DanhGiaChuyenGia(
            maDanhGia=100,
            maKhoaHoc=10,
            maTaiLieu=None,
            maChuyenGia=3,
            trangThai="REJECTED",
            ghiChu="Incomplete syllabus",
            ngayTao=datetime(2026, 11, 24, 12, 0, 0),
            khoaHoc=course,
        ),
    ]

    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        user=expert_user, token=MagicMock()
    )
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch.object(
            workflow_service, "list_expert_review_history", return_value=reviews
        ):
            response = client.get("/api/expert/reviews/history")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["loaiDoiTuong"] == "MATERIAL"
        assert body[0]["maTaiLieu"] == 99
        assert body[0]["tenDoiTuong"] == "FastAPI Security Guide"
        assert body[1]["loaiDoiTuong"] == "COURSE"
        assert body[1]["maKhoaHoc"] == 10
        assert body[1]["tenDoiTuong"] == "Python Backend"
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# M-04: _course_features excludes material_text & enrolled-course materials include course-level
# ---------------------------------------------------------------------------
def test_m04_course_features_does_not_include_material_text():
    lesson = BaiHoc(
        maBaiHoc=1,
        maKhoaHoc=5,
        tieuDe="Routing Basics",
        noiDung="Configure routes",
        taiLieus=[
            _make_material(
                10,
                course_id=5,
                lesson_id=1,
                title="Secret Material Keyword XYZ",
                review_status="DRAFT",
                visibility="HIDDEN",
            )
        ],
    )
    course = KhoaHoc(
        maKhoaHoc=5,
        tieuDe="Vue 3 Fundamentals",
        moTa="Learn Vue 3",
        maDanhMuc=1,
        danhMuc=DanhMuc(maDanhMuc=1, tenDanhMuc="Frontend"),
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        baiHocs=[lesson],
    )
    features = recommendation_service._course_features(course)
    assert features.material_text == ()
    assert len(features.lesson_text) == 1


def test_m04_enrolled_course_materials_returns_course_level_and_lesson_level():
    mock_db = MagicMock()
    category = DanhMuc(maDanhMuc=1, tenDanhMuc="Frontend")
    lesson = BaiHoc(maBaiHoc=10, maKhoaHoc=5, tieuDe="Vue 3 Reactivity", noiDung="Refs and reactive")
    course = KhoaHoc(
        maKhoaHoc=5,
        tieuDe="Vue 3 Fundamentals",
        moTa="Vue 3 composition api and reactivity",
        maDanhMuc=1,
        danhMuc=category,
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        baiHocs=[lesson],
    )
    lesson.khoaHoc = course

    course_level_mat = _make_material(
        201, course_id=5, lesson_id=None, title="Vue 3 Course Syllabus Handbook"
    )
    course_level_mat.khoaHoc = course
    course_level_mat.danhMuc = category

    lesson_level_mat = _make_material(
        202, course_id=5, lesson_id=10, title="Vue 3 Reactivity Deep Dive"
    )
    lesson_level_mat.khoaHoc = course
    lesson_level_mat.baiHoc = lesson
    lesson_level_mat.danhMuc = category

    unapproved_mat = _make_material(
        203, course_id=5, lesson_id=None, title="Vue 3 Draft Notes", review_status="PENDING", visibility="HIDDEN"
    )
    hidden_mat = _make_material(
        204, course_id=5, lesson_id=10, title="Vue 3 Hidden Notes", review_status="APPROVED", visibility="HIDDEN"
    )

    with (
        patch.object(
            recommendation_service.workflow_repository,
            "get_recommendation_course",
            return_value=course,
        ),
        patch.object(
            recommendation_service.workflow_repository,
            "get_enrollment",
            return_value=MagicMock(),
        ),
        patch.object(
            recommendation_service.workflow_repository,
            "get_owned_lesson",
            return_value=lesson,
        ),
        patch.object(
            recommendation_service.workflow_repository,
            "list_recommendation_materials_for_enrolled_course",
            return_value=[course_level_mat, lesson_level_mat, unapproved_mat, hidden_mat],
        ),
    ):
        resp = recommendation_service.recommend_materials(
            mock_db, user_id=45, course_id=5, lesson_id=10, limit=10
        )

    returned_ids = [item.maTaiLieu for item in resp.items]
    assert 201 in returned_ids  # course-level APPROVED+VISIBLE included
    assert 202 in returned_ids  # lesson-level APPROVED+VISIBLE included
    assert 203 not in returned_ids  # PENDING excluded
    assert 204 not in returned_ids  # HIDDEN excluded
    assert returned_ids[0] == 202  # SAME_LESSON ranked first


def test_m04_unenrolled_user_cannot_get_enrolled_course_materials():
    mock_db = MagicMock()
    course = KhoaHoc(maKhoaHoc=5, tieuDe="Vue 3", trangThaiDuyet="APPROVED", trangThaiHienThi="VISIBLE")
    with (
        patch.object(
            recommendation_service.workflow_repository,
            "get_recommendation_course",
            return_value=course,
        ),
        patch.object(
            recommendation_service.workflow_repository,
            "get_enrollment",
            return_value=None,
        ),
    ):
        with pytest.raises(WorkflowForbiddenError):
            recommendation_service.recommend_materials(
                mock_db, user_id=45, course_id=5, lesson_id=None, limit=10
            )


def test_m04_enrolled_course_material_query_uses_left_outer_join():
    captured = {}

    class DummyScalars:
        def unique(self):
            return self

        def all(self):
            return []

    class DummySession:
        def scalars(self, stmt):
            captured["sql"] = str(stmt)
            return DummyScalars()

    workflow_repository.list_recommendation_materials_for_enrolled_course(
        DummySession(), user_id=45, course_id=5
    )
    sql = captured["sql"]
    assert "LEFT OUTER JOIN" in sql
    assert '"TaiLieu"."maKhoaHoc" = "KhoaHoc"."maKhoaHoc"' in sql
    assert '"TaiLieu"."trangThaiDuyet"' in sql
    assert '"TaiLieu"."trangThaiHienThi"' in sql


# ---------------------------------------------------------------------------
# M-05: Server-side pagination for /api/materials and /api/admin/materials
# ---------------------------------------------------------------------------
def test_m05_public_materials_pagination_metadata():
    client = TestClient(app)
    user = _make_user(45, "USER")
    page_items = [_make_material(i) for i in range(21, 41)]

    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        user=user, token=MagicMock()
    )
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch.object(
            workflow_service,
            "list_public_materials",
            return_value=(page_items, 121),
        ) as mock_list:
            response = client.get("/api/materials?page=2&page_size=20&query=Vue")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 121
        assert body["page"] == 2
        assert body["page_size"] == 20
        assert body["total_pages"] == 7
        assert len(body["items"]) == 20
        mock_list.assert_called_once()
        _, kwargs = mock_list.call_args
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 20
        assert kwargs["query"] == "Vue"
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_db, None)


def test_m05_admin_materials_pagination_and_rbac():
    client = TestClient(app)
    admin = _make_user(13, "ADMIN")
    page_items = [_make_material(121)]

    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        user=admin, token=MagicMock()
    )
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch.object(
            workflow_service,
            "list_admin_materials",
            return_value=(page_items, 121),
        ) as mock_admin_list:
            response = client.get("/api/admin/materials?page=7&page_size=20&status=APPROVED")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 121
        assert body["page"] == 7
        assert body["page_size"] == 20
        assert body["total_pages"] == 7
        assert len(body["items"]) == 1
        _, kwargs = mock_admin_list.call_args
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 120
        assert kwargs["status"] == "APPROVED"
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_db, None)

    # Non-admin blocked
    user = _make_user(45, "USER")
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        user=user, token=MagicMock()
    )
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        r_forbid = client.get("/api/admin/materials?page=1&page_size=20")
        assert r_forbid.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_db, None)
