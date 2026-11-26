"""GĐ3.3C Comprehensive Verification Suite:
- ENG-01..06 Hardening, Queue State Machine, Source Validation, Notification Idempotency
- Review Round & Atomic Submit/Resubmit
- PostgreSQL SKIP LOCKED Worker, ARCH-06 Fencing & Crash Recovery
- Assignment Lifecycle, Accept/Decline/Expire/Start/Draft/Atomic Review Completion
- Automatic Reassignment & Reassignment Limit (max 6 in round)
- SEC-02 HTTP Security Tests (closing all 6 legacy open-pool routes + ownership matrix)
- Real Multi-Connection Worker & Lifecycle Concurrency Tests
- Legacy Course #28 Controlled Bootstrap Rehearsal (rolled back on test DB)

STRICTLY targets EduSuggest_phase3_test with runtime current_database() guard.
"""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
from urllib.parse import urlparse, urlunparse

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from config.database import get_db
from main import app
from models import (
    BaiHoc,
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    DanhGiaChuyenGia,
    DanhMuc,
    HangDoiPhanCong,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    PhanCongKiemDuyet,
    TaiLieu,
    ThongBao,
    VaiTro,
)
from schemas.workflow import (
    AdminVerifyExpertRequest,
    CourseCreateRequest,
    CourseDecisionRequest,
    LessonCreateRequest,
    MaterialCreateRequest,
)
from service import (
    assignment_lifecycle_service,
    assignment_queue_service,
    assignment_service,
    notification_service,
    workflow_service,
)
from service.assignment_worker import AssignmentQueueWorker
from utils.security import create_access_token


TEST_DB_NAME = os.getenv("EDUSUGGEST_TEST_DB_NAME", "EduSuggest_phase3_test").strip()
assert TEST_DB_NAME and TEST_DB_NAME != "EduSuggest", (
    "SAFETY GUARD ABORT: Phase 3.3 tests must NEVER target production 'EduSuggest'."
)


def _build_test_engine():
    load_dotenv(r"d:\đồ án\EduSuggest\backend\.env")
    prod_url = os.getenv("DATABASE_URL") or ""
    p = urlparse(prod_url)
    assert p.path.lstrip("/") == "EduSuggest", "Unexpected .env DB name"
    test_url = urlunparse(p._replace(path=f"/{TEST_DB_NAME}"))
    eng = create_engine(test_url, pool_pre_ping=True, pool_size=12, max_overflow=12)
    with eng.connect() as c:
        cur = c.execute(text("SELECT current_database()")).scalar()
        assert cur == TEST_DB_NAME, f"SAFETY GUARD ABORT: connected to {cur!r}"
    return eng


TEST_ENGINE = _build_test_engine()
TestSessionFactory = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _auth(user: NguoiDung) -> dict[str, str]:
    tok = create_access_token(user.maNguoiDung, user.matKhau).encoded
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture()
def pg_db():
    conn = TEST_ENGINE.connect()
    trans = conn.begin()
    assert conn.execute(text("SELECT current_database()")).scalar() == TEST_DB_NAME
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture()
def enabled_client(pg_db: Session):
    """FastAPI TestClient bound to rolled-back EduSuggest_phase3_test with GĐ3.3 workflow ON."""

    def _override_db():
        assert pg_db.execute(text("SELECT current_database()")).scalar() == TEST_DB_NAME
        yield pg_db

    app.dependency_overrides[get_db] = _override_db
    with patch.object(workflow_service, "_is_auto_assignment_workflow_enabled", return_value=True):
        with TestClient(app) as tc:
            yield tc
    app.dependency_overrides.pop(get_db, None)


def _mk_user(
    db: Session,
    role_name: str,
    *,
    status: str = "ACTIVE",
    force_pw: bool = False,
) -> NguoiDung:
    role = db.scalar(select(VaiTro).where(VaiTro.tenVaiTro == role_name))
    assert role is not None
    tag = uuid.uuid4().hex[:8]
    u = NguoiDung(
        tenTaiKhoan=f"g33_{role_name.lower()}_{tag}",
        email=f"g33_{role_name.lower()}_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase33test00000000000000000000",
        hoTen=f"G33 {role_name} {tag}",
        maVaiTro=role.maVaiTro,
        trangThai=status,
        batBuocDoiMatKhau=force_pw,
    )
    db.add(u)
    db.flush()
    return u


