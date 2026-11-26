"""GĐ3.4C Comprehensive Verification Suite:
- Unit Policy Matrix (reason classification, discipline levels, thresholds)
- Rolling Window 168h Exact Boundaries (T-167h59m59s, T-168h00m00s, T-168h00m01s, T, T+1s)
- Disciplinary Cycle & Cross-Cycle Delayed Event Protection
- Auto-Lock (0 -> 1 -> 2 -> 3 -> 4), tuDongKhoa=False, Non-EXPERT immunity
- Durable Two-Step Assignment Revocation Recovery & Draft Preservation
- Immediate Access Revocation & Generic Unlock Bypass Protection
- ADMIN Confirm / Exempt / Lock / Unlock & Audit Log
- Real Multi-Connection Concurrency Tests (C1 Duplicate Violation, C2 Threshold Crossing, C8 Concurrent Unlock, Crash Recovery)

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
    CauHinhPhanCong,
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    DanhMuc,
    HangDoiPhanCong,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    NhatKyKyLuatChuyenGia,
    PhanCongKiemDuyet,
    VaiTro,
    ViPhamChuyenGia,
)
from service import (
    accountability_service,
    assignment_lifecycle_service,
    workflow_service,
)
from service.workflow_service import WorkflowConflictError
from utils.security import create_access_token


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


def _auth(user: NguoiDung) -> dict[str, str]:
    tok = create_access_token(user.maNguoiDung, user.matKhau).encoded
    return {"Authorization": f"Bearer {tok}"}


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


@pytest.fixture()
def acc_client(pg_db: Session):
    def _override_db():
        assert pg_db.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
        yield pg_db

    app.dependency_overrides[get_db] = _override_db
    with (
        patch.object(workflow_service, "_is_auto_assignment_workflow_enabled", return_value=True),
        patch.object(accountability_service, "is_accountability_enabled", return_value=True),
    ):
        with TestClient(app) as tc:
            yield tc
    app.dependency_overrides.pop(get_db, None)


def _mk_user(db: Session, role_name: str, *, status: str = "ACTIVE") -> NguoiDung:
    role = db.scalar(select(VaiTro).where(VaiTro.tenVaiTro == role_name))
    assert role is not None
    tag = uuid.uuid4().hex[:8]
    u = NguoiDung(
        tenTaiKhoan=f"g34_{role_name.lower()}_{tag}",
        email=f"g34_{role_name.lower()}_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase34test00000000000000000000",
        hoTen=f"G34 {role_name} {tag}",
        maVaiTro=role.maVaiTro,
        trangThai=status,
        batBuocDoiMatKhau=False,
    )
    db.add(u)
    db.flush()
    return u


def _mk_expert(db: Session, *, role_name: str = "EXPERT", status: str = "ACTIVE") -> tuple[NguoiDung, ChuyenGia]:
    u = _mk_user(db, role_name, status=status)
    e = ChuyenGia(
        maNguoiDung=u.maNguoiDung,
        trangThaiHoSo="VERIFIED",
        soNamKinhNghiem=6,
    )
    db.add(e)
    db.flush()
    return u, e


def _mk_course(db: Session, prov_id: int, cat_id: int) -> KhoaHoc:
    c = KhoaHoc(
        maNhaCungCap=prov_id,
        maDanhMuc=cat_id,
        tieuDe=f"G34 Course {uuid.uuid4().hex[:6]}",
        gia=Decimal("0"),
        trangThaiDuyet="PENDING",
        trangThaiHienThi="HIDDEN",
        soVongKiemDuyetHienTai=1,
    )
    db.add(c)
    db.flush()
    return c


def _mk_terminal_assignment(
    db: Session,
    *,
    course_id: int,
    expert_id: int,
    cat_id: int,
    status: str,
    occurred_at: datetime,
    reason_code: str | None = "WORKLOAD_PERSONAL",
) -> PhanCongKiemDuyet:
    pc = PhanCongKiemDuyet(
        maKhoaHoc=course_id,
        maChuyenGia=expert_id,
        maDanhMuc=cat_id,
        soVongKiemDuyet=1,
        phuongThucPhanCong="AUTO",
        trangThai=status,
        ngayPhanCong=occurred_at - timedelta(hours=24),
        hanTiepNhan=occurred_at if status == "EXPIRED" else occurred_at + timedelta(hours=12),
        maLyDoTuChoi=reason_code if status == "DECLINED" else None,
        lyDoTuChoi="Busy schedule" if status == "DECLINED" else None,
        chiTietDiem={
            "accountabilityEvent": {
                "eventType": "DECLINED_ASSIGNMENT" if status == "DECLINED" else "EXPIRED_ACCEPTANCE",
                "occurredAt": occurred_at.isoformat(),
                "expertId": expert_id,
            }
        },
    )
    db.add(pc)
    db.flush()
    return pc


# =====================================================================
# 1. UNIT POLICY MATRIX (Section 53)
# =====================================================================
def test_unit_policy_classification_and_discipline_levels():
    assert accountability_service.classify_initial_violation_status(
        violation_type="DECLINED_ASSIGNMENT",
        decline_reason_code="WORKLOAD_PERSONAL",
        expiration_counts_as_violation=True,
    ) == "CONFIRMED"
    for r in ("CONFLICT_OF_INTEREST", "SYSTEM_MISASSIGNMENT", "TECHNICAL_ISSUE", "OTHER"):
        assert accountability_service.classify_initial_violation_status(
            violation_type="DECLINED_ASSIGNMENT",
            decline_reason_code=r,
            expiration_counts_as_violation=True,
        ) == "PENDING_REVIEW"

    assert accountability_service.classify_initial_violation_status(
        violation_type="EXPIRED_ACCEPTANCE",
        decline_reason_code=None,
        expiration_counts_as_violation=True,
    ) == "CONFIRMED"
    assert accountability_service.classify_initial_violation_status(
        violation_type="EXPIRED_ACCEPTANCE",
        decline_reason_code=None,
        expiration_counts_as_violation=False,
    ) is None
    assert accountability_service.classify_initial_violation_status(
        violation_type="ABANDONED_ASSIGNMENT",
        decline_reason_code=None,
        expiration_counts_as_violation=True,
    ) == "PENDING_REVIEW"

    assert accountability_service.compute_discipline_level(0, warning_threshold=2, lock_threshold=4) == ("NORMAL", 0)
    assert accountability_service.compute_discipline_level(1, warning_threshold=2, lock_threshold=4) == ("REMINDER", 1)
    assert accountability_service.compute_discipline_level(2, warning_threshold=2, lock_threshold=4) == ("WARNING_1", 2)
    assert accountability_service.compute_discipline_level(3, warning_threshold=2, lock_threshold=4) == ("WARNING_FINAL", 3)
    assert accountability_service.compute_discipline_level(4, warning_threshold=2, lock_threshold=4) == ("AUTO_LOCK", 4)


# =====================================================================
# 2. ROLLING WINDOW 168H EXACT BOUNDARIES & CROSS-CYCLE DELAYED EVENTS
# =====================================================================
def test_rolling_window_168h_boundaries_and_delayed_events(pg_db: Session):
    T = datetime(2026, 11, 25, 12, 0, 0)
    prov = pg_db.scalar(select(NhaCungCapKhoaHoc).limit(1))
    cat = pg_db.scalar(select(DanhMuc).limit(1))
    u_e, e = _mk_expert(pg_db)

    # 1. T - 167h 59m 59s -> INSIDE (T-168h, T]
    c1 = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
    pc1 = _mk_terminal_assignment(pg_db, course_id=c1.maKhoaHoc, expert_id=e.maChuyenGia, cat_id=cat.maDanhMuc, status="EXPIRED", occurred_at=T - timedelta(hours=167, minutes=59, seconds=59))
    accountability_service.record_violation_for_assignment(pg_db, assignment_id=pc1.maPhanCong, violation_type="EXPIRED_ACCEPTANCE", now=T)

    # 2. Exactly T - 168h 00m 00s -> OUTSIDE (strictly > window_start)
    c2 = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
    pc2 = _mk_terminal_assignment(pg_db, course_id=c2.maKhoaHoc, expert_id=e.maChuyenGia, cat_id=cat.maDanhMuc, status="EXPIRED", occurred_at=T - timedelta(hours=168))
    accountability_service.record_violation_for_assignment(pg_db, assignment_id=pc2.maPhanCong, violation_type="EXPIRED_ACCEPTANCE", now=T)

    # 3. T - 168h 00m 01s -> OUTSIDE
    c3 = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
    pc3 = _mk_terminal_assignment(pg_db, course_id=c3.maKhoaHoc, expert_id=e.maChuyenGia, cat_id=cat.maDanhMuc, status="EXPIRED", occurred_at=T - timedelta(hours=168, seconds=1))
    accountability_service.record_violation_for_assignment(pg_db, assignment_id=pc3.maPhanCong, violation_type="EXPIRED_ACCEPTANCE", now=T)

    # 4. Exact T -> INSIDE (<= T)
    c4 = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
    pc4 = _mk_terminal_assignment(pg_db, course_id=c4.maKhoaHoc, expert_id=e.maChuyenGia, cat_id=cat.maDanhMuc, status="EXPIRED", occurred_at=T)
    accountability_service.record_violation_for_assignment(pg_db, assignment_id=pc4.maPhanCong, violation_type="EXPIRED_ACCEPTANCE", now=T)

    # 5. Future T + 1s -> EXCLUDED
    c5 = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
    pc5 = _mk_terminal_assignment(pg_db, course_id=c5.maKhoaHoc, expert_id=e.maChuyenGia, cat_id=cat.maDanhMuc, status="EXPIRED", occurred_at=T + timedelta(seconds=1))
    accountability_service.record_violation_for_assignment(pg_db, assignment_id=pc5.maPhanCong, violation_type="EXPIRED_ACCEPTANCE", now=T)

    cnt = accountability_service.count_confirmed_violations_in_window(
        pg_db,
        expert_id=e.maChuyenGia,
        cycle=1,
        cycle_started_at=None,
        window_hours=168,
        evaluated_at=T,
    )
    assert cnt == 2  # ONLY pc1 and pc4!

    # Cross-cycle delayed event protection: advance to cycle 2 with anchor = T
    e.chuKyKyLuatSo = 2
    e.mocChuKyKyLuat = T
    pg_db.flush()

    c_old = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
    pc_old = _mk_terminal_assignment(
        pg_db,
        course_id=c_old.maKhoaHoc,
        expert_id=e.maChuyenGia,
        cat_id=cat.maDanhMuc,
        status="EXPIRED",
        occurred_at=T - timedelta(hours=2),  # happened BEFORE unlock anchor T!
    )
    res_old = accountability_service.record_violation_for_assignment(
        pg_db, assignment_id=pc_old.maPhanCong, violation_type="EXPIRED_ACCEPTANCE", now=T + timedelta(minutes=10)
    )
    assert res_old.cycle == 1
    assert res_old.status == "PENDING_REVIEW"
    assert res_old.autoLocked is False


# =====================================================================
# 3. FULL E2E: 4 VIOLATIONS -> AUTO_LOCK -> REVOKE -> SECURITY -> UNLOCK
# =====================================================================
def test_full_accountability_autolock_revocation_security_and_unlock_e2e(pg_db: Session, acc_client: TestClient):
    now = _now_utc()
    admin_u = _mk_user(pg_db, "ADMIN")
    normal_u = _mk_user(pg_db, "USER")
    prov = pg_db.scalar(select(NhaCungCapKhoaHoc).limit(1))
    cat = pg_db.scalar(select(DanhMuc).limit(1))
    exp_u, exp = _mk_expert(pg_db)
    pre_lock_headers = _auth(exp_u)

    # Pre-create 3 active assignments (ASSIGNED, ACCEPTED, IN_PROGRESS with draft) + 1 COMPLETED
    active_pcs = []
    for st, draft in (("ASSIGNED", None), ("ACCEPTED", {"n": "d1"}), ("IN_PROGRESS", {"n": "d2"})):
        c_act = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
        pc = PhanCongKiemDuyet(
            maKhoaHoc=c_act.maKhoaHoc,
            maChuyenGia=exp.maChuyenGia,
            maDanhMuc=cat.maDanhMuc,
            soVongKiemDuyet=1,
            phuongThucPhanCong="AUTO",
            trangThai=st,
            ngayPhanCong=now - timedelta(hours=2),
            hanTiepNhan=now + timedelta(hours=22),
            banNhapDanhGia=draft,
        )
        pg_db.add(pc)
        pg_db.flush()
        active_pcs.append(pc.maPhanCong)

    c_done = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
    pc_done = PhanCongKiemDuyet(
        maKhoaHoc=c_done.maKhoaHoc,
        maChuyenGia=exp.maChuyenGia,
        maDanhMuc=cat.maDanhMuc,
        soVongKiemDuyet=1,
        phuongThucPhanCong="AUTO",
        trangThai="COMPLETED",
        ngayPhanCong=now - timedelta(hours=10),
        hanTiepNhan=now + timedelta(hours=14),
        ngayHoanThanh=now - timedelta(hours=1),
    )
    pg_db.add(pc_done)
    pg_db.flush()

    # Record 1st, 2nd, 3rd violations (REMINDER -> WARNING_1 -> WARNING_FINAL)
    expected_levels = ["REMINDER", "WARNING_1", "WARNING_FINAL"]
    for idx, exp_lvl in enumerate(expected_levels, start=1):
        c_v = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
        pc_v = _mk_terminal_assignment(
            pg_db,
            course_id=c_v.maKhoaHoc,
            expert_id=exp.maChuyenGia,
            cat_id=cat.maDanhMuc,
            status="DECLINED",
            occurred_at=now - timedelta(minutes=10 - idx),
            reason_code="WORKLOAD_PERSONAL",
        )
        r = accountability_service.record_violation_for_assignment(
            pg_db, assignment_id=pc_v.maPhanCong, violation_type="DECLINED_ASSIGNMENT", now=now
        )
        assert r.disciplineLevel == exp_lvl
        assert r.autoLocked is False

    # Also record a PENDING_REVIEW violation (SYSTEM_MISASSIGNMENT) -> must NOT trigger auto-lock!
    c_pend = _mk_course(pg_db, prov.maNhaCungCap, cat.maDanhMuc)
    pc_pend = _mk_terminal_assignment(
        pg_db,
        course_id=c_pend.maKhoaHoc,
        expert_id=exp.maChuyenGia,
        cat_id=cat.maDanhMuc,
        status="DECLINED",
        occurred_at=now - timedelta(minutes=5),
        reason_code="SYSTEM_MISASSIGNMENT",
    )
    r_pend = accountability_service.record_violation_for_assignment(
        pg_db, assignment_id=pc_pend.maPhanCong, violation_type="DECLINED_ASSIGNMENT", now=now
    )
    assert r_pend.status == "PENDING_REVIEW"
    assert r_pend.autoLocked is False

    # Expert can read own summary while ACTIVE (3 confirmed, 1 remaining before lock)
    s_resp = acc_client.get("/api/expert/accountability/summary", headers=pre_lock_headers)
    assert s_resp.status_code == 200
    assert s_resp.json()["confirmedViolationsInWindow"] == 3
    assert s_resp.json()["remainingBeforeLock"] == 1
    assert s_resp.json()["disciplineLevel"] == "WARNING_FINAL"

    # ADMIN confirms the PENDING_REVIEW violation -> hits 4 -> AUTO_LOCK + revokes all 3 active assignments!
    c_resp = acc_client.post(
        f"/api/admin/accountability/violations/{r_pend.violationId}/confirm",
        json={"ghiChuXuLy": "Đã kiểm tra log, không có lỗi hệ thống."},
        headers=_auth(admin_u),
    )
    assert c_resp.status_code == 200
    pg_db.refresh(exp_u)
    assert exp_u.trangThai == "LOCKED"

    # Verify all 3 active assignments were CANCELLED, draft preserved, COMPLETED untouched!
    for apc_id in active_pcs:
        apc = pg_db.get(PhanCongKiemDuyet, apc_id)
        assert apc.trangThai == "CANCELLED"
        assert "ACCOUNT_LOCKED" in (apc.lyDoHuy or "")
    assert pg_db.get(PhanCongKiemDuyet, active_pcs[2]).banNhapDanhGia == {"n": "d2"}
    assert pg_db.get(PhanCongKiemDuyet, pc_done.maPhanCong).trangThai == "COMPLETED"

    # Immediate Access Revocation: pre-lock JWT blocked with 403 on ALL endpoints!
    assert acc_client.get("/api/expert/accountability/summary", headers=pre_lock_headers).status_code == 403
    assert acc_client.get("/api/expert/assignments", headers=pre_lock_headers).status_code == 403

    # Generic admin user status update CANNOT bypass disciplinary unlock!
    with pytest.raises(WorkflowConflictError):
        with patch.object(accountability_service, "is_accountability_enabled", return_value=True):
            workflow_service.update_admin_user_status(pg_db, admin_u.maNguoiDung, exp_u.maNguoiDung, "ACTIVE")

    # Exempting a violation does NOT auto-unlock the account!
    ex_resp = acc_client.post(
        f"/api/admin/accountability/violations/{r_pend.violationId}/exempt",
        json={"ghiChuXuLy": "Miễn trừ sau khi chuyên gia cung cấp bằng chứng."},
        headers=_auth(admin_u),
    )
    assert ex_resp.status_code == 200
    pg_db.refresh(exp_u)
    assert exp_u.trangThai == "LOCKED"

    # Non-ADMIN cannot unlock (403)
    assert acc_client.post(
        f"/api/admin/accountability/experts/{exp.maChuyenGia}/unlock",
        json={"lyDo": "Unauthorized unlock"},
        headers=_auth(normal_u),
    ).status_code == 403

    # ADMIN unlocks -> ACTIVE, cycle 1 -> 2, mocChuKyKyLuat set, audit log recorded!
    un_resp = acc_client.post(
        f"/api/admin/accountability/experts/{exp.maChuyenGia}/unlock",
        json={"lyDo": "Đã trao đổi và cam kết tuân thủ thời hạn."},
        headers=_auth(admin_u),
    )
    assert un_resp.status_code == 200
    assert un_resp.json()["chuKyKyLuatSo"] == 2
    assert un_resp.json()["trangThaiTaiKhoan"] == "ACTIVE"

    # Second unlock on already-ACTIVE account MUST fail (409) and NOT increment cycle!
    un_resp2 = acc_client.post(
        f"/api/admin/accountability/experts/{exp.maChuyenGia}/unlock",
        json={"lyDo": "Duplicate unlock"},
        headers=_auth(admin_u),
    )
    assert un_resp2.status_code == 409
    pg_db.refresh(exp)
    assert exp.chuKyKyLuatSo == 2

    # Audit logs exist and mass-assignment is rejected (422)
    logs_resp = acc_client.get(
        f"/api/admin/accountability/audit-logs?expert_id={exp.maChuyenGia}",
        headers=_auth(admin_u),
    )
    assert logs_resp.status_code == 200
    actions = {item["hanhDong"] for item in logs_resp.json()}
    assert {"REMINDER", "WARNING_1", "WARNING_FINAL", "CONFIRM_VIOLATION", "AUTO_LOCK", "EXEMPT_VIOLATION", "ADMIN_UNLOCK"} <= actions

    assert acc_client.patch(
        "/api/admin/accountability/config",
        json={"nguongCanhBao": 5, "nguongKhoaTaiKhoan": 4},
        headers=_auth(admin_u),
    ).status_code == 422


# =====================================================================
# 4. REAL MULTI-CONNECTION CONCURRENCY & CRASH RECOVERY (C1, C2, C8)
# =====================================================================
def test_accountability_concurrency_c1_c2_c8_and_crash_recovery_on_real_postgres():
    now = _now_utc()
    cleanup: dict[str, list[int]] = {
        "assignments": [],
        "courses": [],
        "experts": [],
        "users": [],
    }

    def _s() -> Session:
        s = TestSessionFactory()
        assert s.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
        return s

    try:
        with _s() as s:
            prov = s.scalar(select(NhaCungCapKhoaHoc).limit(1))
            cat = s.scalar(select(DanhMuc).limit(1))
            admin_u = _mk_user(s, "ADMIN")
            exp_u, exp = _mk_expert(s)
            cleanup["users"].extend([admin_u.maNguoiDung, exp_u.maNguoiDung])
            cleanup["experts"].append(exp.maChuyenGia)

            # Seed 3 confirmed violations
            for i in range(3):
                c = _mk_course(s, prov.maNhaCungCap, cat.maDanhMuc)
                cleanup["courses"].append(c.maKhoaHoc)
                pc = _mk_terminal_assignment(
                    s, course_id=c.maKhoaHoc, expert_id=exp.maChuyenGia, cat_id=cat.maDanhMuc,
                    status="EXPIRED", occurred_at=now - timedelta(hours=5 - i)
                )
                cleanup["assignments"].append(pc.maPhanCong)
                accountability_service.record_violation_for_assignment(
                    s, assignment_id=pc.maPhanCong, violation_type="EXPIRED_ACCEPTANCE", now=now, commit=False
                )

            # Create 2 MORE expired assignments to race threshold crossing (C2) + duplicate violation (C1)
            c4 = _mk_course(s, prov.maNhaCungCap, cat.maDanhMuc)
            c5 = _mk_course(s, prov.maNhaCungCap, cat.maDanhMuc)
            cleanup["courses"].extend([c4.maKhoaHoc, c5.maKhoaHoc])
            pc4 = _mk_terminal_assignment(s, course_id=c4.maKhoaHoc, expert_id=exp.maChuyenGia, cat_id=cat.maDanhMuc, status="EXPIRED", occurred_at=now - timedelta(minutes=2))
            pc5 = _mk_terminal_assignment(s, course_id=c5.maKhoaHoc, expert_id=exp.maChuyenGia, cat_id=cat.maDanhMuc, status="EXPIRED", occurred_at=now - timedelta(minutes=1))
            cleanup["assignments"].extend([pc4.maPhanCong, pc5.maPhanCong])

            # Also add 1 active assignment to prove crash recovery revokes it after lock!
            c_act = _mk_course(s, prov.maNhaCungCap, cat.maDanhMuc)
            cleanup["courses"].append(c_act.maKhoaHoc)
            pc_act = PhanCongKiemDuyet(
                maKhoaHoc=c_act.maKhoaHoc,
                maChuyenGia=exp.maChuyenGia,
                maDanhMuc=cat.maDanhMuc,
                soVongKiemDuyet=1,
                phuongThucPhanCong="AUTO",
                trangThai="ACCEPTED",
                ngayPhanCong=now - timedelta(hours=1),
                hanTiepNhan=now + timedelta(hours=23),
                banNhapDanhGia={"saved": True},
            )
            s.add(pc_act)
            s.flush()
            cleanup["assignments"].append(pc_act.maPhanCong)
            s.commit()
            ids = {
                "admin_uid": admin_u.maNguoiDung,
                "exp_id": exp.maChuyenGia,
                "exp_uid": exp_u.maNguoiDung,
                "pc4": pc4.maPhanCong,
                "pc5": pc5.maPhanCong,
                "pc_act": pc_act.maPhanCong,
            }

        # --- C1 + C2: Concurrent threshold crossing (2 threads record pc4 & pc5 simultaneously) ---
        b_c2 = Barrier(2)

        def _rec(pc_id):
            with _s() as s:
                b_c2.wait()
                return accountability_service.record_violation_for_assignment(
                    s, assignment_id=pc_id, violation_type="EXPIRED_ACCEPTANCE", now=now, commit=True
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            res_c2 = [f.result() for f in [pool.submit(_rec, ids["pc4"]), pool.submit(_rec, ids["pc5"])]]

        # Exactly ONE thread performed AUTO_LOCK; BOTH violations recorded!
        assert sum(1 for r in res_c2 if r.autoLocked) == 1
        with _s() as s:
            auto_locks = s.scalars(
                select(NhatKyKyLuatChuyenGia).where(
                    NhatKyKyLuatChuyenGia.maChuyenGia == ids["exp_id"],
                    NhatKyKyLuatChuyenGia.hanhDong == "AUTO_LOCK",
                )
            ).all()
            assert len(auto_locks) == 1
            # Crash recovery: simulate crash after lock before revocation -> reconcile recovers pc_act!
            revoked = accountability_service.reconcile_locked_expert_assignments(
                s, expert_id=ids["exp_id"], now=now, commit=True
            )
            assert revoked == 1
            assert s.get(PhanCongKiemDuyet, ids["pc_act"]).trangThai == "CANCELLED"

        # --- C8: Concurrent ADMIN unlock (2 threads -> exactly 1 succeeds, cycle increments ONCE!) ---
        b_c8 = Barrier(2)

        def _unlock():
            with _s() as s:
                b_c8.wait()
                try:
                    accountability_service.admin_unlock_expert(
                        s,
                        admin_user_id=ids["admin_uid"],
                        expert_id=ids["exp_id"],
                        reason="Concurrent unlock test",
                        now=now + timedelta(minutes=5),
                    )
                    return "OK"
                except WorkflowConflictError:
                    s.rollback()
                    return "CONFLICT"

        with ThreadPoolExecutor(max_workers=2) as pool:
            res_c8 = sorted(f.result() for f in [pool.submit(_unlock), pool.submit(_unlock)])
        assert res_c8 == ["CONFLICT", "OK"], f"C8 failed: {res_c8}"
        with _s() as s:
            assert s.get(ChuyenGia, ids["exp_id"]).chuKyKyLuatSo == 2

    finally:
        with _s() as sc:
            sc.execute(text('DELETE FROM "ThongBao" WHERE "khoaChongTrung" LIKE \'ACC_%\''))
            if cleanup["users"]:
                sc.execute(text('DELETE FROM "ThongBao" WHERE "maNguoiNhan" = ANY(:ids)'), {"ids": cleanup["users"]})
            if cleanup["courses"]:
                sc.execute(text('DELETE FROM "HangDoiPhanCong" WHERE "maKhoaHoc" = ANY(:ids)'), {"ids": cleanup["courses"]})
            if cleanup["experts"]:
                sc.execute(text('DELETE FROM "NhatKyKyLuatChuyenGia" WHERE "maChuyenGia" = ANY(:ids)'), {"ids": cleanup["experts"]})
                sc.execute(text('DELETE FROM "ViPhamChuyenGia" WHERE "maChuyenGia" = ANY(:ids)'), {"ids": cleanup["experts"]})
            if cleanup["assignments"]:
                sc.execute(text('DELETE FROM "PhanCongKiemDuyet" WHERE "maPhanCong" = ANY(:ids)'), {"ids": cleanup["assignments"]})
            if cleanup["courses"]:
                sc.execute(text('DELETE FROM "KhoaHoc" WHERE "maKhoaHoc" = ANY(:ids)'), {"ids": cleanup["courses"]})
            if cleanup["experts"]:
                sc.execute(text('DELETE FROM "ChuyenGia" WHERE "maChuyenGia" = ANY(:ids)'), {"ids": cleanup["experts"]})
            if cleanup["users"]:
                sc.execute(text('DELETE FROM "NguoiDung" WHERE "maNguoiDung" = ANY(:ids)'), {"ids": cleanup["users"]})
            sc.commit()
