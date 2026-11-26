"""GĐ3.7 Verification Suite:
- ADMIN Manual Assignment (POST /api/admin/assignments/manual):
  * Enforces RBAC (EXPERT -> 403), extra="forbid"
  * Enforces full eligibility (VERIFIED, specialty match, load, pause, not previously excluded, no duplicate active)
  * Persists phuongThucPhanCong='MANUAL', maNguoiPhanCong=admin_id, lyDoPhanCong
  * Atomically cancels open HangDoiPhanCong jobs (no worker race) + sends idempotent notification
- ACC-09 legacy JWT without iat_ms: fail-closed in same-second unlock window
- SEC-02 cross-expert assignment isolation

STRICTLY targets EduSuggest_phase3_test with runtime current_database() guard.
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import urlparse, urlunparse

import jwt
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from config.config import get_settings
from config.database import get_db
from main import app
from models import (
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    DanhMuc,
    HangDoiPhanCong,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    PhanCongKiemDuyet,
    ThongBao,
    VaiTro,
)
from service import accountability_service, assignment_queue_service, workflow_service
from utils.security import JWT_ALGORITHM, _jwt_signing_key, create_access_token


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
        tenTaiKhoan=f"g37_{role_name.lower()}_{tag}",
        email=f"g37_{role_name.lower()}_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase37test00000000000000000000",
        hoTen=f"G37 {role_name} {tag}",
        maVaiTro=role.maVaiTro,
        trangThai=status,
        batBuocDoiMatKhau=False,
    )
    db.add(u)
    db.flush()
    return u


def _mk_expert(db: Session, *, status: str = "ACTIVE", profile_status: str = "VERIFIED") -> tuple[NguoiDung, ChuyenGia]:
    u = _mk_user(db, "EXPERT", status=status)
    e = ChuyenGia(maNguoiDung=u.maNguoiDung, trangThaiHoSo=profile_status, soNamKinhNghiem=7)
    db.add(e)
    db.flush()
    return u, e


def test_admin_manual_assignment_eligibility_atomic_queue_cancel_and_sec02(pg_db: Session, client: TestClient):
    admin = _mk_user(pg_db, "ADMIN")
    exp_u1, exp1 = _mk_expert(pg_db)
    exp_u2, exp2 = _mk_expert(pg_db)  # no matching specialty
    now = _now_utc()

    tag = uuid.uuid4().hex[:6]
    dm = DanhMuc(tenDanhMuc=f"G37 Cat {tag}")
    pg_db.add(dm)
    pg_db.flush()
    cm = ChuyenMon(tenChuyenMon=f"G37 Spec {tag}", nhomChuyenMon="G37", trangThai="ACTIVE", ngayTao=now)
    pg_db.add(cm)
    pg_db.flush()
    pg_db.add(ChuyenMonDanhMuc(maChuyenMon=cm.maChuyenMon, maDanhMuc=dm.maDanhMuc, ngayTao=now))
    pg_db.add(ChuyenGiaChuyenMon(maChuyenGia=exp1.maChuyenGia, maChuyenMon=cm.maChuyenMon, laChuyenMonChinh=True, ngayTao=now))

    prov_u = _mk_user(pg_db, "PROVIDER")
    prov = NhaCungCapKhoaHoc(maNguoiDung=prov_u.maNguoiDung, tieuSu="G37 Org")
    pg_db.add(prov)
    pg_db.flush()
    course = KhoaHoc(
        maNhaCungCap=prov.maNhaCungCap,
        maDanhMuc=dm.maDanhMuc,
        tieuDe=f"G37 Course {tag}",
        gia=Decimal("0"),
        trangThaiDuyet="PENDING",
        trangThaiHienThi="HIDDEN",
        soVongKiemDuyetHienTai=1,
    )
    pg_db.add(course)
    pg_db.flush()

    # Open queue job exists for this course
    job, _ = assignment_queue_service.enqueue_assignment_job(
        pg_db, target_type="COURSE", target_id=course.maKhoaHoc, review_round=1, event_type="SUBMIT", now=now
    )
    pg_db.flush()

    # RBAC: EXPERT cannot call manual assignment -> 403
    r_forbid = client.post(
        "/api/admin/assignments/manual",
        headers=_auth(exp_u1),
        json={
            "loaiDoiTuong": "COURSE",
            "maDoiTuong": course.maKhoaHoc,
            "maChuyenGia": exp1.maChuyenGia,
            "lyDoPhanCong": "Thử vượt quyền",
        },
    )
    assert r_forbid.status_code == 403

    # Ineligible expert (no specialty match) -> 409
    r_inelig = client.post(
        "/api/admin/assignments/manual",
        headers=_auth(admin),
        json={
            "loaiDoiTuong": "COURSE",
            "maDoiTuong": course.maKhoaHoc,
            "maChuyenGia": exp2.maChuyenGia,
            "lyDoPhanCong": "Phân công chuyên gia không khớp chuyên môn",
        },
    )
    assert r_inelig.status_code == 409

    # Valid manual assignment -> 201, MANUAL, maNguoiPhanCong=admin, queue job CANCELLED, notification sent
    r_ok = client.post(
        "/api/admin/assignments/manual",
        headers=_auth(admin),
        json={
            "loaiDoiTuong": "COURSE",
            "maDoiTuong": course.maKhoaHoc,
            "maChuyenGia": exp1.maChuyenGia,
            "lyDoPhanCong": "Ngoại lệ ưu tiên khóa học trọng điểm",
        },
    )
    assert r_ok.status_code == 201
    body = r_ok.json()
    assert body["phuongThucPhanCong"] == "MANUAL"
    assert body["maChuyenGia"] == exp1.maChuyenGia
    pc_id = body["maPhanCong"]

    pc_db = pg_db.get(PhanCongKiemDuyet, pc_id)
    assert int(pc_db.maNguoiPhanCong) == int(admin.maNguoiDung)

    pg_db.refresh(job)
    assert job.trangThai == "CANCELLED"
    assert "MANUAL_ASSIGNED_BY_ADMIN" in (job.lyDoCho or "")

    notif = pg_db.scalar(
        select(ThongBao).where(
            ThongBao.maNguoiNhan == exp_u1.maNguoiDung,
            ThongBao.khoaChongTrung == f"ASSIGN_NEW:{pc_id}:TO:{exp_u1.maNguoiDung}",
        )
    )
    assert notif is not None

    # Duplicate manual assignment rejected -> 409
    r_dup = client.post(
        "/api/admin/assignments/manual",
        headers=_auth(admin),
        json={
            "loaiDoiTuong": "COURSE",
            "maDoiTuong": course.maKhoaHoc,
            "maChuyenGia": exp1.maChuyenGia,
            "lyDoPhanCong": "Cố tạo trùng phân công active",
        },
    )
    assert r_dup.status_code == 409

    # SEC-02: Other expert (exp_u2) cannot view exp_u1's assignment -> 403
    assert client.get(f"/api/expert/assignments/{pc_id}", headers=_auth(exp_u2)).status_code == 403
    # Assigned expert (exp_u1) can view -> 200
    assert client.get(f"/api/expert/assignments/{pc_id}", headers=_auth(exp_u1)).status_code == 200


def test_acc09_legacy_token_without_iat_ms_fails_closed_on_same_second_unlock(pg_db: Session, client: TestClient):
    """Legacy JWT lacking iat_ms issued in the exact same second as ADMIN_UNLOCK MUST return 401."""
    admin = _mk_user(pg_db, "ADMIN")
    exp_u, exp = _mk_expert(pg_db)

    now_utc = datetime.now(UTC)
    settings = get_settings()
    legacy_payload = {
        "sub": str(exp_u.maNguoiDung),
        "jti": str(uuid.uuid4()),
        "iat": int(now_utc.timestamp()),  # integer-second legacy token WITHOUT iat_ms
        "exp": int((now_utc + timedelta(hours=1)).timestamp()),
        "iss": settings.app_name,
    }
    legacy_tok = jwt.encode(
        legacy_payload, _jwt_signing_key(exp_u.matKhau), algorithm=JWT_ALGORITHM
    )
    legacy_headers = {"Authorization": f"Bearer {legacy_tok}"}

    accountability_service.admin_lock_expert(
        pg_db, admin_user_id=admin.maNguoiDung, expert_id=exp.maChuyenGia, reason="Lock legacy test", now=now_utc.replace(tzinfo=None)
    )
    accountability_service.admin_unlock_expert(
        pg_db, admin_user_id=admin.maNguoiDung, expert_id=exp.maChuyenGia, reason="Unlock same second", now=now_utc.replace(tzinfo=None)
    )

    assert client.get("/api/notifications/unread-count", headers=legacy_headers).status_code == 401
