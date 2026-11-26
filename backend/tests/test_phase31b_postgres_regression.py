"""GĐ3.1B PRECHECK-02 (8th split), PRECHECK-07 (Visibility Workflow), and PRECHECK-08 (PostgreSQL Integration Regression).

STRICTLY targets EduSuggest_phase3_test with runtime current_database() guard.
All test data is either rolled back inside a single outer transaction (join_transaction_mode='create_savepoint')
or explicitly cleaned up in finally blocks.
"""
from __future__ import annotations

import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from urllib.parse import urlparse, urlunparse

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

sys.path.insert(0, r"d:\đồ án\EduSuggest\backend")

from models import (  # noqa: E402
    ChuyenGia,
    DanhMuc,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    TaiLieu,
    VaiTro,
)
from schemas.workflow import (  # noqa: E402
    CourseCreateRequest,
    CourseDecisionRequest,
    LessonCreateRequest,
    MaterialCreateRequest,
    MaterialDecisionRequest,
)
from service import workflow_service  # noqa: E402
from service.workflow_service import (  # noqa: E402
    WorkflowConflictError,
    WorkflowForbiddenError,
)


def _build_test_engine():
    load_dotenv(r"d:\đồ án\EduSuggest\backend\.env")
    prod_url = os.getenv("DATABASE_URL") or ""
    p = urlparse(prod_url)
    assert p.path.lstrip("/") == "EduSuggest", "Unexpected .env DB name"
    test_url = urlunparse(p._replace(path="/EduSuggest_phase3_test"))
    eng = create_engine(test_url, pool_pre_ping=True)
    with eng.connect() as c:
        cur = c.execute(text("SELECT current_database()")).scalar()
        assert cur == "EduSuggest_phase3_test", f"SAFETY GUARD ABORT: connected to {cur!r}"
    return eng


TEST_ENGINE = _build_test_engine()


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def pg_db():
    """Outer transaction + SAVEPOINT mode so service db.commit() never persists to test DB."""
    conn = TEST_ENGINE.connect()
    trans = conn.begin()
    assert conn.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


def _create_user(db: Session, role_name: str, *, status: str = "ACTIVE", force_pw: bool = False) -> NguoiDung:
    role = db.scalar(select(VaiTro).where(VaiTro.tenVaiTro == role_name))
    assert role is not None
    tag = uuid.uuid4().hex[:8]
    u = NguoiDung(
        tenTaiKhoan=f"t31b_{role_name.lower()}_{tag}",
        email=f"t31b_{role_name.lower()}_{tag}@example.com",
        matKhau="$2b$12$dummyhashvalueforregressiontest000000000000000000000",
        hoTen=f"Test {role_name} {tag}",
        maVaiTro=role.maVaiTro,
        trangThai=status,
        batBuocDoiMatKhau=force_pw,
    )
    db.add(u)
    db.flush()
    return u


def _create_provider(db: Session) -> tuple[NguoiDung, NhaCungCapKhoaHoc]:
    u = _create_user(db, "PROVIDER")
    p = NhaCungCapKhoaHoc(
        maNguoiDung=u.maNguoiDung,
        tieuSu=f"Bio {u.tenTaiKhoan}",
        chuyenMon="Software Engineering",
    )
    db.add(p)
    db.flush()
    return u, p


def _create_expert(
    db: Session,
    *,
    profile_status: str = "VERIFIED",
    account_status: str = "ACTIVE",
    force_pw: bool = False,
) -> tuple[NguoiDung, ChuyenGia]:
    u = _create_user(db, "EXPERT", status=account_status, force_pw=force_pw)
    e = ChuyenGia(
        maNguoiDung=u.maNguoiDung,
        trangThaiHoSo=profile_status,
        soNamKinhNghiem=5,
        chuyenMon="Backend Engineering",
    )
    db.add(e)
    db.flush()
    return u, e