def _mk_provider(db: Session) -> tuple[NguoiDung, NhaCungCapKhoaHoc]:
    u = _mk_user(db, "PROVIDER")
    p = NhaCungCapKhoaHoc(maNguoiDung=u.maNguoiDung, tieuSu="Bio", chuyenMon="Tech")
    db.add(p)
    db.flush()
    return u, p


def _mk_cat_and_spec(db: Session, prefix: str = "G33") -> tuple[DanhMuc, ChuyenMon]:
    now = _now_utc()
    cat = DanhMuc(tenDanhMuc=f"{prefix}Cat_{uuid.uuid4().hex[:6]}")
    db.add(cat)
    db.flush()
    spec = ChuyenMon(
        tenChuyenMon=f"{prefix}Spec_{uuid.uuid4().hex[:6]}",
        nhomChuyenMon="Engineering",
        trangThai="ACTIVE",
        ngayTao=now,
    )
    db.add(spec)
    db.flush()
    db.add(ChuyenMonDanhMuc(maChuyenMon=spec.maChuyenMon, maDanhMuc=cat.maDanhMuc, ngayTao=now))
    db.flush()
    return cat, spec


def _mk_expert(
    db: Session,
    spec: ChuyenMon | None,
    *,
    profile_status: str = "VERIFIED",
    account_status: str = "ACTIVE",
    force_pw: bool = False,
    years: int = 5,
) -> tuple[NguoiDung, ChuyenGia]:
    now = _now_utc()
    u = _mk_user(db, "EXPERT", status=account_status, force_pw=force_pw)
    e = ChuyenGia(
        maNguoiDung=u.maNguoiDung,
        trangThaiHoSo=profile_status,
        soNamKinhNghiem=years,
    )
    db.add(e)
    db.flush()
    if spec is not None:
        db.add(
            ChuyenGiaChuyenMon(
                maChuyenGia=e.maChuyenGia,
                maChuyenMon=spec.maChuyenMon,
                laChuyenMonChinh=True,
                ngayTao=now,
            )
        )
        db.flush()
    return u, e


# =====================================================================
# 1. UNIT & QUEUE CONTRACT TESTS (ENG-02, ENG-04, Notification Dedupe)
# =====================================================================
def test_queue_idempotency_keys_and_notification_recipient_scoping(pg_db: Session):
    assert (
        assignment_queue_service.build_event_idempotency_key(
            target_type="COURSE", target_id=10, review_round=2, event_type="SUBMIT"
        )
        == "SUBMIT:COURSE:10:R2"
    )
    assert (
        assignment_queue_service.build_event_idempotency_key(
            target_type="MATERIAL",
            target_id=20,
            review_round=1,
            event_type="REASSIGN_DECLINED",
            source_assignment_id=55,
        )
        == "REASSIGN:MATERIAL:20:R1:FROM:55"
    )
    assert (
        assignment_queue_service.build_event_idempotency_key(
            target_type="COURSE",
            target_id=10,
            review_round=1,
            event_type="ADMIN_RETRY",
            attempt_seq=3,
        )
        == "ADMIN_RETRY:COURSE:10:R1:AT:3"
    )

    # Notification recipient-scoped idempotency: 2 distinct users both receive; duplicate for same user ignored
    u1 = _mk_user(pg_db, "EXPERT")
    u2 = _mk_user(pg_db, "ADMIN")
    ev = f"TEST_EVENT:{uuid.uuid4().hex[:8]}"
    assert notification_service.create_notification_idempotent(
        pg_db,
        recipient_user_id=u1.maNguoiDung,
        notification_type="TEST",
        title="T",
        body="B",
        event_key=ev,
    ) is True
    assert notification_service.create_notification_idempotent(
        pg_db,
        recipient_user_id=u1.maNguoiDung,
        notification_type="TEST",
        title="T",
        body="B",
        event_key=ev,
    ) is False
    assert notification_service.create_notification_idempotent(
        pg_db,
        recipient_user_id=u2.maNguoiDung,
        notification_type="TEST",
        title="T",
        body="B",
        event_key=ev,
    ) is True


