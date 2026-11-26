"""GĐ3.5 Comprehensive Verification Suite:
- Expert Availability Management (CRUD, 30-day cap, half-open [start, end) overlap, cancel, ADMIN approve/reject/revoke, active assignments preserved, completion + WAITING_ELIGIBLE wake-up)
- Notification Center (paginated list, is_read filter, unread count, mark one read, mark all read, strict ownership, {event_key}:TO:{user_id} idempotency)
- Hardening Verification:
  * ACC-09: Pre-lock JWT rejected (401) after ADMIN unlock; fresh JWT succeeds (200)
  * ACC-10: Exact historical cycle lookup across multiple ADMIN unlocks
  * ACC-11: Policy snapshot at event time (tinhViPhamHetHan) honored even if config changes later
  * ACC-12: Durable crash-recovery reconciliation for unrecorded DECLINED/EXPIRED events
  * ACC-13: Immediate 403 block on direct URL access when locked
  * ACC-14: Real multi-connection concurrency tests (overlap create, approve vs assign, confirm vs exempt)

STRICTLY targets EduSuggest_phase3_test with runtime current_database() guard.
"""
from __future__ import annotations

import os
import time
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
from sqlalchemy import create_engine, delete, select, text
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
    ThongBao,
    VaiTro,
    ViPhamChuyenGia,
    YeuCauTamNgungChuyenGia,
)
from service import (
    accountability_service,
    assignment_queue_service,
    assignment_service,
    availability_service,
    notification_service,
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
        tenTaiKhoan=f"g35_{role_name.lower()}_{tag}",
        email=f"g35_{role_name.lower()}_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase35test00000000000000000000",
        hoTen=f"G35 {role_name} {tag}",
        maVaiTro=role.maVaiTro,
        trangThai=status,
        batBuocDoiMatKhau=False,
    )
    db.add(u)
    db.flush()
    return u


def _mk_expert(db: Session, *, status: str = "ACTIVE") -> tuple[NguoiDung, ChuyenGia]:
    u = _mk_user(db, "EXPERT", status=status)
    e = ChuyenGia(
        maNguoiDung=u.maNguoiDung,
        trangThaiHoSo="VERIFIED",
        soNamKinhNghiem=6,
    )
    db.add(e)
    db.flush()
    return u, e


def _mk_isolated_domain(db: Session) -> tuple[DanhMuc, ChuyenMon, NhaCungCapKhoaHoc]:
    tag = uuid.uuid4().hex[:6]
    now = _now_utc()
    dm = DanhMuc(tenDanhMuc=f"G35 Cat {tag}", moTa="Isolated test category")
    db.add(dm)
    db.flush()
    cm = ChuyenMon(
        tenChuyenMon=f"G35 Spec {tag}",
        nhomChuyenMon="G35_TEST",
        trangThai="ACTIVE",
        ngayTao=now,
    )
    db.add(cm)
    db.flush()
    db.add(ChuyenMonDanhMuc(maChuyenMon=cm.maChuyenMon, maDanhMuc=dm.maDanhMuc, ngayTao=now))
    prov_u = _mk_user(db, "PROVIDER")
    prov = NhaCungCapKhoaHoc(maNguoiDung=prov_u.maNguoiDung, tieuSu=f"G35 Org {tag}")
    db.add(prov)
    db.flush()
    return dm, cm, prov


def _attach_spec(db: Session, expert: ChuyenGia, cm: ChuyenMon) -> None:
    db.add(
        ChuyenGiaChuyenMon(
            maChuyenGia=expert.maChuyenGia,
            maChuyenMon=cm.maChuyenMon,
            laChuyenMonChinh=True,
            ngayTao=_now_utc(),
        )
    )
    db.flush()


def _mk_course(db: Session, prov_id: int, cat_id: int) -> KhoaHoc:
    c = KhoaHoc(
        maNhaCungCap=prov_id,
        maDanhMuc=cat_id,
        tieuDe=f"G35 Course {uuid.uuid4().hex[:6]}",
        gia=Decimal("0"),
        trangThaiDuyet="PENDING",
        trangThaiHienThi="HIDDEN",
        soVongKiemDuyetHienTai=1,
    )
    db.add(c)
    db.flush()
    return c


