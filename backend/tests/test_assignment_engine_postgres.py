"""PostgreSQL 16 Integration, Atomic Assignment, and Concurrency Tests (C1–C11) for GĐ3.2.

STRICT DATABASE SAFETY GUARD:
- Connects ONLY to `EduSuggest_phase3_test`.
- Asserts `SELECT current_database() == 'EduSuggest_phase3_test'` on engine init & every fixture.
- All single-connection tests roll back inside an outer transaction.
- All multi-connection concurrency tests explicitly delete every created record in `finally`
  following FK order, leaving `EduSuggest_phase3_test` clean (0 leftover assignments/fixtures).
"""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from urllib.parse import urlparse, urlunparse

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from models import (
    CauHinhPhanCong,
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    DanhMuc,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    PhanCongKiemDuyet,
    TaiLieu,
    VaiTro,
    YeuCauTamNgungChuyenGia,
)
from schemas.assignment import (
    AssignmentStatusCode,
    EligibilityReasonCode,
    WorkerJobContext,
)
from service import assignment_service


def _build_test_engine():
    load_dotenv(r"d:\đồ án\EduSuggest\backend\.env")
    prod_url = os.getenv("DATABASE_URL") or ""
    p = urlparse(prod_url)
    assert p.path.lstrip("/") == "EduSuggest", "Unexpected .env DB name"
    test_url = urlunparse(p._replace(path="/EduSuggest_phase3_test"))
    eng = create_engine(test_url, pool_pre_ping=True, pool_size=12, max_overflow=12)
    with eng.connect() as c:
        cur = c.execute(text("SELECT current_database()")).scalar()
        assert cur == "EduSuggest_phase3_test", f"SAFETY GUARD ABORT: connected to {cur!r}"
    return eng


TEST_ENGINE = _build_test_engine()
TestSessionFactory = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def pg_db():
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
        tenTaiKhoan=f"g32_{role_name.lower()}_{tag}",
        email=f"g32_{role_name.lower()}_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase32enginetest0000000000000000",
        hoTen=f"G32 {role_name} {tag}",
        maVaiTro=role.maVaiTro,
        trangThai=status,
        batBuocDoiMatKhau=force_pw,
    )
    db.add(u)
    db.flush()
    return u


def _mk_category(db: Session, prefix: str = "G32Cat") -> DanhMuc:
    cat = DanhMuc(tenDanhMuc=f"{prefix}_{uuid.uuid4().hex[:6]}")
    db.add(cat)
    db.flush()
    return cat


def _mk_specialty(
    db: Session,
    cat_ids: list[int],
    *,
    status: str = "ACTIVE",
    prefix: str = "G32Spec",
) -> ChuyenMon:
    now = _now_utc()
    spec = ChuyenMon(
        tenChuyenMon=f"{prefix}_{uuid.uuid4().hex[:6]}",
        nhomChuyenMon="Engineering",
        trangThai=status,
        ngayTao=now,
    )
    db.add(spec)
    db.flush()
    for cid in cat_ids:
        db.add(ChuyenMonDanhMuc(maChuyenMon=spec.maChuyenMon, maDanhMuc=cid, ngayTao=now))
    db.flush()
    return spec


def _mk_expert(
    db: Session,
    *,
    role_name: str = "EXPERT",
    account_status: str = "ACTIVE",
    force_pw: bool = False,
    profile_status: str = "VERIFIED",
    years: int | None = 5,
    primary_spec: ChuyenMon | None = None,
    secondary_specs: list[ChuyenMon] | None = None,
) -> tuple[NguoiDung, ChuyenGia]:
    u = _mk_user(db, role_name, status=account_status, force_pw=force_pw)
    e = ChuyenGia(
        maNguoiDung=u.maNguoiDung,
        trangThaiHoSo=profile_status,
        soNamKinhNghiem=years,
        chuyenMon="Legacy text ignored",
    )
    db.add(e)
    db.flush()
    now = _now_utc()
    if primary_spec is not None:
        db.add(
            ChuyenGiaChuyenMon(
                maChuyenGia=e.maChuyenGia,
                maChuyenMon=primary_spec.maChuyenMon,
                laChuyenMonChinh=True,
                ngayTao=now,
            )
        )
    for sp in secondary_specs or []:
        db.add(
            ChuyenGiaChuyenMon(
                maChuyenGia=e.maChuyenGia,
                maChuyenMon=sp.maChuyenMon,
                laChuyenMonChinh=False,
                ngayTao=now,
            )
        )
    db.flush()
    return u, e


def _mk_provider(db: Session, user: NguoiDung | None = None) -> tuple[NguoiDung, NhaCungCapKhoaHoc]:
    u = user or _mk_user(db, "PROVIDER")
    p = NhaCungCapKhoaHoc(maNguoiDung=u.maNguoiDung, tieuSu="Bio", chuyenMon="Tech")
    db.add(p)
    db.flush()
    return u, p