# =====================================================================
# PRECHECK-07: Full Visibility Workflow Regression on Real PostgreSQL 16
# =====================================================================
def test_precheck07_visibility_workflow_and_check_constraint_on_postgres(pg_db: Session):
    cat = pg_db.scalar(select(DanhMuc).limit(1))
    assert cat is not None
    provider_user, _ = _create_provider(pg_db)
    expert_user, _ = _create_expert(pg_db, profile_status="VERIFIED")

    # 1. PROVIDER creates course (DRAFT / HIDDEN)
    course = workflow_service.create_provider_course(
        pg_db,
        provider_user.maNguoiDung,
        CourseCreateRequest(
            tieuDe="GD3.1B Visibility Workflow Course",
            moTa="Course description for PostgreSQL visibility check",
            maDanhMuc=cat.maDanhMuc,
            gia=Decimal("0"),
            trinhDo="BEGINNER",
            thoiLuong=120,
        ),
    )
    assert course.trangThaiHienThi == "HIDDEN"

    # 2. PROVIDER adds 1 lesson and submits course -> PENDING / HIDDEN
    workflow_service.create_provider_lesson(
        pg_db,
        provider_user.maNguoiDung,
        course.maKhoaHoc,
        LessonCreateRequest(tieuDe="Lesson 1", noiDung="Intro", thuTu=1),
    )
    submitted = workflow_service.submit_provider_course(pg_db, provider_user.maNguoiDung, course.maKhoaHoc)
    assert submitted.trangThaiDuyet == "PENDING"
    assert submitted.trangThaiHienThi == "HIDDEN"

    # 3. DB CHECK ck_KhoaHoc_visible_requires_approved MUST reject PENDING/VISIBLE
    sp = pg_db.begin_nested()
    submitted.trangThaiHienThi = "VISIBLE"
    with pytest.raises(IntegrityError):
        pg_db.flush()
    sp.rollback()

    # 4. EXPERT VERIFIED requests revision -> NEEDS_REVISION / HIDDEN
    rev, _ = workflow_service.decide_course(
        pg_db,
        expert_user.maNguoiDung,
        course.maKhoaHoc,
        CourseDecisionRequest(trangThai="NEEDS_REVISION", ghiChu="Need more detail"),
    )
    assert rev.trangThaiDuyet == "NEEDS_REVISION"
    assert rev.trangThaiHienThi == "HIDDEN"

    # 5. PROVIDER re-submits -> PENDING / HIDDEN
    resub = workflow_service.submit_provider_course(pg_db, provider_user.maNguoiDung, course.maKhoaHoc)
    assert resub.trangThaiDuyet == "PENDING"
    assert resub.trangThaiHienThi == "HIDDEN"

    # 6. EXPERT VERIFIED approves -> APPROVED / HIDDEN, then ADMIN sets VISIBLE & HIDDEN
    appr, _ = workflow_service.decide_course(
        pg_db,
        expert_user.maNguoiDung,
        course.maKhoaHoc,
        CourseDecisionRequest(trangThai="APPROVED", ghiChu="Looks great"),
    )
    assert appr.trangThaiDuyet == "APPROVED"
    vis = workflow_service.set_course_visibility(pg_db, course.maKhoaHoc, "VISIBLE")
    assert vis.trangThaiHienThi == "VISIBLE"
    hid = workflow_service.set_course_visibility(pg_db, course.maKhoaHoc, "HIDDEN")
    assert hid.trangThaiHienThi == "HIDDEN"

    # 7. Create second course and test REJECTED -> cannot set VISIBLE
    c2 = workflow_service.create_provider_course(
        pg_db,
        provider_user.maNguoiDung,
        CourseCreateRequest(
            tieuDe="GD3.1B Rejected Course",
            moTa="Course to reject",
            maDanhMuc=cat.maDanhMuc,
            gia=Decimal("0"),
            trinhDo="BEGINNER",
            thoiLuong=60,
        ),
    )
    workflow_service.create_provider_lesson(
        pg_db,
        provider_user.maNguoiDung,
        c2.maKhoaHoc,
        LessonCreateRequest(tieuDe="Lesson 1", noiDung="Intro", thuTu=1),
    )
    workflow_service.submit_provider_course(pg_db, provider_user.maNguoiDung, c2.maKhoaHoc)
    rej, _ = workflow_service.decide_course(
        pg_db,
        expert_user.maNguoiDung,
        c2.maKhoaHoc,
        CourseDecisionRequest(trangThai="REJECTED", ghiChu="Not eligible"),
    )
    assert rej.trangThaiDuyet == "REJECTED"
    assert rej.trangThaiHienThi == "HIDDEN"
    with pytest.raises(WorkflowForbiddenError):
        workflow_service.set_course_visibility(pg_db, c2.maKhoaHoc, "VISIBLE")


