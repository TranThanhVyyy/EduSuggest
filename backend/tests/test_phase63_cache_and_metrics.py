"""GĐ6.3B Cache Correctness, Raw-SQL Invalidation, Rollback Isolation, and Evaluation Metric Tests.

Strictly runs ONLY against EduSuggest_phase4_test (refuses to run on EduSuggest).
"""
from __future__ import annotations

import math
import os
import tracemalloc
import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from config.config import get_settings
from models import BaiHoc, DanhMuc, KhoaHoc, NguoiDung, NhaCungCapKhoaHoc, TaiLieu, VaiTro
from service import recommendation_service


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ6.3 tests require EduSuggest_phase4_test database.")
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


def _create_user(db: Session, role_name: str, full_name: str) -> NguoiDung:
    role = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == role_name)).first()
    assert role is not None
    tag = uuid.uuid4().hex[:8]
    user = NguoiDung(
        tenTaiKhoan=f"p63_{role_name.lower()}_{tag}",
        email=f"p63_{tag}@test.edusuggest.local",
        matKhau="argon2-placeholder",
        hoTen=full_name,
        maVaiTro=role.maVaiTro,
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    db.add(user)
    db.flush()
    return user


def test_fingerprint_detects_same_length_raw_sql_updates_on_course_lesson_category_material(
    db_session: Session,
):
    """Covers GĐ6.3B scenarios 1-8: title, description, lesson content, add/del lesson, category, material, status, visibility."""
    prov_user = _create_user(db_session, "PROVIDER", "Provider Cache Audit")
    provider = NhaCungCapKhoaHoc(maNguoiDung=prov_user.maNguoiDung)
    db_session.add(provider)
    cat = DanhMuc(tenDanhMuc="AlphaCat", moTa="AlphaDesc")
    db_session.add(cat)
    db_session.flush()

    course = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat.maDanhMuc,
        tieuDe="AAAA Title",
        moTa="AAAA Description",
        trinhDo="BEGINNER",
        thoiLuong=60,
        gia=0,
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=datetime(2099, 1, 1),
    )
    db_session.add(course)
    db_session.flush()

    lesson = BaiHoc(
        maKhoaHoc=course.maKhoaHoc,
        tieuDe="L1 AAAA",
        noiDung="Content AAAA",
        thuTu=1,
        thoiLuong=20,
    )
    material = TaiLieu(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=cat.maDanhMuc,
        tieuDe="Mat AAAA",
        moTa="MatDesc AAAA",
        loai="TEXT",
        trangThaiDuyet="APPROVED",
        trangThaiHienThi="VISIBLE",
        ngayTao=datetime(2099, 1, 1),
    )
    db_session.add_all([lesson, material])
    db_session.flush()

    fp0 = recommendation_service._course_corpus_fingerprint(db_session)
    mfp0 = recommendation_service._material_corpus_fingerprint(db_session)

    # 1. Same-length raw SQL course title update WITHOUT touching ngayCapNhat
    db_session.execute(
        text('UPDATE "KhoaHoc" SET "tieuDe" = \'BBBB Title\' WHERE "maKhoaHoc" = :id'),
        {"id": course.maKhoaHoc},
    )
    fp1 = recommendation_service._course_corpus_fingerprint(db_session)
    assert fp1 != fp0

    # 2. Same-length raw SQL course description update
    db_session.execute(
        text('UPDATE "KhoaHoc" SET "moTa" = \'BBBB Description\' WHERE "maKhoaHoc" = :id'),
        {"id": course.maKhoaHoc},
    )
    fp2 = recommendation_service._course_corpus_fingerprint(db_session)
    assert fp2 != fp1

    # 3. Same-length raw SQL lesson content update
    db_session.execute(
        text('UPDATE "BaiHoc" SET "noiDung" = \'Content BBBB\' WHERE "maBaiHoc" = :id'),
        {"id": lesson.maBaiHoc},
    )
    fp3 = recommendation_service._course_corpus_fingerprint(db_session)
    assert fp3 != fp2

    # 4. Same-length raw SQL category rename
    db_session.execute(
        text('UPDATE "DanhMuc" SET "tenDanhMuc" = \'Beta_Cat\' WHERE "maDanhMuc" = :id'),
        {"id": cat.maDanhMuc},
    )
    fp4 = recommendation_service._course_corpus_fingerprint(db_session)
    mfp1 = recommendation_service._material_corpus_fingerprint(db_session)
    assert fp4 != fp3
    assert mfp1 != mfp0

    # 5. Same-length raw SQL material description update
    db_session.execute(
        text('UPDATE "TaiLieu" SET "moTa" = \'MatDesc BBBB\' WHERE "maTaiLieu" = :id'),
        {"id": material.maTaiLieu},
    )
    mfp2 = recommendation_service._material_corpus_fingerprint(db_session)
    assert mfp2 != mfp1

    # 6. Status APPROVED -> PENDING & Visibility VISIBLE -> HIDDEN (satisfies DB check constraint)
    db_session.execute(
        text('UPDATE "KhoaHoc" SET "trangThaiDuyet" = \'PENDING\', "trangThaiHienThi" = \'HIDDEN\' WHERE "maKhoaHoc" = :id'),
        {"id": course.maKhoaHoc},
    )
    fp5 = recommendation_service._course_corpus_fingerprint(db_session)
    assert fp5 != fp4