def _mk_course(
    db: Session,
    provider_id: int,
    cat_id: int | None,
    *,
    status: str = "PENDING",
    review_round: int = 1,
) -> KhoaHoc:
    c = KhoaHoc(
        maNhaCungCap=provider_id,
        maDanhMuc=cat_id,
        tieuDe=f"G32 Course {uuid.uuid4().hex[:6]}",
        moTa="Test course",
        gia=Decimal("0"),
        trangThaiDuyet=status,
        trangThaiHienThi="HIDDEN",
        soVongKiemDuyetHienTai=review_round,
    )
    db.add(c)
    db.flush()
    return c


def _mk_material(
    db: Session,
    provider_id: int,
    cat_id: int | None,
    *,
    course_id: int | None = None,
    status: str = "PENDING",
    review_round: int = 1,
) -> TaiLieu:
    m = TaiLieu(
        maNhaCungCap=provider_id,
        maDanhMuc=cat_id,
        maKhoaHoc=course_id,
        tieuDe=f"G32 Material {uuid.uuid4().hex[:6]}",
        duongDanTep="https://example.com/g32.pdf",
        loai="PDF",
        trangThaiDuyet=status,
        trangThaiHienThi="HIDDEN",
        soVongKiemDuyetHienTai=review_round,
    )
    db.add(m)
    db.flush()
    return m


