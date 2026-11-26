from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from api.dependencies import (
    AuthenticatedPrincipal,
    get_current_principal,
    get_optional_current_principal,
)
from config.database import get_db
from main import app
from models import (
    BaiHoc,
    DanhMuc,
    KhoaHoc,
    NguoiDung,
    TaiLieu,
    VaiTro,
)
from service import workflow_service
from service.workflow_service import WorkflowNotFoundError
from utils.security import create_access_token


def _make_user(user_id: int, role_name: str, password_hash: str = "hashed-secret") -> NguoiDung:
    return NguoiDung(
        maNguoiDung=user_id,
        tenTaiKhoan=f"{role_name.lower()}_{user_id}",
        hoTen=f"{role_name} User",
        email=f"{role_name.lower()}_{user_id}@test.local",
        matKhau=password_hash,
        vaiTro=VaiTro(maVaiTro=1, tenVaiTro=role_name),
    )


def _make_category(cat_id: int, name: str = "Khoa học dữ liệu") -> DanhMuc:
    return DanhMuc(maDanhMuc=cat_id, tenDanhMuc=name, moTa="Mô tả danh mục")


def _make_course(
    course_id: int,
    *,
    review_status: str = "APPROVED",
    visibility: str = "VISIBLE",
    with_lessons: bool = True,
) -> KhoaHoc:
    course = KhoaHoc(
        maKhoaHoc=course_id,
        maNhaCungCap=5,
        maDanhMuc=1,
        maNguoiDuyet=2 if review_status == "APPROVED" else None,
        tieuDe=f"Khóa học #{course_id}",
        moTa="Mô tả công khai của khóa học",
        gia=Decimal("199000"),
        trinhDo="Beginner",
        thoiLuong=120,
        trangThaiDuyet=review_status,
        trangThaiHienThi=visibility,
        ngayTao=datetime(2026, 11, 20, 10, 0, 0),
        ngayCapNhat=datetime(2026, 11, 24, 10, 0, 0),
    )
    if with_lessons:
        lesson_mat = _make_material(
            500 + course_id,
            course_id=course_id,
            lesson_id=100 + course_id,
            review_status="APPROVED",
            visibility="VISIBLE",
        )
        draft_mat = _make_material(
            600 + course_id,
            course_id=course_id,
            lesson_id=100 + course_id,
            review_status="DRAFT",
            visibility="HIDDEN",
        )
        lesson = BaiHoc(
            maBaiHoc=100 + course_id,
            maKhoaHoc=course_id,
            tieuDe="Bài 1: Nội dung bảo vệ",
            noiDung="Nội dung chi tiết chỉ dành cho học viên đã đăng ký",
            duongDanVideo="https://private.edusuggest.local/videos/lesson-1.mp4",
            thoiLuong=30,
            thuTu=1,
            ngayTao=datetime(2026, 11, 20, 10, 0, 0),
        )
        lesson.taiLieus = [lesson_mat, draft_mat]
        course.baiHocs = [lesson]
    else:
        course.baiHocs = []
    return course


def _make_material(
    material_id: int,
    *,
    course_id: int | None = None,
    lesson_id: int | None = None,
    review_status: str = "APPROVED",
    visibility: str = "VISIBLE",
) -> TaiLieu:
    material = TaiLieu(
        maTaiLieu=material_id,
        maNhaCungCap=5,
        maKhoaHoc=course_id,
        maBaiHoc=lesson_id,
        maDanhMuc=1,
        tieuDe=f"Tài liệu #{material_id}",
        duongDanTep=f"https://private.edusuggest.local/files/material-{material_id}.pdf",
        loai="PDF",
        moTa="Mô tả tài liệu học tập",
        trangThaiDuyet=review_status,
        trangThaiHienThi=visibility,
        maNguoiDuyet=2 if review_status == "APPROVED" else None,
        ngayDuyet=datetime(2026, 11, 22, 10, 0, 0) if review_status == "APPROVED" else None,
        ngayTao=datetime(2026, 11, 20, 10, 0, 0),
        ngayCapNhat=datetime(2026, 11, 24, 10, 0, 0),
    )
    material.danhMuc = _make_category(1)
    return material


@pytest.fixture()
def client():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        with TestClient(app) as test_client:
            yield test_client, mock_db
    finally:
        app.dependency_overrides.clear()


