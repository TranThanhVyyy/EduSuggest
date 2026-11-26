"""OS-process crash recovery acceptance for the durable assignment worker."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

os.environ["DEBUG"] = "False"

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
    NhatKyKyLuatChuyenGia,
    PhanCongKiemDuyet,
    ThongBao,
    VaiTro,
    ViPhamChuyenGia,
)
from schemas.assignment import WorkerJobContext
from service.assignment_worker import AssignmentQueueWorker

BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKER_SCRIPT = BACKEND_DIR / "scripts" / "run_assignment_worker.py"
TEST_DATABASE = os.getenv("EDUSUGGEST_TEST_DB_NAME", "EduSuggest_phase3_test").strip()
assert TEST_DATABASE and TEST_DATABASE != "EduSuggest", (
    "SAFETY VIOLATION: Worker recovery tests must NEVER target production 'EduSuggest'."
)


def _wait_until(predicate, *, timeout: float, description: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {description}")


def test_abrupt_worker_kill_reclaims_stale_lease_without_duplicate(tmp_path: Path):
    load_dotenv(BACKEND_DIR / ".env")
    configured = make_url(os.environ["DATABASE_URL"])
    assert configured.database in ("EduSuggest", TEST_DATABASE)
    engine = create_engine(configured.set(database=TEST_DATABASE), pool_pre_ping=True)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with engine.connect() as guard:
        assert guard.execute(text("SELECT current_database()" )).scalar_one() == TEST_DATABASE

    tag = uuid.uuid4().hex[:10]
    now = datetime.now(UTC).replace(tzinfo=None)
    ids: dict[str, int] = {}
    killed_worker: subprocess.Popen[str] | None = None
    recovery_worker: subprocess.Popen[str] | None = None
    lock_session: Session | None = None
    control_dir = tmp_path / "control"
    control_dir.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "DEBUG": "False",
            "AUTO_ASSIGNMENT_WORKFLOW_ENABLED": "True",
            "AUTO_ASSIGNMENT_WORKER_ENABLED": "True",
            "ACCOUNTABILITY_ENABLED": "True",
            "DATABASE_URL": configured.set(database=TEST_DATABASE).render_as_string(
                hide_password=False
            ),
        }
    )

    try:
        with sessions() as db:
            assert db.execute(text("SELECT current_database()" )).scalar_one() == TEST_DATABASE
            roles = {
                role.tenVaiTro: role.maVaiTro for role in db.scalars(select(VaiTro)).all()
            }
            provider_user = NguoiDung(
                tenTaiKhoan=f"g383_kill_provider_{tag}",
                email=f"g383_kill_provider_{tag}@test.invalid",
                matKhau="$2b$12$dummyhashvalueforg383kill000000000000000000000000",
                maVaiTro=roles["PROVIDER"],
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            expert_user = NguoiDung(
                tenTaiKhoan=f"g383_kill_expert_{tag}",
                email=f"g383_kill_expert_{tag}@test.invalid",
                matKhau="$2b$12$dummyhashvalueforg383kill000000000000000000000000",
                maVaiTro=roles["EXPERT"],
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            db.add_all([provider_user, expert_user])
            db.flush()
            provider = NhaCungCapKhoaHoc(
                maNguoiDung=provider_user.maNguoiDung, tieuSu="GĐ3.8.3 kill fixture"
            )
            expert = ChuyenGia(
                maNguoiDung=expert_user.maNguoiDung,
                trangThaiHoSo="VERIFIED",
                soNamKinhNghiem=7,
            )
            category = DanhMuc(tenDanhMuc=f"G383 Kill Category {tag}")
            specialty = ChuyenMon(
                tenChuyenMon=f"G383 Kill Specialty {tag}",
                nhomChuyenMon="G383",
                trangThai="ACTIVE",
                ngayTao=now,
            )
            db.add_all([provider, expert, category, specialty])
            db.flush()
            db.add_all(
                [
                    ChuyenMonDanhMuc(
                        maChuyenMon=specialty.maChuyenMon,
                        maDanhMuc=category.maDanhMuc,
                        ngayTao=now,
                    ),
                    ChuyenGiaChuyenMon(
                        maChuyenGia=expert.maChuyenGia,
                        maChuyenMon=specialty.maChuyenMon,
                        laChuyenMonChinh=True,
                        ngayTao=now,
                    ),
                ]
            )
            course = KhoaHoc(
                maNhaCungCap=provider.maNhaCungCap,
                maDanhMuc=category.maDanhMuc,
                tieuDe=f"G383 Abrupt Kill Course {tag}",
                gia=0,
                trangThaiDuyet="PENDING",
                trangThaiHienThi="HIDDEN",
                soVongKiemDuyetHienTai=1,
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add(course)
            db.flush()
            job = HangDoiPhanCong(
                loaiDoiTuong="COURSE",
                maKhoaHoc=course.maKhoaHoc,
                soVongKiemDuyet=1,
                loaiSuKien="SUBMIT",
                khoaChongTrung=f"SUBMIT:COURSE:{course.maKhoaHoc}:R1",
                trangThai="PENDING",
                uuTien=100,
                soLanThu=0,
                soLanThuToiDa=5,
                thoiDiemChayTiepTheo=now,
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add(job)
            db.commit()
            ids = {
                "provider_user": int(provider_user.maNguoiDung),
                "expert_user": int(expert_user.maNguoiDung),
                "provider": int(provider.maNhaCungCap),
                "expert": int(expert.maChuyenGia),
                "category": int(category.maDanhMuc),
                "specialty": int(specialty.maChuyenMon),
                "course": int(course.maKhoaHoc),
                "job": int(job.maCongViec),
            }

        # Force the first worker to block after its short claim transaction commits.
        lock_session = sessions()
        lock_session.scalars(
            select(KhoaHoc)
            .where(KhoaHoc.maKhoaHoc == ids["course"])
            .with_for_update()
        ).one()

        killed_id = f"g383-killed-{tag}"
        killed_worker = subprocess.Popen(
            [
                sys.executable,
                str(WORKER_SCRIPT),
                "--expected-database",
                TEST_DATABASE,
                "--poll-interval",
                "0.2",
                "--lease-seconds",
                "5",
                "--worker-id",
                killed_id,
                "--log-file",
                str(tmp_path / "killed.jsonl"),
                "--control-dir",
                str(control_dir),
            ],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        def claimed_by_first_worker() -> bool:
            with sessions() as db:
                row = db.get(HangDoiPhanCong, ids["job"])
                return bool(
                    row
                    and row.trangThai == "PROCESSING"
                    and row.maWorker == killed_id
                    and row.claimToken is not None
                )

        _wait_until(claimed_by_first_worker, timeout=15, description="first worker claim")
        with sessions() as db:
            claimed_job = db.get(HangDoiPhanCong, ids["job"])
            assert claimed_job is not None and claimed_job.claimToken is not None
            stale_context = WorkerJobContext(
                maCongViec=int(claimed_job.maCongViec),
                claimToken=claimed_job.claimToken,
                leaseGeneration=int(claimed_job.leaseGeneration),
                maWorker=str(claimed_job.maWorker),
                loaiSuKien=claimed_job.loaiSuKien,
                maPhanCongNguon=claimed_job.maPhanCongNguon,
            )

        killed_worker.kill()  # Deliberate TerminateProcess: no graceful marker/signal.
        assert killed_worker.wait(timeout=10) != 0
        killed_worker = None
        lock_session.rollback()
        lock_session.close()
        lock_session = None

        recovery_id = f"g383-recovery-{tag}"
        recovery_worker = subprocess.Popen(
            [
                sys.executable,
                str(WORKER_SCRIPT),
                "--expected-database",
                TEST_DATABASE,
                "--poll-interval",
                "0.2",
                "--lease-seconds",
                "5",
                "--worker-id",
                recovery_id,
                "--log-file",
                str(tmp_path / "recovery.jsonl"),
                "--control-dir",
                str(control_dir),
            ],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        def recovered_done() -> bool:
            with sessions() as db:
                row = db.get(HangDoiPhanCong, ids["job"])
                return bool(row and row.trangThai == "DONE")

        _wait_until(recovered_done, timeout=30, description="stale lease recovery")
        with sessions() as db:
            job = db.get(HangDoiPhanCong, ids["job"])
            assignments = list(
                db.scalars(
                    select(PhanCongKiemDuyet).where(
                        PhanCongKiemDuyet.maKhoaHoc == ids["course"]
                    )
                ).all()
            )
            assert job is not None
            assert job.trangThai == "DONE"
            assert job.leaseGeneration >= 2
            assert job.soLanThu == 1
            assert job.maWorker is None and job.claimToken is None and job.hanXuLy is None
            assert len(assignments) == 1
            assignment = assignments[0]
            assert assignment.maChuyenGia == ids["expert"]
            notifications = list(
                db.scalars(
                    select(ThongBao).where(
                        ThongBao.maNguoiNhan == ids["expert_user"]
                    )
                ).all()
            )
            assert len(
                [
                    item
                    for item in notifications
                    if item.duLieuLienKet
                    and item.duLieuLienKet.get("maPhanCong") == assignment.maPhanCong
                ]
            ) == 1

        stale_worker = AssignmentQueueWorker(
            sessions,
            worker_id=stale_context.maWorker,
            lease_seconds=5,
            expected_db_name=TEST_DATABASE,
        )
        stale_outcome = stale_worker.process_claimed_job(stale_context)
        assert stale_outcome.fencedOut is True
        assert stale_outcome.finalQueueStatus == "FENCED_OUT"

        pid_metadata = None
        for pid_file in control_dir.glob("worker-*.pid"):
            candidate = json.loads(pid_file.read_text(encoding="utf-8"))
            if candidate.get("worker_id") == recovery_id:
                pid_metadata = candidate
                break
        assert pid_metadata is not None
        (control_dir / f"worker-{pid_metadata['pid']}.stop").write_text(
            "stop", encoding="ascii"
        )
        assert recovery_worker.wait(timeout=10) == 0
        recovery_worker = None
    finally:
        if lock_session is not None:
            lock_session.rollback()
            lock_session.close()
        for process in (killed_worker, recovery_worker):
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=10)
        if ids:
            with sessions() as db:
                assert db.execute(text("SELECT current_database()" )).scalar_one() == TEST_DATABASE
                assignment_ids = list(
                    db.scalars(
                        select(PhanCongKiemDuyet.maPhanCong).where(
                            PhanCongKiemDuyet.maKhoaHoc == ids["course"]
                        )
                    ).all()
                )
                db.execute(
                    delete(ViPhamChuyenGia).where(
                        ViPhamChuyenGia.maPhanCong.in_(assignment_ids)
                    )
                )
                db.execute(
                    delete(NhatKyKyLuatChuyenGia).where(
                        NhatKyKyLuatChuyenGia.maChuyenGia == ids["expert"]
                    )
                )
                db.execute(
                    delete(ThongBao).where(
                        ThongBao.maNguoiNhan.in_(
                            [ids["provider_user"], ids["expert_user"]]
                        )
                    )
                )
                db.execute(
                    delete(PhanCongKiemDuyet).where(
                        PhanCongKiemDuyet.maKhoaHoc == ids["course"]
                    )
                )
                db.execute(
                    delete(HangDoiPhanCong).where(
                        HangDoiPhanCong.maCongViec == ids["job"]
                    )
                )
                db.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc == ids["course"]))
                db.execute(
                    delete(ChuyenGiaChuyenMon).where(
                        ChuyenGiaChuyenMon.maChuyenGia == ids["expert"]
                    )
                )
                db.execute(
                    delete(ChuyenMonDanhMuc).where(
                        ChuyenMonDanhMuc.maChuyenMon == ids["specialty"]
                    )
                )
                db.execute(
                    delete(NhaCungCapKhoaHoc).where(
                        NhaCungCapKhoaHoc.maNhaCungCap == ids["provider"]
                    )
                )
                db.execute(
                    delete(ChuyenGia).where(ChuyenGia.maChuyenGia == ids["expert"])
                )
                db.execute(
                    delete(NguoiDung).where(
                        NguoiDung.maNguoiDung.in_(
                            [ids["provider_user"], ids["expert_user"]]
                        )
                    )
                )
                db.execute(
                    delete(ChuyenMon).where(ChuyenMon.maChuyenMon == ids["specialty"])
                )
                db.execute(delete(DanhMuc).where(DanhMuc.maDanhMuc == ids["category"]))
                db.commit()
        engine.dispose()