# =====================================================================
# PRECHECK-08: SEC-01, SEC-03, SEC-04, SEC-05 & Material Integrity on PG
# =====================================================================
def test_precheck08_sec01_sec03_sec04_sec05_material_workflow_on_postgres(pg_db: Session):
    cat = pg_db.scalar(select(DanhMuc).limit(1))
    provider_user, _ = _create_provider(pg_db)
    draft_expert, _ = _create_expert(pg_db, profile_status="DRAFT")
    locked_expert, _ = _create_expert(pg_db, profile_status="VERIFIED", account_status="LOCKED")
    force_pw_expert, _ = _create_expert(pg_db, profile_status="VERIFIED", force_pw=True)
    verified_expert, _ = _create_expert(pg_db, profile_status="VERIFIED")

    # SEC-01: unverified, locked, force_pw experts MUST be blocked (WorkflowForbiddenError)
    for blocked in (draft_expert, locked_expert, force_pw_expert):
        with pytest.raises(WorkflowForbiddenError):
            workflow_service.list_expert_courses(pg_db, blocked.maNguoiDung)
        with pytest.raises(WorkflowForbiddenError):
            workflow_service.list_expert_materials(pg_db, blocked.maNguoiDung)

    # Verified expert is allowed
    pending_courses = workflow_service.list_expert_courses(pg_db, verified_expert.maNguoiDung)
    assert isinstance(pending_courses, list)

    # SEC-03: KhoaHoc #28 (PENDING/HIDDEN) and TaiLieu #132 (PENDING/HIDDEN) are NOT public
    public_c28 = pg_db.scalar(
        select(KhoaHoc).where(
            KhoaHoc.maKhoaHoc == 28,
            KhoaHoc.trangThaiDuyet == "APPROVED",
            KhoaHoc.trangThaiHienThi == "VISIBLE",
        )
    )
    public_m132 = pg_db.scalar(
        select(TaiLieu).where(
            TaiLieu.maTaiLieu == 132,
            TaiLieu.trangThaiDuyet == "APPROVED",
            TaiLieu.trangThaiHienThi == "VISIBLE",
        )
    )
    assert public_c28 is None
    assert public_m132 is None

    # SEC-04: Standalone material without category can be drafted, but MUST be rejected on submit
    draft_no_cat = workflow_service.create_provider_standalone_material(
        pg_db,
        provider_user.maNguoiDung,
        MaterialCreateRequest(
            tieuDe="No Cat Material",
            moTa="Missing category",
            loai="PDF",
            duongDanTep="https://example.com/mat.pdf",
            maDanhMuc=None,
            maKhoaHoc=None,
        ),
    )
    with pytest.raises(WorkflowConflictError):
        workflow_service.submit_provider_material(pg_db, provider_user.maNguoiDung, draft_no_cat.maTaiLieu)

    mat = workflow_service.create_provider_standalone_material(
        pg_db,
        provider_user.maNguoiDung,
        MaterialCreateRequest(
            tieuDe="Valid Standalone Material 31B",
            moTa="Valid category",
            loai="PDF",
            duongDanTep="https://example.com/mat-31b.pdf",
            maDanhMuc=cat.maDanhMuc,
            maKhoaHoc=None,
        ),
    )
    mat_sub = workflow_service.submit_provider_material(pg_db, provider_user.maNguoiDung, mat.maTaiLieu)
    assert mat_sub.trangThaiDuyet == "PENDING"
    mat_appr, _ = workflow_service.decide_material(
        pg_db,
        verified_expert.maNguoiDung,
        mat.maTaiLieu,
        MaterialDecisionRequest(trangThai="APPROVED", ghiChu="Approved in 31B"),
    )
    assert mat_appr.trangThaiDuyet == "APPROVED"

    # SEC-05: list_admin_experts excludes non-EXPERT role (ChuyenGia #4 is USER role);
    # list_expert_candidates excludes DRAFT/LOCKED/force_pw and includes verified_expert
    admin_experts = workflow_service.list_admin_experts(pg_db)
    assert all((cg is None or cg.maChuyenGia != 4) for _, cg in admin_experts)
    candidates = workflow_service.list_expert_candidates(pg_db)
    cand_uids = {item["user"].maNguoiDung for item in candidates}
    assert verified_expert.maNguoiDung in cand_uids
    assert draft_expert.maNguoiDung not in cand_uids
    assert locked_expert.maNguoiDung not in cand_uids
    assert force_pw_expert.maNguoiDung not in cand_uids