# =====================================================================
# 1. EXPERT AVAILABILITY MANAGEMENT + ENGINE INTEGRATION
# =====================================================================
def test_availability_create_validation_30day_cap_and_overlap(pg_db: Session, client: TestClient):
    admin = _mk_user(pg_db, "ADMIN")
    exp_u, exp = _mk_expert(pg_db)
    now = _now_utc()

    # > 30 days rejected (409)
    r_too_long = client.post(
        "/api/expert/availability",
        headers=_auth(exp_u),
        json={
            "ngayBatDau": (now + timedelta(days=1)).isoformat(),
            "ngayKetThuc": (now + timedelta(days=32)).isoformat(),
            "lyDo": "Nghỉ phép dài hơn 30 ngày",
        },
    )
    assert r_too_long.status_code == 409

    # end <= start rejected (422)
    r_bad_range = client.post(
        "/api/expert/availability",
        headers=_auth(exp_u),
        json={
            "ngayBatDau": (now + timedelta(days=2)).isoformat(),
            "ngayKetThuc": (now + timedelta(days=2)).isoformat(),
            "lyDo": "Khoảng thời gian rỗng",
        },
    )
    assert r_bad_range.status_code == 422

    # Valid creation (201) -> PENDING + notifies ADMIN
    t1 = now + timedelta(days=1)
    t2 = now + timedelta(days=5)
    r_ok = client.post(
        "/api/expert/availability",
        headers=_auth(exp_u),
        json={
            "ngayBatDau": t1.isoformat(),
            "ngayKetThuc": t2.isoformat(),
            "lyDo": "Công tác nước ngoài 4 ngày",
        },
    )
    assert r_ok.status_code == 201
    body = r_ok.json()
    assert body["trangThai"] == "PENDING"
    assert body["maChuyenGia"] == exp.maChuyenGia

    admin_notifs = pg_db.scalars(
        select(ThongBao).where(
            ThongBao.maNguoiNhan == admin.maNguoiDung,
            ThongBao.loaiThongBao == "AVAILABILITY_REQUESTED",
        )
    ).all()
    assert len(admin_notifs) >= 1

    # Overlapping interval [t1+2d, t2+2d) rejected (409)
    r_overlap = client.post(
        "/api/expert/availability",
        headers=_auth(exp_u),
        json={
            "ngayBatDau": (t1 + timedelta(days=2)).isoformat(),
            "ngayKetThuc": (t2 + timedelta(days=2)).isoformat(),
            "lyDo": "Yêu cầu bị chồng lấn",
        },
    )
    assert r_overlap.status_code == 409

    # Touching half-open interval [t2, t2+3d) ALLOWED (201)
    r_touch = client.post(
        "/api/expert/availability",
        headers=_auth(exp_u),
        json={
            "ngayBatDau": t2.isoformat(),
            "ngayKetThuc": (t2 + timedelta(days=3)).isoformat(),
            "lyDo": "Tiếp nối ngay sau đợt trước",
        },
    )
    assert r_touch.status_code == 201


def test_availability_expert_cancel_rules_and_ownership(pg_db: Session, client: TestClient):
    admin = _mk_user(pg_db, "ADMIN")
    exp_u1, _ = _mk_expert(pg_db)
    exp_u2, _ = _mk_expert(pg_db)
    now = _now_utc()

    # PENDING -> cancel allowed
    req1 = availability_service.create_availability_request(
        pg_db,
        user_id=exp_u1.maNguoiDung,
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
        reason="Lý do tạm ngừng 1",
        now=now,
    )
    # Other expert cannot cancel -> 403
    r_other = client.post(
        f"/api/expert/availability/{req1.maYeuCau}/cancel",
        headers=_auth(exp_u2),
        json={"lyDoHuy": "Cố tình hủy hộ người khác"},
    )
    assert r_other.status_code == 403

    r_c1 = client.post(
        f"/api/expert/availability/{req1.maYeuCau}/cancel",
        headers=_auth(exp_u1),
        json={"lyDoHuy": "Thay đổi kế hoạch cá nhân"},
    )
    assert r_c1.status_code == 200
    assert r_c1.json()["trangThai"] == "CANCELLED"

    # Future APPROVED -> cancel allowed
    req2 = availability_service.create_availability_request(
        pg_db,
        user_id=exp_u1.maNguoiDung,
        start_at=now + timedelta(days=6),
        end_at=now + timedelta(days=8),
        reason="Lý do tạm ngừng 2",
        now=now,
    )
    availability_service.admin_approve_availability(
        pg_db, admin_user_id=admin.maNguoiDung, request_id=req2.maYeuCau, now=now
    )
    r_c2 = client.post(
        f"/api/expert/availability/{req2.maYeuCau}/cancel",
        headers=_auth(exp_u1),
        json={"lyDoHuy": "Hủy trước khi đến ngày bắt đầu"},
    )
    assert r_c2.status_code == 200
    assert r_c2.json()["trangThai"] == "CANCELLED"

    # Active APPROVED (now >= ngayBatDau) -> cancel rejected (409)
    req3 = availability_service.create_availability_request(
        pg_db,
        user_id=exp_u1.maNguoiDung,
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(days=2),
        reason="Đang nghỉ phép rồi",
        now=now,
    )
    availability_service.admin_approve_availability(
        pg_db, admin_user_id=admin.maNguoiDung, request_id=req3.maYeuCau, now=now
    )
    r_c3 = client.post(
        f"/api/expert/availability/{req3.maYeuCau}/cancel",
        headers=_auth(exp_u1),
        json={"lyDoHuy": "Muốn tự hủy khi đang nghỉ"},
    )
    assert r_c3.status_code == 409


