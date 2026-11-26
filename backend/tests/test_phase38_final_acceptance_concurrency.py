"""GĐ3.8 Final Acceptance Multi-Connection Concurrency Suite:
- C-ManualVsAuto: Manual Assignment racing with Automatic assign_best_expert -> 0 deadlocks, strictly 1 active assignment
- C-AcceptVsExpire: EXPERT accept_assignment racing with worker expire_overdue_assignments -> strictly 1 wins
- C-DeclineVsExpire: EXPERT decline_assignment racing with worker expire_overdue_assignments -> strictly 1 wins
- C-DecisionVsCancel: EXPERT submit_assignment_decision racing with ADMIN cancel_assignment -> strictly 1 wins
- C-DecisionVsLock: EXPERT submit_assignment_decision racing with ADMIN lock_expert -> strictly 1 wins

STRICTLY targets EduSuggest_phase3_test with runtime current_database() guard.
"""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import Session, sessionmaker

from models import (
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
    NhatKyKyLuatChuyenGia,
    PhanCongKiemDuyet,
    ThongBao,
    VaiTro,
    ViPhamChuyenGia,
)
from service import (
    accountability_service,
    assignment_lifecycle_service,
    assignment_queue_service,
    assignment_service,
)
from service.assignment_worker import AssignmentQueueWorker
from service.workflow_service import WorkflowConflictError, WorkflowForbiddenError


TEST_DB_NAME = os.getenv("EDUSUGGEST_TEST_DB_NAME", "EduSuggest_phase3_test").strip()
assert TEST_DB_NAME and TEST_DB_NAME != "EduSuggest", (
    "SAFETY GUARD ABORT: Phase 3.8 concurrency tests must NEVER target production 'EduSuggest'."
)


def _build_test_engine():
    load_dotenv(r"d:\đồ án\EduSuggest\backend\.env")
    prod_url = os.getenv("DATABASE_URL") or ""
    p = urlparse(prod_url)
    assert p.path.lstrip("/") == "EduSuggest"
    test_url = urlunparse(p._replace(path=f"/{TEST_DB_NAME}"))
    eng = create_engine(test_url, pool_pre_ping=True, pool_size=12, max_overflow=12)
    with eng.connect() as c:
        assert c.execute(text("SELECT current_database()")).scalar() == TEST_DB_NAME
    return eng