# ===========================================================================
# A. ANONYMOUS ACCESS TESTS
# ===========================================================================
def test_anonymous_can_read_public_categories(client):
    test_client, _ = client
    with patch.object(
        workflow_service, "list_categories", return_value=[_make_category(1, "AI & Data")]
    ):
        resp = test_client.get("/api/categories")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0] == {"maDanhMuc": 1, "tenDanhMuc": "AI & Data", "moTa": "Mô tả danh mục"}


def test_anonymous_can_read_public_courses(client):
    test_client, _ = client
    public_course = _make_course(10, review_status="APPROVED", visibility="VISIBLE")
    with patch.object(workflow_service, "list_user_catalog", return_value=[public_course]):
        resp = test_client.get("/api/courses", params={"query": "Khóa", "limit": 20})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["maKhoaHoc"] == 10
    assert body[0]["trangThaiDuyet"] == "APPROVED"
    assert body[0]["trangThaiHienThi"] == "VISIBLE"


def test_anonymous_can_read_public_materials_without_file_urls(client):
    test_client, _ = client
    standalone = _make_material(201, course_id=None, lesson_id=None)
    course_linked = _make_material(202, course_id=10, lesson_id=None)
    with patch.object(
        workflow_service,
        "list_public_materials",
        return_value=([standalone, course_linked], 2),
    ):
        resp = test_client.get("/api/materials", params={"page": 1, "page_size": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total_pages"] == 1
    assert len(body["items"]) == 2
    # Standalone material is preserved
    assert body["items"][0]["maTaiLieu"] == 201
    assert body["items"][0]["maKhoaHoc"] is None
    assert body["items"][0]["tenDanhMuc"] == "Khoa học dữ liệu"
    # Private file URLs MUST NOT be exposed to anonymous visitors
    assert body["items"][0]["duongDanTep"] is None
    assert body["items"][1]["duongDanTep"] is None


def test_anonymous_public_course_detail_hides_protected_lessons(client):
    test_client, _ = client
    public_course = _make_course(10, with_lessons=True)
    with patch.object(workflow_service, "get_user_course", return_value=public_course):
        resp = test_client.get("/api/courses/10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["maKhoaHoc"] == 10
    assert body["tieuDe"] == "Khóa học #10"
    # Lessons, videos, and attached materials must NOT be exposed to anonymous
    assert body["baiHocs"] == []


def test_anonymous_public_material_detail_returns_metadata_without_file_url(client):
    test_client, _ = client
    standalone = _make_material(201, course_id=None, lesson_id=None)
    with patch.object(workflow_service, "get_public_material", return_value=standalone):
        resp = test_client.get("/api/materials/201")
    assert resp.status_code == 200
    body = resp.json()
    assert body["maTaiLieu"] == 201
    assert body["tieuDe"] == "Tài liệu #201"
    assert body["tenDanhMuc"] == "Khoa học dữ liệu"
    assert body["duongDanTep"] is None


@pytest.mark.parametrize("state", ["DRAFT", "PENDING", "HIDDEN"])
def test_anonymous_non_public_course_returns_404(client, state):
    test_client, _ = client
    with patch.object(
        workflow_service,
        "get_user_course",
        side_effect=WorkflowNotFoundError("Course was not found."),
    ):
        resp = test_client.get("/api/courses/999")
    assert resp.status_code == 404


@pytest.mark.parametrize("state", ["DRAFT", "PENDING", "HIDDEN"])
def test_anonymous_non_public_material_returns_404(client, state):
    test_client, _ = client
    with patch.object(
        workflow_service,
        "get_public_material",
        side_effect=WorkflowNotFoundError("Public learning material was not found."),
    ):
        resp = test_client.get("/api/materials/999")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/recommendations/courses"),
        ("GET", "/api/recommendations/materials"),
        ("GET", "/api/courses/1/similar"),
        ("GET", "/api/materials/1/similar"),
        ("GET", "/api/enrollments"),
        ("POST", "/api/courses/1/enrollments"),
        ("GET", "/api/learning/courses/1"),
        ("GET", "/api/learning/courses/1/progress"),
        ("POST", "/api/learning/courses/1/lessons/1/complete"),
        ("GET", "/api/learning/history"),
        ("GET", "/api/auth/me"),
        ("GET", "/api/admin/courses"),
        ("GET", "/api/admin/users"),
        ("GET", "/api/admin/materials"),
        ("GET", "/api/admin/analytics/summary"),
        ("GET", "/api/provider/courses"),
        ("GET", "/api/provider/materials"),
        ("POST", "/api/provider/materials"),
        ("GET", "/api/expert/courses/pending"),
        ("GET", "/api/expert/materials/pending"),
        ("GET", "/api/expert/reviews/history"),
    ],
)
def test_anonymous_blocked_from_all_protected_endpoints(client, method, path):
    test_client, _ = client
    # Also send spoofed role headers to prove client headers are never trusted
    resp = test_client.request(
        method,
        path,
        headers={"X-Role": "ADMIN", "X-User-Role": "USER"},
    )
    assert resp.status_code == 401, f"Expected 401 for {method} {path}, got {resp.status_code}"


# ===========================================================================
# B. INVALID / EXPIRED / MALFORMED / REVOKED TOKENS MUST RETURN 401 (NEVER ANONYMOUS)
# ===========================================================================
@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/categories",
        "/api/courses",
        "/api/courses/10",
        "/api/materials",
        "/api/materials/201",
    ],
)
@pytest.mark.parametrize(
    "bad_header",
    [
        "Bearer invalid.jwt.token",
        "Bearer ",
        "Basic dXNlcjpwYXNz",
        "MalformedSingleToken",
    ],
)
def test_invalid_or_malformed_token_rejected_with_401_on_public_endpoints(
    client, endpoint, bad_header
):
    test_client, _ = client
    resp = test_client.get(endpoint, headers={"Authorization": bad_header})
    assert resp.status_code == 401