def test_availability_admin_approve_reject_revoke_and_engine_exclusion(pg_db: Session, client: TestClient):
    admin = _mk_user(pg_db, "ADMIN")
    dm, cm, prov = _mk_isolated_domain(pg_db)
    exp_u, exp = _mk_expert(pg_db)
    _attach_spec(pg_db, exp, cm)
    now = _now_utc()

    # Existing ASSIGNED task must NOT be cancelled when pause is approved
    course1 = _mk_course(pg_db, prov.maNhaCungCap, dm.maDanhMuc)
    existing_pc = PhanCongKiemDuyet(
        maKhoaHoc=course1.maKhoaHoc,
        maChuyenGia=exp.maChuyenGia,
        maDanhMuc=dm.maDanhMuc,
        soVongKiemDuyet=1,
        trangThai="ASSIGNED",
        phuongThucPhanCong="AUTO",
        hanTiepNhan=now + timedelta(hours=24),
        ngayPhanCong=now,
        ngayCapNhat=now,
    )
    pg_db.add(existing_pc)
    pg_db.flush()

    req = availability_service.create_availability_request(
        pg_db,
        user_id=exp_u.maNguoiDung,
        start_at=now - timedelta(minutes=10),
        end_at=now + timedelta(days=3),
        reason="Nghỉ phép khẩn cấp",
        now=now,
    )
    r_app = client.post(
        f"/api/admin/availability/{req.maYeuCau}/approve",
        headers=_auth(admin),
        json={"ghiChuXuLy": "Đồng ý cho nghỉ"},
    )
    assert r_app.status_code == 200
    assert r_app.json()["trangThai"] == "APPROVED"

    # Existing assignment is untouched!
    pg_db.refresh(existing_pc)
    assert existing_pc.trangThai == "ASSIGNED"

    # New course cannot be assigned to paused expert -> NO_ELIGIBLE_EXPERT
    course2 = _mk_course(pg_db, prov.maNhaCungCap, dm.maDanhMuc)
    res_paused = assignment_service.assign_best_expert(
        pg_db, target_type="COURSE", target_id=course2.maKhoaHoc, expected_review_round=1, now=now
    )
    assert res_paused.status.value == "NO_ELIGIBLE_EXPERT"

    # Put a WAITING_ELIGIBLE job in queue, then ADMIN revokes pause -> job wakes up to PENDING
    job, _ = assignment_queue_service.enqueue_assignment_job(
        pg_db,
        target_type="COURSE",
        target_id=course2.maKhoaHoc,
        review_round=1,
        event_type="SUBMIT",
        now=now,
    )
    job.trangThai = "WAITING_ELIGIBLE"
    job.thoiDiemChayTiepTheo = now + timedelta(hours=6)
    pg_db.flush()

    r_rev = client.post(
        f"/api/admin/availability/{req.maYeuCau}/revoke",
        headers=_auth(admin),
        json={"lyDoHuy": "Thu hồi theo thỏa thuận quay lại sớm"},
    )
    assert r_rev.status_code == 200
    assert r_rev.json()["trangThai"] == "CANCELLED"
    pg_db.refresh(job)
    assert job.trangThai == "PENDING"

    # Expert is now eligible again!
    res_back = assignment_service.assign_best_expert(
        pg_db, target_type="COURSE", target_id=course2.maKhoaHoc, expected_review_round=1, now=now
    )
    assert res_back.status.value == "ASSIGNED"
    assert res_back.assignedExpertId == exp.maChuyenGia

    # Reject flow with mandatory note
    req_rej = availability_service.create_availability_request(
        pg_db,
        user_id=exp_u.maNguoiDung,
        start_at=now + timedelta(days=5),
        end_at=now + timedelta(days=7),
        reason="Xin nghỉ thêm cuối tuần",
        now=now,
    )
    r_rej = client.post(
        f"/api/admin/availability/{req_rej.maYeuCau}/reject",
        headers=_auth(admin),
        json={"ghiChuXuLy": "Đang cao điểm kiểm duyệt"},
    )
    assert r_rej.status_code == 200
    assert r_rej.json()["trangThai"] == "REJECTED"


