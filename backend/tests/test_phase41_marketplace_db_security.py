"""GĐ4.1 PostgreSQL security, constraint, grandfathering, and concurrency tests.

Strictly runs ONLY against EduSuggest_phase4_test (refuses to run on EduSuggest).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
import uuid

import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from config.config import get_settings
from models import (
    BaiHoc,
    ChiTietDonHang,
    ChiTietGioHang,
    DangKyKhoaHoc,
    DanhMuc,
    DonHang,
    GioHang,
    KhoaHoc,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    TaiLieu,
    ThanhToan,
    VaiTro,
    YeuThich,
)
from repository import workflow_repository
from service import private_material_service, recommendation_service, workflow_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
    WorkflowPaymentRequiredError,
)


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ4.1 tests require EduSuggest_phase4_test database.")
    return raw


@pytest.fixture(scope="module")
def pg_engine():
    url = _phase4_test_url()
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        assert db_name == "EduSuggest_phase4_test", f"Refusing to run on {db_name}"
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert rev in {"d4e5f6a7b8c9", "e5f6a7b8c9d0"}, f"Unexpected revision {rev}"
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _create_temp_user(db: Session, role_name: str = "USER") -> NguoiDung:
    role = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == role_name)).first()
    assert role is not None
    tag = uuid.uuid4().hex[:8]
    user = NguoiDung(
        maVaiTro=role.maVaiTro,
        tenTaiKhoan=f"p4test_{tag}",
        hoTen=f"Phase4 Test {tag}",
        email=f"p4test_{tag}@example.test",
        matKhau="argon2-placeholder",
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    db.add(user)
    db.flush()
    return user


def _create_temp_course(
    db: Session,
    *,
    provider_id: int,
    category_id: int,
    gia: Decimal | None,
    approval: str = "APPROVED",
    visibility: str = "VISIBLE",
) -> tuple[KhoaHoc, BaiHoc]:
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(UTC).replace(tzinfo=None)
    course = KhoaHoc(
        maNhaCungCap=provider_id,
        maDanhMuc=category_id,
        tieuDe=f"Phase4 Test Course {tag}",
        moTa="Khóa học kiểm thử bảo mật thương mại GĐ4.1",
        gia=gia,
        trinhDo="Beginner",
        thoiLuong=60,
        trangThaiDuyet=approval,
        trangThaiHienThi=visibility,
        ngayTao=now,
        ngayCapNhat=now,
    )
    db.add(course)
    db.flush()
    lesson = BaiHoc(
        maKhoaHoc=course.maKhoaHoc,
        tieuDe=f"Bài 1 - {tag}",
        noiDung="Nội dung kiểm thử bài học",
        thoiLuong=15,
        thuTu=1,
        ngayTao=now,
    )
    db.add(lesson)
    db.flush()
    return course, lesson


@pytest.fixture
def isolated_fixtures(pg_engine):
    """Create temporary test user, provider/category refs, and courses; clean up after test."""
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    created_course_ids: list[int] = []
    created_lesson_ids: list[int] = []
    created_material_ids: list[int] = []
    created_user_ids: list[int] = []
    created_order_ids: list[int] = []

    try:
        provider_id = db.scalar(select(NhaCungCapKhoaHoc.maNhaCungCap).limit(1))
        category_id = db.scalar(select(DanhMuc.maDanhMuc).limit(1))
        assert provider_id is not None and category_id is not None

        user = _create_temp_user(db, "USER")
        created_user_ids.append(user.maNguoiDung)

        free_course, free_lesson = _create_temp_course(
            db, provider_id=provider_id, category_id=category_id, gia=Decimal("0")
        )
        paid_course, paid_lesson = _create_temp_course(
            db, provider_id=provider_id, category_id=category_id, gia=Decimal("499000")
        )
        null_price_course, null_lesson = _create_temp_course(
            db, provider_id=provider_id, category_id=category_id, gia=None
        )
        hidden_course, hidden_lesson = _create_temp_course(
            db,
            provider_id=provider_id,
            category_id=category_id,
            gia=Decimal("0"),
            approval="PENDING",
            visibility="HIDDEN",
        )
        for c, l in (
            (free_course, free_lesson),
            (paid_course, paid_lesson),
            (null_price_course, null_lesson),
            (hidden_course, hidden_lesson),
        ):
            created_course_ids.append(c.maKhoaHoc)
            created_lesson_ids.append(l.maBaiHoc)

        db.commit()
        yield {
            "SessionLocal": SessionLocal,
            "user_id": user.maNguoiDung,
            "provider_id": provider_id,
            "category_id": category_id,
            "free_course_id": free_course.maKhoaHoc,
            "free_lesson_id": free_lesson.maBaiHoc,
            "paid_course_id": paid_course.maKhoaHoc,
            "paid_lesson_id": paid_lesson.maBaiHoc,
            "null_price_course_id": null_price_course.maKhoaHoc,
            "hidden_course_id": hidden_course.maKhoaHoc,
            "created_order_ids": created_order_ids,
            "created_material_ids": created_material_ids,
        }
    finally:
        db.rollback()
        # Clean in strict FK order
        if created_user_ids:
            db.execute(delete(LichSuHocTap).where(LichSuHocTap.maNguoiDung.in_(created_user_ids)))
            db.execute(delete(DangKyKhoaHoc).where(DangKyKhoaHoc.maNguoiDung.in_(created_user_ids)))
            db.execute(delete(YeuThich).where(YeuThich.maNguoiDung.in_(created_user_ids)))
            cart_ids = list(
                db.scalars(select(GioHang.maGioHang).where(GioHang.maNguoiDung.in_(created_user_ids)))
            )
            if cart_ids:
                db.execute(delete(ChiTietGioHang).where(ChiTietGioHang.maGioHang.in_(cart_ids)))
                db.execute(delete(GioHang).where(GioHang.maGioHang.in_(cart_ids)))
            order_ids = list(
                db.scalars(select(DonHang.maDonHang).where(DonHang.maNguoiDung.in_(created_user_ids)))
            )
            all_order_ids = list(set(order_ids + created_order_ids))
            if all_order_ids:
                db.execute(delete(ThanhToan).where(ThanhToan.maDonHang.in_(all_order_ids)))
                db.execute(delete(ChiTietDonHang).where(ChiTietDonHang.maDonHang.in_(all_order_ids)))
                db.execute(delete(DonHang).where(DonHang.maDonHang.in_(all_order_ids)))
        if created_material_ids:
            db.execute(delete(TaiLieu).where(TaiLieu.maTaiLieu.in_(created_material_ids)))
        if created_lesson_ids:
            db.execute(delete(BaiHoc).where(BaiHoc.maBaiHoc.in_(created_lesson_ids)))
        if created_course_ids:
            db.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(created_course_ids)))
        if created_user_ids:
            db.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(created_user_ids)))
        db.commit()
        db.close()


def _enable_commerce_gate(monkeypatch, enabled: bool) -> None:
    monkeypatch.setenv("COMMERCE_ENROLLMENT_GATE_ENABLED", "true" if enabled else "false")
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# 1. COM-01 & COM-03: Free vs Paid vs NULL vs Hidden/Unapproved Enrollment
# ---------------------------------------------------------------------------
def test_com01_free_allowed_paid_null_hidden_blocked(isolated_fixtures, monkeypatch):
    _enable_commerce_gate(monkeypatch, True)
    try:
        db = isolated_fixtures["SessionLocal"]()
        uid = isolated_fixtures["user_id"]

        # Free course (gia == 0) succeeds and records nguonCapQuyen='FREE'
        enr = workflow_service.enroll_user_in_course(db, uid, isolated_fixtures["free_course_id"])
        assert enr.trangThaiQuyenHoc == "ACTIVE"
        assert enr.nguonCapQuyen == "FREE"
        assert enr.maDonHang is None

        # Paid course (gia > 0) is strictly blocked with WorkflowPaymentRequiredError
        with pytest.raises(WorkflowPaymentRequiredError):
            workflow_service.enroll_user_in_course(db, uid, isolated_fixtures["paid_course_id"])
        assert workflow_repository.get_enrollment(
            db, uid, isolated_fixtures["paid_course_id"], active_only=False
        ) is None

        # NULL price course is NOT treated as free (fail-closed)
        with pytest.raises(WorkflowConflictError):
            workflow_service.enroll_user_in_course(db, uid, isolated_fixtures["null_price_course_id"])

        # Hidden / unapproved course is blocked
        with pytest.raises(WorkflowNotFoundError):
            workflow_service.enroll_user_in_course(db, uid, isolated_fixtures["hidden_course_id"])
        db.close()
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# 2. COM-03: Negative course price blocked at PostgreSQL CHECK constraint
# ---------------------------------------------------------------------------
def test_com03_negative_course_price_rejected_by_db(isolated_fixtures):
    db = isolated_fixtures["SessionLocal"]()
    try:
        bad_course = KhoaHoc(
            maNhaCungCap=isolated_fixtures["provider_id"],
            maDanhMuc=isolated_fixtures["category_id"],
            tieuDe="Negative Price Test",
            gia=Decimal("-1000"),
            trangThaiDuyet="DRAFT",
            trangThaiHienThi="HIDDEN",
        )
        db.add(bad_course)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. COM-02: Concurrent enrollment race + DB UNIQUE (maNguoiDung, maKhoaHoc)
# ---------------------------------------------------------------------------
def test_com02_concurrent_enrollment_no_duplicate(isolated_fixtures, monkeypatch):
    _enable_commerce_gate(monkeypatch, True)
    try:
        SessionLocal = isolated_fixtures["SessionLocal"]
        uid = isolated_fixtures["user_id"]
        cid = isolated_fixtures["free_course_id"]

        def _worker(_):
            s = SessionLocal()
            try:
                workflow_service.enroll_user_in_course(s, uid, cid)
                return "OK"
            except WorkflowConflictError:
                return "CONFLICT"
            finally:
                s.close()

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(_worker, range(6)))

        assert results.count("OK") == 1
        assert results.count("CONFLICT") == 5

        # Direct DB duplicate insert must also fail on uq_DangKyKhoaHoc_user_course
        db = SessionLocal()
        try:
            dup = DangKyKhoaHoc(
                maNguoiDung=uid,
                maKhoaHoc=cid,
                ngayDangKy=datetime.now(UTC).replace(tzinfo=None),
                tienDo=Decimal("0"),
                nguonCapQuyen="FREE",
                trangThaiQuyenHoc="ACTIVE",
            )
            db.add(dup)
            with pytest.raises(IntegrityError):
                db.flush()
            db.rollback()
        finally:
            db.close()
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# 4. Wishlist & Cart DB Constraints (Unique ownership & duplicate items)
# ---------------------------------------------------------------------------
def test_wishlist_and_cart_constraints(isolated_fixtures):
    db = isolated_fixtures["SessionLocal"]()
    uid = isolated_fixtures["user_id"]
    paid_cid = isolated_fixtures["paid_course_id"]
    try:
        # Wishlist duplicate rejected
        db.add(YeuThich(maNguoiDung=uid, maKhoaHoc=paid_cid))
        db.flush()
        db.add(YeuThich(maNguoiDung=uid, maKhoaHoc=paid_cid))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

        # Cart 1-per-user ownership constraint
        cart = GioHang(maNguoiDung=uid)
        db.add(cart)
        db.flush()
        db.add(GioHang(maNguoiDung=uid))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

        # Cart item duplicate & invalid giaLucThem <= 0
        cart = GioHang(maNguoiDung=uid)
        db.add(cart)
        db.flush()
        db.add(ChiTietGioHang(maGioHang=cart.maGioHang, maKhoaHoc=paid_cid, giaLucThem=Decimal("499000")))
        db.flush()
        db.add(ChiTietGioHang(maGioHang=cart.maGioHang, maKhoaHoc=paid_cid, giaLucThem=Decimal("499000")))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

        cart2 = GioHang(maNguoiDung=uid)
        db.add(cart2)
        db.flush()
        db.add(ChiTietGioHang(maGioHang=cart2.maGioHang, maKhoaHoc=paid_cid, giaLucThem=Decimal("0")))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Order & Payment Idempotency, Invalid Monetary Values & ON DELETE RESTRICT
# ---------------------------------------------------------------------------
def test_order_payment_idempotency_monetary_and_restrict(isolated_fixtures):
    db = isolated_fixtures["SessionLocal"]()
    uid = isolated_fixtures["user_id"]
    paid_cid = isolated_fixtures["paid_course_id"]
    provider_id = isolated_fixtures["provider_id"]
    now = datetime.now(UTC).replace(tzinfo=None)
    ttl = now + timedelta(minutes=15)
    tag = uuid.uuid4().hex[:8]
    try:
        # Invalid monetary value (tongTien = 0) rejected
        db.add(
            DonHang(
                maSoDonHang=f"ORD-BAD-{tag}",
                maNguoiDung=uid,
                nguonTao="CART",
                tongTien=Decimal("0"),
                donViTienTe="VND",
                trangThai="PENDING",
                khoaChongTrung=f"idem-bad-{tag}",
                hanThanhToan=ttl,
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

        # Invalid currency ('USD') rejected
        db.add(
            DonHang(
                maSoDonHang=f"ORD-USD-{tag}",
                maNguoiDung=uid,
                nguonTao="CART",
                tongTien=Decimal("499000"),
                donViTienTe="USD",
                trangThai="PENDING",
                khoaChongTrung=f"idem-usd-{tag}",
                hanThanhToan=ttl,
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

        # Valid order + snapshot item
        order = DonHang(
            maSoDonHang=f"ORD-OK-{tag}",
            maNguoiDung=uid,
            nguonTao="BUY_NOW",
            tongTien=Decimal("499000"),
            donViTienTe="VND",
            trangThai="PENDING",
            khoaChongTrung=f"idem-ok-{tag}",
            hanThanhToan=ttl,
        )
        db.add(order)
        db.flush()
        isolated_fixtures["created_order_ids"].append(order.maDonHang)

        db.add(
            ChiTietDonHang(
                maDonHang=order.maDonHang,
                maKhoaHoc=paid_cid,
                maNhaCungCap=provider_id,
                tieuDeSnapshot="Snapshot Course Title",
                giaTaiThoiDiemMua=Decimal("499000"),
            )
        )
        db.commit()

        # Duplicate order idempotency key rejected
        db.add(
            DonHang(
                maSoDonHang=f"ORD-DUP-{tag}",
                maNguoiDung=uid,
                nguonTao="BUY_NOW",
                tongTien=Decimal("499000"),
                donViTienTe="VND",
                trangThai="PENDING",
                khoaChongTrung=f"idem-ok-{tag}",
                hanThanhToan=ttl,
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

        # Multiple FAILED payments allowed, then 1 PAID allowed, 2nd PAID rejected by partial unique index
        db.add(
            ThanhToan(
                maDonHang=order.maDonHang,
                maNguoiDung=uid,
                congThanhToan="MOCK_SANDBOX",
                maGiaoDichNoiBo=f"TXN-F1-{tag}",
                soTien=Decimal("499000"),
                donViTienTe="VND",
                trangThai="FAILED",
                khoaChongTrung=f"pay-f1-{tag}",
            )
        )
        db.add(
            ThanhToan(
                maDonHang=order.maDonHang,
                maNguoiDung=uid,
                congThanhToan="MOCK_SANDBOX",
                maGiaoDichNoiBo=f"TXN-P1-{tag}",
                maGiaoDichCong=f"GW-P1-{tag}",
                soTien=Decimal("499000"),
                donViTienTe="VND",
                trangThai="PAID",
                khoaChongTrung=f"pay-p1-{tag}",
                daXacMinhChuKy=True,
                ngayThanhToan=now,
            )
        )
        db.commit()

        # 2nd PAID payment for the SAME order must fail uq_ThanhToan_one_paid_per_order
        db.add(
            ThanhToan(
                maDonHang=order.maDonHang,
                maNguoiDung=uid,
                congThanhToan="MOCK_SANDBOX",
                maGiaoDichNoiBo=f"TXN-P2-{tag}",
                maGiaoDichCong=f"GW-P2-{tag}",
                soTien=Decimal("499000"),
                donViTienTe="VND",
                trangThai="PAID",
                khoaChongTrung=f"pay-p2-{tag}",
                daXacMinhChuKy=True,
                ngayThanhToan=now,
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

        # ON DELETE RESTRICT prevents deleting a course that has order history
        with pytest.raises(IntegrityError):
            db.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc == paid_cid))
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 6. Legacy Grandfathering: All 150 pre-existing enrollments remain ACTIVE
# ---------------------------------------------------------------------------
def test_legacy_enrollments_preserved_and_accessible_when_gate_enabled(db_session, monkeypatch):
    _enable_commerce_gate(monkeypatch, True)
    try:
        rows = db_session.execute(
            text(
                'SELECT COUNT(*), '
                'COUNT(*) FILTER (WHERE "trangThaiQuyenHoc" = \'ACTIVE\'), '
                'COUNT(*) FILTER (WHERE "nguonCapQuyen" = \'LEGACY\'), '
                'COUNT(*) FILTER (WHERE "maDonHang" IS NULL) '
                'FROM "DangKyKhoaHoc"'
            )
        ).one()
        total, active_cnt, legacy_cnt, null_order_cnt = rows
        assert total >= 150
        assert active_cnt == total
        assert legacy_cnt >= 150
        assert null_order_cnt >= 150

        # Pick an existing paid-course legacy enrollment and verify learning access still works
        sample = db_session.execute(
            text(
                'SELECT d."maNguoiDung", d."maKhoaHoc" '
                'FROM "DangKyKhoaHoc" d '
                'JOIN "KhoaHoc" k ON k."maKhoaHoc" = d."maKhoaHoc" '
                'WHERE k."gia" > 0 AND k."trangThaiDuyet" = \'APPROVED\' AND k."trangThaiHienThi" = \'VISIBLE\' '
                'AND d."nguonCapQuyen" = \'LEGACY\' '
                'LIMIT 1'
            )
        ).first()
        assert sample is not None
        legacy_uid, legacy_cid = sample
        course, _completed = workflow_service.get_user_learning_course(db_session, legacy_uid, legacy_cid)
        assert course.maKhoaHoc == legacy_cid
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# 7. REVOKED entitlement blocks private content & preserves LichSuHocTap
# ---------------------------------------------------------------------------
def test_revoked_entitlement_blocks_access_preserves_history_and_allows_reactivation(isolated_fixtures):
    db = isolated_fixtures["SessionLocal"]()
    uid = isolated_fixtures["user_id"]
    cid = isolated_fixtures["paid_course_id"]
    lid = isolated_fixtures["paid_lesson_id"]
    provider_id = isolated_fixtures["provider_id"]
    category_id = isolated_fixtures["category_id"]
    now = datetime.now(UTC).replace(tzinfo=None)
    ttl = now + timedelta(minutes=15)
    tag = uuid.uuid4().hex[:8]

    try:
        # Attach an approved visible private material to the paid course
        mat = TaiLieu(
            maNhaCungCap=provider_id,
            maKhoaHoc=cid,
            maBaiHoc=lid,
            maDanhMuc=category_id,
            tieuDe=f"Private Material {tag}",
            duongDanTep=f"private://materials/nonexistent-{tag}.pdf",
            loai="PDF",
            trangThaiDuyet="APPROVED",
            trangThaiHienThi="VISIBLE",
            ngayTao=now,
        )
        db.add(mat)
        db.flush()
        isolated_fixtures["created_material_ids"].append(mat.maTaiLieu)

        # Simulate Order #1 PAID -> ACTIVE enrollment
        order1 = DonHang(
            maSoDonHang=f"ORD-R1-{tag}",
            maNguoiDung=uid,
            nguonTao="BUY_NOW",
            tongTien=Decimal("499000"),
            donViTienTe="VND",
            trangThai="PAID",
            khoaChongTrung=f"idem-r1-{tag}",
            hanThanhToan=ttl,
            ngayThanhToan=now,
        )
        db.add(order1)
        db.flush()
        isolated_fixtures["created_order_ids"].append(order1.maDonHang)

        enrollment = DangKyKhoaHoc(
            maNguoiDung=uid,
            maKhoaHoc=cid,
            ngayDangKy=now,
            tienDo=Decimal("100"),
            ngayHoanThanh=now,
            maDonHang=order1.maDonHang,
            nguonCapQuyen="PURCHASE",
            trangThaiQuyenHoc="ACTIVE",
        )
        db.add(enrollment)
        db.flush()

        history = LichSuHocTap(
            maNguoiDung=uid,
            maKhoaHoc=cid,
            maBaiHoc=lid,
            tienDo="COMPLETED",
            ngayTao=now,
        )
        db.add(history)
        db.commit()

        # Verify ACTIVE enrollment can access course lessons
        course_ok, completed_ok = workflow_service.get_user_learning_course(db, uid, cid)
        assert course_ok.maKhoaHoc == cid
        assert lid in completed_ok

        # Simulate confirmed REFUND on Order #1 -> REVOKE entitlement without deleting enrollment or history
        order1.trangThai = "REFUNDED"
        order1.ngayHoanTien = now
        order1.lyDoHuyHoacHoan = "Kiểm thử hoàn tiền GĐ4.1"
        enrollment.trangThaiQuyenHoc = "REVOKED"
        enrollment.ngayThuHoi = now
        enrollment.lyDoThuHoi = "Thu hồi do đơn hàng hoàn tiền"
        db.commit()

        # REVOKED user MUST be blocked from lessons, lesson completion, materials recommendation, and private file
        with pytest.raises(WorkflowForbiddenError):
            workflow_service.get_user_learning_course(db, uid, cid)
        with pytest.raises(WorkflowForbiddenError):
            workflow_service.complete_user_lesson(db, uid, cid, lid)
        with pytest.raises(WorkflowForbiddenError):
            recommendation_service.recommend_materials(db, uid, cid, lid, limit=5)

        user_obj = db.get(NguoiDung, uid)
        with pytest.raises(WorkflowForbiddenError):
            private_material_service.authorize_private_file(db, user=user_obj, material_id=mat.maTaiLieu)

        # REVOKED enrollment is excluded from active enrollments list, but LichSuHocTap & tienDo remain preserved!
        assert workflow_repository.list_enrollments(db, uid) == []
        preserved_history = workflow_repository.list_learning_history(db, uid)
        assert any(h.maBaiHoc == lid and h.tienDo == "COMPLETED" for h in preserved_history)
        db.refresh(enrollment)
        assert Decimal(enrollment.tienDo) == Decimal("100")

        # Re-purchase via Order #2 -> reactivates the SAME DangKyKhoaHoc row cleanly without losing progress
        order2 = DonHang(
            maSoDonHang=f"ORD-R2-{tag}",
            maNguoiDung=uid,
            nguonTao="BUY_NOW",
            tongTien=Decimal("499000"),
            donViTienTe="VND",
            trangThai="PAID",
            khoaChongTrung=f"idem-r2-{tag}",
            hanThanhToan=ttl,
            ngayThanhToan=now,
        )
        db.add(order2)
        db.flush()
        isolated_fixtures["created_order_ids"].append(order2.maDonHang)

        enrollment.maDonHang = order2.maDonHang
        enrollment.nguonCapQuyen = "PURCHASE"
        enrollment.trangThaiQuyenHoc = "ACTIVE"
        enrollment.ngayThuHoi = None
        enrollment.lyDoThuHoi = None
        db.commit()

        course_restored, completed_restored = workflow_service.get_user_learning_course(db, uid, cid)
        assert course_restored.maKhoaHoc == cid
        assert lid in completed_restored
        assert Decimal(enrollment.tienDo) == Decimal("100")
    finally:
        db.close()