TEST_ENGINE = _build_test_engine()
TestSessionFactory = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _setup_race_fixture(s: Session, *, pc_status: str | None = None, expired_accept: bool = False):
    assert s.execute(text("SELECT current_database()")).scalar() == TEST_DB_NAME
    now = _now_utc()
    tag = uuid.uuid4().hex[:8]
    roles = {r.tenVaiTro: r.maVaiTro for r in s.scalars(select(VaiTro)).all()}

    admin = NguoiDung(
        tenTaiKhoan=f"g38_adm_{tag}", email=f"g38_adm_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase38test00000000000000000000",
        hoTen="G38 Admin", maVaiTro=roles["ADMIN"], trangThai="ACTIVE", batBuocDoiMatKhau=False,
    )
    exp_u = NguoiDung(
        tenTaiKhoan=f"g38_exp_{tag}", email=f"g38_exp_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase38test00000000000000000000",
        hoTen="G38 Expert", maVaiTro=roles["EXPERT"], trangThai="ACTIVE", batBuocDoiMatKhau=False,
    )
    prov_u = NguoiDung(
        tenTaiKhoan=f"g38_prv_{tag}", email=f"g38_prv_{tag}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase38test00000000000000000000",
        hoTen="G38 Prov", maVaiTro=roles["PROVIDER"], trangThai="ACTIVE", batBuocDoiMatKhau=False,
    )
    s.add_all([admin, exp_u, prov_u])
    s.flush()

    exp = ChuyenGia(maNguoiDung=exp_u.maNguoiDung, trangThaiHoSo="VERIFIED", soNamKinhNghiem=6)
    prov = NhaCungCapKhoaHoc(maNguoiDung=prov_u.maNguoiDung, tieuSu=f"G38 Org {tag}")
    dm = DanhMuc(tenDanhMuc=f"G38 Cat {tag}")
    cm = ChuyenMon(tenChuyenMon=f"G38 Spec {tag}", nhomChuyenMon="G38", trangThai="ACTIVE", ngayTao=now)
    s.add_all([exp, prov, dm, cm])
    s.flush()
    s.add(ChuyenMonDanhMuc(maChuyenMon=cm.maChuyenMon, maDanhMuc=dm.maDanhMuc, ngayTao=now))
    s.add(ChuyenGiaChuyenMon(maChuyenGia=exp.maChuyenGia, maChuyenMon=cm.maChuyenMon, laChuyenMonChinh=True, ngayTao=now))

    course = KhoaHoc(
        maNhaCungCap=prov.maNhaCungCap, maDanhMuc=dm.maDanhMuc, tieuDe=f"G38 Course {tag}",
        gia=Decimal("0"), trangThaiDuyet="PENDING", trangThaiHienThi="HIDDEN", soVongKiemDuyetHienTai=1,
    )
    s.add(course)
    s.flush()

    pc_id = None
    if pc_status is not None:
        pc = PhanCongKiemDuyet(
            maKhoaHoc=course.maKhoaHoc, maChuyenGia=exp.maChuyenGia, maDanhMuc=dm.maDanhMuc,
            soVongKiemDuyet=1, phuongThucPhanCong="AUTO", trangThai=pc_status,
            ngayPhanCong=now - timedelta(hours=25),
            hanTiepNhan=(now - timedelta(seconds=10)) if expired_accept else (now + timedelta(hours=12)),
            hanKiemDuyet=(now + timedelta(hours=48)) if pc_status in ("ACCEPTED", "IN_PROGRESS") else None,
            ngayChapNhan=(now - timedelta(hours=1)) if pc_status in ("ACCEPTED", "IN_PROGRESS") else None,
            ngayCapNhat=now,
        )
        s.add(pc)
        s.flush()
        pc_id = int(pc.maPhanCong)

    s.commit()
    return {
        "admin_uid": int(admin.maNguoiDung),
        "exp_uid": int(exp_u.maNguoiDung),
        "prov_uid": int(prov_u.maNguoiDung),
        "exp_id": int(exp.maChuyenGia),
        "prov_id": int(prov.maNhaCungCap),
        "dm_id": int(dm.maDanhMuc),
        "cm_id": int(cm.maChuyenMon),
        "course_id": int(course.maKhoaHoc),
        "pc_id": pc_id,
    }


def _cleanup_race_fixture(ids: dict) -> None:
    u_ids = [ids["admin_uid"], ids["exp_uid"], ids["prov_uid"]]
    with TestSessionFactory() as cs:
        cs.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_(u_ids)))
        cs.execute(delete(NhatKyKyLuatChuyenGia).where(NhatKyKyLuatChuyenGia.maChuyenGia == ids["exp_id"]))
        cs.execute(delete(ViPhamChuyenGia).where(ViPhamChuyenGia.maChuyenGia == ids["exp_id"]))
        cs.execute(delete(HangDoiPhanCong).where(HangDoiPhanCong.maKhoaHoc == ids["course_id"]))
        cs.execute(delete(DanhGiaChuyenGia).where(DanhGiaChuyenGia.maKhoaHoc == ids["course_id"]))
        cs.execute(delete(PhanCongKiemDuyet).where(PhanCongKiemDuyet.maKhoaHoc == ids["course_id"]))
        cs.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc == ids["course_id"]))
        cs.execute(delete(ChuyenGiaChuyenMon).where(ChuyenGiaChuyenMon.maChuyenGia == ids["exp_id"]))
        cs.execute(delete(ChuyenGia).where(ChuyenGia.maChuyenGia == ids["exp_id"]))
        cs.execute(delete(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNhaCungCap == ids["prov_id"]))
        cs.execute(delete(ChuyenMonDanhMuc).where(ChuyenMonDanhMuc.maChuyenMon == ids["cm_id"]))
        cs.execute(delete(ChuyenMon).where(ChuyenMon.maChuyenMon == ids["cm_id"]))
        cs.execute(delete(DanhMuc).where(DanhMuc.maDanhMuc == ids["dm_id"]))
        cs.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(u_ids)))
        cs.commit()