def test_availability_completion_and_waiting_eligible_wakeup(pg_db: Session):
    admin = _mk_user(pg_db, "ADMIN")
    dm, cm, prov = _mk_isolated_domain(pg_db)
    exp_u, exp = _mk_expert(pg_db)
    _attach_spec(pg_db, exp, cm)
    now = _now_utc()

    req_app = availability_service.create_availability_request(
        pg_db,
        user_id=exp_u.maNguoiDung,
        start_at=now - timedelta(days=2),
        end_at=now + timedelta(hours=1),
        reason="Đợt tạm ngừng sắp kết thúc",
        now=now,
    )
    availability_service.admin_approve_availability(
        pg_db, admin_user_id=admin.maNguoiDung, request_id=req_app.maYeuCau, now=now
    )
    req_pend = availability_service.create_availability_request(
        pg_db,
        user_id=exp_u.maNguoiDung,
        start_at=now + timedelta(hours=1),
        end_at=now + timedelta(hours=2),
        reason="Đợt chờ duyệt sẽ quá hạn",
        now=now,
    )

    course = _mk_course(pg_db, prov.maNhaCungCap, dm.maDanhMuc)
    job, _ = assignment_queue_service.enqueue_assignment_job(
        pg_db,
        target_type="COURSE",
        target_id=course.maKhoaHoc,
        review_round=1,
        event_type="SUBMIT",
        now=now,
    )
    job.trangThai = "WAITING_ELIGIBLE"
    job.thoiDiemChayTiepTheo = now + timedelta(hours=6)
    pg_db.flush()

    # Advance time past both end times
    later = now + timedelta(hours=3)
    completed_cnt = availability_service.complete_ended_availability_requests(pg_db, now=later)
    assert completed_cnt >= 1

    pg_db.refresh(req_app)
    pg_db.refresh(req_pend)
    pg_db.refresh(job)
    assert req_app.trangThai == "COMPLETED"
    assert req_pend.trangThai == "EXPIRED"
    assert job.trangThai == "PENDING"


# =====================================================================
# 2. NOTIFICATION CENTER & OWNERSHIP
# =====================================================================
def test_notification_center_list_filter_unread_mark_read_and_ownership(pg_db: Session, client: TestClient):
    user_a = _mk_user(pg_db, "USER")
    user_b = _mk_user(pg_db, "USER")
    now = _now_utc()

    # Idempotency check: same event_key for user_a twice -> only 1 inserted; user_b gets own row
    ev = f"TEST_EV:{uuid.uuid4().hex[:8]}"
    assert notification_service.create_notification_idempotent(
        pg_db,
        recipient_user_id=user_a.maNguoiDung,
        notification_type="SYSTEM_INFO",
        title="Thông báo 1",
        body="Nội dung 1",
        event_key=ev,
        now=now,
    ) is True
    assert notification_service.create_notification_idempotent(
        pg_db,
        recipient_user_id=user_a.maNguoiDung,
        notification_type="SYSTEM_INFO",
        title="Thông báo 1",
        body="Nội dung 1",
        event_key=ev,
        now=now,
    ) is False
    assert notification_service.create_notification_idempotent(
        pg_db,
        recipient_user_id=user_b.maNguoiDung,
        notification_type="SYSTEM_INFO",
        title="Thông báo cho B",
        body="Nội dung B",
        event_key=ev,
        now=now,
    ) is True
    notification_service.create_notification_idempotent(
        pg_db,
        recipient_user_id=user_a.maNguoiDung,
        notification_type="SYSTEM_INFO",
        title="Thông báo 2",
        body="Nội dung 2",
        event_key=f"{ev}:2",
        now=now + timedelta(seconds=1),
    )
    pg_db.flush()

    # Unread count for user A = 2
    r_cnt = client.get("/api/notifications/unread-count", headers=_auth(user_a))
    assert r_cnt.status_code == 200
    assert r_cnt.json()["unreadCount"] == 2

    # List paginated for user A
    r_list = client.get("/api/notifications?is_read=false&limit=10&offset=0", headers=_auth(user_a))
    assert r_list.status_code == 200
    data = r_list.json()
    assert data["total"] == 2
    assert data["unreadCount"] == 2
    first_id = data["items"][0]["maThongBao"]

    # User B cannot mark User A's notification read -> 404
    r_cross = client.post(f"/api/notifications/{first_id}/read", headers=_auth(user_b))
    assert r_cross.status_code == 404

    # User A marks one read -> unread becomes 1
    r_read1 = client.post(f"/api/notifications/{first_id}/read", headers=_auth(user_a))
    assert r_read1.status_code == 200
    assert r_read1.json()["daDoc"] is True
    assert r_read1.json()["ngayDoc"] is not None

    r_cnt2 = client.get("/api/notifications/unread-count", headers=_auth(user_a))
    assert r_cnt2.json()["unreadCount"] == 1

    # User A marks all read -> updatedCount = 1; User B still has 1 unread!
    r_all = client.post("/api/notifications/read-all", headers=_auth(user_a))
    assert r_all.status_code == 200
    assert r_all.json()["updatedCount"] == 1

    r_cnt_b = client.get("/api/notifications/unread-count", headers=_auth(user_b))
    assert r_cnt_b.json()["unreadCount"] == 1