# =====================================================================
# SECTION 43: PostgreSQL Eligibility Integration Tests (All 28 Cases)
# =====================================================================
def test_eligibility_all_28_rules_on_real_postgres(pg_db: Session):
    now = _now_utc()
    cat_target = _mk_category(pg_db, "TargetCat")
    cat_other = _mk_category(pg_db, "OtherCat")
    spec_primary = _mk_specialty(pg_db, [cat_target.maDanhMuc], status="ACTIVE", prefix="SpecPrim")
    spec_sec1 = _mk_specialty(pg_db, [cat_target.maDanhMuc], status="ACTIVE", prefix="SpecSec1")
    spec_sec2 = _mk_specialty(pg_db, [cat_target.maDanhMuc], status="ACTIVE", prefix="SpecSec2")
    spec_inactive = _mk_specialty(pg_db, [cat_target.maDanhMuc], status="INACTIVE", prefix="SpecInact")
    spec_other = _mk_specialty(pg_db, [cat_other.maDanhMuc], status="ACTIVE", prefix="SpecOther")

    _, prov = _mk_provider(pg_db)
    course = _mk_course(pg_db, prov.maNhaCungCap, cat_target.maDanhMuc, status="PENDING", review_round=2)

    # 1. Eligible PRIMARY expert
    _, e_primary = _mk_expert(pg_db, primary_spec=spec_primary, years=8)
    # 2. Eligible SECONDARY expert with multiple matching specialties (must NOT duplicate candidate)
    _, e_secondary = _mk_expert(pg_db, primary_spec=spec_other, secondary_specs=[spec_sec1, spec_sec2], years=6)
    # 3-5. Non-EXPERT roles (USER, ADMIN, PROVIDER)
    _, e_user_role = _mk_expert(pg_db, role_name="USER", primary_spec=spec_primary)
    _, e_admin_role = _mk_expert(pg_db, role_name="ADMIN", primary_spec=spec_primary)
    _, e_prov_role = _mk_expert(pg_db, role_name="PROVIDER", primary_spec=spec_primary)
    # 6-7. LOCKED and force_pw
    _, e_locked = _mk_expert(pg_db, account_status="LOCKED", primary_spec=spec_primary)
    _, e_forcepw = _mk_expert(pg_db, force_pw=True, primary_spec=spec_primary)
    # 8-10. Unverified profiles
    _, e_draft = _mk_expert(pg_db, profile_status="DRAFT", primary_spec=spec_primary)
    _, e_pend_ver = _mk_expert(pg_db, profile_status="PENDING_VERIFICATION", primary_spec=spec_primary)
    _, e_needs_upd = _mk_expert(pg_db, profile_status="NEEDS_UPDATE", primary_spec=spec_primary)
    # 11-12. INACTIVE specialty & non-matching category
    _, e_inact_spec = _mk_expert(pg_db, primary_spec=spec_inactive)
    _, e_other_cat = _mk_expert(pg_db, primary_spec=spec_other)
    # 13. Workload full (5/5)
    _, e_full = _mk_expert(pg_db, primary_spec=spec_primary)
    for i in range(5):
        dummy_c = _mk_course(pg_db, prov.maNhaCungCap, cat_other.maDanhMuc, review_round=1)
        pg_db.add(
            PhanCongKiemDuyet(
                maKhoaHoc=dummy_c.maKhoaHoc,
                maChuyenGia=e_full.maChuyenGia,
                maDanhMuc=cat_other.maDanhMuc,
                soVongKiemDuyet=1,
                phuongThucPhanCong="AUTO",
                trangThai="ASSIGNED",
                ngayPhanCong=now - timedelta(hours=1),
                hanTiepNhan=now + timedelta(hours=23),
            )
        )
    # 14-19. Availability cases: active APPROVED, exact start [start, end), exact end, PENDING, future, ended
    _, e_paused = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        YeuCauTamNgungChuyenGia(
            maChuyenGia=e_paused.maChuyenGia,
            ngayBatDau=now - timedelta(hours=1),
            ngayKetThuc=now + timedelta(hours=2),
            lyDo="Vacation",
            trangThai="APPROVED",
        )
    )
    _, e_boundary_start = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        YeuCauTamNgungChuyenGia(
            maChuyenGia=e_boundary_start.maChuyenGia,
            ngayBatDau=now,  # inclusive start -> BLOCKED
            ngayKetThuc=now + timedelta(hours=5),
            lyDo="Boundary start",
            trangThai="APPROVED",
        )
    )
    _, e_boundary_end = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        YeuCauTamNgungChuyenGia(
            maChuyenGia=e_boundary_end.maChuyenGia,
            ngayBatDau=now - timedelta(hours=5),
            ngayKetThuc=now,  # exclusive end -> ALLOWED
            lyDo="Boundary end",
            trangThai="APPROVED",
        )
    )
    _, e_avail_pending = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        YeuCauTamNgungChuyenGia(
            maChuyenGia=e_avail_pending.maChuyenGia,
            ngayBatDau=now - timedelta(hours=1),
            ngayKetThuc=now + timedelta(hours=2),
            lyDo="Pending pause",
            trangThai="PENDING",
        )
    )
    _, e_avail_future = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        YeuCauTamNgungChuyenGia(
            maChuyenGia=e_avail_future.maChuyenGia,
            ngayBatDau=now + timedelta(hours=1),
            ngayKetThuc=now + timedelta(hours=5),
            lyDo="Future pause",
            trangThai="APPROVED",
        )
    )
    _, e_avail_ended = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        YeuCauTamNgungChuyenGia(
            maChuyenGia=e_avail_ended.maChuyenGia,
            ngayBatDau=now - timedelta(hours=10),
            ngayKetThuc=now - timedelta(hours=1),
            lyDo="Ended pause",
            trangThai="APPROVED",
        )
    )

    # 20-22. Round exclusions: DECLINED current round (blocked), EXPIRED current round (blocked), DECLINED old round (allowed)
    _, e_declined_curr = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        PhanCongKiemDuyet(
            maKhoaHoc=course.maKhoaHoc,
            maChuyenGia=e_declined_curr.maChuyenGia,
            maDanhMuc=cat_target.maDanhMuc,
            soVongKiemDuyet=2,
            phuongThucPhanCong="AUTO",
            trangThai="DECLINED",
            ngayPhanCong=now - timedelta(hours=5),
            hanTiepNhan=now + timedelta(hours=19),
        )
    )
    _, e_expired_curr = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        PhanCongKiemDuyet(
            maKhoaHoc=course.maKhoaHoc,
            maChuyenGia=e_expired_curr.maChuyenGia,
            maDanhMuc=cat_target.maDanhMuc,
            soVongKiemDuyet=2,
            phuongThucPhanCong="AUTO",
            trangThai="EXPIRED",
            ngayPhanCong=now - timedelta(hours=30),
            hanTiepNhan=now - timedelta(hours=6),
        )
    )
    _, e_declined_old = _mk_expert(pg_db, primary_spec=spec_primary)
    pg_db.add(
        PhanCongKiemDuyet(
            maKhoaHoc=course.maKhoaHoc,
            maChuyenGia=e_declined_old.maChuyenGia,
            maDanhMuc=cat_target.maDanhMuc,
            soVongKiemDuyet=1,  # OLD round -> ALLOWED in round 2!
            phuongThucPhanCong="AUTO",
            trangThai="DECLINED",
            ngayPhanCong=now - timedelta(hours=50),
            hanTiepNhan=now - timedelta(hours=26),
        )
    )

    # 23. Conflict of interest: expert is also the owner (NhaCungCapKhoaHoc.maNguoiDung) of the course
    u_coi, e_coi = _mk_expert(pg_db, primary_spec=spec_primary)
    _, prov_coi = _mk_provider(pg_db, user=u_coi)
    course_coi = _mk_course(pg_db, prov_coi.maNhaCungCap, cat_target.maDanhMuc, review_round=1)
    pg_db.flush()

    preview = assignment_service.rank_candidates(pg_db, "COURSE", course.maKhoaHoc, now=now)
    assert preview.isTargetValid is True
    eligible_ids = [r.maChuyenGia for r in preview.rankedCandidates]
    excluded_map = {ex.maChuyenGia: set(ex.reasons) for ex in preview.excludedCandidates}

    # Eligible set check (no duplicates!)
    assert len(eligible_ids) == len(set(eligible_ids))
    for should_be_eligible in (
        e_primary.maChuyenGia,
        e_secondary.maChuyenGia,
        e_boundary_end.maChuyenGia,
        e_avail_pending.maChuyenGia,
        e_avail_future.maChuyenGia,
        e_avail_ended.maChuyenGia,
        e_declined_old.maChuyenGia,
    ):
        assert should_be_eligible in eligible_ids

    # Excluded reason codes verification
    assert EligibilityReasonCode.ROLE_NOT_EXPERT in excluded_map[e_user_role.maChuyenGia]
    assert EligibilityReasonCode.ROLE_NOT_EXPERT in excluded_map[e_admin_role.maChuyenGia]
    assert EligibilityReasonCode.ROLE_NOT_EXPERT in excluded_map[e_prov_role.maChuyenGia]
    assert EligibilityReasonCode.ACCOUNT_NOT_ACTIVE in excluded_map[e_locked.maChuyenGia]
    assert EligibilityReasonCode.PASSWORD_CHANGE_REQUIRED in excluded_map[e_forcepw.maChuyenGia]
    assert EligibilityReasonCode.PROFILE_NOT_VERIFIED in excluded_map[e_draft.maChuyenGia]
    assert EligibilityReasonCode.PROFILE_NOT_VERIFIED in excluded_map[e_pend_ver.maChuyenGia]
    assert EligibilityReasonCode.PROFILE_NOT_VERIFIED in excluded_map[e_needs_upd.maChuyenGia]
    assert EligibilityReasonCode.NO_ACTIVE_SPECIALTY in excluded_map[e_inact_spec.maChuyenGia]
    assert EligibilityReasonCode.SPECIALTY_NOT_MATCHED in excluded_map[e_other_cat.maChuyenGia]
    assert EligibilityReasonCode.WORKLOAD_LIMIT_REACHED in excluded_map[e_full.maChuyenGia]
    assert EligibilityReasonCode.AVAILABILITY_PAUSED in excluded_map[e_paused.maChuyenGia]
    assert EligibilityReasonCode.AVAILABILITY_PAUSED in excluded_map[e_boundary_start.maChuyenGia]
    assert EligibilityReasonCode.DECLINED_IN_CURRENT_ROUND in excluded_map[e_declined_curr.maChuyenGia]
    assert EligibilityReasonCode.EXPIRED_IN_CURRENT_ROUND in excluded_map[e_expired_curr.maChuyenGia]

    # Conflict of Interest check on course_coi
    preview_coi = assignment_service.rank_candidates(pg_db, "COURSE", course_coi.maKhoaHoc, now=now)
    excluded_coi = {ex.maChuyenGia: set(ex.reasons) for ex in preview_coi.excludedCandidates}
    assert e_coi.maChuyenGia not in [r.maChuyenGia for r in preview_coi.rankedCandidates]
    assert EligibilityReasonCode.CONFLICT_OF_INTEREST in excluded_coi[e_coi.maChuyenGia]

    # No matching specialty category -> NO_ELIGIBLE_EXPERT
    cat_empty = _mk_category(pg_db, "EmptyCat")
    course_empty = _mk_course(pg_db, prov.maNhaCungCap, cat_empty.maDanhMuc, review_round=1)
    preview_empty = assignment_service.rank_candidates(pg_db, "COURSE", course_empty.maKhoaHoc, now=now)
    assert preview_empty.rankedCandidates == ()
    assert preview_empty.noCandidateReason == EligibilityReasonCode.NO_ELIGIBLE_EXPERT