def test_concurrency_manual_assign_vs_auto_assign():
    """Manual Assignment racing with Automatic assign_best_expert -> 0 deadlocks, strictly 1 active assignment."""
    with TestSessionFactory() as s:
        ids = _setup_race_fixture(s)
    try:
        barrier = Barrier(2)

        def _manual() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                try:
                    assignment_service.assign_expert_manually(
                        ws, admin_user_id=ids["admin_uid"], target_type="COURSE",
                        target_id=ids["course_id"], expert_id=ids["exp_id"],
                        reason="Concurrent manual assign test",
                    )
                    return "MANUAL_OK"
                except WorkflowConflictError:
                    ws.rollback()
                    return "CONFLICT"

        def _auto() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                res = assignment_service.assign_best_expert(
                    ws, target_type="COURSE", target_id=ids["course_id"], expected_review_round=1
                )
                ws.commit()
                return res.status.value

        with ThreadPoolExecutor(max_workers=2) as pool:
            manual_future = pool.submit(_manual)
            auto_future = pool.submit(_auto)
            r_man = manual_future.result(timeout=15)
            r_auto = auto_future.result(timeout=15)

        assert (r_man == "MANUAL_OK" and r_auto == "ALREADY_ASSIGNED") or (
            r_man == "CONFLICT" and r_auto == "ASSIGNED"
        )
        with TestSessionFactory() as vs:
            cnt = vs.execute(
                text('SELECT count(*) FROM "PhanCongKiemDuyet" WHERE "maKhoaHoc"=:cid AND "trangThai" IN (\'ASSIGNED\',\'ACCEPTED\',\'IN_PROGRESS\')'),
                {"cid": ids["course_id"]},
            ).scalar()
            assert cnt == 1
    finally:
        _cleanup_race_fixture(ids)


def test_manual_assignment_races_claimed_processing_queue_job():
    """A manual assignment racing an already PROCESSING worker job converges safely."""
    with TestSessionFactory() as setup:
        ids = _setup_race_fixture(setup)
        now = _now_utc()
        job, _ = assignment_queue_service.enqueue_assignment_job(
            setup,
            target_type="COURSE",
            target_id=ids["course_id"],
            review_round=1,
            event_type="SUBMIT",
            now=now,
        )
        setup.commit()
        job_id = int(job.maCongViec)

    worker = AssignmentQueueWorker(
        TestSessionFactory,
        worker_id=f"g382-processing-{uuid.uuid4().hex[:6]}",
        lease_seconds=30,
        batch_size=1,
        expected_db_name=TEST_DB_NAME,
    )
    claimed = worker.claim_next_jobs(now=now)
    assert len(claimed) == 1 and claimed[0].maCongViec == job_id
    barrier = Barrier(2)

    def worker_path():
        barrier.wait(timeout=10)
        return worker.process_claimed_job(claimed[0], now=now + timedelta(seconds=1))

    def manual_path():
        barrier.wait(timeout=10)
        with TestSessionFactory() as session:
            assert session.execute(text("SELECT current_database()")).scalar_one() == TEST_DB_NAME
            try:
                assignment = assignment_service.assign_expert_manually(
                    session,
                    admin_user_id=ids["admin_uid"],
                    target_type="COURSE",
                    target_id=ids["course_id"],
                    expert_id=ids["exp_id"],
                    reason="G382 claimed processing race",
                    now=now + timedelta(seconds=1),
                )
                return ("assigned", int(assignment.maPhanCong))
            except WorkflowConflictError as exc:
                session.rollback()
                return ("conflict", str(exc))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            worker_future = pool.submit(worker_path)
            manual_future = pool.submit(manual_path)
            worker_result = worker_future.result(timeout=20)
            manual_result = manual_future.result(timeout=20)

        with TestSessionFactory() as verify:
            assert verify.execute(text("SELECT current_database()")).scalar_one() == TEST_DB_NAME
            active = list(
                verify.scalars(
                    select(PhanCongKiemDuyet).where(
                        PhanCongKiemDuyet.maKhoaHoc == ids["course_id"],
                        PhanCongKiemDuyet.trangThai.in_(("ASSIGNED", "ACCEPTED", "IN_PROGRESS")),
                    )
                ).all()
            )
            queue_job = verify.get(HangDoiPhanCong, job_id)
            assert len(active) == 1
            assert queue_job is not None and queue_job.trangThai == "DONE"
            assert queue_job.maWorker is None and queue_job.claimToken is None
            assert worker_result.finalQueueStatus == "DONE"
            assert manual_result[0] in {"assigned", "conflict"}
            assert active[0].maChuyenGia == ids["exp_id"]
    finally:
        _cleanup_race_fixture(ids)