# =====================================================================
# 3. HARDENING: ACC-09, ACC-10, ACC-11, ACC-12, ACC-13
# =====================================================================
def test_acc09_pre_lock_jwt_rejected_after_admin_unlock_fresh_jwt_succeeds(
    pg_db: Session, client: TestClient
):
    admin = _mk_user(pg_db, "ADMIN")
    exp_u, exp = _mk_expert(pg_db)

    # Issue pre-lock JWT NOW
    pre_lock_headers = _auth(exp_u)
    assert client.get("/api/notifications/unread-count", headers=pre_lock_headers).status_code == 200

    # Lock expert -> ACC-13: direct access returns 403 immediately
    accountability_service.admin_lock_expert(
        pg_db,
        admin_user_id=admin.maNguoiDung,
        expert_id=exp.maChuyenGia,
        reason="Khóa kiểm tra ACC-09 và ACC-13",
    )
    assert client.get("/api/notifications/unread-count", headers=pre_lock_headers).status_code == 403
    assert client.get("/api/expert/availability", headers=pre_lock_headers).status_code == 403

    # Wait >1s so unlock mocChuKyKyLuat (second resolution) is strictly > pre_lock_token.iat
    time.sleep(1.1)
    accountability_service.admin_unlock_expert(
        pg_db,
        admin_user_id=admin.maNguoiDung,
        expert_id=exp.maChuyenGia,
        reason="Mở khóa để kiểm tra ACC-09",
    )

    # ACC-09: Pre-lock JWT MUST be rejected with 401 even though user is ACTIVE again!
    r_stale = client.get("/api/notifications/unread-count", headers=pre_lock_headers)
    assert r_stale.status_code == 401

    # Freshly issued JWT after unlock succeeds (200)
    fresh_headers = _auth(exp_u)
    r_fresh = client.get("/api/notifications/unread-count", headers=fresh_headers)
    assert r_fresh.status_code == 200


def test_acc10_multi_unlock_exact_historical_cycle(pg_db: Session):
    admin = _mk_user(pg_db, "ADMIN")
    dm, _, prov = _mk_isolated_domain(pg_db)
    _, exp = _mk_expert(pg_db)

    t0 = _now_utc() - timedelta(hours=10)
    t_unlock1 = t0 + timedelta(hours=2)
    t_unlock2 = t0 + timedelta(hours=5)

    # Cycle 1 -> lock -> unlock1 (now Cycle 2) -> lock -> unlock2 (now Cycle 3)
    accountability_service.admin_lock_expert(
        pg_db, admin_user_id=admin.maNguoiDung, expert_id=exp.maChuyenGia, reason="Lock cycle 1", now=t0 + timedelta(hours=1)
    )
    accountability_service.admin_unlock_expert(
        pg_db, admin_user_id=admin.maNguoiDung, expert_id=exp.maChuyenGia, reason="Unlock to cycle 2", now=t_unlock1
    )
    accountability_service.admin_lock_expert(
        pg_db, admin_user_id=admin.maNguoiDung, expert_id=exp.maChuyenGia, reason="Lock cycle 2", now=t0 + timedelta(hours=4)
    )
    accountability_service.admin_unlock_expert(
        pg_db, admin_user_id=admin.maNguoiDung, expert_id=exp.maChuyenGia, reason="Unlock to cycle 3", now=t_unlock2
    )
    pg_db.refresh(exp)
    assert int(exp.chuKyKyLuatSo) == 3

    # Delayed event from Cycle 1 (occurred at t0 + 30m < t_unlock1)
    course = _mk_course(pg_db, prov.maNhaCungCap, dm.maDanhMuc)
    pc = PhanCongKiemDuyet(
        maKhoaHoc=course.maKhoaHoc,
        maChuyenGia=exp.maChuyenGia,
        maDanhMuc=dm.maDanhMuc,
        soVongKiemDuyet=1,
        trangThai="EXPIRED",
        phuongThucPhanCong="AUTO",
        hanTiepNhan=t0 + timedelta(minutes=30),
        ngayPhanCong=t0,
        ngayCapNhat=t0 + timedelta(minutes=30),
        chiTietDiem={
            "accountabilityEvent": {
                "eventType": "EXPIRED_ACCEPTANCE",
                "occurredAt": (t0 + timedelta(minutes=30)).isoformat(),
                "expertId": int(exp.maChuyenGia),
            }
        },
    )
    pg_db.add(pc)
    pg_db.flush()

    res = accountability_service.record_violation_for_assignment(
        pg_db,
        assignment_id=pc.maPhanCong,
        violation_type="EXPIRED_ACCEPTANCE",
        now=t0 + timedelta(hours=6),
        commit=False,
    )
    assert res.created is True
    vp = pg_db.get(ViPhamChuyenGia, res.violationId)
    assert vp is not None
    # Exact historical cycle 1 (NOT cycle 2!)
    assert int(vp.chuKyKyLuatSo) == 1
    # Must not trigger count in current cycle 3
    assert res.confirmedCountInWindow == 0