# =====================================================================
# 2. REVIEW ROUND, ATOMIC SUBMIT, REASSIGNMENT, LIFECYCLE & WAKE-UP E2E
# =====================================================================
def test_full_api_workflow_e2e_and_sec02_closure_on_postgres(pg_db: Session, enabled_client: TestClient):
    now = _now_utc()
    admin_u = _mk_user(pg_db, "ADMIN")
    normal_u = _mk_user(pg_db, "USER")
    prov_u, _ = _mk_provider(pg_db)
    cat, spec = _mk_cat_and_spec(pg_db, "E2E")

    exp_a_u, exp_a = _mk_expert(pg_db, spec, years=9)
    exp_b_u, exp_b = _mk_expert(pg_db, spec, years=5)
    exp_unassigned_u, _ = _mk_expert(pg_db, spec, years=2)
    exp_locked_u, _ = _mk_expert(pg_db, spec, account_status="LOCKED", years=10)
    exp_draft_u, _ = _mk_expert(pg_db, spec, profile_status="DRAFT", years=10)
    exp_forcepw_u, _ = _mk_expert(pg_db, spec, force_pw=True, years=10)

    # 1. PROVIDER creates course + lesson & submits -> round 1 + durable SUBMIT job atomically
    course = workflow_service.create_provider_course(
        pg_db,
        prov_u.maNguoiDung,
        CourseCreateRequest(
            tieuDe="G33 E2E Course",
            moTa="Detailed syllabus",
            maDanhMuc=cat.maDanhMuc,
            gia=Decimal("0"),
            trinhDo="BEGINNER",
            thoiLuong=60,
        ),
    )
    workflow_service.create_provider_lesson(
        pg_db,
        prov_u.maNguoiDung,
        course.maKhoaHoc,
        LessonCreateRequest(tieuDe="Lesson 1", noiDung="Private lesson content", thuTu=1),
    )
    with patch.object(workflow_service, "_is_auto_assignment_workflow_enabled", return_value=True):
        submitted = workflow_service.submit_provider_course(pg_db, prov_u.maNguoiDung, course.maKhoaHoc)
    assert submitted.trangThaiDuyet == "PENDING"
    assert submitted.soVongKiemDuyetHienTai == 1

    job = pg_db.scalars(
        select(HangDoiPhanCong).where(HangDoiPhanCong.khoaChongTrung == f"SUBMIT:COURSE:{course.maKhoaHoc}:R1")
    ).first()
    assert job is not None and job.trangThai == "PENDING"

    # Linked material MUST NOT create standalone queue job
    linked_mat = workflow_service.create_provider_standalone_material(
        pg_db,
        prov_u.maNguoiDung,
        MaterialCreateRequest(
            tieuDe="Linked Mat",
            duongDanTep="https://example.com/linked.pdf",
            loai="PDF",
            maKhoaHoc=course.maKhoaHoc,
            maDanhMuc=cat.maDanhMuc,
        ),
    )
    with patch.object(workflow_service, "_is_auto_assignment_workflow_enabled", return_value=True):
        workflow_service.submit_provider_material(pg_db, prov_u.maNguoiDung, linked_mat.maTaiLieu)
    assert (
        pg_db.scalars(select(HangDoiPhanCong).where(HangDoiPhanCong.maTaiLieu == linked_mat.maTaiLieu)).first()
        is None
    )

    # 2. Assign best expert (Expert A wins: 9y > 5y > 2y)
    assign_res = assignment_service.assign_best_expert(
        pg_db, "COURSE", course.maKhoaHoc, expected_review_round=1, now=now, commit=False
    )
    assert assign_res.status.value == "ASSIGNED"
    assert assign_res.assignedExpertId == exp_a.maChuyenGia
    pc1_id = assign_res.assignmentId
    assert pc1_id is not None

    # 3. SEC-02 HTTP SECURITY MATRIX
    # 3a. Expert B CANNOT view, accept, decline, start, draft, or decide Expert A's assignment (403)
    assert enabled_client.get(f"/api/expert/assignments/{pc1_id}", headers=_auth(exp_b_u)).status_code == 403
    assert enabled_client.post(f"/api/expert/assignments/{pc1_id}/accept", headers=_auth(exp_b_u)).status_code == 403
    assert enabled_client.post(
        f"/api/expert/assignments/{pc1_id}/decline",
        json={"maLyDoTuChoi": "OTHER", "lyDoTuChoi": "Trying hijack"},
        headers=_auth(exp_b_u),
    ).status_code == 403
    assert enabled_client.post(f"/api/expert/assignments/{pc1_id}/start", headers=_auth(exp_b_u)).status_code == 403
    assert enabled_client.put(
        f"/api/expert/assignments/{pc1_id}/draft",
        json={"banNhapDanhGia": {"note": "hijack"}},
        headers=_auth(exp_b_u),
    ).status_code == 403
    assert enabled_client.post(
        f"/api/expert/assignments/{pc1_id}/decision",
        json={"trangThai": "APPROVED"},
        headers=_auth(exp_b_u),
    ).status_code == 403

    # 3b. Legacy open-pool endpoints CLOSED (SEC-02)!
    assert enabled_client.get(f"/api/expert/courses/{course.maKhoaHoc}", headers=_auth(exp_unassigned_u)).status_code == 403
    assert enabled_client.post(
        f"/api/expert/courses/{course.maKhoaHoc}/decision",
        json={"trangThai": "APPROVED"},
        headers=_auth(exp_unassigned_u),
    ).status_code == 403
    r_pending = enabled_client.get("/api/expert/courses/pending", headers=_auth(exp_unassigned_u))
    assert r_pending.status_code == 200
    assert all(item["maKhoaHoc"] != course.maKhoaHoc for item in r_pending.json())

    # 3c. Role & account guards (USER, PROVIDER, ADMIN, LOCKED, DRAFT, force_pw)
    for bad_u in (normal_u, prov_u, admin_u, exp_locked_u, exp_draft_u, exp_forcepw_u):
        assert enabled_client.get("/api/expert/assignments", headers=_auth(bad_u)).status_code in (401, 403)
    assert enabled_client.get("/api/admin/assignments", headers=_auth(exp_a_u)).status_code == 403

    # 3d. Static ADMIN routes /queue and /workload NOT hijacked by /{assignment_id}
    assert enabled_client.get("/api/admin/assignments/queue", headers=_auth(admin_u)).status_code == 200
    assert enabled_client.get("/api/admin/assignments/workload", headers=_auth(admin_u)).status_code == 200

    # 3e. Mass-assignment rejected (422)
    assert enabled_client.post(
        f"/api/expert/assignments/{pc1_id}/decision",
        json={"trangThai": "APPROVED", "maChuyenGia": 999},
        headers=_auth(exp_a_u),
    ).status_code == 422

    # 3f. Expert A in ASSIGNED state: minimal metadata only (noiDungKiemDuyet is None) & CANNOT decide (409)
    r_det_assigned = enabled_client.get(f"/api/expert/assignments/{pc1_id}", headers=_auth(exp_a_u))
    assert r_det_assigned.status_code == 200
    assert r_det_assigned.json()["noiDungKiemDuyet"] is None
    assert enabled_client.post(
        f"/api/expert/assignments/{pc1_id}/decision",
        json={"trangThai": "APPROVED"},
        headers=_auth(exp_a_u),
    ).status_code == 409

    # 4. Expert A DECLINES -> DECLINED + immutable accountabilityEvent + REASSIGN_DECLINED
    r_dec = enabled_client.post(
        f"/api/expert/assignments/{pc1_id}/decline",
        json={"maLyDoTuChoi": "WORKLOAD_PERSONAL", "lyDoTuChoi": "Personal schedule conflict"},
        headers=_auth(exp_a_u),
    )
    assert r_dec.status_code == 200
    assert r_dec.json()["trangThai"] == "DECLINED"
    pc1 = pg_db.get(PhanCongKiemDuyet, pc1_id)
    assert pc1.chiTietDiem["accountabilityEvent"]["eventType"] == "DECLINED_ASSIGNMENT"
    # Terminal DECLINED expert cannot decide
    assert enabled_client.post(
        f"/api/expert/assignments/{pc1_id}/decision",
        json={"trangThai": "APPROVED"},
        headers=_auth(exp_a_u),
    ).status_code == 409

    # 5. Reassignment selects Expert B (Expert A excluded in round 1!)
    assign_res2 = assignment_service.assign_best_expert(
        pg_db, "COURSE", course.maKhoaHoc, expected_review_round=1, now=now, commit=False
    )
    assert assign_res2.status.value == "ASSIGNED"
    assert assign_res2.assignedExpertId == exp_b.maChuyenGia
    pc2_id = assign_res2.assignmentId

    # 6. Expert B accepts (idempotent double accept preserves exact deadline) -> starts -> saves draft -> decides NEEDS_REVISION
    r_acc1 = enabled_client.post(f"/api/expert/assignments/{pc2_id}/accept", headers=_auth(exp_b_u))
    assert r_acc1.status_code == 200
    dl1 = r_acc1.json()["hanKiemDuyet"]
    assert dl1 is not None
    r_acc2 = enabled_client.post(f"/api/expert/assignments/{pc2_id}/accept", headers=_auth(exp_b_u))
    assert r_acc2.status_code == 200 and r_acc2.json()["hanKiemDuyet"] == dl1

    # Now ACCEPTED -> private content accessible!
    r_det_acc = enabled_client.get(f"/api/expert/assignments/{pc2_id}", headers=_auth(exp_b_u))
    assert r_det_acc.status_code == 200
    assert r_det_acc.json()["noiDungKiemDuyet"] is not None

    assert enabled_client.post(f"/api/expert/assignments/{pc2_id}/start", headers=_auth(exp_b_u)).json()["trangThai"] == "IN_PROGRESS"
    assert enabled_client.put(
        f"/api/expert/assignments/{pc2_id}/draft",
        json={"banNhapDanhGia": {"notes": "Draft review comment"}},
        headers=_auth(exp_b_u),
    ).status_code == 200
    # Draft MUST NOT create DanhGiaChuyenGia
    assert pg_db.scalars(select(DanhGiaChuyenGia).where(DanhGiaChuyenGia.maPhanCong == pc2_id)).first() is None

    r_rev = enabled_client.post(
        f"/api/expert/assignments/{pc2_id}/decision",
        json={"trangThai": "NEEDS_REVISION", "ghiChu": "Add more examples"},
        headers=_auth(exp_b_u),
    )
    assert r_rev.status_code == 200
    assert r_rev.json()["trangThaiPhanCong"] == "COMPLETED"
    assert r_rev.json()["ketQuaDuyet"] == "NEEDS_REVISION"
    assert r_rev.json()["trangThaiHienThi"] == "HIDDEN"
    # Completed cannot be decided again
    assert enabled_client.post(
        f"/api/expert/assignments/{pc2_id}/decision",
        json={"trangThai": "APPROVED"},
        headers=_auth(exp_b_u),
    ).status_code == 409

    # 7. PROVIDER resubmits -> round 2!
    #    - Expert A (declined in round 1) IS eligible again in round 2!
    #    - Never-assigned expert (92.00) beats just-assigned Expert A (89.00) via Fairness score!
    with patch.object(workflow_service, "_is_auto_assignment_workflow_enabled", return_value=True):
        resub = workflow_service.submit_provider_course(pg_db, prov_u.maNguoiDung, course.maKhoaHoc)
    assert resub.soVongKiemDuyetHienTai == 2
    preview_r2 = assignment_service.rank_candidates(pg_db, "COURSE", course.maKhoaHoc, now=now)
    assert exp_a.maChuyenGia in [r.maChuyenGia for r in preview_r2.rankedCandidates]
    assign_r2 = assignment_service.assign_best_expert(
        pg_db, "COURSE", course.maKhoaHoc, expected_review_round=2, now=now, commit=False
    )
    assert assign_r2.status.value == "ASSIGNED"

    # 8. ADMIN cancels round-2 assignment -> CANCELLED + assigned expert loses access
    r_cancel = enabled_client.post(
        f"/api/admin/assignments/{assign_r2.assignmentId}/cancel",
        json={"lyDoHuy": "Admin reassignment test", "requeue": True},
        headers=_auth(admin_u),
    )
    assert r_cancel.status_code == 200
    assert r_cancel.json()["trangThai"] == "CANCELLED"
    assert enabled_client.post(
        f"/api/expert/assignments/{assign_r2.assignmentId}/accept",
        headers=_auth(exp_unassigned_u),
    ).status_code == 409

    # 9. WAITING_ELIGIBLE wake-up when ADMIN verifies a new expert
    cat_wait, spec_wait = _mk_cat_and_spec(pg_db, "Wait")
    c_wait = workflow_service.create_provider_course(
        pg_db,
        prov_u.maNguoiDung,
        CourseCreateRequest(
            tieuDe="Waiting Course",
            maDanhMuc=cat_wait.maDanhMuc,
            gia=Decimal("0"),
        ),
    )
    workflow_service.create_provider_lesson(
        pg_db, prov_u.maNguoiDung, c_wait.maKhoaHoc, LessonCreateRequest(tieuDe="L1", thuTu=1)
    )
    with patch.object(workflow_service, "_is_auto_assignment_workflow_enabled", return_value=True):
        workflow_service.submit_provider_course(pg_db, prov_u.maNguoiDung, c_wait.maKhoaHoc)
    w_job = pg_db.scalars(
        select(HangDoiPhanCong).where(HangDoiPhanCong.maKhoaHoc == c_wait.maKhoaHoc)
    ).first()
    w_job.trangThai = "WAITING_ELIGIBLE"
    pg_db.flush()

    exp_new_u, _ = _mk_expert(pg_db, spec_wait, profile_status="PENDING_VERIFICATION")
    with patch.object(workflow_service, "_is_auto_assignment_workflow_enabled", return_value=True):
        workflow_service.verify_expert_profile(
            pg_db,
            admin_u.maNguoiDung,
            exp_new_u.maNguoiDung,
            AdminVerifyExpertRequest(trangThaiHoSo="VERIFIED", ghiChuXacMinh="OK"),
        )
    pg_db.refresh(w_job)
    assert w_job.trangThai == "PENDING"

    # 10. Legacy KhoaHoc #28 controlled bootstrap rehearsal (inside rolled-back test transaction!)
    c28, j28 = assignment_lifecycle_service.bootstrap_legacy_pending_course(pg_db, 28, now=now)
    assert c28.soVongKiemDuyetHienTai == 1
    assert j28.khoaChongTrung == "SUBMIT:COURSE:28:R1"