def test_expired_token_rejected_with_401_on_public_endpoints(client):
    test_client, _ = client
    user = _make_user(7, "USER", password_hash="user-secret-hash")
    expired_payload = {
        "sub": str(user.maNguoiDung),
        "jti": "expired-jti-123",
        "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(
        expired_payload,
        "expired-test-signing-key-32-bytes-minimum!",
        algorithm="HS256",
    )
    with patch("api.dependencies.user_repository.get_by_id", return_value=user):
        resp = test_client.get(
            "/api/courses", headers={"Authorization": f"Bearer {expired_token}"}
        )
    assert resp.status_code == 401


def test_revoked_token_rejected_with_401_on_public_endpoints(client):
    test_client, _ = client
    user = _make_user(7, "USER", password_hash="user-secret-hash")
    valid_token = create_access_token(user.maNguoiDung, user.matKhau)
    with (
        patch("api.dependencies.user_repository.get_by_id", return_value=user),
        patch("api.dependencies.token_repository.is_revoked", return_value=True),
    ):
        resp = test_client.get(
            "/api/materials", headers={"Authorization": f"Bearer {valid_token.encoded}"}
        )
    assert resp.status_code == 401


# ===========================================================================
# C. AUTHENTICATED USER TESTS
# ===========================================================================
def test_authenticated_user_enrolled_sees_course_lessons_and_material_urls(client):
    test_client, _ = client
    learner = _make_user(12, "USER")
    principal = AuthenticatedPrincipal(user=learner, token=MagicMock())
    app.dependency_overrides[get_optional_current_principal] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal

    public_course = _make_course(10, with_lessons=True)
    with (
        patch.object(workflow_service, "get_user_course", return_value=public_course),
        patch.object(workflow_service, "user_is_enrolled", return_value=True),
    ):
        resp = test_client.get("/api/courses/10")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["baiHocs"]) == 1
    # Only APPROVED+VISIBLE lesson materials included (draft filtered out)
    assert len(body["baiHocs"][0]["taiLieus"]) == 1
    assert body["baiHocs"][0]["taiLieus"][0]["maTaiLieu"] == 510