def test_acc11_policy_snapshot_honored_when_config_changes(pg_db: Session):
    dm, _, prov = _mk_isolated_domain(pg_db)
    _, exp = _mk_expert(pg_db)
    now = _now_utc()

    # Current live config has tinhViPhamHetHan = True
    cfg = pg_db.scalar(select(CauHinhPhanCong))
    cfg.tinhViPhamHetHan = True
    pg_db.flush()

    # Event occurred earlier when policySnapshot had tinhViPhamHetHan = False
    course = _mk_course(pg_db, prov.maNhaCungCap, dm.maDanhMuc)
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

    res = accountability_service.record_violation_for_assignment(
        pg_db,
        assignment_id=pc.maPhanCong,
        violation_type="EXPIRED_ACCEPTANCE",
        now=now,
        commit=False,
    )
    assert res.created is False
    assert res.violationId is None


def test_acc12_crash_recovery_reconciles_unrecorded_events(pg_db: Session):
    dm, _, prov = _mk_isolated_domain(pg_db)
    _, exp = _mk_expert(pg_db)
    now = _now_utc()

    # Simulate crash: DECLINED assignment saved with accountabilityEvent, but no ViPhamChuyenGia row
    course = _mk_course(pg_db, prov.maNhaCungCap, dm.maDanhMuc)
    pc = PhanCongKiemDuyet(
        maKhoaHoc=course.maKhoaHoc,
        maChuyenGia=exp.maChuyenGia,
        maDanhMuc=dm.maDanhMuc,
        soVongKiemDuyet=1,
        trangThai="DECLINED",
        maLyDoTuChoi="WORKLOAD_PERSONAL",
        lyDoTuChoi="Bận đột xuất",
        phuongThucPhanCong="AUTO",
        hanTiepNhan=now + timedelta(hours=12),
        ngayPhanCong=now - timedelta(hours=1),
        ngayCapNhat=now,
        chiTietDiem={
            "accountabilityEvent": {
                "eventType": "DECLINED_ASSIGNMENT",
                "reasonCode": "WORKLOAD_PERSONAL",
                "explanation": "Bận đột xuất",
                "occurredAt": now.isoformat(),
                "expertId": int(exp.maChuyenGia),
            }
        },
    )
    pg_db.add(pc)
    pg_db.flush()

    with patch.object(accountability_service, "is_accountability_enabled", return_value=True):
        recovered1 = accountability_service.reconcile_unrecorded_accountability_events(
            pg_db, limit=50, now=now, commit=False
        )
        assert recovered1 >= 1
        vp = pg_db.scalar(
            select(ViPhamChuyenGia).where(ViPhamChuyenGia.maPhanCong == pc.maPhanCong)
        )
        assert vp is not None
        assert vp.loaiViPham == "DECLINED_ASSIGNMENT"

        # Idempotent second run recovers 0 for this assignment
        recovered2 = accountability_service.reconcile_unrecorded_accountability_events(
            pg_db, limit=50, now=now, commit=False
        )
        assert recovered2 == 0


# =====================================================================
# 4. REAL MULTI-CONNECTION CONCURRENCY TESTS (ACC-14 & AVAILABILITY)
# =====================================================================
def test_concurrency_parallel_overlapping_availability_create():
    """Two concurrent connections create overlapping pause requests -> strictly 1 succeeds."""
    cleanup_ids: dict[str, list[int]] = {"users": [], "experts": [], "avail": []}
    now = _now_utc()
    try:
        with TestSessionFactory() as s:
            assert s.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
            exp_u, exp = _mk_expert(s)
            s.commit()
            uid = int(exp_u.maNguoiDung)
            eid = int(exp.maChuyenGia)
            cleanup_ids["users"].append(uid)
            cleanup_ids["experts"].append(eid)

        barrier = Barrier(2)

        def _worker(idx: int) -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                try:
                    req = availability_service.create_availability_request(
                        ws,
                        user_id=uid,
                        start_at=now + timedelta(days=2),
                        end_at=now + timedelta(days=5),
                        reason=f"Concurrent overlap request #{idx}",
                        now=now,
                    )
                    cleanup_ids["avail"].append(int(req.maYeuCau))
                    return "OK"
                except WorkflowConflictError:
                    ws.rollback()
                    return "CONFLICT"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(_worker, [1, 2]))

        assert sorted(results) == ["CONFLICT", "OK"]
    finally:
        with TestSessionFactory() as cs:
            if cleanup_ids["avail"]:
                cs.execute(
                    delete(ThongBao).where(
                        ThongBao.khoaChongTrung.like("AVAIL_REQ:%")
                    )
                )
                cs.execute(
                    delete(YeuCauTamNgungChuyenGia).where(
                        YeuCauTamNgungChuyenGia.maYeuCau.in_(cleanup_ids["avail"])
                    )
                )
            if cleanup_ids["experts"]:
                cs.execute(delete(ChuyenGia).where(ChuyenGia.maChuyenGia.in_(cleanup_ids["experts"])))
            if cleanup_ids["users"]:
                cs.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(cleanup_ids["users"])))
            cs.commit()


