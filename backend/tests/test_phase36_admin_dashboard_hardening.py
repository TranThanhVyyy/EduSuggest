"""GĐ3.6 Verification Suite:
- ACC-09 same-second millisecond precision JWT rejection after ADMIN_UNLOCK
- Reconciliation non-infinite loop protection for policy-skipped events
- ADMIN System Config API (GET/PATCH /api/admin/assignments/config) + validation + RBAC
- ADMIN Expert Overview API (GET /api/admin/assignments/overview) + RBAC

STRICTLY targets EduSuggest_phase3_test with runtime current_database() guard.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import urlparse, urlunparse

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from config.database import get_db
from main import app
from models import (
    ChuyenGia,
    DanhMuc,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    PhanCongKiemDuyet,
    VaiTro,
    ViPhamChuyenGia,
    YeuCauTamNgungChuyenGia,
)
from service import accountability_service, workflow_service
from utils.security import create_access_token


def _build_test_engine():
    load_dotenv(r"d:\đồ án\EduSuggest\backend\.env")
    prod_url = os.getenv("DATABASE_URL") or ""
    p = urlparse(prod_url)
    assert p.path.lstrip("/") == "EduSuggest"
    test_url = urlunparse(p._replace(path="/EduSuggest_phase3_test"))
    eng = create_engine(test_url, pool_pre_ping=True)
    with eng.connect() as c:
        assert c.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
    return eng


TEST_ENGINE = _build_test_engine()


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
def client(pg_db: Session):
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
        tenTaiKhoan=f"g36_{role_name.lower()}_{tag}",
        email=f"g36_{role_name.lower()}_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase36test00000000000000000000",
        hoTen=f"G36 {role_name} {tag}",
        maVaiTro=role.maVaiTro,
        trangThai=status,
        batBuocDoiMatKhau=False,
    )
    db.add(u)
    db.flush()
    return u


def _mk_expert(db: Session, *, status: str = "ACTIVE", profile_status: str = "VERIFIED") -> tuple[NguoiDung, ChuyenGia]:
    u = _mk_user(db, "EXPERT", status=status)
    e = ChuyenGia(maNguoiDung=u.maNguoiDung, trangThaiHoSo=profile_status, soNamKinhNghiem=5)
    db.add(e)
    db.flush()
    return u, e


def test_acc09_same_second_pre_lock_jwt_rejected_after_unlock(pg_db: Session, client: TestClient):
    """ACC-09 millisecond precision: even without 1s sleep, pre-lock JWT is rejected after unlock."""
    admin = _mk_user(pg_db, "ADMIN")
    exp_u, exp = _mk_expert(pg_db)

    pre_lock_headers = _auth(exp_u)
    time.sleep(0.02)  # 20ms later (same second!)
    accountability_service.admin_lock_expert(
        pg_db, admin_user_id=admin.maNguoiDung, expert_id=exp.maChuyenGia, reason="Lock same-second test"
    )
    accountability_service.admin_unlock_expert(
        pg_db, admin_user_id=admin.maNguoiDung, expert_id=exp.maChuyenGia, reason="Unlock same-second test"
    )

    # Pre-lock JWT issued 20ms earlier MUST return 401
    assert client.get("/api/notifications/unread-count", headers=pre_lock_headers).status_code == 401

    time.sleep(0.02)
    fresh_headers = _auth(exp_u)
    assert client.get("/api/notifications/unread-count", headers=fresh_headers).status_code == 200


def test_reconciliation_no_infinite_loop_on_skipped_policy_event(pg_db: Session):
    """Policy-skipped EXPIRED events are marked reconciledSkipped=True and never re-processed."""
    _, exp = _mk_expert(pg_db)
    dm = DanhMuc(tenDanhMuc=f"G36 Cat {uuid.uuid4().hex[:6]}")
    pg_db.add(dm)
    pg_db.flush()
    prov_u = _mk_user(pg_db, "PROVIDER")
    prov = NhaCungCapKhoaHoc(maNguoiDung=prov_u.maNguoiDung, tieuSu="G36 Org")
    pg_db.add(prov)
    pg_db.flush()
    course = KhoaHoc(
        maNhaCungCap=prov.maNhaCungCap,
        maDanhMuc=dm.maDanhMuc,
        tieuDe="G36 Course",
        gia=Decimal("0"),
        trangThaiDuyet="PENDING",
        trangThaiHienThi="HIDDEN",
        soVongKiemDuyetHienTai=1,
    )
    pg_db.add(course)
    pg_db.flush()
    now = _now_utc()

    pc = PhanCongKiemDuyet(
        maKhoaHoc=course.maKhoaHoc,
        maChuyenGia=exp.maChuyenGia,
        maDanhMuc=dm.maDanhMuc,
        soVongKiemDuyet=1,
        trangThai="EXPIRED",
        phuongThucPhanCong="AUTO",
        hanTiepNhan=now - timedelta(minutes=5),
        ngayPhanCong=now - timedelta(hours=2),
        ngayCapNhat=now - timedelta(minutes=5),
        chiTietDiem={
            "accountabilityEvent": {
                "eventType": "EXPIRED_ACCEPTANCE",
                "occurredAt": (now - timedelta(minutes=5)).isoformat(),
                "expertId": int(exp.maChuyenGia),
                "policySnapshot": {"tinhViPhamHetHan": False},
            }
        },
    )
    pg_db.add(pc)
    pg_db.flush()

    # First reconciliation marks it reconciledSkipped=True (returns 0 violations created)
    rec1 = accountability_service.reconcile_unrecorded_accountability_events(pg_db, now=now, commit=False)
    assert rec1 == 0
    pg_db.refresh(pc)
    assert pc.chiTietDiem["accountabilityEvent"]["reconciledSkipped"] is True

    # Second reconciliation skips it cleanly without even calling record_violation_for_assignment
    with patch.object(accountability_service, "record_violation_for_assignment") as spy:
        rec2 = accountability_service.reconcile_unrecorded_accountability_events(pg_db, now=now, commit=False)
        assert rec2 == 0
        spy.assert_not_called()


def test_admin_assignment_config_get_patch_validation_and_rbac(pg_db: Session, client: TestClient):
    admin = _mk_user(pg_db, "ADMIN")
    exp_u, _ = _mk_expert(pg_db)

    # RBAC: EXPERT forbidden
    assert client.get("/api/admin/assignments/config", headers=_auth(exp_u)).status_code == 403
    assert client.patch("/api/admin/assignments/config", headers=_auth(exp_u), json={"gioiHanTaiToiDa": 6}).status_code == 403

    # GET singleton
    r_get = client.get("/api/admin/assignments/config", headers=_auth(admin))
    assert r_get.status_code == 200
    assert r_get.json()["maCauHinh"] == 1

    # Reject unknown field (extra="forbid")
    r_extra = client.patch("/api/admin/assignments/config", headers=_auth(admin), json={"hackField": 123})
    assert r_extra.status_code == 422

    # Reject invalid threshold ordering
    r_bad = client.patch(
        "/api/admin/assignments/config",
        headers=_auth(admin),
        json={"nguongCanhBao": 5, "nguongKhoaTaiKhoan": 4},
    )
    assert r_bad.status_code == 422

    # Valid update
    r_ok = client.patch(
        "/api/admin/assignments/config",
        headers=_auth(admin),
        json={
            "gioiHanTaiToiDa": 6,
            "thoiGianTamNgungToiDaNgay": 21,
            "uuTienTuyetDoiChuyenMonChinh": True,
        },
    )
    assert r_ok.status_code == 200
    body = r_ok.json()
    assert body["gioiHanTaiToiDa"] == 6
    assert body["thoiGianTamNgungToiDaNgay"] == 21
    assert body["uuTienTuyetDoiChuyenMonChinh"] is True


def test_admin_expert_overview_real_postgres_kpis_and_rbac(pg_db: Session, client: TestClient):
    admin = _mk_user(pg_db, "ADMIN")
    exp_u1, exp1 = _mk_expert(pg_db, status="ACTIVE", profile_status="VERIFIED")
    _, exp2 = _mk_expert(pg_db, status="LOCKED", profile_status="PENDING_VERIFICATION")
    now = _now_utc()

    # Active approved pause for exp1
    pg_db.add(
        YeuCauTamNgungChuyenGia(
            maChuyenGia=exp1.maChuyenGia,
            ngayBatDau=now - timedelta(hours=2),
            ngayKetThuc=now + timedelta(days=2),
            lyDo="Tạm ngừng kiểm thử overview",
            trangThai="APPROVED",
            ngayGuiYeuCau=now - timedelta(hours=3),
            ngayCapNhat=now - timedelta(hours=2),
        )
    )
    pg_db.flush()

    # RBAC: EXPERT forbidden
    assert client.get("/api/admin/assignments/overview", headers=_auth(exp_u1)).status_code == 403

    r = client.get("/api/admin/assignments/overview", headers=_auth(admin))
    assert r.status_code == 200
    data = r.json()
    assert data["totalExperts"] >= 2
    assert data["verifiedExperts"] >= 1
    assert data["pendingVerificationExperts"] >= 1
    assert data["pausedExperts"] >= 1
    assert data["lockedExperts"] >= 1
    assert "assignmentStatusBreakdown" in data
    assert "queueStatusBreakdown" in data
    assert "disciplineLevelBreakdown" in data
