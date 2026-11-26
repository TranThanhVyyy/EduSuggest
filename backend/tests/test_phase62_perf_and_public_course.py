"""GĐ6.2 PostgreSQL regression tests: Recommendation corpus cache & public course metadata/syllabus.

Strictly runs ONLY against EduSuggest_phase4_test (refuses to run on EduSuggest).
"""
from __future__ import annotations

from datetime import datetime
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from config.config import get_settings
from config.database import get_db
from main import app
from models import BaiHoc, DanhMuc, KhoaHoc, NguoiDung, NhaCungCapKhoaHoc, VaiTro
from service import recommendation_service


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ6.2 tests require EduSuggest_phase4_test database.")
    return raw


@pytest.fixture(scope="module")
def pg_engine():
    url = _phase4_test_url()
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        assert db_name == "EduSuggest_phase4_test", f"Refusing to run on {db_name}"
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session: Session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as tc:
            yield tc
    finally:
        app.dependency_overrides.pop(get_db, None)


def _create_user(db: Session, role_name: str, full_name: str) -> NguoiDung:
    role = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == role_name)).first()
    assert role is not None
    tag = uuid.uuid4().hex[:8]
    user = NguoiDung(
        tenTaiKhoan=f"p62_{role_name.lower()}_{tag}",
        email=f"p62_{tag}@test.edusuggest.local",
        matKhau="argon2-placeholder",
        hoTen=full_name,
        maVaiTro=role.maVaiTro,
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    db.add(user)
    db.flush()
    return user


def test_public_course_detail_exposes_provider_count_and_locked_syllabus_without_leaking_content(
    client: TestClient, db_session: Session
):
    provider_user = _create_user(db_session, "PROVIDER", "Học viện Kỹ thuật Số GĐ6.2")
    provider = NhaCungCapKhoaHoc(
        maNguoiDung=provider_user.maNguoiDung,
        tieuSu="Đơn vị đào tạo thực chiến",
        chuyenMon="Cloud & Backend",
    )
    db_session.add(provider)
    db_session.flush()

    category = DanhMuc(tenDanhMuc=f"Cloud GĐ6.2 {uuid.uuid4().hex[:6]}", moTa="Danh mục kiểm thử GĐ6.2")
    db_session.add(category)
    db_session.flush()

    course = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=category.maDanhMuc,
        tieuDe="Kiến trúc Cloud Thực chiến GĐ6.2",
        moTa="Khóa học kiểm thử public syllabus và đếm bài học.",
        trinhDo="INTERMEDIATE",
        thoiLuong=180,
        gia=599000,
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
    )
    db_session.add(course)
    db_session.flush()

    l1 = BaiHoc(
        maKhoaHoc=course.maKhoaHoc,
        tieuDe="Bài 1: Tổng quan kiến trúc hệ thống",
        noiDung="SECRET_PAID_CONTENT_LESSON_1",
        duongDanVideo="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        thuTu=1,
        thoiLuong=35,
    )
    l2 = BaiHoc(
        maKhoaHoc=course.maKhoaHoc,
        tieuDe="Bài 2: Triển khai HA & Auto-scaling",
        noiDung="SECRET_PAID_CONTENT_LESSON_2",
        duongDanVideo="https://www.youtube.com/watch?v=9bZkp7q19f0",
        thuTu=2,
        thoiLuong=45,
    )
    db_session.add_all([l1, l2])
    db_session.flush()

    # Guest request (uses overridden db_session so uncommitted flushed rows are visible & rolled back cleanly)
    resp = client.get(f"/api/courses/{course.maKhoaHoc}")
    assert resp.status_code == 200
    body = resp.json()

    assert body["tenNhaCungCap"] == "Học viện Kỹ thuật Số GĐ6.2"
    assert body["soLuongBaiHoc"] == 2
    assert body["baiHocs"] == []
    assert len(body["deCuongCongKhai"]) == 2
    assert body["deCuongCongKhai"][0]["tieuDe"] == "Bài 1: Tổng quan kiến trúc hệ thống"
    assert body["deCuongCongKhai"][1]["tieuDe"] == "Bài 2: Triển khai HA & Auto-scaling"

    # Ensure zero paid content or video URLs leak in public syllabus
    serialized = str(body)
    assert "SECRET_PAID_CONTENT_LESSON_1" not in serialized
    assert "SECRET_PAID_CONTENT_LESSON_2" not in serialized
    assert "dQw4w9WgXcQ" not in serialized
    assert "9bZkp7q19f0" not in serialized


def test_recommendation_cache_preserves_exact_ranking_and_invalidates_on_visibility_change(
    db_session: Session,
):
    learner = _create_user(db_session, "USER", "Học viên Kiểm thử Rec")
    provider_user = _create_user(db_session, "PROVIDER", "Provider Rec")
    provider = NhaCungCapKhoaHoc(maNguoiDung=provider_user.maNguoiDung)
    db_session.add(provider)
    cat = DanhMuc(tenDanhMuc=f"AI & Data GĐ6.2 {uuid.uuid4().hex[:6]}", moTa="Machine Learning")
    db_session.add(cat)
    db_session.flush()

    c1 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat.maDanhMuc,
        tieuDe="Python Machine Learning Thực Chiến GĐ6.2",
        moTa="Scikit-learn, Pandas, đánh giá mô hình",
        trinhDo="BEGINNER",
        thoiLuong=120,
        gia=0,
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
    )
    c2 = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat.maDanhMuc,
        tieuDe="Deep Learning với PyTorch GĐ6.2",
        moTa="Mạng nơ-ron và huấn luyện GPU",
        trinhDo="INTERMEDIATE",
        thoiLuong=200,
        gia=399000,
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=datetime(2099, 1, 1),
    )
    db_session.add_all([c1, c2])
    db_session.flush()

    recommendation_service.invalidate_recommendation_cache()
    cold = recommendation_service.recommend_courses(db_session, learner.maNguoiDung, limit=200)
    warm = recommendation_service.recommend_courses(db_session, learner.maNguoiDung, limit=200)

    assert [i.maKhoaHoc for i in cold.items] == [i.maKhoaHoc for i in warm.items]
    assert [i.score for i in cold.items] == [i.score for i in warm.items]
    assert c2.maKhoaHoc in [i.maKhoaHoc for i in warm.items]

    # Hide c2 -> fingerprint must change automatically and exclude c2 from recommendations
    c2.trangThaiHienThi = "HIDDEN"
    db_session.flush()
    after_hide = recommendation_service.recommend_courses(db_session, learner.maNguoiDung, limit=200)
    assert c2.maKhoaHoc not in [i.maKhoaHoc for i in after_hide.items]
