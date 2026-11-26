"""Integration tests for EduSuggest recommendation system.

SAFETY REQUIREMENT:
All tests in this suite MUST execute against a dedicated test database
(default: 'EduSuggest_phase3_test', configurable via EDUSUGGEST_TEST_DB_NAME).
Execution against production 'EduSuggest' is strictly prevented.
All fixture records are created inside a rolled-back outer transaction.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from config.config import get_settings
from config.database import get_db
from main import app
from models import (
    BaiHoc,
    DangKyKhoaHoc,
    DanhMuc,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    TaiLieu,
    VaiTro,
)
from utils.security import create_access_token

TEST_DB_NAME = os.getenv("EDUSUGGEST_TEST_DB_NAME", "EduSuggest_phase3_test").strip()
assert TEST_DB_NAME and TEST_DB_NAME != "EduSuggest", (
    "SAFETY VIOLATION: Recommendation integration tests must NEVER target production 'EduSuggest'."
)


@pytest.fixture(scope="session")
def test_db_engine():
    settings = get_settings()
    base_url = settings.database_url.get_secret_value()
    parts = base_url.rsplit("/", 1)
    test_db_url = f"{parts[0]}/{TEST_DB_NAME}"
    engine = create_engine(test_db_url, pool_pre_ping=True)

    # Strict Safety Check
    with engine.connect() as conn:
        current_db = conn.execute(text("SELECT current_database();")).scalar()
        if current_db != TEST_DB_NAME or current_db == "EduSuggest":
            pytest.fail(
                f"SAFETY VIOLATION: Expected connected database '{TEST_DB_NAME}', "
                f"got '{current_db}'. Aborting integration tests."
            )

    yield engine
    engine.dispose()


def _seed_isolated_recommendation_dataset(session: Session) -> None:
    """Ensure isolated recommendation fixtures exist inside the rolled-back transaction."""
    user_role = session.scalar(select(VaiTro).where(VaiTro.tenVaiTro == "USER"))
    assert user_role is not None
    existing_newbie = session.scalar(
        select(NguoiDung).where(NguoiDung.tenTaiKhoan == "learner_frontend_newbie")
    )
    if existing_newbie is not None:
        # Ensure test learners have USER role only within this rolled-back transaction
        for uname in (
            "learner_frontend_newbie",
            "learner_vue_specialist",
            "learner_fullstack_hybrid",
        ):
            u = session.scalar(select(NguoiDung).where(NguoiDung.tenTaiKhoan == uname))
            if u is not None and u.maVaiTro != user_role.maVaiTro:
                u.maVaiTro = user_role.maVaiTro
        session.flush()
        return
    provider = session.scalar(select(NhaCungCapKhoaHoc).limit(1))
    assert provider is not None
    cats = session.scalars(select(DanhMuc).order_by(DanhMuc.maDanhMuc)).all()
    assert len(cats) >= 3
    cat_fe, cat_be, cat_data = cats[0].maDanhMuc, cats[1].maDanhMuc, cats[2].maDanhMuc

    now = datetime.now(UTC).replace(tzinfo=None)
    pw_hash = "$2b$12$dummyhashvalueforrecommendationtest0000000000000000"

    u_newbie = NguoiDung(
        tenTaiKhoan="learner_frontend_newbie",
        email="learner_frontend_newbie@test.local",
        hoTen="Frontend Newbie",
        matKhau=pw_hash,
        maVaiTro=user_role.maVaiTro,
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    u_vue = NguoiDung(
        tenTaiKhoan="learner_vue_specialist",
        email="learner_vue_specialist@test.local",
        hoTen="Vue Specialist",
        matKhau=pw_hash,
        maVaiTro=user_role.maVaiTro,
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    u_hybrid = NguoiDung(
        tenTaiKhoan="learner_fullstack_hybrid",
        email="learner_fullstack_hybrid@test.local",
        hoTen="Fullstack Hybrid",
        matKhau=pw_hash,
        maVaiTro=user_role.maVaiTro,
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    session.add_all([u_newbie, u_vue, u_hybrid])
    session.flush()

    c1 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_fe,
        tieuDe="Vue.js 3 và Tailwind CSS Toàn diện Frontend",
        moTa="Xây dựng giao diện frontend hiện đại với Vue.js 3, Composition API, Pinia, Vue Router và Tailwind CSS.",
        trinhDo="BEGINNER",
        gia=Decimal("0"),
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=now,
    )
    c2 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_fe,
        tieuDe="Single Page App với Vue 3 Composition API và Pinia Tailwind CSS",
        moTa="Thực hành frontend Vue.js 3 Composition API, Pinia state management, Vue Router và Tailwind CSS.",
        trinhDo="INTERMEDIATE",
        gia=Decimal("0"),
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=now,
    )
    c3 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_fe,
        tieuDe="Thiết kế Giao diện UI/UX Hiện đại với React Vue.js 3 và Tailwind CSS",
        moTa="Thiết kế giao diện frontend UI/UX hiện đại với Tailwind CSS, component Vue.js 3 và React.",
        trinhDo="INTERMEDIATE",
        gia=Decimal("0"),
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=now,
    )
    c4 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_be,
        tieuDe="Python FastAPI và SQLAlchemy Backend REST API",
        moTa="Xây dựng REST API backend hiệu năng cao bằng Python FastAPI, SQLAlchemy ORM và PostgreSQL.",
        trinhDo="INTERMEDIATE",
        gia=Decimal("0"),
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=now,
    )
    c5 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_be,
        tieuDe="Kiến trúc Microservices Python FastAPI PostgreSQL SQLAlchemy",
        moTa="Phát triển backend Python FastAPI, SQLAlchemy, PostgreSQL và Docker cho hệ thống lớn.",
        trinhDo="ADVANCED",
        gia=Decimal("0"),
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=now,
    )
    c7 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_data,
        tieuDe="Lập trình di động Flutter Dart Android iOS",
        moTa="Xây dựng ứng dụng di động đa nền tảng với Flutter và Dart.",
        trinhDo="BEGINNER",
        gia=Decimal("0"),
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=now,
    )
    c8 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_data,
        tieuDe="Phân tích dữ liệu Pandas NumPy Data Science",
        moTa="Xử lý dữ liệu thống kê và trực quan hóa bằng Pandas và NumPy.",
        trinhDo="BEGINNER",
        gia=Decimal("0"),
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=now,
    )
    c11 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_fe,
        tieuDe="C11 Hidden Course Vue",
        moTa="Hidden course",
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="HIDDEN",
        ngayTao=now,
    )
    c12 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_fe,
        tieuDe="C12 Pending Course Vue",
        moTa="Pending course",
        trangThaiDuyet="PENDING",
        trangThaiHienThi="HIDDEN",
        ngayTao=now,
    )
    c13 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat_fe,
        tieuDe="C13 Rejected Course Vue",
        moTa="Rejected course",
        trangThaiDuyet="REJECTED",
        trangThaiHienThi="HIDDEN",
        ngayTao=now,
    )
    session.add_all([c1, c2, c3, c4, c5, c7, c8, c11, c12, c13])
    session.flush()

    lesson1 = BaiHoc(
        maKhoaHoc=c1.maKhoaHoc,
        tieuDe="Bài 1: Cài đặt Vue 3 Composition API và Tailwind CSS",
        noiDung="Khởi tạo dự án Vite, Vue 3 Composition API và Tailwind CSS.",
        thuTu=1,
    )
    session.add(lesson1)
    session.flush()

    mat1 = TaiLieu(
        maKhoaHoc=c1.maKhoaHoc,
        maBaiHoc=lesson1.maBaiHoc,
        maDanhMuc=cat_fe,
        maNhaCungCap=provider.maNhaCungCap,
        tieuDe="Tài liệu Bài 1 Vue 3 Composition API và Tailwind CSS",
        moTa="Hướng dẫn chi tiết cài đặt Vite, Vue 3 Composition API và Tailwind CSS.",
        loai="PDF",
        duongDanTep="https://example.com/vue3-lesson1.pdf",
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
    )
    session.add(mat1)
    session.flush()

    session.add_all(
        [
            DangKyKhoaHoc(maNguoiDung=u_vue.maNguoiDung, maKhoaHoc=c1.maKhoaHoc, ngayDangKy=now),
            DangKyKhoaHoc(maNguoiDung=u_hybrid.maNguoiDung, maKhoaHoc=c1.maKhoaHoc, ngayDangKy=now),
            DangKyKhoaHoc(maNguoiDung=u_hybrid.maNguoiDung, maKhoaHoc=c4.maKhoaHoc, ngayDangKy=now),
        ]
    )
    session.flush()


@pytest.fixture
def db_session(test_db_engine):
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )
    session = session_factory()

    # Re-verify inside session
    curr = session.execute(text("SELECT current_database();")).scalar()
    assert curr == TEST_DB_NAME and curr != "EduSuggest", f"Database must be {TEST_DB_NAME}"

    _seed_isolated_recommendation_dataset(session)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        curr = db_session.execute(text("SELECT current_database();")).scalar()
        if curr != TEST_DB_NAME or curr == "EduSuggest":
            raise RuntimeError(f"Safety violation: get_db connected to {curr}")
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # Instantiate TestClient without entering lifespan so default .env (Production EduSuggest) is never touched.
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def _auth_headers(user: NguoiDung) -> dict[str, str]:
    token = create_access_token(user.maNguoiDung, user.matKhau).encoded
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Test Scenarios 1 to 7
# ---------------------------------------------------------------------------


def test_scenario_1_course_status_and_visibility_filtering(client, db_session):
    """Kịch bản 1: Chỉ gợi ý các khóa học APPROVED + VISIBLE.

    Không được xuất hiện C11 (HIDDEN), C12 (PENDING), C13 (REJECTED).
    """
    user = db_session.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "learner_frontend_newbie")
        .limit(1)
    )
    assert user is not None

    response = client.get(
        "/api/recommendations/courses?limit=20", headers=_auth_headers(user)
    )
    assert response.status_code == 200
    data = response.json()

    returned_ids = {item["maKhoaHoc"] for item in data["items"]}
    assert len(returned_ids) > 0

    # Query all returned courses from DB to verify approval and visibility
    courses = db_session.scalars(
        select(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(returned_ids))
    ).all()

    for c in courses:
        assert c.trangThaiDuyet == "APPROVED", f"Course {c.maKhoaHoc} must be APPROVED"
        assert c.trangThaiHienThi == "VISIBLE", f"Course {c.maKhoaHoc} must be VISIBLE"

    # Verify C11, C12, C13 are excluded
    excluded_courses = db_session.scalars(
        select(KhoaHoc).where(
            (KhoaHoc.trangThaiDuyet != "APPROVED")
            | (KhoaHoc.trangThaiHienThi != "VISIBLE")
        )
    ).all()
    excluded_ids = {c.maKhoaHoc for c in excluded_courses}
    assert len(excluded_ids) >= 3, (
        "Should have at least 3 excluded courses in test dataset"
    )

    overlap = returned_ids.intersection(excluded_ids)
    assert not overlap, f"Excluded courses {overlap} were returned in recommendations!"


def test_scenario_2_similar_courses(client, db_session):
    """Kịch bản 2: Gợi ý khóa học tương tự.

    Với C1 (Vue.js 3 và Tailwind CSS):
    - Không trả về chính C1.
    - C2 (Vue 3 Composition API và Pinia) có điểm tương đồng cao.
    - So sánh điểm giữa C2 và các khóa không liên quan (ví dụ C7 Mobile, C8 Data Science).
    """
    user = db_session.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "learner_vue_specialist")
        .limit(1)
    )
    assert user is not None

    c1 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Vue.js 3 và Tailwind CSS%"))
        .limit(1)
    )
    assert c1 is not None

    response = client.get(
        f"/api/courses/{c1.maKhoaHoc}/similar?limit=10", headers=_auth_headers(user)
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0

    # 1. Source course C1 must NOT be in the results
    item_ids = [item["maKhoaHoc"] for item in items]
    assert c1.maKhoaHoc not in item_ids

    # 2. Check positions and scores of C2 and C3
    c2 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Single Page App với Vue 3%"))
        .limit(1)
    )
    c3 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Thiết kế Giao diện UI/UX Hiện đại với React%"))
        .limit(1)
    )
    assert c2 is not None and c3 is not None

    # With additional frontend courses added to the catalog after initial seed,
    # both C2 and C3 must remain in the Top 3 similar courses.
    top_3_ids = [item["maKhoaHoc"] for item in items[:3]]
    assert c2.maKhoaHoc in top_3_ids, (
        f"C2 ({c2.maKhoaHoc}) should be in Top 3, got {top_3_ids}"
    )
    assert c3.maKhoaHoc in top_3_ids, (
        f"C3 ({c3.maKhoaHoc}) should be in Top 3, got {top_3_ids}"
    )

    # Log actual similarity scores and ranks
    c3_item = next(it for it in items if it["maKhoaHoc"] == c3.maKhoaHoc)
    c2_item = next(it for it in items if it["maKhoaHoc"] == c2.maKhoaHoc)
    # With expanded 25-course corpus, TF-IDF cosine similarity for C2/C3 remains strong (> 0.35)
    assert c3_item["score"] > 0.35
    assert c2_item["score"] > 0.35

    # Both C2 and C3 must strictly beat unrelated courses (e.g. Flutter mobile, Pandas data)
    for it in items:
        if "Flutter" in it["tieuDe"] or "Pandas" in it["tieuDe"]:
            assert c2_item["score"] > it["score"], (
                "C2 score should be strictly higher than Mobile or Data courses"
            )
            assert c3_item["score"] > it["score"], (
                "C3 score should be strictly higher than Mobile or Data courses"
            )


def test_scenario_3_enrolled_course_exclusion(client, db_session):
    """Kịch bản 3: Loại trừ khóa học đã đăng ký.

    User learner_vue_specialist đã đăng ký C1:
    - C1 KHÔNG được xuất hiện trong kết quả gợi ý.
    - C2 xuất hiện và được xếp hạng cao.
    - personalized == True và strategy == 'content_based'.
    """
    user = db_session.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "learner_vue_specialist")
        .limit(1)
    )
    assert user is not None

    c1 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Vue.js 3 và Tailwind CSS%"))
        .limit(1)
    )
    assert c1 is not None

    # Verify user actually enrolled in C1 in test database
    enr = db_session.scalar(
        select(DangKyKhoaHoc).where(
            DangKyKhoaHoc.maNguoiDung == user.maNguoiDung,
            DangKyKhoaHoc.maKhoaHoc == c1.maKhoaHoc,
        )
    )
    assert enr is not None

    response = client.get(
        "/api/recommendations/courses?limit=10", headers=_auth_headers(user)
    )
    assert response.status_code == 200
    data = response.json()

    assert data["personalized"] is True
    assert data["strategy"] == "content_based"

    recommended_ids = [item["maKhoaHoc"] for item in data["items"]]
    assert c1.maKhoaHoc not in recommended_ids, (
        "Enrolled course C1 must be excluded from recommendations"
    )

    # C2 should be in recommendations
    c2 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Single Page App với Vue 3%"))
        .limit(1)
    )
    assert c2.maKhoaHoc in recommended_ids


def test_scenario_4_contextual_material_recommendation(client, db_session):
    """Kịch bản 4: Gợi ý tài liệu học tập theo ngữ cảnh bài học.

    User learner_vue_specialist đã đăng ký C1:
    - Gọi gợi ý tài liệu cho C1, lesson 1.
    - Trả về danh sách tài liệu hợp lệ.
    - Tài liệu thuộc lesson 1 được ưu tiên hàng đầu.
    """
    user = db_session.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "learner_vue_specialist")
        .limit(1)
    )
    c1 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Vue.js 3 và Tailwind CSS%"))
        .limit(1)
    )
    lesson_1 = db_session.scalar(
        select(BaiHoc)
        .where(BaiHoc.maKhoaHoc == c1.maKhoaHoc, BaiHoc.thuTu == 1)
        .limit(1)
    )
    assert lesson_1 is not None

    response = client.get(
        f"/api/recommendations/materials?course_id={c1.maKhoaHoc}&lesson_id={lesson_1.maBaiHoc}&limit=10",
        headers=_auth_headers(user),
    )
    assert response.status_code == 200
    data = response.json()
    items = data["items"]
    assert len(items) > 0

    # Top item should belong to lesson_1
    top_material = items[0]
    assert top_material["maBaiHoc"] == lesson_1.maBaiHoc
    assert top_material["score"] > 0.0


def test_scenario_5_cold_start_user(client, db_session):
    """Kịch bản 5: Người dùng mới (Cold-start).

    User learner_frontend_newbie không có enrollment hay learning history:
    - Không bị lỗi 500.
    - Trả về kết quả Discovery (các khóa học gần đây).
    - personalized == False.
    - strategy == 'latest'.
    - reasonCodes chứa 'RECENT_COURSE'.
    """
    user = db_session.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "learner_frontend_newbie")
        .limit(1)
    )
    assert user is not None

    # Verify 0 enrollments
    enr_count = db_session.scalar(
        select(text("COUNT(1)"))
        .select_from(DangKyKhoaHoc)
        .where(DangKyKhoaHoc.maNguoiDung == user.maNguoiDung)
    )
    assert enr_count == 0

    response = client.get(
        "/api/recommendations/courses?limit=10", headers=_auth_headers(user)
    )
    assert response.status_code == 200
    data = response.json()

    assert data["personalized"] is False
    assert data["strategy"] == "latest"
    assert len(data["items"]) > 0

    for item in data["items"]:
        assert "RECENT_COURSE" in item["reasonCodes"]
        assert item["score"] is None  # Latest strategy has no numeric score


def test_scenario_6_multi_interest_user(client, db_session):
    """Kịch bản 6: Người dùng đa sở thích (Multi-Interest).

    User learner_fullstack_hybrid đã đăng ký C1 (Frontend) và C4 (Backend):
    - Cả C1 và C4 đều bị loại trừ khỏi danh sách gợi ý.
    - Kết quả gợi ý chứa sự kết hợp giữa Frontend và Backend/Database.
    """
    user = db_session.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "learner_fullstack_hybrid")
        .limit(1)
    )
    assert user is not None

    c1 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Vue.js 3 và Tailwind CSS%"))
        .limit(1)
    )
    c4 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Python FastAPI và SQLAlchemy%"))
        .limit(1)
    )
    assert c1 is not None and c4 is not None

    response = client.get(
        "/api/recommendations/courses?limit=10", headers=_auth_headers(user)
    )
    assert response.status_code == 200
    data = response.json()

    assert data["personalized"] is True
    assert data["strategy"] == "content_based"

    recommended_ids = [item["maKhoaHoc"] for item in data["items"]]
    assert c1.maKhoaHoc not in recommended_ids, "Enrolled C1 must be excluded"
    assert c4.maKhoaHoc not in recommended_ids, "Enrolled C4 must be excluded"

    # Get categories of recommended items
    categories = {item["maDanhMuc"] for item in data["items"]}
    # Expect multiple categories present (e.g. Frontend Category 1, Backend Category 2, or DB Category 3)
    assert len(categories) >= 2, (
        f"Expected diverse multi-interest categories, got {categories}"
    )


def test_scenario_7_enrollment_gate(client, db_session):
    """Kịch bản 7: Kiểm tra Enrollment Gate bảo vệ truy cập tài liệu.

    - User learner_frontend_newbie chưa đăng ký C4: gọi gợi ý tài liệu C4 -> 403 Forbidden.
    - User learner_vue_specialist đã đăng ký C1: gọi gợi ý tài liệu C1 -> 200 OK.
    """
    newbie = db_session.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "learner_frontend_newbie")
        .limit(1)
    )
    specialist = db_session.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "learner_vue_specialist")
        .limit(1)
    )
    c1 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Vue.js 3 và Tailwind CSS%"))
        .limit(1)
    )
    c4 = db_session.scalar(
        select(KhoaHoc)
        .where(KhoaHoc.tieuDe.like("%Python FastAPI và SQLAlchemy%"))
        .limit(1)
    )

    # 1. Newbie calling C4 materials -> Forbidden 403
    resp_unauth = client.get(
        f"/api/recommendations/materials?course_id={c4.maKhoaHoc}",
        headers=_auth_headers(newbie),
    )
    assert resp_unauth.status_code == 403
    assert (
        "Enroll in this course before requesting its materials."
        in resp_unauth.json()["detail"]
    )

    # 2. Specialist calling C1 materials -> OK 200
    resp_auth = client.get(
        f"/api/recommendations/materials?course_id={c1.maKhoaHoc}",
        headers=_auth_headers(specialist),
    )
    assert resp_auth.status_code == 200
    assert len(resp_auth.json()["items"]) > 0