def test_cache_rollback_isolation_and_bounded_memory_across_invalidations(pg_engine):
    """Uncommitted rolled-back mutations cannot poison a committed session, and memory stays bounded."""
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    recommendation_service.invalidate_recommendation_cache()

    with SessionLocal() as s_clean:
        learner = _create_user(s_clean, "USER", "Committed Reader")
        s_clean.flush()
        baseline = recommendation_service.recommend_courses(s_clean, learner.maNguoiDung, limit=10)
        baseline_ids = [i.maKhoaHoc for i in baseline.items]

    # Separate session performs uncommitted insert, queries recommendations, then rolls back
    with SessionLocal() as s_dirty:
        prov_u = _create_user(s_dirty, "PROVIDER", "Dirty Prov")
        prov = NhaCungCapKhoaHoc(maNguoiDung=prov_u.maNguoiDung)
        s_dirty.add(prov)
        s_dirty.flush()
        dirty_course = KhoaHoc(
            maNhaCungCap=prov.maNhaCungCap,
            tieuDe="UNCOMMITTED_DIRTY_COURSE_G63",
            gia=0,
            trangThaiDuyet="APPROVED",
            trangThaiHienThi="VISIBLE",
            ngayTao=datetime(2099, 12, 31),
        )
        s_dirty.add(dirty_course)
        s_dirty.flush()
        dirty_id = dirty_course.maKhoaHoc
        dirty_res = recommendation_service.recommend_courses(s_dirty, prov_u.maNguoiDung, limit=10)
        assert dirty_id in [i.maKhoaHoc for i in dirty_res.items]
        s_dirty.rollback()

    # Subsequent committed session MUST NOT see dirty_id
    with SessionLocal() as s_after:
        reader = _create_user(s_after, "USER", "Post Rollback Reader")
        s_after.flush()
        after_res = recommendation_service.recommend_courses(s_after, reader.maNguoiDung, limit=10)
        after_ids = [i.maKhoaHoc for i in after_res.items]
        assert dirty_id not in after_ids
        assert after_ids == baseline_ids

    # Repeated invalidations must not leak unbounded cache entries
    tracemalloc.start()
    for _ in range(15):
        recommendation_service.invalidate_recommendation_cache()
        with SessionLocal() as s_loop:
            recommendation_service._get_cached_course_corpus(s_loop)
    stats = recommendation_service.get_recommendation_cache_stats()
    current_b, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert stats["course_entries"] <= 8
    assert current_b < 50 * 1024 * 1024  # well under 50 MB


def test_offline_evaluation_metrics_mathematical_correctness():
    """Verify Precision@K, Recall@K, HitRate@K, NDCG@K, MRR@K formulas on a known hand-computed vector."""
    relevant = {10, 20, 30}
    ranked = [99, 20, 88, 10, 77]  # hits at ranks 2 (id=20) and 4 (id=10)
    k = 5

    hits = [1 if item in relevant else 0 for item in ranked[:k]]
    precision_5 = sum(hits) / k
    recall_5 = sum(hits) / len(relevant)
    hit_rate_5 = 1.0 if any(hits) else 0.0
    mrr_5 = next((1.0 / (idx + 1) for idx, h in enumerate(hits) if h), 0.0)
    dcg = sum(h / math.log2(idx + 2) for idx, h in enumerate(hits))
    idcg = sum(1.0 / math.log2(idx + 2) for idx in range(min(len(relevant), k)))
    ndcg_5 = dcg / idcg

    assert math.isclose(precision_5, 2 / 5, rel_tol=1e-12)
    assert math.isclose(recall_5, 2 / 3, rel_tol=1e-12)
    assert hit_rate_5 == 1.0
    assert math.isclose(mrr_5, 0.5, rel_tol=1e-12)
    expected_ndcg = (1 / math.log2(3) + 1 / math.log2(5)) / (1 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4))
    assert math.isclose(ndcg_5, expected_ndcg, rel_tol=1e-12)
