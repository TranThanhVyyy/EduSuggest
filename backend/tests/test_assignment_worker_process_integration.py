"""Real subprocess integration: provider submit -> durable queue -> workers -> assignment/notification.

All writes require an explicit current_database() guard for EduSuggest_phase3_test.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKER_SCRIPT = BACKEND_DIR / "scripts" / "run_assignment_worker.py"
load_dotenv(BACKEND_DIR / ".env")
_base_url = make_url(os.environ["DATABASE_URL"])
assert _base_url.database in ("EduSuggest", "EduSuggest_phase3_test")
_engine = create_engine(_base_url.set(database="EduSuggest_phase3_test"), pool_pre_ping=True)
with _engine.connect() as _conn:
    assert _conn.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase3_test"
_Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def _role_id(db: Session, name: str) -> int:
    return int(db.scalar(select(VaiTro.maVaiTro).where(VaiTro.tenVaiTro == name)))


def _wait_until(predicate, timeout: float, description: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {description}")


def _pid_file_for_worker(control_dir: Path, worker_id: str) -> tuple[Path, dict] | None:
    for pid_file in control_dir.glob("worker-*.pid"):
        try:
            metadata = json.loads(pid_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if metadata.get("worker_id") == worker_id:
            return pid_file, metadata
    return None


def test_provider_submit_is_processed_by_two_real_worker_processes(tmp_path: Path):
    # Imported after the database guard above to keep module initialization explicit.
    from api.dependencies import get_db
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
        ViPhamChuyenGia,
        NhatKyKyLuatChuyenGia,
    )
    from service import workflow_service
    from utils.security import create_access_token
    from unittest.mock import patch

    tag = uuid.uuid4().hex[:10]
    now = datetime.now(UTC).replace(tzinfo=None)
    ids: dict[str, int] = {}
    workers: list[subprocess.Popen[str]] = []
    worker_ids: dict[int, str] = {}
    worker_console_streams = []
    stop_dir = tmp_path / "control"
    log_dir = tmp_path / "logs"
    stop_dir.mkdir()
    log_dir.mkdir()

    with _Session() as db:
        assert db.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase3_test"
        provider_user = NguoiDung(
            tenTaiKhoan=f"g381_provider_{tag}", email=f"g381_provider_{tag}@test.invalid",
            matKhau="$2b$12$dummyhashvalueforworkerprocessg381000000000000000",
            maVaiTro=_role_id(db, "PROVIDER"), trangThai="ACTIVE", batBuocDoiMatKhau=False,
        )
        expert_user = NguoiDung(
            tenTaiKhoan=f"g381_expert_{tag}", email=f"g381_expert_{tag}@test.invalid",
            matKhau="$2b$12$dummyhashvalueforworkerprocessg381000000000000000",
            maVaiTro=_role_id(db, "EXPERT"), trangThai="ACTIVE", batBuocDoiMatKhau=False,
        )
        db.add_all([provider_user, expert_user])
        db.flush()
        provider = NhaCungCapKhoaHoc(maNguoiDung=provider_user.maNguoiDung, tieuSu="GĐ3.8.1 process test")
        expert = ChuyenGia(maNguoiDung=expert_user.maNguoiDung, trangThaiHoSo="VERIFIED", soNamKinhNghiem=8)
        category = DanhMuc(tenDanhMuc=f"G381 Category {tag}")
        specialty = ChuyenMon(
            tenChuyenMon=f"G381 Specialty {tag}", nhomChuyenMon="G381",
            trangThai="ACTIVE", ngayTao=now,
        )
        db.add_all([provider, expert, category, specialty])
        db.flush()
        db.add_all([
            ChuyenMonDanhMuc(maChuyenMon=specialty.maChuyenMon, maDanhMuc=category.maDanhMuc, ngayTao=now),
            ChuyenGiaChuyenMon(maChuyenGia=expert.maChuyenGia, maChuyenMon=specialty.maChuyenMon, laChuyenMonChinh=True, ngayTao=now),
        ])
        course = KhoaHoc(
            maNhaCungCap=provider.maNhaCungCap, maDanhMuc=category.maDanhMuc,
            tieuDe=f"G381 Worker Process Course {tag}", moTa="worker process integration",
            gia=Decimal("0"), trinhDo="BEGINNER", thoiLuong=30,
            trangThaiDuyet=None, trangThaiHienThi="HIDDEN",
            soVongKiemDuyetHienTai=0,
        )
        db.add(course)
        db.flush()
        lesson = BaiHoc(maKhoaHoc=course.maKhoaHoc, tieuDe="Lesson", noiDung="Private review content", thuTu=1)
        db.add(lesson)
        db.commit()
        ids = {
            "provider_user": int(provider_user.maNguoiDung),
            "expert_user": int(expert_user.maNguoiDung),
            "expert": int(expert.maChuyenGia),
            "category": int(category.maDanhMuc),
            "specialty": int(specialty.maChuyenMon),
            "course": int(course.maKhoaHoc),
            "lesson": int(lesson.maBaiHoc),
        }
        provider_password_hash = provider_user.matKhau

    def override_db():
        with _Session() as db:
            assert db.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase3_test"
            yield db

    app.dependency_overrides[get_db] = override_db
    token = create_access_token(ids["provider_user"], provider_password_hash).encoded
    api = TestClient(app)  # no context manager: do not run FastAPI lifespan against the production .env URL
    env = os.environ.copy()
    env.update({
        "DEBUG": "False",
        "AUTO_ASSIGNMENT_WORKFLOW_ENABLED": "True",
        "AUTO_ASSIGNMENT_WORKER_ENABLED": "True",
        "ACCOUNTABILITY_ENABLED": "True",
    })
    try:
        with patch.object(workflow_service, "_is_auto_assignment_workflow_enabled", return_value=True):
            response = api.post(
                f"/api/provider/courses/{ids['course']}/submit",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200, response.text
        with _Session() as db:
            assert db.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase3_test"
            job = db.scalar(select(HangDoiPhanCong).where(HangDoiPhanCong.maKhoaHoc == ids["course"]))
            assert job is not None and job.trangThai == "PENDING"
            assert job.khoaChongTrung == f"SUBMIT:COURSE:{ids['course']}:R1"

        # Two separate OS processes contend for one durable job; PostgreSQL claim/fencing is authoritative.
        for index in range(2):
            log_file = log_dir / f"worker-{index}.jsonl"
            console_file = (log_dir / f"worker-{index}.console.log").open("w", encoding="utf-8")
            worker_console_streams.append(console_file)
            worker_id = f"g381-{tag}-{index}"
            process = subprocess.Popen(
                [
                    sys.executable, str(WORKER_SCRIPT),
                    "--expected-database", "EduSuggest_phase3_test",
                    "--poll-interval", "0.2",
                    "--worker-id", worker_id,
                    "--log-file", str(log_file),
                    "--control-dir", str(stop_dir),
                ],
                cwd=BACKEND_DIR,
                env=env,
                stdout=console_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
            workers.append(process)
            worker_ids[id(process)] = worker_id

        ready_deadline = time.monotonic() + 10
        while time.monotonic() < ready_deadline and not all(
            _pid_file_for_worker(stop_dir, worker_ids[id(p)]) is not None for p in workers
        ):
            exited = [p for p in workers if p.poll() is not None]
            if exited:
                details = [
                    (p.pid, p.returncode, (log_dir / f"worker-{index}.console.log").read_text(encoding="utf-8"))
                    for index, p in enumerate(workers) if p in exited
                ]
                raise AssertionError(f"Worker process failed before ready: {details}")
            time.sleep(0.1)
        assert all(_pid_file_for_worker(stop_dir, worker_ids[id(p)]) is not None for p in workers), "worker startup timed out"

        _wait_until(
            lambda: _queue_status(ids["course"]) == "DONE",
            timeout=20,
            description="worker queue completion",
        )
        with _Session() as db:
            assignment_rows = list(db.scalars(
                select(PhanCongKiemDuyet).where(PhanCongKiemDuyet.maKhoaHoc == ids["course"])
            ).all())
            notification_rows = list(db.scalars(
                select(ThongBao).where(ThongBao.maNguoiNhan == ids["expert_user"])
            ).all())
            assert len(assignment_rows) == 1
            assert assignment_rows[0].maChuyenGia == ids["expert"]
            assert assignment_rows[0].trangThai == "ASSIGNED"
            assert len([n for n in notification_rows if n.duLieuLienKet and n.duLieuLienKet.get("maPhanCong") == assignment_rows[0].maPhanCong]) == 1

        # Graceful stop is marker based, so Windows processes are not force-killed.
        for process in workers:
            found = _pid_file_for_worker(stop_dir, worker_ids[id(process)])
            if found:
                _, metadata = found
                (stop_dir / f"worker-{metadata['pid']}.stop").write_text("stop", encoding="ascii")
        for process in workers:
            assert process.wait(timeout=10) == 0
        _wait_until(
            lambda: all(_pid_file_for_worker(stop_dir, worker_ids[id(p)]) is None for p in workers),
            timeout=5,
            description="two workers graceful exit",
        )
        workers.clear()
        worker_ids.clear()
        assert not list(stop_dir.glob("worker-*.pid"))

        # Restart a fresh worker against an empty queue, then stop it gracefully.
        restart_console = (log_dir / "restart.console.log").open("w", encoding="utf-8")
        worker_console_streams.append(restart_console)
        restart = subprocess.Popen(
            [sys.executable, str(WORKER_SCRIPT), "--expected-database", "EduSuggest_phase3_test",
             "--poll-interval", "0.2", "--worker-id", f"g381-{tag}-restart",
             "--log-file", str(log_dir / "restart.jsonl"), "--control-dir", str(stop_dir)],
            cwd=BACKEND_DIR, env=env, stdout=restart_console, stderr=subprocess.STDOUT, text=True,
        )
        workers.append(restart)
        worker_ids[id(restart)] = f"g381-{tag}-restart"
        _wait_until(lambda: _pid_file_for_worker(stop_dir, worker_ids[id(restart)]) is not None, timeout=10, description="restarted worker readiness")
        _, metadata = _pid_file_for_worker(stop_dir, worker_ids[id(restart)])
        (stop_dir / f"worker-{metadata['pid']}.stop").write_text("stop", encoding="ascii")
        assert restart.wait(timeout=10) == 0
        _wait_until(lambda: _pid_file_for_worker(stop_dir, worker_ids[id(restart)]) is None, timeout=5, description="restarted worker graceful exit")
        workers.clear()
        worker_ids.clear()
    finally:
        for pid_file in stop_dir.glob("worker-*.pid"):
            try:
                metadata = json.loads(pid_file.read_text(encoding="utf-8"))
                (stop_dir / f"worker-{int(metadata['pid'])}.stop").touch(exist_ok=True)
            except (OSError, ValueError, KeyError, TypeError):
                pass
        for process in workers:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
        for stream in worker_console_streams:
            stream.close()
        app.dependency_overrides.pop(get_db, None)
        with _Session() as db:
            assert db.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase3_test"
            assignment_ids = list(db.scalars(select(PhanCongKiemDuyet.maPhanCong).where(PhanCongKiemDuyet.maKhoaHoc == ids.get("course", -1))).all())
            db.execute(delete(ViPhamChuyenGia).where(ViPhamChuyenGia.maPhanCong.in_(assignment_ids)))
            db.execute(delete(NhatKyKyLuatChuyenGia).where(NhatKyKyLuatChuyenGia.maChuyenGia == ids.get("expert", -1)))
            db.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_([ids.get("provider_user", -1), ids.get("expert_user", -1)])))
            db.execute(delete(DanhGiaChuyenGia).where(DanhGiaChuyenGia.maPhanCong.in_(assignment_ids)))
            db.execute(delete(PhanCongKiemDuyet).where(PhanCongKiemDuyet.maKhoaHoc == ids.get("course", -1)))
            db.execute(delete(HangDoiPhanCong).where(HangDoiPhanCong.maKhoaHoc == ids.get("course", -1)))
            db.execute(delete(TaiLieu).where(TaiLieu.maKhoaHoc == ids.get("course", -1)))
            db.execute(delete(BaiHoc).where(BaiHoc.maKhoaHoc == ids.get("course", -1)))
            db.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc == ids.get("course", -1)))
            db.execute(delete(ChuyenGiaChuyenMon).where(ChuyenGiaChuyenMon.maChuyenGia == ids.get("expert", -1)))
            db.execute(delete(ChuyenMonDanhMuc).where(ChuyenMonDanhMuc.maChuyenMon == ids.get("specialty", -1)))
            db.execute(delete(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNguoiDung == ids.get("provider_user", -1)))
            db.execute(delete(ChuyenGia).where(ChuyenGia.maChuyenGia == ids.get("expert", -1)))
            db.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_([ids.get("provider_user", -1), ids.get("expert_user", -1)])))
            db.execute(delete(ChuyenMon).where(ChuyenMon.maChuyenMon == ids.get("specialty", -1)))
            db.execute(delete(DanhMuc).where(DanhMuc.maDanhMuc == ids.get("category", -1)))
            db.commit()


def _queue_status(course_id: int) -> str | None:
    with _Session() as db:
        assert db.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase3_test"
        return db.scalar(select(HangDoiPhanCong.trangThai).where(HangDoiPhanCong.maKhoaHoc == course_id))


from models import (  # noqa: E402
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
    BaiHoc,
    TaiLieu,
    ThongBao,
    VaiTro,
    ViPhamChuyenGia,
    NhatKyKyLuatChuyenGia,
)