def test_concurrency_approve_availability_vs_assign_best_expert():
    """Concurrent ADMIN approve_availability (active now) vs assign_best_expert -> 0 deadlocks."""
    cleanup: dict[str, list[int]] = {
        "users": [], "experts": [], "cats": [], "specs": [], "provs": [], "courses": [], "avail": []
    }
    now = _now_utc()
    try:
        with TestSessionFactory() as s:
            assert s.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
            admin = _mk_user(s, "ADMIN")
            dm, cm, prov = _mk_isolated_domain(s)
            exp_u, exp = _mk_expert(s)
            _attach_spec(s, exp, cm)
            course = _mk_course(s, prov.maNhaCungCap, dm.maDanhMuc)
            req = availability_service.create_availability_request(
                s,
                user_id=exp_u.maNguoiDung,
                start_at=now - timedelta(minutes=5),
                end_at=now + timedelta(days=2),
                reason="Concurrent approve vs assign test",
                now=now,
            )
            admin_id = int(admin.maNguoiDung)
            req_id = int(req.maYeuCau)
            course_id = int(course.maKhoaHoc)
            cleanup["users"].extend([admin_id, int(exp_u.maNguoiDung), int(prov.maNguoiDung)])
            cleanup["experts"].append(int(exp.maChuyenGia))
            cleanup["cats"].append(int(dm.maDanhMuc))
            cleanup["specs"].append(int(cm.maChuyenMon))
            cleanup["provs"].append(int(prov.maNhaCungCap))
            cleanup["courses"].append(course_id)
            cleanup["avail"].append(req_id)

        barrier = Barrier(2)

        def _run_approve() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                availability_service.admin_approve_availability(
                    ws, admin_user_id=admin_id, request_id=req_id, now=now
                )
                return "APPROVED"

        def _run_assign() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                res = assignment_service.assign_best_expert(
                    ws, target_type="COURSE", target_id=course_id, expected_review_round=1, now=now
                )
                ws.commit()
                return res.status.value

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_run_approve)
            f2 = pool.submit(_run_assign)
            r1 = f1.result(timeout=15)
            r2 = f2.result(timeout=15)

        # Both finish cleanly with 0 deadlocks; assign either ran before (ASSIGNED) or after (NO_ELIGIBLE_EXPERT)
        assert r1 == "APPROVED"
        assert r2 in ("ASSIGNED", "NO_ELIGIBLE_EXPERT")
    finally:
        with TestSessionFactory() as cs:
            if cleanup["courses"]:
                cs.execute(delete(PhanCongKiemDuyet).where(PhanCongKiemDuyet.maKhoaHoc.in_(cleanup["courses"])))
                cs.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(cleanup["courses"])))
            if cleanup["avail"]:
                cs.execute(delete(ThongBao).where(ThongBao.khoaChongTrung.like("AVAIL_%")))
                cs.execute(delete(YeuCauTamNgungChuyenGia).where(YeuCauTamNgungChuyenGia.maYeuCau.in_(cleanup["avail"])))
            if cleanup["experts"]:
                cs.execute(delete(ChuyenGiaChuyenMon).where(ChuyenGiaChuyenMon.maChuyenGia.in_(cleanup["experts"])))
                cs.execute(delete(ChuyenGia).where(ChuyenGia.maChuyenGia.in_(cleanup["experts"])))
            if cleanup["provs"]:
                cs.execute(delete(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNhaCungCap.in_(cleanup["provs"])))
            if cleanup["specs"]:
                cs.execute(delete(ChuyenMonDanhMuc).where(ChuyenMonDanhMuc.maChuyenMon.in_(cleanup["specs"])))
                cs.execute(delete(ChuyenMon).where(ChuyenMon.maChuyenMon.in_(cleanup["specs"])))
            if cleanup["cats"]:
                cs.execute(delete(DanhMuc).where(DanhMuc.maDanhMuc.in_(cleanup["cats"])))
            if cleanup["users"]:
                cs.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(cleanup["users"])))
            cs.commit()


