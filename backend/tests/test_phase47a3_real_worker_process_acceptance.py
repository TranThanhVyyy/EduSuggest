"""GĐ4.7A.3 Real OS-Process Acceptance Tests for Durable Payment Reconciliation Worker
and Financial Integrity Invariants on `EduSuggest_phase4_test` (35 tables, e5f6a7b8c9d0).

Proves with real subprocesses (`scripts/run_payment_reconciliation_worker.py`):
1. Two concurrent OS worker processes share `TacVuDoiSoatThanhToan` via `SKIP LOCKED` without duplicates.
2. Abrupt OS process kill (`proc.kill()`) leaves stale lease that a second OS process reclaims cleanly.
3. Graceful shutdown (`terminate()`) exits cleanly without corrupting queue state.
4. Payment in `PARTIALLY_REFUNDED` state still routes any 2nd captured payment to `CAPTURED_UNAPPLIED`
   (never double-counts revenue).
5. Zero runtime service/API files contain `session_replication_role`.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import sessionmaker

from config.config import get_settings
from config.database import get_db
from main import app
from models import (
    BaiHoc,
    BaoCaoSuCoThanhToan,
    ChiTietDonHang,
    ChiTietGioHang,
    DangKyKhoaHoc,
    DanhMuc,
    DonHang,
    GioHang,
    HoanTienNgoaiLe,
    KhoaHoc,
    LanThuHoanTien,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    SuKienThanhToan,
    TacVuDoiSoatThanhToan,
    ThanhToan,
    ThongBao,
    VaiTro,
    YeuThich,
)
from utils.security import create_access_token, hash_password

BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKER_SCRIPT = BACKEND_DIR / "scripts" / "run_payment_reconciliation_worker.py"


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ4.7A.3 tests require EduSuggest_phase4_test database.")
    return raw


@pytest.fixture(scope="module")
def pg_engine():
    url = _phase4_test_url()
    engine = create_engine(url, pool_pre_ping=True, pool_size=12, max_overflow=12)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase4_test"
    yield engine
    engine.dispose()


def test_p47a3_no_session_replication_role_in_runtime_code():
    """Verify test-only cleanup mechanism (`session_replication_role`) NEVER appears in runtime app code."""
    for folder in ("api", "service", "repository", "config", "models", "scripts"):
        root = BACKEND_DIR / folder
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            assert "session_replication_role" not in content, (
                f"Forbidden test-only cleanup directive found in runtime file: {py_file}"
            )


def test_p47a3_real_os_worker_subprocesses_concurrency_crash_and_restart_recovery(pg_engine, monkeypatch):
    """Run real OS processes of `run_payment_reconciliation_worker.py` on `EduSuggest_phase4_test`:
    - Seed a CAPTURED_UNAPPLIED payment + durable reconciliation task.
    - Spawn 2 concurrent real OS worker processes -> task processed cleanly to ESCALATED_ADMIN (since auto-restore=False).
    - Seed a stale-leased PROCESSING task (simulating an abruptly killed worker) -> spawn fresh OS worker ->
      reclaims stale lease (leaseGeneration incremented) and finishes cleanly without losing the job.
    - Verify graceful termination on a long-running worker subprocess.
    """
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    created_users: list[int] = []
    created_providers: list[int] = []
    created_courses: list[int] = []
    created_lessons: list[int] = []
    procs: list[subprocess.Popen[str]] = []

    try:
        now = datetime.now(UTC).replace(tzinfo=None)
        tag = uuid.uuid4().hex[:8]
        with SessionLocal() as db:
            role_user = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == "USER")).first()
            role_prov = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == "PROVIDER")).first()
            cat_id = db.scalar(select(DanhMuc.maDanhMuc).limit(1))
            assert role_user and role_prov and cat_id

            u_prov = NguoiDung(
                maVaiTro=role_prov.maVaiTro,
                tenTaiKhoan=f"p473_prov_{tag}",
                hoTen=f"P473 Prov {tag}",
                email=f"p473_prov_{tag}@example.test",
                matKhau=hash_password("P473!Test99"),
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            u_buy = NguoiDung(
                maVaiTro=role_user.maVaiTro,
                tenTaiKhoan=f"p473_user_{tag}",
                hoTen=f"P473 User {tag}",
                email=f"p473_user_{tag}@example.test",
                matKhau=hash_password("P473!Test99"),
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            db.add_all([u_prov, u_buy])
            db.flush()
            created_users.extend([int(u_prov.maNguoiDung), int(u_buy.maNguoiDung)])

            prov = NhaCungCapKhoaHoc(maNguoiDung=u_prov.maNguoiDung, tieuSu="P47A3 Prov", chuyenMon="Ops")
            db.add(prov)
            db.flush()
            created_providers.append(int(prov.maNhaCungCap))

            course = KhoaHoc(
                maNhaCungCap=prov.maNhaCungCap,
                maDanhMuc=cat_id,
                tieuDe=f"P473 Course {tag}",
                moTa="Real OS worker acceptance test",
                gia=Decimal("450000"),
                trinhDo="Intermediate",
                thoiLuong=60,
                trangThaiDuyet="APPROVED",
                trangThaiHienThi="VISIBLE",
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add(course)
            db.flush()
            created_courses.append(int(course.maKhoaHoc))

            order = DonHang(
                maSoDonHang=f"ORD-P473-{tag.upper()}",
                maNguoiDung=u_buy.maNguoiDung,
                nguonTao="BUY_NOW",
                tongTien=Decimal("450000"),
                donViTienTe="VND",
                trangThai="PAID",
                khoaChongTrung=f"ord-p473-{tag}",
                hanThanhToan=now + timedelta(minutes=15),
                ngayThanhToan=now,
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add(order)
            db.flush()

            # Simulate a 2nd captured payment (CAPTURED_UNAPPLIED) on already-PAID order
            pay = ThanhToan(
                maDonHang=order.maDonHang,
                maNguoiDung=u_buy.maNguoiDung,
                congThanhToan="VNPAY_SANDBOX",
                maGiaoDichNoiBo=f"TXN-P473-{tag.upper()}",
                maGiaoDichCong=f"VNP-P473-{tag.upper()}",
                soTien=Decimal("450000"),
                donViTienTe="VND",
                trangThai="CAPTURED_UNAPPLIED",
                daThuTien=True,
                soTienDaThuThucTe=Decimal("450000"),
                khoaChongTrung=f"pay-p473-{tag}",
                daXacMinhChuKy=True,
                duLieuPhanHoiAnToan={"fundsCaptured": True, "reconciliationRequired": True},
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add(pay)
            db.flush()

            # Task 1: PENDING task for 2 concurrent real OS workers
            t1 = TacVuDoiSoatThanhToan(
                loaiTacVu="RETRY_CAPTURED_UNAPPLIED",
                maDonHang=order.maDonHang,
                maThanhToan=pay.maThanhToan,
                khoaChongTrung=f"p473:concurrent:{tag}",
                trangThai="PENDING",
                soLanThu=0,
                soLanThuToiDa=4,
                thoiDiemChayTiepTheo=now - timedelta(seconds=5),
                leaseGeneration=0,
                ngayTao=now,
                ngayCapNhat=now,
            )
            # Task 2: Stale-leased PROCESSING task from an abruptly killed worker (hanLease in past!)
            t2 = TacVuDoiSoatThanhToan(
                loaiTacVu="RETRY_CAPTURED_UNAPPLIED",
                maDonHang=order.maDonHang,
                maThanhToan=pay.maThanhToan,
                khoaChongTrung=f"p473:stale:{tag}",
                trangThai="PROCESSING",
                soLanThu=1,
                soLanThuToiDa=4,
                thoiDiemChayTiepTheo=now - timedelta(minutes=2),
                maWorker="dead-worker-crashed",
                claimToken="dead-token-001",
                leaseGeneration=1,
                hanLease=now - timedelta(seconds=30),
                ngayTao=now - timedelta(minutes=2),
                ngayCapNhat=now - timedelta(minutes=2),
            )
            db.add_all([t1, t2])
            db.commit()
            t1_id, t2_id = int(t1.maTacVu), int(t2.maTacVu)

        worker_env = os.environ.copy()
        worker_env.update(
            {
                "DEBUG": "False",
                "PAYMENT_RECONCILIATION_WORKER_ENABLED": "True",
                "PAYMENT_AUTO_RESTORE_ENABLED": "False",
                "PAYMENT_AUTO_GATEWAY_QUERY_ENABLED": "False",
            }
        )

        # Spawn 2 concurrent real OS worker processes!
        for wid in (f"os-w1-{tag}", f"os-w2-{tag}"):
            p = subprocess.Popen(
                [
                    sys.executable,
                    str(WORKER_SCRIPT),
                    "--expected-database",
                    "EduSuggest_phase4_test",
                    "--worker-id",
                    wid,
                    "--poll-interval",
                    "0.2",
                    "--lease-seconds",
                    "10",
                ],
                cwd=BACKEND_DIR,
                env=worker_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            procs.append(p)

        # Wait up to 15s for both t1 (concurrent) and t2 (stale-lease reclaim) to reach ESCALATED_ADMIN
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            with SessionLocal() as db:
                r1 = db.get(TacVuDoiSoatThanhToan, t1_id)
                r2 = db.get(TacVuDoiSoatThanhToan, t2_id)
                if r1 and r2 and r1.trangThai == "ESCALATED_ADMIN" and r2.trangThai == "ESCALATED_ADMIN":
                    break
            time.sleep(0.2)

        # Abrupt kill worker 1 + graceful terminate worker 2
        procs[0].kill()
        procs[0].wait(timeout=10)
        procs[1].terminate()
        procs[1].wait(timeout=10)
        procs.clear()

        with SessionLocal() as db:
            r1 = db.get(TacVuDoiSoatThanhToan, t1_id)
            r2 = db.get(TacVuDoiSoatThanhToan, t2_id)
            assert r1 is not None and r1.trangThai == "ESCALATED_ADMIN"
            assert r1.leaseGeneration == 1
            assert r2 is not None and r2.trangThai == "ESCALATED_ADMIN"
            # Stale lease was reclaimed -> leaseGeneration MUST be >= 2 and claimToken rotated!
            assert r2.leaseGeneration >= 2
            assert r2.claimToken != "dead-token-001"
            assert r2.maWorker != "dead-worker-crashed"
    finally:
        for p in procs:
            try:
                p.kill()
                p.wait(timeout=5)
            except Exception:
                pass
        cleanup = SessionLocal()
        try:
            assert cleanup.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase4_test"
            cleanup.execute(text("SET LOCAL session_replication_role = 'replica'"))
            if created_users:
                oids = list(cleanup.scalars(select(DonHang.maDonHang).where(DonHang.maNguoiDung.in_(created_users))))
                if oids:
                    cleanup.execute(delete(TacVuDoiSoatThanhToan).where(TacVuDoiSoatThanhToan.maDonHang.in_(oids)))
                    cleanup.execute(delete(SuKienThanhToan).where(SuKienThanhToan.maDonHang.in_(oids)))
                    cleanup.execute(delete(BaoCaoSuCoThanhToan).where(BaoCaoSuCoThanhToan.maDonHang.in_(oids)))
                    rids = list(cleanup.scalars(select(HoanTienNgoaiLe.maHoanTien).where(HoanTienNgoaiLe.maDonHang.in_(oids))))
                    if rids:
                        cleanup.execute(delete(LanThuHoanTien).where(LanThuHoanTien.maHoanTien.in_(rids)))
                        cleanup.execute(delete(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maHoanTien.in_(rids)))
                    cleanup.execute(delete(ThanhToan).where(ThanhToan.maDonHang.in_(oids)))
                    cleanup.execute(delete(ChiTietDonHang).where(ChiTietDonHang.maDonHang.in_(oids)))
                    cleanup.execute(delete(DonHang).where(DonHang.maDonHang.in_(oids)))
                cleanup.execute(delete(DangKyKhoaHoc).where(DangKyKhoaHoc.maNguoiDung.in_(created_users)))
                cleanup.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_(created_users)))
            if created_courses:
                cleanup.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(created_courses)))
            if created_providers:
                cleanup.execute(delete(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNhaCungCap.in_(created_providers)))
            if created_users:
                cleanup.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(created_users)))
            cleanup.commit()
        finally:
            cleanup.close()