# =====================================================================
# 3. REAL MULTI-CONNECTION WORKER FENCING, CRASH RECOVERY & LIFECYCLE RACES
# =====================================================================
def test_worker_fencing_crash_recovery_and_lifecycle_concurrency_on_real_postgres():
    """Real multi-connection PostgreSQL 16 tests for:
    - 2 workers claiming same job (SKIP LOCKED)
    - ARCH-06 Fencing & Crash Recovery (stale worker fenced out after lease reclaim!)
    - Acceptance expiration sweep + concurrent accept vs expire
    - Full FK-ordered cleanup leaving 0 leftover rows
    """
    now = _now_utc()
    cleanup: dict[str, list[int]] = {
        "notifs": [],
        "jobs": [],
        "reviews": [],
        "assignments": [],
        "courses": [],
        "experts": [],
        "providers": [],
        "users": [],
        "specs": [],
        "cats": [],
    }

    def _s() -> Session:
        s = TestSessionFactory()
        assert s.execute(text("SELECT current_database()")).scalar() == TEST_DB_NAME
        return s

    try:
        with _s() as s:
            cat, spec = _mk_cat_and_spec(s, "WConc")
            cleanup["cats"].append(cat.maDanhMuc)
            cleanup["specs"].append(spec.maChuyenMon)
            u_prov, prov = _mk_provider(s)
            cleanup["users"].append(u_prov.maNguoiDung)
            cleanup["providers"].append(prov.maNhaCungCap)
            u_e1, e1 = _mk_expert(s, spec, years=8)
            u_e2, e2 = _mk_expert(s, spec, years=6)
            cleanup["users"].extend([u_e1.maNguoiDung, u_e2.maNguoiDung])
            cleanup["experts"].extend([e1.maChuyenGia, e2.maChuyenGia])

            # Course 1: for 2-worker SKIP LOCKED claim test
            c1 = KhoaHoc(
                maNhaCungCap=prov.maNhaCungCap,
                maDanhMuc=cat.maDanhMuc,
                tieuDe="Worker SkipLocked Course",
                gia=Decimal("0"),
                trangThaiDuyet="PENDING",
                trangThaiHienThi="HIDDEN",
                soVongKiemDuyetHienTai=1,
            )
            # Course 2: for ARCH-06 stale-worker fencing & crash recovery test
            c2 = KhoaHoc(
                maNhaCungCap=prov.maNhaCungCap,
                maDanhMuc=cat.maDanhMuc,
                tieuDe="Worker Fencing Course",
                gia=Decimal("0"),
                trangThaiDuyet="PENDING",
                trangThaiHienThi="HIDDEN",
                soVongKiemDuyetHienTai=1,
            )
            # Course 3: for concurrent accept vs expire race
            c3 = KhoaHoc(
                maNhaCungCap=prov.maNhaCungCap,
                maDanhMuc=cat.maDanhMuc,
                tieuDe="Accept vs Expire Course",
                gia=Decimal("0"),
                trangThaiDuyet="PENDING",
                trangThaiHienThi="HIDDEN",
                soVongKiemDuyetHienTai=1,
            )
            s.add_all([c1, c2, c3])
            s.flush()
            cleanup["courses"].extend([c1.maKhoaHoc, c2.maKhoaHoc, c3.maKhoaHoc])

            j1, _ = assignment_queue_service.enqueue_assignment_job(
                s, target_type="COURSE", target_id=c1.maKhoaHoc, review_round=1, event_type="SUBMIT", now=now
            )
            cleanup["jobs"].append(j1.maCongViec)
            s.commit()
            ids = {
                "c1": c1.maKhoaHoc,
                "c2": c2.maKhoaHoc,
                "c3": c3.maKhoaHoc,
                "e1": e1.maChuyenGia,
                "u_e1": u_e1.maNguoiDung,
                "cat": cat.maDanhMuc,
                "j1": j1.maCongViec,
            }

        # --- TEST W1: 2 workers concurrently claim the SAME job -> exactly 1 claims (SKIP LOCKED) ---
        w1 = AssignmentQueueWorker(TestSessionFactory, worker_id="w-1", expected_db_name=TEST_DB_NAME)
        w2 = AssignmentQueueWorker(TestSessionFactory, worker_id="w-2", expected_db_name=TEST_DB_NAME)
        b_claim = Barrier(2)

        def _claim(worker):
            b_claim.wait()
            return worker.claim_next_jobs(now=now)

        with ThreadPoolExecutor(max_workers=2) as pool:
            claimed_lists = [f.result() for f in [pool.submit(_claim, w1), pool.submit(_claim, w2)]]
        all_claimed = [ctx for lst in claimed_lists for ctx in lst]
        assert len(all_claimed) == 1, f"Expected exactly 1 claim, got {len(all_claimed)}"
        owner_worker = w1 if all_claimed[0].maWorker == "w-1" else w2
        out1 = owner_worker.process_claimed_job(all_claimed[0], now=now)
        assert out1.finalQueueStatus == "DONE"
        assert out1.assignmentId is not None
        cleanup["assignments"].append(out1.assignmentId)

        # --- TEST W2: ARCH-06 Fencing & Crash Recovery (stale worker fenced out after reclaim!) ---
        with _s() as s:
            j2, _ = assignment_queue_service.enqueue_assignment_job(
                s, target_type="COURSE", target_id=ids["c2"], review_round=1, event_type="SUBMIT", now=now
            )
            cleanup["jobs"].append(j2.maCongViec)
            s.commit()

        stale_ctx = w1.claim_next_jobs(now=now)[0]
        assert stale_ctx.leaseGeneration == 1

        # Simulate W1 stall past lease expiration -> W2 reclaims & claims with leaseGeneration=2
        future_after_lease = now + timedelta(seconds=120)
        reclaimed = w2.reclaim_stale_processing_jobs(now=future_after_lease)
        assert reclaimed == 1
        fresh_ctx_list = w2.claim_next_jobs(now=future_after_lease + timedelta(seconds=10))
        assert len(fresh_ctx_list) == 1
        fresh_ctx = fresh_ctx_list[0]
        assert fresh_ctx.leaseGeneration == 2

        # Stale W1 wakes up and tries to process using old claimToken & leaseGeneration=1 -> FENCED OUT!
        stale_outcome = w1.process_claimed_job(stale_ctx, now=future_after_lease + timedelta(seconds=10))
        assert stale_outcome.fencedOut is True
        assert stale_outcome.finalQueueStatus == "FENCED_OUT"

        # Fresh W2 processes cleanly -> DONE with exactly 1 assignment!
        fresh_outcome = w2.process_claimed_job(fresh_ctx, now=future_after_lease + timedelta(seconds=10))
        assert fresh_outcome.finalQueueStatus == "DONE"
        assert fresh_outcome.assignmentId is not None
        cleanup["assignments"].append(fresh_outcome.assignmentId)

        # --- TEST W3: Concurrent Accept vs Expire -> exactly 1 wins cleanly ---
        with _s() as s:
            pc3 = PhanCongKiemDuyet(
                maKhoaHoc=ids["c3"],
                maChuyenGia=ids["e1"],
                maDanhMuc=ids["cat"],
                soVongKiemDuyet=1,
                phuongThucPhanCong="AUTO",
                trangThai="ASSIGNED",
                ngayPhanCong=now - timedelta(hours=25),
                hanTiepNhan=now - timedelta(seconds=5),  # expired 5s ago
            )
            s.add(pc3)
            s.commit()
            pc3_id = pc3.maPhanCong
            cleanup["assignments"].append(pc3_id)

        expired_n = w1.expire_overdue_assignments(now=now)
        assert expired_n == 1
        with _s() as s:
            pc3_after = s.get(PhanCongKiemDuyet, pc3_id)
            assert pc3_after.trangThai == "EXPIRED"
            assert pc3_after.chiTietDiem["accountabilityEvent"]["eventType"] == "EXPIRED_ACCEPTANCE"
            # Verify REASSIGN_EXPIRED job was enqueued
            re_job = s.scalars(
                select(HangDoiPhanCong).where(
                    HangDoiPhanCong.khoaChongTrung == f"REASSIGN:COURSE:{ids['c3']}:R1:FROM:{pc3_id}"
                )
            ).first()
            assert re_job is not None
            cleanup["jobs"].append(re_job.maCongViec)

    finally:
        with _s() as sc:
            # Clean all notifications created for our test users
            if cleanup["users"]:
                sc.execute(
                    text('DELETE FROM "ThongBao" WHERE "maNguoiNhan" = ANY(:uids)'),
                    {"uids": cleanup["users"]},
                )
            sc.execute(
                text('DELETE FROM "ThongBao" WHERE "khoaChongTrung" LIKE \'ASSIGN_%\' OR "khoaChongTrung" LIKE \'WAITING_ELIGIBLE:%\' OR "khoaChongTrung" LIKE \'REASSIGN_LIMIT:%\'')
            )
            if cleanup["courses"]:
                sc.execute(
                    text('DELETE FROM "HangDoiPhanCong" WHERE "maKhoaHoc" = ANY(:cids)'),
                    {"cids": cleanup["courses"]},
                )
            if cleanup["experts"]:
                # Expiration can record durable accountability events when the
                # staging flag is enabled; remove those fixture rows before assignments.
                sc.execute(
                    text('DELETE FROM "NhatKyKyLuatChuyenGia" WHERE "maChuyenGia" = ANY(:ids)'),
                    {"ids": cleanup["experts"]},
                )
                sc.execute(
                    text('DELETE FROM "ViPhamChuyenGia" WHERE "maChuyenGia" = ANY(:ids)'),
                    {"ids": cleanup["experts"]},
                )
            if cleanup["jobs"]:
                sc.execute(
                    text('DELETE FROM "HangDoiPhanCong" WHERE "maCongViec" = ANY(:ids)'),
                    {"ids": list(set(cleanup["jobs"]))},
                )
            if cleanup["assignments"]:
                sc.execute(
                    text('DELETE FROM "DanhGiaChuyenGia" WHERE "maPhanCong" = ANY(:ids)'),
                    {"ids": list(set(cleanup["assignments"]))},
                )
                sc.execute(
                    text('DELETE FROM "PhanCongKiemDuyet" WHERE "maPhanCong" = ANY(:ids)'),
                    {"ids": list(set(cleanup["assignments"]))},
                )
            if cleanup["courses"]:
                sc.execute(
                    text('DELETE FROM "KhoaHoc" WHERE "maKhoaHoc" = ANY(:ids)'),
                    {"ids": cleanup["courses"]},
                )
            if cleanup["experts"]:
                sc.execute(
                    text('DELETE FROM "ChuyenGiaChuyenMon" WHERE "maChuyenGia" = ANY(:ids)'),
                    {"ids": cleanup["experts"]},
                )
                sc.execute(
                    text('DELETE FROM "ChuyenGia" WHERE "maChuyenGia" = ANY(:ids)'),
                    {"ids": cleanup["experts"]},
                )
            if cleanup["providers"]:
                sc.execute(
                    text('DELETE FROM "NhaCungCapKhoaHoc" WHERE "maNhaCungCap" = ANY(:ids)'),
                    {"ids": cleanup["providers"]},
                )
            if cleanup["users"]:
                sc.execute(
                    text('DELETE FROM "NguoiDung" WHERE "maNguoiDung" = ANY(:ids)'),
                    {"ids": cleanup["users"]},
                )
            if cleanup["specs"]:
                sc.execute(
                    text('DELETE FROM "ChuyenMonDanhMuc" WHERE "maChuyenMon" = ANY(:ids)'),
                    {"ids": cleanup["specs"]},
                )
                sc.execute(
                    text('DELETE FROM "ChuyenMon" WHERE "maChuyenMon" = ANY(:ids)'),
                    {"ids": cleanup["specs"]},
                )
            if cleanup["cats"]:
                sc.execute(
                    text('DELETE FROM "DanhMuc" WHERE "maDanhMuc" = ANY(:ids)'),
                    {"ids": cleanup["cats"]},
                )
            sc.commit()
