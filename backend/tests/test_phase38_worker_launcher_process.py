"""Real Subprocess Integration Tests for Independent Worker Launcher (`run_assignment_worker.py`).

Tests the ACTUAL standalone Python process (NOT just calling run_once() in-process):
1. Refuses to start when AUTO_ASSIGNMENT_WORKER_ENABLED=False (exit code 2).
2. Aborts safely when --expected-db does not match SELECT current_database() (exit code 3).
3. Executes full real flow on EduSuggest_phase3_test:
   submit -> HangDoiPhanCong -> independent subprocess run_assignment_worker.py --once
   -> PhanCongKiemDuyet(ASSIGNED) + ThongBao(ASSIGNMENT_NEW) + HangDoiPhanCong(DONE).
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import Session

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
from service import assignment_queue_service

BACKEND_DIR = Path(__file__).resolve().parent.parent
LAUNCHER_SCRIPT = BACKEND_DIR / "run_assignment_worker.py"


def _get_test_db_url() -> str:
    load_dotenv(BACKEND_DIR / ".env")
    prod_url = os.getenv("DATABASE_URL") or ""
    p = urlparse(prod_url)
    assert p.path.lstrip("/") == "EduSuggest"
    return urlunparse(p._replace(path="/EduSuggest_phase3_test"))


def test_worker_launcher_refuses_when_flag_disabled():
    env = os.environ.copy()
    env["DATABASE_URL"] = _get_test_db_url()
    env["AUTO_ASSIGNMENT_WORKER_ENABLED"] = "false"
    proc = subprocess.run(
        [sys.executable, str(LAUNCHER_SCRIPT), "--once", "--expected-db", "EduSuggest_phase3_test"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 2
    assert "worker_refused_flag_disabled" in (proc.stdout + proc.stderr)


def test_worker_launcher_aborts_on_wrong_expected_db():
    env = os.environ.copy()
    env["DATABASE_URL"] = _get_test_db_url()
    env["AUTO_ASSIGNMENT_WORKFLOW_ENABLED"] = "true"
    env["AUTO_ASSIGNMENT_WORKER_ENABLED"] = "true"
    env["ACCOUNTABILITY_ENABLED"] = "true"
    proc = subprocess.run(
        [sys.executable, str(LAUNCHER_SCRIPT), "--once", "--expected-db", "SomeOtherDatabase"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 3
    assert "worker_db_guard_abort" in (proc.stdout + proc.stderr)


def test_worker_launcher_real_subprocess_e2e_on_test_db():
    """Real independent subprocess: submit -> queue -> worker process -> assignment + notification."""
    test_url = _get_test_db_url()
    engine = create_engine(test_url, pool_pre_ping=True)
    now = datetime.now(UTC).replace(tzinfo=None)
    tag = uuid.uuid4().hex[:8]
    ids: dict[str, int] = {}

    try:
        with Session(engine) as db:
            assert db.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
            roles = {r.tenVaiTro: r.maVaiTro for r in db.scalars(select(VaiTro)).all()}

            exp_u = NguoiDung(
                tenTaiKhoan=f"g38_wk_exp_{tag}",
                email=f"g38_wk_exp_{tag}@test.local",
                matKhau="$2b$12$dummyhashvalueforphase38worker000000000000000000",
                hoTen=f"G38 Worker Expert {tag}",
                maVaiTro=roles["EXPERT"],
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            prov_u = NguoiDung(
                tenTaiKhoan=f"g38_wk_prv_{tag}",
                email=f"g38_wk_prv_{tag}@test.local",
                matKhau="$2b$12$dummyhashvalueforphase38worker000000000000000000",
                hoTen=f"G38 Worker Prov {tag}",
                maVaiTro=roles["PROVIDER"],
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            db.add_all([exp_u, prov_u])
            db.flush()

            exp = ChuyenGia(maNguoiDung=exp_u.maNguoiDung, trangThaiHoSo="VERIFIED", soNamKinhNghiem=8)
            prov = NhaCungCapKhoaHoc(maNguoiDung=prov_u.maNguoiDung, tieuSu=f"G38 Org {tag}")
            dm = DanhMuc(tenDanhMuc=f"G38 WkCat {tag}")
            cm = ChuyenMon(tenChuyenMon=f"G38 WkSpec {tag}", nhomChuyenMon="G38_WK", trangThai="ACTIVE", ngayTao=now)
            db.add_all([exp, prov, dm, cm])
            db.flush()

            db.add(ChuyenMonDanhMuc(maChuyenMon=cm.maChuyenMon, maDanhMuc=dm.maDanhMuc, ngayTao=now))
            db.add(ChuyenGiaChuyenMon(maChuyenGia=exp.maChuyenGia, maChuyenMon=cm.maChuyenMon, laChuyenMonChinh=True, ngayTao=now))

            course = KhoaHoc(
                maNhaCungCap=prov.maNhaCungCap,
                maDanhMuc=dm.maDanhMuc,
                tieuDe=f"G38 Worker Course {tag}",
                gia=Decimal("0"),
                trangThaiDuyet="PENDING",
                trangThaiHienThi="HIDDEN",
                soVongKiemDuyetHienTai=1,
            )
            db.add(course)
            db.flush()

            job, _ = assignment_queue_service.enqueue_assignment_job(
                db,
                target_type="COURSE",
                target_id=course.maKhoaHoc,
                review_round=1,
                event_type="SUBMIT",
                now=now,
            )
            db.commit()

            ids = {
                "exp_uid": int(exp_u.maNguoiDung),
                "prov_uid": int(prov_u.maNguoiDung),
                "exp_id": int(exp.maChuyenGia),
                "prov_id": int(prov.maNhaCungCap),
                "dm_id": int(dm.maDanhMuc),
                "cm_id": int(cm.maChuyenMon),
                "course_id": int(course.maKhoaHoc),
                "job_id": int(job.maCongViec),
            }

        # Launch REAL independent worker subprocess!
        env = os.environ.copy()
        env["DATABASE_URL"] = test_url
        env["AUTO_ASSIGNMENT_WORKFLOW_ENABLED"] = "true"
        env["AUTO_ASSIGNMENT_WORKER_ENABLED"] = "true"
        env["ACCOUNTABILITY_ENABLED"] = "true"

        proc = subprocess.run(
            [
                sys.executable,
                str(LAUNCHER_SCRIPT),
                "--once",
                "--expected-db",
                "EduSuggest_phase3_test",
                "--allow-multiple",
            ],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"Worker failed: {proc.stdout}\n{proc.stderr}"
        assert "worker_tick_completed" in (proc.stdout + proc.stderr)

        with Session(engine) as verify_db:
            job_after = verify_db.get(HangDoiPhanCong, ids["job_id"])
            assert job_after is not None and job_after.trangThai == "DONE"

            pc = verify_db.scalar(
                select(PhanCongKiemDuyet).where(
                    PhanCongKiemDuyet.maKhoaHoc == ids["course_id"],
                    PhanCongKiemDuyet.trangThai == "ASSIGNED",
                )
            )
            assert pc is not None
            assert int(pc.maChuyenGia) == ids["exp_id"]

            notif = verify_db.scalar(
                select(ThongBao).where(
                    ThongBao.maNguoiNhan == ids["exp_uid"],
                    ThongBao.khoaChongTrung == f"ASSIGN_CREATED:{pc.maPhanCong}:TO:{ids['exp_uid']}",
                )
            )
            assert notif is not None
    finally:
        if ids:
            with Session(engine) as cs:
                cs.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_([ids["exp_uid"], ids["prov_uid"]])))
                cs.execute(delete(HangDoiPhanCong).where(HangDoiPhanCong.maKhoaHoc == ids["course_id"]))
                cs.execute(delete(PhanCongKiemDuyet).where(PhanCongKiemDuyet.maKhoaHoc == ids["course_id"]))
                cs.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc == ids["course_id"]))
                cs.execute(delete(ChuyenGiaChuyenMon).where(ChuyenGiaChuyenMon.maChuyenGia == ids["exp_id"]))
                cs.execute(delete(ChuyenGia).where(ChuyenGia.maChuyenGia == ids["exp_id"]))
                cs.execute(delete(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNhaCungCap == ids["prov_id"]))
                cs.execute(delete(ChuyenMonDanhMuc).where(ChuyenMonDanhMuc.maChuyenMon == ids["cm_id"]))
                cs.execute(delete(ChuyenMon).where(ChuyenMon.maChuyenMon == ids["cm_id"]))
                cs.execute(delete(DanhMuc).where(DanhMuc.maDanhMuc == ids["dm_id"]))
                cs.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_([ids["exp_uid"], ids["prov_uid"]])))
                cs.commit()
        engine.dispose()