# =====================================================================
# PRECHECK-02: Explicit Independent Concurrency Proof for Invariants #7 & #8
# =====================================================================
def test_precheck02_independent_concurrency_vipham_and_thongbao():
    """Explicitly separates ViPhamChuyenGia.maPhanCong (#7) and ThongBao.khoaChongTrung (#8)."""
    with TEST_ENGINE.connect() as c:
        assert c.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
        expert_id = int(c.execute(text('SELECT "maChuyenGia" FROM "ChuyenGia" LIMIT 1')).scalar())
        expert_uid = int(
            c.execute(
                text('SELECT "maNguoiDung" FROM "ChuyenGia" WHERE "maChuyenGia" = :eid'),
                {"eid": expert_id},
            ).scalar()
        )
        course_id = int(c.execute(text('SELECT "maKhoaHoc" FROM "KhoaHoc" LIMIT 1')).scalar())
        cat_id = int(
            c.execute(
                text('SELECT "maDanhMuc" FROM "KhoaHoc" WHERE "maKhoaHoc" = :cid'),
                {"cid": course_id},
            ).scalar()
        )

    now = _now_utc()
    created_pc_id = None
    created_vp_ids: list[int] = []
    created_tb_ids: list[int] = []

    try:
        with TEST_ENGINE.begin() as conn:
            created_pc_id = int(
                conn.execute(
                    text(
                        'INSERT INTO "PhanCongKiemDuyet" '
                        '("maKhoaHoc","maChuyenGia","maDanhMuc","soVongKiemDuyet","phuongThucPhanCong",'
                        '"trangThai","ngayPhanCong","hanTiepNhan") '
                        'VALUES (:cid,:eid,:cat,99,\'AUTO\',\'EXPIRED\',:now,:dl) RETURNING "maPhanCong"'
                    ),
                    {"cid": course_id, "eid": expert_id, "cat": cat_id, "now": now, "dl": now + timedelta(hours=24)},
                ).scalar()
            )

        # Invariant #7: ViPhamChuyenGia.maPhanCong UNIQUE under 2 concurrent connections
        b7 = Barrier(2)

        def _race_vipham():
            with TEST_ENGINE.connect() as conn:
                b7.wait()
                try:
                    vid = conn.execute(
                        text(
                            'INSERT INTO "ViPhamChuyenGia" ("maChuyenGia","maPhanCong","loaiViPham") '
                            'VALUES (:eid,:pcid,\'EXPIRED_ACCEPTANCE\') RETURNING "maViPham"'
                        ),
                        {"eid": expert_id, "pcid": created_pc_id},
                    ).scalar()
                    conn.commit()
                    return ("OK", int(vid))
                except IntegrityError:
                    conn.rollback()
                    return ("UNIQUE_VIOLATION", None)

        with ThreadPoolExecutor(max_workers=2) as pool:
            r7 = [f.result() for f in [pool.submit(_race_vipham), pool.submit(_race_vipham)]]
        statuses7 = sorted(x[0] for x in r7)
        created_vp_ids.extend(x[1] for x in r7 if x[1] is not None)
        assert statuses7 == ["OK", "UNIQUE_VIOLATION"], f"Invariant #7 failed: {r7}"

        # Invariant #8: ThongBao.khoaChongTrung UNIQUE under 2 concurrent connections (recipient-scoped key)
        b8 = Barrier(2)
        idem_key = f"ACC_L1:E{expert_id}:C1:V{created_vp_ids[0]}:TO:{expert_uid}:{uuid.uuid4().hex[:6]}"

        def _race_thongbao():
            with TEST_ENGINE.connect() as conn:
                b8.wait()
                try:
                    tid = conn.execute(
                        text(
                            'INSERT INTO "ThongBao" ("maNguoiNhan","loaiThongBao","tieuDe","noiDung","khoaChongTrung") '
                            'VALUES (:uid,\'ACCOUNTABILITY\',\'Test\',\'Body\',:k) RETURNING "maThongBao"'
                        ),
                        {"uid": expert_uid, "k": idem_key},
                    ).scalar()
                    conn.commit()
                    return ("OK", int(tid))
                except IntegrityError:
                    conn.rollback()
                    return ("UNIQUE_VIOLATION", None)

        with ThreadPoolExecutor(max_workers=2) as pool:
            r8 = [f.result() for f in [pool.submit(_race_thongbao), pool.submit(_race_thongbao)]]
        statuses8 = sorted(x[0] for x in r8)
        created_tb_ids.extend(x[1] for x in r8 if x[1] is not None)
        assert statuses8 == ["OK", "UNIQUE_VIOLATION"], f"Invariant #8 failed: {r8}"

    finally:
        with TEST_ENGINE.begin() as conn:
            for tid in created_tb_ids:
                conn.execute(text('DELETE FROM "ThongBao" WHERE "maThongBao" = :id'), {"id": tid})
            for vid in created_vp_ids:
                conn.execute(text('DELETE FROM "ViPhamChuyenGia" WHERE "maViPham" = :id'), {"id": vid})
            if created_pc_id is not None:
                conn.execute(
                    text('DELETE FROM "PhanCongKiemDuyet" WHERE "maPhanCong" = :id'),
                    {"id": created_pc_id},
                )