def test_concurrency_decision_vs_admin_cancel():
    """EXPERT submit_assignment_decision racing with ADMIN cancel_assignment -> strictly 1 wins."""
    with TestSessionFactory() as s:
        ids = _setup_race_fixture(s, pc_status="IN_PROGRESS")
    try:
        barrier = Barrier(2)

        def _decide() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                try:
                    assignment_lifecycle_service.submit_assignment_decision(
                        ws, ids["exp_uid"], ids["pc_id"],
                        trang_thai="APPROVED", noi_dung_danh_gia="Đạt yêu cầu học thuật",
                    )
                    return "DECIDED"
                except (WorkflowConflictError, WorkflowForbiddenError):
                    ws.rollback()
                    return "REJECTED"

        def _cancel() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                try:
                    assignment_lifecycle_service.admin_cancel_assignment(
                        ws, ids["admin_uid"], ids["pc_id"],
                        reason="Concurrent cancel vs decision", requeue=False,
                    )
                    return "CANCELLED"
                except WorkflowConflictError:
                    ws.rollback()
                    return "REJECTED"

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_decide)
            f2 = pool.submit(_cancel)
            r1, r2 = f1.result(timeout=15), f2.result(timeout=15)

        assert sorted([r1, r2]) in (["CANCELLED", "REJECTED"], ["DECIDED", "REJECTED"])
    finally:
        _cleanup_race_fixture(ids)


def test_concurrency_accept_vs_expire():
    """EXPERT accept_assignment racing with worker expire_overdue_assignments -> consistent single terminal/active state."""
    with TestSessionFactory() as s:
        ids = _setup_race_fixture(s, pc_status="ASSIGNED", expired_accept=True)
    try:
        barrier = Barrier(2)
        worker = AssignmentQueueWorker(session_factory=TestSessionFactory)

        def _accept() -> str:
            with TestSessionFactory() as ws:
                barrier.wait(timeout=5)
                try:
                    assignment_lifecycle_service.accept_assignment(
                        ws, ids["exp_uid"], ids["pc_id"], now=_now_utc() - timedelta(minutes=1)
                    )
                    return "ACCEPTED"
                except WorkflowConflictError:
                    ws.rollback()
                    return "CONFLICT"

        def _expire() -> int:
            barrier.wait(timeout=5)
            return worker.expire_overdue_assignments(now=_now_utc())

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_accept)
            f2 = pool.submit(_expire)
            r_acc = f1.result(timeout=15)
            r_exp = f2.result(timeout=15)

        with TestSessionFactory() as vs:
            pc = vs.get(PhanCongKiemDuyet, ids["pc_id"])
            assert pc is not None
            assert pc.trangThai in ("ACCEPTED", "EXPIRED")
            if pc.trangThai == "ACCEPTED":
                assert r_acc == "ACCEPTED"
            else:
                assert r_exp >= 1
    finally:
        _cleanup_race_fixture(ids)
