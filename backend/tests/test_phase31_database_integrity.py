"""PostgreSQL Constraint, ORM & Concurrency Tests for GĐ3.1A — STRICTLY on EduSuggest_phase3_test.

SAFETY GUARD:
- Connects ONLY to EduSuggest_phase3_test (asserts SELECT current_database() == 'EduSuggest_phase3_test').
- Every test uses rolled-back transactions or explicit fixture cleanup so EduSuggest_phase3_test
  ends with 1 row in CauHinhPhanCong and 0 rows in the other 6 new tables.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
from urllib.parse import urlparse, urlunparse
import uuid

from dotenv import load_dotenv
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, configure_mappers, sessionmaker

from models import (
    CauHinhPhanCong,
    ChuyenGia,
    DanhGiaChuyenGia,
    HangDoiPhanCong,
    KhoaHoc,
    NguoiDung,
    NhatKyKyLuatChuyenGia,
    PhanCongKiemDuyet,
    TaiLieu,
    ThongBao,
    VaiTro,
    ViPhamChuyenGia,
    YeuCauTamNgungChuyenGia,
)


def _build_test_engine():
    load_dotenv(r"d:\đồ án\EduSuggest\backend\.env")
    prod_url = os.getenv("DATABASE_URL") or ""
    p = urlparse(prod_url)
    assert p.path.lstrip("/") == "EduSuggest", "Unexpected .env DB name"
    test_url = urlunparse(p._replace(path="/EduSuggest_phase3_test"))
    eng = create_engine(test_url, pool_pre_ping=True)
    with eng.connect() as c:
        cur = c.execute(text("SELECT current_database()")).scalar()
        assert cur == "EduSuggest_phase3_test", f"SAFETY GUARD ABORT: connected to {cur!r}"
    return eng


TEST_ENGINE = _build_test_engine()
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def db_session():
    """Each test runs inside a single rolled-back outer transaction."""
    conn = TEST_ENGINE.connect()
    trans = conn.begin()
    assert conn.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
    session = Session(bind=conn)
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


def _base_ids(db: Session) -> dict[str, int]:
    admin_id = db.scalar(select(NguoiDung.maNguoiDung).join(VaiTro).where(VaiTro.tenVaiTro == "ADMIN"))
    expert_id = db.scalar(select(ChuyenGia.maChuyenGia).limit(1))
    expert_uid = db.scalar(select(ChuyenGia.maNguoiDung).where(ChuyenGia.maChuyenGia == expert_id))
    course_id = db.scalar(select(KhoaHoc.maKhoaHoc).limit(1))
    cat_id = db.scalar(select(KhoaHoc.maDanhMuc).where(KhoaHoc.maKhoaHoc == course_id))
    mat_id = db.scalar(select(TaiLieu.maTaiLieu).limit(1))
    return {
        "admin_id": int(admin_id),
        "expert_id": int(expert_id),
        "expert_uid": int(expert_uid),
        "course_id": int(course_id),
        "cat_id": int(cat_id),
        "mat_id": int(mat_id),
    }


# ---------------------------------------------------------------------------
# Nhóm A: CauHinhPhanCong (Singleton & Bounds)
# ---------------------------------------------------------------------------


def test_group_a_singleton_config_seeded_and_enforced(db_session: Session):
    cfg = db_session.get(CauHinhPhanCong, 1)
    assert cfg is not None
    assert cfg.gioiHanTaiToiDa == 5
    assert cfg.hanTiepNhanGio == 24
    assert cfg.hanKiemDuyetGio == 72
    assert cfg.khoangThongKeGio == 168
    assert cfg.nguongCanhBao == 2
    assert cfg.nguongKhoaTaiKhoan == 4
    assert cfg.tinhViPhamHetHan is True
    assert cfg.tuDongKhoa is True
    assert cfg.thoiGianTamNgungToiDaNgay == 30
    assert cfg.soLanTaiPhanCongToiDa == 5
    assert cfg.uuTienTuyetDoiChuyenMonChinh is False

    # Second row blocked by CHECK (maCauHinh = 1)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(CauHinhPhanCong(maCauHinh=2))
            db_session.flush()

    # Invalid bounds blocked
    for field, bad_val in [
        ("gioiHanTaiToiDa", 0),
        ("hanTiepNhanGio", 0),
        ("hanKiemDuyetGio", 0),
        ("nguongCanhBao", 0),
        ("nguongKhoaTaiKhoan", 2),  # <= nguongCanhBao (2)
    ]:
        with pytest.raises(IntegrityError):
            with db_session.begin_nested():
                setattr(cfg, field, bad_val)
                db_session.flush()


# ---------------------------------------------------------------------------
# Nhóm B: PhanCongKiemDuyet Constraints & Partial Unique Indexes
# ---------------------------------------------------------------------------


def test_group_b_assignment_constraints_and_active_uniqueness(db_session: Session):
    ids = _base_ids(db_session)
    now = _now_utc()

    # Valid AUTO course assignment
    a1 = PhanCongKiemDuyet(
        maKhoaHoc=ids["course_id"],
        maChuyenGia=ids["expert_id"],
        maDanhMuc=ids["cat_id"],
        soVongKiemDuyet=1,
        phuongThucPhanCong="AUTO",
        diemPhuHop=Decimal("85.50"),
        chiTietDiem={"spec": 50, "load": 24, "exp": 5, "fair": 6.5},
        trangThai="ASSIGNED",
        ngayPhanCong=now,
        hanTiepNhan=now + timedelta(hours=24),
    )
    db_session.add(a1)
    db_session.flush()
    assert a1.maPhanCong is not None

    # Second active assignment for same course blocked by uq_phancong_active_course
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                PhanCongKiemDuyet(
                    maKhoaHoc=ids["course_id"],
                    maChuyenGia=ids["expert_id"],
                    maDanhMuc=ids["cat_id"],
                    soVongKiemDuyet=2,
                    phuongThucPhanCong="AUTO",
                    trangThai="ACCEPTED",
                    ngayPhanCong=now,
                    hanTiepNhan=now + timedelta(hours=24),
                )
            )
            db_session.flush()

    # After finishing a1 (DECLINED), a new assignment for same course is allowed!
    a1.trangThai = "DECLINED"
    db_session.flush()
    a2 = PhanCongKiemDuyet(
        maKhoaHoc=ids["course_id"],
        maChuyenGia=ids["expert_id"],
        maDanhMuc=ids["cat_id"],
        soVongKiemDuyet=1,
        phuongThucPhanCong="MANUAL",
        maNguoiPhanCong=ids["admin_id"],
        trangThai="ASSIGNED",
        ngayPhanCong=now,
        hanTiepNhan=now + timedelta(hours=24),
    )
    db_session.add(a2)
    db_session.flush()

    # Invalid cases: both NULL, both NOT NULL, score > 100, AUTO with actor, MANUAL without actor, bad deadline
    invalid_kwargs = [
        {"maKhoaHoc": None, "maTaiLieu": None},
        {"maKhoaHoc": ids["course_id"], "maTaiLieu": ids["mat_id"]},
        {"maTaiLieu": ids["mat_id"], "diemPhuHop": Decimal("101.00")},
        {"maTaiLieu": ids["mat_id"], "diemPhuHop": Decimal("-1.00")},
        {"maTaiLieu": ids["mat_id"], "soVongKiemDuyet": 0},
        {"maTaiLieu": ids["mat_id"], "phuongThucPhanCong": "AUTO", "maNguoiPhanCong": ids["admin_id"]},
        {"maTaiLieu": ids["mat_id"], "phuongThucPhanCong": "MANUAL", "maNguoiPhanCong": None},
        {"maTaiLieu": ids["mat_id"], "trangThai": "INVALID_STATE"},
        {"maTaiLieu": ids["mat_id"], "hanTiepNhan": now - timedelta(hours=1)},
    ]
    for kw in invalid_kwargs:
        base = dict(
            maChuyenGia=ids["expert_id"],
            maDanhMuc=ids["cat_id"],
            soVongKiemDuyet=1,
            phuongThucPhanCong="AUTO",
            trangThai="ASSIGNED",
            ngayPhanCong=now,
            hanTiepNhan=now + timedelta(hours=24),
        )
        base.update(kw)
        with pytest.raises(IntegrityError):
            with db_session.begin_nested():
                db_session.add(PhanCongKiemDuyet(**base))
                db_session.flush()


# ---------------------------------------------------------------------------
# Nhóm C: DanhGiaChuyenGia.maPhanCong (ARCH-02)
# ---------------------------------------------------------------------------


def test_group_c_review_result_one_per_assignment(db_session: Session):
    ids = _base_ids(db_session)
    now = _now_utc()
    # Legacy reviews with NULL maPhanCong preserved
    legacy_null_count = db_session.scalar(
        select(DanhGiaChuyenGia.maDanhGia).where(DanhGiaChuyenGia.maPhanCong.is_(None)).limit(1)
    )
    assert legacy_null_count is not None

    a = PhanCongKiemDuyet(
        maTaiLieu=ids["mat_id"],
        maChuyenGia=ids["expert_id"],
        maDanhMuc=ids["cat_id"],
        trangThai="IN_PROGRESS",
        ngayPhanCong=now,
        hanTiepNhan=now + timedelta(hours=24),
    )
    db_session.add(a)
    db_session.flush()

    r1 = DanhGiaChuyenGia(
        maTaiLieu=ids["mat_id"],
        maChuyenGia=ids["expert_id"],
        maPhanCong=a.maPhanCong,
        trangThai="APPROVED",
        ngayTao=now,
    )
    db_session.add(r1)
    db_session.flush()

    # Duplicate official review for same maPhanCong blocked by uq_danhgia_maPhanCong
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                DanhGiaChuyenGia(
                    maTaiLieu=ids["mat_id"],
                    maChuyenGia=ids["expert_id"],
                    maPhanCong=a.maPhanCong,
                    trangThai="REJECTED",
                    ngayTao=now,
                )
            )
            db_session.flush()


# ---------------------------------------------------------------------------
# Nhóm D: HangDoiPhanCong (ARCH-01 + ARCH-06)
# ---------------------------------------------------------------------------


def test_group_d_durable_queue_idempotency_and_lease(db_session: Session):
    ids = _base_ids(db_session)
    now = _now_utc()
    key = f"SUBMIT:COURSE:{ids['course_id']}:R99"

    j1 = HangDoiPhanCong(
        loaiDoiTuong="COURSE",
        maKhoaHoc=ids["course_id"],
        soVongKiemDuyet=1,
        loaiSuKien="SUBMIT",
        khoaChongTrung=key,
        trangThai="PENDING",
    )
    db_session.add(j1)
    db_session.flush()

    # Duplicate open job for same course blocked by uq_hangdoi_open_course
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                HangDoiPhanCong(
                    loaiDoiTuong="COURSE",
                    maKhoaHoc=ids["course_id"],
                    soVongKiemDuyet=1,
                    loaiSuKien="ADMIN_RETRY",
                    khoaChongTrung=key + ":RETRY",
                    trangThai="PENDING",
                )
            )
            db_session.flush()

    # PROCESSING without claimToken/maWorker/hanXuLy blocked
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            j1.trangThai = "PROCESSING"
            db_session.flush()

    # Valid PROCESSING with UUID claimToken -> DONE -> new reassign job allowed
    j1.trangThai = "PROCESSING"
    j1.claimToken = uuid.uuid4()
    j1.maWorker = "worker-1"
    j1.leaseGeneration = 1
    j1.hanXuLy = now + timedelta(minutes=2)
    db_session.flush()

    j1.trangThai = "DONE"
    db_session.flush()

    j2 = HangDoiPhanCong(
        loaiDoiTuong="COURSE",
        maKhoaHoc=ids["course_id"],
        soVongKiemDuyet=1,
        loaiSuKien="REASSIGN_DECLINED",
        khoaChongTrung=f"REASSIGN:COURSE:{ids['course_id']}:R99:FROM:1",
        trangThai="PENDING",
    )
    db_session.add(j2)
    db_session.flush()


# ---------------------------------------------------------------------------
# Nhóm E, F, G, H, I: Accountability, Availability, Notification, Visibility, ORM
# ---------------------------------------------------------------------------


def test_group_e_f_g_h_i_integrity_and_orm(db_session: Session):
    configure_mappers()
    ids = _base_ids(db_session)
    now = _now_utc()

    # E: ViPhamChuyenGia UNIQUE(maPhanCong) + NhatKyKyLuatChuyenGia
    a = PhanCongKiemDuyet(
        maKhoaHoc=ids["course_id"],
        maChuyenGia=ids["expert_id"],
        maDanhMuc=ids["cat_id"],
        trangThai="DECLINED",
        ngayPhanCong=now,
        hanTiepNhan=now + timedelta(hours=24),
    )
    db_session.add(a)
    db_session.flush()

    v1 = ViPhamChuyenGia(
        maChuyenGia=ids["expert_id"],
        maPhanCong=a.maPhanCong,
        loaiViPham="DECLINED_ASSIGNMENT",
        chuKyKyLuatSo=1,
    )
    db_session.add(v1)
    db_session.flush()
    assert v1.trangThaiXuLy == "PENDING_REVIEW"

    # Second violation (even different loaiViPham!) on same maPhanCong blocked by ARCH-03
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                ViPhamChuyenGia(
                    maChuyenGia=ids["expert_id"],
                    maPhanCong=a.maPhanCong,
                    loaiViPham="EXPIRED_ACCEPTANCE",
                    chuKyKyLuatSo=1,
                )
            )
            db_session.flush()

    # NhatKyKyLuatChuyenGia actor consistency
    db_session.add(
        NhatKyKyLuatChuyenGia(
            maChuyenGia=ids["expert_id"],
            maNguoiDung=ids["expert_uid"],
            hanhDong="AUTO_LOCK",
            nguonThucHien="SYSTEM",
            maNguoiThucHien=None,
            lyDo="Test auto lock log",
            chinhSachSnapshot={"threshold": 4},
        )
    )
    db_session.flush()
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                NhatKyKyLuatChuyenGia(
                    maChuyenGia=ids["expert_id"],
                    maNguoiDung=ids["expert_uid"],
                    hanhDong="ADMIN_UNLOCK",
                    nguonThucHien="ADMIN",
                    maNguoiThucHien=None,  # Must be NOT NULL for ADMIN!
                    lyDo="Missing admin",
                )
            )
            db_session.flush()

    # F: YeuCauTamNgungChuyenGia range check + adjacent intervals allowed
    db_session.add(
        YeuCauTamNgungChuyenGia(
            maChuyenGia=ids["expert_id"],
            ngayBatDau=now + timedelta(days=1),
            ngayKetThuc=now + timedelta(days=3),
            lyDo="Nghỉ phép",
        )
    )
    db_session.flush()
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                YeuCauTamNgungChuyenGia(
                    maChuyenGia=ids["expert_id"],
                    ngayBatDau=now + timedelta(days=3),
                    ngayKetThuc=now + timedelta(days=3),
                    lyDo="Invalid zero range",
                )
            )
            db_session.flush()

    # G: ThongBao unique khoaChongTrung
    nkey = f"ACC_L2:E{ids['expert_id']}:C1:V{v1.maViPham}"
    db_session.add(
        ThongBao(
            maNguoiNhan=ids["expert_uid"],
            loaiThongBao="ACCOUNTABILITY_WARNING",
            tieuDe="Cảnh báo vi phạm",
            noiDung="Đạt mốc 2 vi phạm",
            duLieuLienKet={"level": 2},
            khoaChongTrung=nkey,
        )
    )
    db_session.flush()
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(
                ThongBao(
                    maNguoiNhan=ids["expert_uid"],
                    loaiThongBao="ACCOUNTABILITY_WARNING",
                    tieuDe="Trùng",
                    noiDung="Trùng",
                    khoaChongTrung=nkey,
                )
            )
            db_session.flush()

    # H: KhoaHoc ck_KhoaHoc_visible_requires_approved (all 6 cases)
    q = chr(34)
    for st, vis, ok in [
        ("APPROVED", "VISIBLE", True),
        ("APPROVED", "HIDDEN", True),
        ("PENDING", "HIDDEN", True),
        ("PENDING", "VISIBLE", False),
        ("REJECTED", "VISIBLE", False),
        (None, "VISIBLE", False),
    ]:
        if ok:
            with db_session.begin_nested():
                db_session.execute(
                    text(f"UPDATE {q}KhoaHoc{q} SET {q}trangThaiDuyet{q}=:st, {q}trangThaiHienThi{q}=:vis WHERE {q}maKhoaHoc{q}=28"),
                    {"st": st, "vis": vis},
                )
        else:
            with pytest.raises(IntegrityError):
                with db_session.begin_nested():
                    db_session.execute(
                        text(f"UPDATE {q}KhoaHoc{q} SET {q}trangThaiDuyet{q}=:st, {q}trangThaiHienThi{q}=:vis WHERE {q}maKhoaHoc{q}=28"),
                        {"st": st, "vis": vis},
                    )


# ---------------------------------------------------------------------------
# Section 26: 7 Real Multi-Connection PostgreSQL Concurrency Tests
# ---------------------------------------------------------------------------


def _run_two_concurrent(fn1, fn2):
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(fn1)
        f2 = pool.submit(fn2)
        return [f1.result(), f2.result()]


def test_concurrency_all_7_unique_invariants_on_real_postgres():
    setup_db = TestSession()
    ids = _base_ids(setup_db)
    setup_db.close()
    now = _now_utc()
    created_assignments: list[int] = []
    created_jobs: list[int] = []
    created_reviews: list[int] = []
    created_violations: list[int] = []
    created_notifs: list[int] = []

    try:
        # 1. Two concurrent active assignments on same course
        def _insert_course_assign():
            s = TestSession()
            try:
                row = PhanCongKiemDuyet(
                    maKhoaHoc=ids["course_id"],
                    maChuyenGia=ids["expert_id"],
                    maDanhMuc=ids["cat_id"],
                    trangThai="ASSIGNED",
                    ngayPhanCong=now,
                    hanTiepNhan=now + timedelta(hours=24),
                )
                s.add(row)
                s.commit()
                created_assignments.append(row.maPhanCong)
                return "OK"
            except IntegrityError:
                s.rollback()
                return "CONFLICT"
            finally:
                s.close()

        assert sorted(_run_two_concurrent(_insert_course_assign, _insert_course_assign)) == ["CONFLICT", "OK"]

        # 2. Two concurrent active assignments on same material
        def _insert_mat_assign():
            s = TestSession()
            try:
                row = PhanCongKiemDuyet(
                    maTaiLieu=ids["mat_id"],
                    maChuyenGia=ids["expert_id"],
                    maDanhMuc=ids["cat_id"],
                    trangThai="ASSIGNED",
                    ngayPhanCong=now,
                    hanTiepNhan=now + timedelta(hours=24),
                )
                s.add(row)
                s.commit()
                created_assignments.append(row.maPhanCong)
                return "OK"
            except IntegrityError:
                s.rollback()
                return "CONFLICT"
            finally:
                s.close()

        assert sorted(_run_two_concurrent(_insert_mat_assign, _insert_mat_assign)) == ["CONFLICT", "OK"]

        # 3. Two concurrent open jobs on same course (different keys)
        def _insert_open_job(suffix: str):
            s = TestSession()
            try:
                row = HangDoiPhanCong(
                    loaiDoiTuong="COURSE",
                    maKhoaHoc=ids["course_id"],
                    soVongKiemDuyet=1,
                    loaiSuKien="SUBMIT",
                    khoaChongTrung=f"CONC_OPEN:{uuid.uuid4().hex[:8]}:{suffix}",
                    trangThai="PENDING",
                )
                s.add(row)
                s.commit()
                created_jobs.append(row.maCongViec)
                return "OK"
            except IntegrityError:
                s.rollback()
                return "CONFLICT"
            finally:
                s.close()

        assert sorted(_run_two_concurrent(lambda: _insert_open_job("A"), lambda: _insert_open_job("B"))) == ["CONFLICT", "OK"]

        # 4. Two concurrent jobs with same idempotency key on material
        shared_key = f"CONC_KEY:{uuid.uuid4().hex[:8]}"

        def _insert_same_key_job():
            s = TestSession()
            try:
                row = HangDoiPhanCong(
                    loaiDoiTuong="MATERIAL",
                    maTaiLieu=ids["mat_id"],
                    soVongKiemDuyet=1,
                    loaiSuKien="SUBMIT",
                    khoaChongTrung=shared_key,
                    trangThai="PENDING",
                )
                s.add(row)
                s.commit()
                created_jobs.append(row.maCongViec)
                return "OK"
            except IntegrityError:
                s.rollback()
                return "CONFLICT"
            finally:
                s.close()

        assert sorted(_run_two_concurrent(_insert_same_key_job, _insert_same_key_job)) == ["CONFLICT", "OK"]

        # 5. Two concurrent violations on same assignment
        target_assign_id = created_assignments[0]

        def _insert_violation():
            s = TestSession()
            try:
                row = ViPhamChuyenGia(
                    maChuyenGia=ids["expert_id"],
                    maPhanCong=target_assign_id,
                    loaiViPham="DECLINED_ASSIGNMENT",
                    chuKyKyLuatSo=1,
                )
                s.add(row)
                s.commit()
                created_violations.append(row.maViPham)
                return "OK"
            except IntegrityError:
                s.rollback()
                return "CONFLICT"
            finally:
                s.close()

        assert sorted(_run_two_concurrent(_insert_violation, _insert_violation)) == ["CONFLICT", "OK"]

        # 6. Two concurrent review results on same assignment
        def _insert_review():
            s = TestSession()
            try:
                row = DanhGiaChuyenGia(
                    maKhoaHoc=ids["course_id"],
                    maChuyenGia=ids["expert_id"],
                    maPhanCong=target_assign_id,
                    trangThai="APPROVED",
                    ngayTao=now,
                )
                s.add(row)
                s.commit()
                created_reviews.append(row.maDanhGia)
                return "OK"
            except IntegrityError:
                s.rollback()
                return "CONFLICT"
            finally:
                s.close()

        assert sorted(_run_two_concurrent(_insert_review, _insert_review)) == ["CONFLICT", "OK"]

        # 7. Two concurrent notifications with same khoaChongTrung
        shared_nkey = f"CONC_NOTIF:{uuid.uuid4().hex[:8]}"

        def _insert_notif():
            s = TestSession()
            try:
                row = ThongBao(
                    maNguoiNhan=ids["expert_uid"],
                    loaiThongBao="TEST",
                    tieuDe="Test",
                    noiDung="Test",
                    khoaChongTrung=shared_nkey,
                )
                s.add(row)
                s.commit()
                created_notifs.append(row.maThongBao)
                return "OK"
            except IntegrityError:
                s.rollback()
                return "CONFLICT"
            finally:
                s.close()

        assert sorted(_run_two_concurrent(_insert_notif, _insert_notif)) == ["CONFLICT", "OK"]
    finally:
        # Clean up ONLY synthetic fixtures in exact reverse FK order on EduSuggest_phase3_test
        cs = TestSession()
        try:
            assert cs.execute(text("SELECT current_database()")).scalar() == "EduSuggest_phase3_test"
            for nid in created_notifs:
                obj = cs.get(ThongBao, nid)
                if obj:
                    cs.delete(obj)
            for vid in created_violations:
                obj = cs.get(ViPhamChuyenGia, vid)
                if obj:
                    cs.delete(obj)
            for rid in created_reviews:
                obj = cs.get(DanhGiaChuyenGia, rid)
                if obj:
                    cs.delete(obj)
            for jid in created_jobs:
                obj = cs.get(HangDoiPhanCong, jid)
                if obj:
                    cs.delete(obj)
            cs.flush()
            for aid in created_assignments:
                obj = cs.get(PhanCongKiemDuyet, aid)
                if obj:
                    cs.delete(obj)
            cs.commit()
        finally:
            cs.close()