def test_authenticated_user_material_file_url_policy(client):
    test_client, _ = client
    learner = _make_user(12, "USER")
    principal = AuthenticatedPrincipal(user=learner, token=MagicMock())
    app.dependency_overrides[get_optional_current_principal] = lambda: principal

    standalone = _make_material(201, course_id=None, lesson_id=None)
    enrolled_course_mat = _make_material(202, course_id=10, lesson_id=None)
    unenrolled_course_mat = _make_material(203, course_id=20, lesson_id=120)

    # 1. Standalone material -> file URL exposed to authenticated USER
    with patch.object(workflow_service, "get_public_material", return_value=standalone):
        r1 = test_client.get("/api/materials/201")
    assert r1.status_code == 200
    assert r1.json()["duongDanTep"] == standalone.duongDanTep

    # 2. Course-linked material (enrolled) -> file URL exposed
    with (
        patch.object(workflow_service, "get_public_material", return_value=enrolled_course_mat),
        patch.object(workflow_service, "user_is_enrolled", return_value=True),
    ):
        r2 = test_client.get("/api/materials/202")
    assert r2.status_code == 200
    assert r2.json()["duongDanTep"] == enrolled_course_mat.duongDanTep

    # 3. Course-linked material (NOT enrolled) -> file URL MUST be masked
    with (
        patch.object(workflow_service, "get_public_material", return_value=unenrolled_course_mat),
        patch.object(workflow_service, "user_is_enrolled", return_value=False),
    ):
        r3 = test_client.get("/api/materials/203")
    assert r3.status_code == 200
    assert r3.json()["duongDanTep"] is None

    # 4. Catalog listing masks unenrolled course material while keeping standalone & enrolled
    with (
        patch.object(
            workflow_service,
            "list_public_materials",
            return_value=([standalone, enrolled_course_mat, unenrolled_course_mat], 3),
        ),
        patch.object(
            workflow_service, "get_user_enrolled_course_ids", return_value={10}
        ),
    ):
        r4 = test_client.get("/api/materials")
    assert r4.status_code == 200
    items = r4.json()["items"]
    assert items[0]["duongDanTep"] == standalone.duongDanTep
    assert items[1]["duongDanTep"] == enrolled_course_mat.duongDanTep
    assert items[2]["duongDanTep"] is None


# ===========================================================================
# D. ROLE SEPARATION PRESERVED (ADMIN / PROVIDER / EXPERT / USER)
# ===========================================================================
@pytest.mark.parametrize(
    "role,forbidden_endpoint",
    [
        ("USER", "/api/admin/courses"),
        ("USER", "/api/provider/courses"),
        ("USER", "/api/expert/courses/pending"),
        ("PROVIDER", "/api/admin/courses"),
        ("PROVIDER", "/api/expert/courses/pending"),
        ("PROVIDER", "/api/recommendations/courses"),
        ("EXPERT", "/api/admin/courses"),
        ("EXPERT", "/api/provider/courses"),
        ("EXPERT", "/api/enrollments"),
        ("ADMIN", "/api/provider/courses"),
        ("ADMIN", "/api/expert/courses/pending"),
        ("ADMIN", "/api/recommendations/courses"),
    ],
)
def test_role_boundaries_remain_strictly_enforced(client, role, forbidden_endpoint):
    test_client, _ = client
    actor = _make_user(99, role)
    principal = AuthenticatedPrincipal(user=actor, token=MagicMock())
    app.dependency_overrides[get_current_principal] = lambda: principal

    resp = test_client.get(forbidden_endpoint)
    assert resp.status_code == 403


# ===========================================================================
# E. REPOSITORY QUERY SAFETY (APPROVED + VISIBLE, NO INNER JOIN ON MATERIALS)
# ===========================================================================
def test_repository_public_queries_enforce_approved_and_visible_without_dropping_standalone():
    from repository import workflow_repository

    executed_sql = []

    class FakeResult:
        def all(self):
            return []

        def first(self):
            return None

    class CapturingSession:
        def scalars(self, statement):
            executed_sql.append(str(statement.compile(compile_kwargs={"literal_binds": True})))
            return FakeResult()

        def scalar(self, statement):
            executed_sql.append(str(statement.compile(compile_kwargs={"literal_binds": True})))
            return 0

    db = CapturingSession()
    workflow_repository.list_public_courses(db, query=None, category_id=None, limit=20)
    workflow_repository.get_public_course(db, 1)
    workflow_repository.list_public_materials(db, limit=20, offset=0)
    workflow_repository.get_public_material(db, 1)

    for sql in executed_sql:
        assert "'APPROVED'" in sql
        assert "'VISIBLE'" in sql

    # Materials public listing must NOT use INNER JOIN on KhoaHoc or BaiHoc
    materials_list_sql = executed_sql[3]  # after courses list, get course, materials count
    assert 'INNER JOIN "KhoaHoc"' not in materials_list_sql
    assert 'INNER JOIN "BaiHoc"' not in materials_list_sql