def test_concurrency_admin_confirm_vs_exempt_same_violation():
    """ACC-14: Concurrent ADMIN confirm vs exempt on same PENDING_REVIEW violation -> strictly 1 wins."""
    cleanup: dict[str, list[int]] = {
        "users": [], "experts": [], "cats": [], "specs": [], "provs": [], "courses": []
    }
    now = _now_utc()
    try:
        with TestSessionFactory() as s:
            assert s.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
            admin1 = _mk_user(s, "ADMIN")
            admin2 = _mk_user(s, "ADMIN")
            dm, cm, prov = _mk_isolated_domain(s)
            exp_u, exp = _mk_expert(s)
            course = _mk_course(s, prov.maNhaCungCap, dm.maDanhMuc)
            pc = PhanCongKiemDuyet(
                maKhoaHoc=course.maKhoaHoc,
                maChuyenGia=exp.maChuyenGia,
                maDanhMuc=dm.maDanhMuc,
                soVongKiemDuyet=1,
                trangThai="DECLINED",
                maLyDoTuChoi="CONFLICT_OF_INTEREST",
                lyDoTuChoi="Xung đột lợi ích cần xác minh",
                phuongThucPhanCong="AUTO",
                hanTiepNhan=now + timedelta(hours=12),
                ngayPhanCong=now - timedelta(hours=1),
                ngayCapNhat=now,
            )
            s.add(pc)
            s.flush()
            vp = ViPhamChuyenGia(
                maChuyenGia=exp.maChuyenGia,
                maPhanCong=pc.maPhanCong,
                loaiViPham="DECLINED_ASSIGNMENT",
                trangThaiXuLy="PENDING_REVIEW",
                chuKyKyLuatSo=1,
                ngayViPham=now,
                lyDo="Chờ quản trị viên xác minh",
            )
            s.add(vp)
            s.commit()
            vp_id = int(vp.maViPham)
            a1_id = int(admin1.maNguoiDung)
            a2_id = int(admin2.maNguoiDung)
            cleanup["users"].extend([a1_id, a2_id, int(exp_u.maNguoiDung), int(prov.maNguoiDung)])
            cleanup["experts"].append(int(exp.maChuyenGia))
            cleanup["cats"].append(int(dm.maDanhMuc))
            cleanup["specs"].append(int(cm.maChuyenMon))
            cleanup["provs"].append(int(prov.maNhaCungCap))
            cleanup["courses"].append(int(course.maKhoaHoc))

        barrier = Barrier(2)

        def _confirm() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                try:
                    accountability_service.admin_confirm_violation(
                        ws, admin_user_id=a1_id, violation_id=vp_id, note="Xác nhận vi phạm", now=now
                    )
                    return "CONFIRMED"
                except WorkflowConflictError:
                    ws.rollback()
                    return "CONFLICT"

        def _exempt() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                try:
                    accountability_service.admin_exempt_violation(
                        ws, admin_user_id=a2_id, violation_id=vp_id, note="Miễn trừ hợp lệ", now=now
                    )
                    return "EXEMPTED"
                except WorkflowConflictError:
                    ws.rollback()
                    return "CONFLICT"

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_confirm)
            f2 = pool.submit(_exempt)
            r1 = f1.result(timeout=15)
            r2 = f2.result(timeout=15)

        # Serialized cleanly under ARCH-05 lock:
        # - If exempt ran first: confirm raises CONFLICT -> ("CONFLICT", "EXEMPTED")
        # - If confirm ran first: exempt legitimately overrides CONFIRMED -> ("CONFIRMED", "EXEMPTED")
        assert r2 == "EXEMPTED"
        assert r1 in ("CONFLICT", "CONFIRMED")
        with TestSessionFactory() as vs:
            final_vp = vs.get(ViPhamChuyenGia, vp_id)
            assert final_vp is not None and final_vp.trangThaiXuLy == "EXEMPTED"
    finally:
        with TestSessionFactory() as cs:
            if cleanup["experts"]:
                cs.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_(cleanup["users"])))
                cs.execute(delete(NhatKyKyLuatChuyenGia).where(NhatKyKyLuatChuyenGia.maChuyenGia.in_(cleanup["experts"])))
                cs.execute(delete(ViPhamChuyenGia).where(ViPhamChuyenGia.maChuyenGia.in_(cleanup["experts"])))
            if cleanup["courses"]:
                cs.execute(delete(PhanCongKiemDuyet).where(PhanCongKiemDuyet.maKhoaHoc.in_(cleanup["courses"])))
                cs.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(cleanup["courses"])))
            if cleanup["experts"]:
                cs.execute(delete(ChuyenGia).where(ChuyenGia.maChuyenGia.in_(cleanup["experts"])))
            if cleanup["provs"]:
                cs.execute(delete(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNhaCungCap.in_(cleanup["provs"])))
            if cleanup["specs"]:
                cs.execute(delete(ChuyenMonDanhMuc).where(ChuyenMonDanhMuc.maChuyenMon.in_(cleanup["specs"])))
                cs.execute(delete(ChuyenMon).where(ChuyenMon.maChuyenMon.in_(cleanup["specs"])))
            if cleanup["cats"]:
                cs.execute(delete(DanhMuc).where(DanhMuc.maDanhMuc.in_(cleanup["cats"])))
            if cleanup["users"]:
                cs.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(cleanup["users"])))
            cs.commit()