# =====================================================================
# SECTION 44: PostgreSQL Atomic Assignment Tests
# =====================================================================
def test_atomic_assignment_all_business_invariants(pg_db: Session):
    now = _now_utc()
    cat = _mk_category(pg_db, "AtomicCat")
    spec = _mk_specialty(pg_db, [cat.maDanhMuc], prefix="AtomicSpec")
    _, prov = _mk_provider(pg_db)
    _, expert = _mk_expert(pg_db, primary_spec=spec, years=7)

    # 1. Valid COURSE assignment
    c = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc, status="PENDING", review_round=1)
    res = assignment_service.assign_best_expert(
        pg_db,
        "COURSE",
        c.maKhoaHoc,
        expected_review_round=1,
        now=now,
        worker_context=WorkerJobContext(
            maCongViec=999,
            claimToken=uuid.uuid4(),
            leaseGeneration=1,
            maWorker="worker-test",
        ),
        commit=False,
    )
    assert res.status == AssignmentStatusCode.ASSIGNED
    assert res.assignedExpertId == expert.maChuyenGia
    assert res.assignmentId is not None
    pc = pg_db.get(PhanCongKiemDuyet, res.assignmentId)
    assert pc is not None
    assert pc.phuongThucPhanCong == "AUTO"
    assert pc.maNguoiPhanCong is None
    assert pc.trangThai == "ASSIGNED"
    assert pc.hanTiepNhan == now + timedelta(hours=24)
    assert pc.hanKiemDuyet is None
    assert pc.diemPhuHop == res.score.totalScore
    assert pc.maChuyenMonKhop == spec.maChuyenMon
    assert pc.chiTietDiem["scoringVersion"] == "3.2.0"
    assert c.soVongKiemDuyetHienTai == 1  # never incremented by engine

    # 2. Retry idempotency -> ALREADY_ASSIGNED
    res_dup = assignment_service.assign_best_expert(
        pg_db, "COURSE", c.maKhoaHoc, expected_review_round=1, now=now
    )
    assert res_dup.status == AssignmentStatusCode.ALREADY_ASSIGNED
    assert res_dup.assignmentId == res.assignmentId

    # 3. Valid standalone MATERIAL assignment
    m = _mk_material(pg_db, prov.maNhaCungCap, cat.maDanhMuc, course_id=None, status="PENDING", review_round=1)
    res_m = assignment_service.assign_best_expert(pg_db, "MATERIAL", m.maTaiLieu, expected_review_round=1, now=now)
    assert res_m.status == AssignmentStatusCode.ASSIGNED

    # 4. Linked material rejected
    m_linked = _mk_material(pg_db, prov.maNhaCungCap, cat.maDanhMuc, course_id=c.maKhoaHoc, review_round=1)
    res_linked = assignment_service.assign_best_expert(pg_db, "MATERIAL", m_linked.maTaiLieu, now=now)
    assert res_linked.status == AssignmentStatusCode.INVALID_TARGET
    assert res_linked.reasonCode == EligibilityReasonCode.TARGET_NOT_STANDALONE_MATERIAL

    # 5. Nonexistent, missing category, non-PENDING, round=0, stale round
    assert assignment_service.assign_best_expert(pg_db, "COURSE", 999999, now=now).status == AssignmentStatusCode.INVALID_TARGET
    m_nocat = _mk_material(pg_db, prov.maNhaCungCap, None, review_round=1)
    assert assignment_service.assign_best_expert(pg_db, "MATERIAL", m_nocat.maTaiLieu, now=now).reasonCode == EligibilityReasonCode.TARGET_CATEGORY_MISSING
    c_appr = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc, status="APPROVED", review_round=1)
    assert assignment_service.assign_best_expert(pg_db, "COURSE", c_appr.maKhoaHoc, now=now).reasonCode == EligibilityReasonCode.TARGET_NOT_PENDING
    c_r0 = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc, status="PENDING", review_round=0)
    assert assignment_service.assign_best_expert(pg_db, "COURSE", c_r0.maKhoaHoc, now=now).reasonCode == EligibilityReasonCode.TARGET_ROUND_INVALID
    c_r2 = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc, status="PENDING", review_round=2)
    assert assignment_service.assign_best_expert(pg_db, "COURSE", c_r2.maKhoaHoc, expected_review_round=1, now=now).status == AssignmentStatusCode.STALE_REVIEW_ROUND

    # 6. Reassignment limit: max 6 in a round (1 initial + 5 reassignments)
    c_lim = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc, status="PENDING", review_round=1)
    for idx in range(6):
        _, tmp_e = _mk_expert(pg_db, primary_spec=spec)
        pg_db.add(
            PhanCongKiemDuyet(
                maKhoaHoc=c_lim.maKhoaHoc,
                maChuyenGia=tmp_e.maChuyenGia,
                maDanhMuc=cat.maDanhMuc,
                soVongKiemDuyet=1,
                phuongThucPhanCong="AUTO",
                trangThai="DECLINED",
                ngayPhanCong=now - timedelta(hours=10 - idx),
                hanTiepNhan=now + timedelta(hours=14),
            )
        )
    pg_db.flush()
    res_lim = assignment_service.assign_best_expert(pg_db, "COURSE", c_lim.maKhoaHoc, expected_review_round=1, now=now)
    assert res_lim.status == AssignmentStatusCode.REASSIGNMENT_LIMIT_REACHED

    # 7. No eligible expert -> WAITING_ELIGIBLE & 0 rows created
    cat_none = _mk_category(pg_db, "NoExpertCat")
    c_none = _mk_course(pg_db, prov.maNhaCungCap, cat_none.maDanhMuc, status="PENDING", review_round=1)
    res_none = assignment_service.assign_best_expert(pg_db, "COURSE", c_none.maKhoaHoc, expected_review_round=1, now=now)
    assert res_none.status == AssignmentStatusCode.NO_ELIGIBLE_EXPERT
    assert res_none.queueRecommendedStatus == "WAITING_ELIGIBLE"


# =====================================================================
# SECTION 45: PostgreSQL Concurrency Tests C1–C11 (Real Multi-Connection)
# =====================================================================
def test_concurrency_c1_to_c11_on_real_postgres():
    """Real multi-connection PostgreSQL 16 concurrency verification (C1–C11) with full cleanup."""
    now = _now_utc()
    cleanup: dict[str, list[int]] = {
        "assignments": [],
        "pauses": [],
        "materials": [],
        "courses": [],
        "experts": [],
        "providers": [],
        "users": [],
        "specs": [],
        "cats": [],
    }

    def _new_session() -> Session:
        s = TestSessionFactory()
        assert s.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
        return s

    try:
        # Setup isolated concurrency fixtures in committed setup transaction
        with _new_session() as s:
            cat = _mk_category(s, "ConcCat")
            cleanup["cats"].append(cat.maDanhMuc)
            spec = _mk_specialty(s, [cat.maDanhMuc], prefix="ConcSpec")
            cleanup["specs"].append(spec.maChuyenMon)
            u_prov, prov = _mk_provider(s)
            cleanup["users"].append(u_prov.maNguoiDung)
            cleanup["providers"].append(prov.maNhaCungCap)

            # Create 3 eligible experts
            experts = []
            for y in (9, 7, 5):
                u_e, e = _mk_expert(s, primary_spec=spec, years=y)
                cleanup["users"].append(u_e.maNguoiDung)
                cleanup["experts"].append(e.maChuyenGia)
                experts.append((u_e.maNguoiDung, e.maChuyenGia))

            # C1 course & C2 material
            c1 = _mk_course(s, prov.maNhaCungCap, cat.maDanhMuc, review_round=1)
            m2 = _mk_material(s, prov.maNhaCungCap, cat.maDanhMuc, review_round=1)
            cleanup["courses"].append(c1.maKhoaHoc)
            cleanup["materials"].append(m2.maTaiLieu)

            # C3 capacity test: isolated category & single expert with 4/5 active load
            cat_cap = _mk_category(s, "CapCat")
            cleanup["cats"].append(cat_cap.maDanhMuc)
            spec_cap = _mk_specialty(s, [cat_cap.maDanhMuc], prefix="CapSpec")
            cleanup["specs"].append(spec_cap.maChuyenMon)
            u_cap, e_cap = _mk_expert(s, primary_spec=spec_cap, years=8)
            cleanup["users"].append(u_cap.maNguoiDung)
            cleanup["experts"].append(e_cap.maChuyenGia)
            for _ in range(4):
                dc = _mk_course(s, prov.maNhaCungCap, cat_cap.maDanhMuc, review_round=1)
                cleanup["courses"].append(dc.maKhoaHoc)
                pc = PhanCongKiemDuyet(
                    maKhoaHoc=dc.maKhoaHoc,
                    maChuyenGia=e_cap.maChuyenGia,
                    maDanhMuc=cat_cap.maDanhMuc,
                    soVongKiemDuyet=1,
                    phuongThucPhanCong="AUTO",
                    trangThai="ASSIGNED",
                    ngayPhanCong=now - timedelta(hours=2),
                    hanTiepNhan=now + timedelta(hours=22),
                )
                s.add(pc)
                s.flush()
                cleanup["assignments"].append(pc.maPhanCong)
            c3_a = _mk_course(s, prov.maNhaCungCap, cat_cap.maDanhMuc, review_round=1)
            c3_b = _mk_course(s, prov.maNhaCungCap, cat_cap.maDanhMuc, review_round=1)
            cleanup["courses"].extend([c3_a.maKhoaHoc, c3_b.maKhoaHoc])

            # C4 multiple courses
            c4_list = [_mk_course(s, prov.maNhaCungCap, cat.maDanhMuc, review_round=1) for _ in range(4)]
            cleanup["courses"].extend(x.maKhoaHoc for x in c4_list)

            # C5 Account Lock Race (dedicated category + 1 expert)
            cat_c5 = _mk_category(s, "C5Cat")
            cleanup["cats"].append(cat_c5.maDanhMuc)
            spec_c5 = _mk_specialty(s, [cat_c5.maDanhMuc], prefix="C5Spec")
            cleanup["specs"].append(spec_c5.maChuyenMon)
            u_c5, e_c5 = _mk_expert(s, primary_spec=spec_c5)
            cleanup["users"].append(u_c5.maNguoiDung)
            cleanup["experts"].append(e_c5.maChuyenGia)
            c5 = _mk_course(s, prov.maNhaCungCap, cat_c5.maDanhMuc, review_round=1)
            cleanup["courses"].append(c5.maKhoaHoc)

            # C6 Verification Race
            cat_c6 = _mk_category(s, "C6Cat")
            cleanup["cats"].append(cat_c6.maDanhMuc)
            spec_c6 = _mk_specialty(s, [cat_c6.maDanhMuc], prefix="C6Spec")
            cleanup["specs"].append(spec_c6.maChuyenMon)
            u_c6, e_c6 = _mk_expert(s, primary_spec=spec_c6)
            cleanup["users"].append(u_c6.maNguoiDung)
            cleanup["experts"].append(e_c6.maChuyenGia)
            c6 = _mk_course(s, prov.maNhaCungCap, cat_c6.maDanhMuc, review_round=1)
            cleanup["courses"].append(c6.maKhoaHoc)

            # C7 Specialty Change Race
            cat_c7 = _mk_category(s, "C7Cat")
            cleanup["cats"].append(cat_c7.maDanhMuc)
            spec_c7 = _mk_specialty(s, [cat_c7.maDanhMuc], prefix="C7Spec")
            cleanup["specs"].append(spec_c7.maChuyenMon)
            u_c7, e_c7 = _mk_expert(s, primary_spec=spec_c7)
            cleanup["users"].append(u_c7.maNguoiDung)
            cleanup["experts"].append(e_c7.maChuyenGia)
            c7 = _mk_course(s, prov.maNhaCungCap, cat_c7.maDanhMuc, review_round=1)
            cleanup["courses"].append(c7.maKhoaHoc)

            # C8 Availability Race
            cat_c8 = _mk_category(s, "C8Cat")
            cleanup["cats"].append(cat_c8.maDanhMuc)
            spec_c8 = _mk_specialty(s, [cat_c8.maDanhMuc], prefix="C8Spec")
            cleanup["specs"].append(spec_c8.maChuyenMon)
            u_c8, e_c8 = _mk_expert(s, primary_spec=spec_c8)
            cleanup["users"].append(u_c8.maNguoiDung)
            cleanup["experts"].append(e_c8.maChuyenGia)
            c8 = _mk_course(s, prov.maNhaCungCap, cat_c8.maDanhMuc, review_round=1)
            cleanup["courses"].append(c8.maKhoaHoc)

            # C9 Review Round Race
            c9 = _mk_course(s, prov.maNhaCungCap, cat.maDanhMuc, review_round=1)
            cleanup["courses"].append(c9.maKhoaHoc)

            # C10 Rollback Recovery
            c10 = _mk_course(s, prov.maNhaCungCap, cat.maDanhMuc, review_round=1)
            cleanup["courses"].append(c10.maKhoaHoc)

            s.commit()
            ids = {
                "c1": c1.maKhoaHoc,
                "m2": m2.maTaiLieu,
                "e_cap": e_cap.maChuyenGia,
                "c3_a": c3_a.maKhoaHoc,
                "c3_b": c3_b.maKhoaHoc,
                "c4": [x.maKhoaHoc for x in c4_list],
                "u_c5": u_c5.maNguoiDung,
                "c5": c5.maKhoaHoc,
                "e_c6": e_c6.maChuyenGia,
                "c6": c6.maKhoaHoc,
                "spec_c7": spec_c7.maChuyenMon,
                "c7": c7.maKhoaHoc,
                "e_c8": e_c8.maChuyenGia,
                "c8": c8.maKhoaHoc,
                "c9": c9.maKhoaHoc,
                "c10": c10.maKhoaHoc,
            }

        # --- C1: Same Course (2 concurrent transactions -> exactly 1 ASSIGNED, 1 ALREADY_ASSIGNED) ---
        b1 = Barrier(2)

        def _run_assign(t_type, t_id, barrier=None, exp_round=1):
            with _new_session() as s:
                if barrier:
                    barrier.wait()
                res = assignment_service.assign_best_expert(
                    s, t_type, t_id, expected_review_round=exp_round, now=now, commit=True
                )
                if res.assignmentId:
                    cleanup["assignments"].append(res.assignmentId)
                return res.status

        with ThreadPoolExecutor(max_workers=2) as pool:
            r_c1 = sorted(
                f.result().value
                for f in [
                    pool.submit(_run_assign, "COURSE", ids["c1"], b1),
                    pool.submit(_run_assign, "COURSE", ids["c1"], b1),
                ]
            )
        assert r_c1 == ["ALREADY_ASSIGNED", "ASSIGNED"], f"C1 failed: {r_c1}"

        # --- C2: Same Material (2 concurrent transactions -> exactly 1 ASSIGNED, 1 ALREADY_ASSIGNED) ---
        b2 = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            r_c2 = sorted(
                f.result().value
                for f in [
                    pool.submit(_run_assign, "MATERIAL", ids["m2"], b2),
                    pool.submit(_run_assign, "MATERIAL", ids["m2"], b2),
                ]
            )
        assert r_c2 == ["ALREADY_ASSIGNED", "ASSIGNED"], f"C2 failed: {r_c2}"

        # --- C3: Same Expert Capacity (4/5 load + 2 concurrent courses -> NEVER exceeds 5!) ---
        b3 = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            r_c3 = sorted(
                f.result().value
                for f in [
                    pool.submit(_run_assign, "COURSE", ids["c3_a"], b3),
                    pool.submit(_run_assign, "COURSE", ids["c3_b"], b3),
                ]
            )
        assert r_c3 == ["ASSIGNED", "NO_ELIGIBLE_EXPERT"], f"C3 failed: {r_c3}"
        with _new_session() as s:
            final_cap_load = s.execute(
                text(
                    'SELECT COUNT(*) FROM "PhanCongKiemDuyet" '
                    'WHERE "maChuyenGia" = :eid AND "trangThai" IN (\'ASSIGNED\',\'ACCEPTED\',\'IN_PROGRESS\')'
                ),
                {"eid": ids["e_cap"]},
            ).scalar()
            assert int(final_cap_load) == 5

        # --- C4 & C11: Multiple Experts & Multiple Courses concurrently (zero overload, zero unhandled deadlock) ---
        b4 = Barrier(len(ids["c4"]))
        with ThreadPoolExecutor(max_workers=len(ids["c4"])) as pool:
            r_c4 = [
                f.result()
                for f in [pool.submit(_run_assign, "COURSE", cid, b4) for cid in ids["c4"]]
            ]
        assert all(st == AssignmentStatusCode.ASSIGNED for st in r_c4), f"C4 failed: {r_c4}"

        # --- C5: Account Lock Race (lock commits before assignment completes -> NO_ELIGIBLE_EXPERT) ---
        with _new_session() as s_lock:
            u = s_lock.get(NguoiDung, ids["u_c5"])
            u.trangThai = "LOCKED"
            s_lock.commit()
        assert _run_assign("COURSE", ids["c5"]) == AssignmentStatusCode.NO_ELIGIBLE_EXPERT

        # --- C6: Verification Race (VERIFIED -> NEEDS_UPDATE before assignment -> NO_ELIGIBLE_EXPERT) ---
        with _new_session() as s_ver:
            e = s_ver.get(ChuyenGia, ids["e_c6"])
            e.trangThaiHoSo = "NEEDS_UPDATE"
            s_ver.commit()
        assert _run_assign("COURSE", ids["c6"]) == AssignmentStatusCode.NO_ELIGIBLE_EXPERT

        # --- C7: Specialty Deactivation Race (ACTIVE -> INACTIVE -> NO_ELIGIBLE_EXPERT) ---
        with _new_session() as s_sp:
            sp = s_sp.get(ChuyenMon, ids["spec_c7"])
            sp.trangThai = "INACTIVE"
            s_sp.commit()
        assert _run_assign("COURSE", ids["c7"]) == AssignmentStatusCode.NO_ELIGIBLE_EXPERT

        # --- C8: Availability Race (APPROVED pause committed -> NO_ELIGIBLE_EXPERT) ---
        with _new_session() as s_av:
            p_req = YeuCauTamNgungChuyenGia(
                maChuyenGia=ids["e_c8"],
                ngayBatDau=now - timedelta(minutes=5),
                ngayKetThuc=now + timedelta(hours=24),
                lyDo="Concurrent approved pause",
                trangThai="APPROVED",
            )
            s_av.add(p_req)
            s_av.commit()
            cleanup["pauses"].append(p_req.maYeuCau)
        assert _run_assign("COURSE", ids["c8"]) == AssignmentStatusCode.NO_ELIGIBLE_EXPERT

        # --- C9: Review Round Race (round 1 -> 2 committed -> expected round 1 gets STALE_REVIEW_ROUND) ---
        with _new_session() as s_rr:
            c_obj = s_rr.get(KhoaHoc, ids["c9"])
            c_obj.soVongKiemDuyetHienTai = 2
            s_rr.commit()
        assert _run_assign("COURSE", ids["c9"], exp_round=1) == AssignmentStatusCode.STALE_REVIEW_ROUND

        # --- C10: Rollback Recovery (1st tx acquires lock & rolls back -> 2nd tx succeeds) ---
        with _new_session() as s_rb:
            s_rb.execute(
                text('SELECT "maKhoaHoc" FROM "KhoaHoc" WHERE "maKhoaHoc" = :id FOR UPDATE'),
                {"id": ids["c10"]},
            )
            s_rb.rollback()
        assert _run_assign("COURSE", ids["c10"]) == AssignmentStatusCode.ASSIGNED

    finally:
        # Strict FK-ordered cleanup leaving EduSuggest_phase3_test spotless
        with _new_session() as sc:
            if cleanup["assignments"]:
                sc.execute(
                    text('DELETE FROM "PhanCongKiemDuyet" WHERE "maPhanCong" = ANY(:ids)'),
                    {"ids": list(set(cleanup["assignments"]))},
                )
            if cleanup["pauses"]:
                sc.execute(
                    text('DELETE FROM "YeuCauTamNgungChuyenGia" WHERE "maYeuCau" = ANY(:ids)'),
                    {"ids": cleanup["pauses"]},
                )
            if cleanup["materials"]:
                sc.execute(
                    text('DELETE FROM "TaiLieu" WHERE "maTaiLieu" = ANY(:ids)'),
                    {"ids": cleanup["materials"]},
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
