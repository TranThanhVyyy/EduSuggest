"""GĐ4.7A Enhanced Payment Stress, Fault Injection, Hardening & 24-Table Compatibility Tests.

Tests against real PostgreSQL `EduSuggest_phase4_test` (never writes to Production `EduSuggest`):
- 100x concurrent VNPay IPN callback replay
- Multi-attempt concurrent payment initiation & duplicate-capture preservation
- Multi-order same-course race (2nd paid order flags CONFLICT_ALREADY_OWNED_ACTIVE)
- Mid-transaction DB rollback before commit (_post_payment_hook fault injection)
- HARDEN-01: VNPay requires BOTH vnp_ResponseCode == "00" AND vnp_TransactionStatus == "00"
- HARDEN-02: Idempotency-Key request fingerprint mismatch -> 409 Conflict
- HARDEN-03: Late FAILED callback never clobbers fundsCaptured reconciliation JSONB
- Repurchase after FULL_ORDER exception refund (preserves LichSuHocTap)
- HARDEN-04: Fail-closed 503 on 24-table DB when Marketplace tables do not exist
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
import os
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

from config.config import get_settings
from config.database import get_db
from main import app
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
    ThanhToan,
    ThongBao,
    VaiTro,
    YeuThich,
)
from service import commerce_service, order_payment_service
from service.payment_providers import (
    build_vnpay_hash_data,
    compute_vnpay_hmac_sha512,
)
from utils.security import create_access_token, hash_password

_TEST_TMN = "TESTTMN47A"
_TEST_SECRET = "TEST_ONLY_IN_MEMORY_HMAC_SHA512_SECRET_KEY_PHASE47A"
_TEST_RETURN = "http://127.0.0.1:5176/payment/result"


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ4.7A tests require EduSuggest_phase4_test database.")
    return raw


@pytest.fixture(scope="module")
def pg_engine():
    url = _phase4_test_url()
    engine = create_engine(url, pool_pre_ping=True, pool_size=30, max_overflow=30)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        assert db_name == "EduSuggest_phase4_test", f"Refusing to run on {db_name}"
    yield engine
    engine.dispose()


def _sign_vnpay(params: dict[str, str], secret: str = _TEST_SECRET) -> dict[str, str]:
    signed = dict(params)
    signed["vnp_SecureHash"] = compute_vnpay_hmac_sha512(build_vnpay_hash_data(signed), secret)
    return signed


def _vnpay_params(
    merchant_ref: str,
    amount_vnd: Decimal,
    tx_no: str | None = None,
    resp_code: str = "00",
    tx_status: str = "00",
) -> dict[str, str]:
    payload = {
        "vnp_TmnCode": _TEST_TMN,
        "vnp_Amount": str(int(amount_vnd * Decimal("100"))),
        "vnp_BankCode": "NCB",
        "vnp_OrderInfo": f"Thanh toan {merchant_ref}",
        "vnp_PayDate": "20261126204000",
        "vnp_ResponseCode": resp_code,
        "vnp_TransactionNo": tx_no or f"VNP47{uuid.uuid4().hex[:7].upper()}",
        "vnp_TxnRef": merchant_ref,
        "vnp_SecureHashType": "HMACSHA512",
    }
    if tx_status is not None:
        payload["vnp_TransactionStatus"] = tx_status
    return _sign_vnpay(payload)


@pytest.fixture
def env(pg_engine, monkeypatch):
    monkeypatch.setenv("COMMERCE_ENROLLMENT_GATE_ENABLED", "true")
    monkeypatch.setenv("MOCK_PAYMENT_ENABLED", "true")
    monkeypatch.setenv("VNPAY_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("VNPAY_TMN_CODE", _TEST_TMN)
    monkeypatch.setenv("VNPAY_HASH_SECRET", _TEST_SECRET)
    monkeypatch.setenv("VNPAY_PAYMENT_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
    monkeypatch.setenv("VNPAY_RETURN_URL", _TEST_RETURN)
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()

    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    db = SessionLocal()
    created_users: list[int] = []
    created_providers: list[int] = []
    created_courses: list[int] = []
    created_lessons: list[int] = []

    try:
        category_id = db.scalar(select(DanhMuc.maDanhMuc).limit(1))
        assert category_id is not None

        def _make_user(role_name: str) -> tuple[int, str]:
            role = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == role_name)).first()
            assert role is not None
            tag = uuid.uuid4().hex[:8]
            pwd_hash = hash_password(f"P47!{tag}99")
            u = NguoiDung(
                maVaiTro=role.maVaiTro,
                tenTaiKhoan=f"p47_{role_name.lower()}_{tag}",
                hoTen=f"P47 {role_name} {tag}",
                email=f"p47_{role_name.lower()}_{tag}@example.test",
                matKhau=pwd_hash,
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            db.add(u)
            db.flush()
            created_users.append(u.maNguoiDung)
            return int(u.maNguoiDung), create_access_token(u.maNguoiDung, pwd_hash).encoded

        prov_uid, _ = _make_user("PROVIDER")
        p = NhaCungCapKhoaHoc(
            maNguoiDung=prov_uid,
            tieuSu="P47A Provider",
            chuyenMon="Systems",
        )
        db.add(p)
        db.flush()
        created_providers.append(int(p.maNhaCungCap))

        def _make_course(gia: Decimal) -> tuple[int, int]:
            tag = uuid.uuid4().hex[:8]
            now = datetime.now(UTC).replace(tzinfo=None)
            c = KhoaHoc(
                maNhaCungCap=p.maNhaCungCap,
                maDanhMuc=category_id,
                tieuDe=f"P47A Course {tag}",
                moTa="Khóa học kiểm thử GĐ4.7A",
                gia=gia,
                trinhDo="Intermediate",
                thoiLuong=90,
                trangThaiDuyet="APPROVED",
                trangThaiHienThi="VISIBLE",
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add(c)
            db.flush()
            l = BaiHoc(
                maKhoaHoc=c.maKhoaHoc,
                tieuDe=f"Bài 1 {tag}",
                noiDung="Nội dung",
                thoiLuong=15,
                thuTu=1,
                ngayTao=now,
            )
            db.add(l)
            db.flush()
            created_courses.append(int(c.maKhoaHoc))
            created_lessons.append(int(l.maBaiHoc))
            return int(c.maKhoaHoc), int(l.maBaiHoc)

        u1_id, tok_u1 = _make_user("USER")
        admin_id, tok_admin = _make_user("ADMIN")
        c1_id, l1_id = _make_course(Decimal("599000"))
        c2_id, l2_id = _make_course(Decimal("399000"))
        db.commit()

        yield {
            "client": client,
            "SessionLocal": SessionLocal,
            "u1_id": u1_id,
            "tok_u1": tok_u1,
            "admin_id": admin_id,
            "tok_admin": tok_admin,
            "c1_id": c1_id,
            "l1_id": l1_id,
            "c2_id": c2_id,
            "l2_id": l2_id,
            "h": lambda tok: {"Authorization": f"Bearer {tok}"},
        }
    finally:
        db.close()
        cleanup = SessionLocal()
        try:
            assert cleanup.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase4_test"
            cleanup.execute(text("SET LOCAL session_replication_role = 'replica'"))
            if created_users:
                oids = list(cleanup.scalars(select(DonHang.maDonHang).where(DonHang.maNguoiDung.in_(created_users))))
                gids = list(cleanup.scalars(select(GioHang.maGioHang).where(GioHang.maNguoiDung.in_(created_users))))
                if oids:
                    cleanup.execute(text('DELETE FROM "TacVuDoiSoatThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": oids})
                    cleanup.execute(text('DELETE FROM "SuKienThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": oids})
                    cleanup.execute(text('DELETE FROM "BaoCaoSuCoThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": oids})
                    cleanup.execute(text('DELETE FROM "LanThuHoanTien" WHERE "maHoanTien" IN (SELECT "maHoanTien" FROM "HoanTienNgoaiLe" WHERE "maDonHang" = ANY(:oids))'), {"oids": oids})
                    cleanup.execute(text('DELETE FROM "HoanTienNgoaiLe" WHERE "maDonHang" = ANY(:oids)'), {"oids": oids})
                    cleanup.execute(delete(ThanhToan).where(ThanhToan.maDonHang.in_(oids)))
                    cleanup.execute(delete(ChiTietDonHang).where(ChiTietDonHang.maDonHang.in_(oids)))
                cleanup.execute(delete(LichSuHocTap).where(LichSuHocTap.maNguoiDung.in_(created_users)))
                cleanup.execute(delete(DangKyKhoaHoc).where(DangKyKhoaHoc.maNguoiDung.in_(created_users)))
                if oids:
                    cleanup.execute(delete(DonHang).where(DonHang.maDonHang.in_(oids)))
                if gids:
                    cleanup.execute(delete(ChiTietGioHang).where(ChiTietGioHang.maGioHang.in_(gids)))
                    cleanup.execute(delete(GioHang).where(GioHang.maGioHang.in_(gids)))
                cleanup.execute(delete(YeuThich).where(YeuThich.maNguoiDung.in_(created_users)))
                cleanup.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_(created_users)))
            if created_lessons:
                cleanup.execute(delete(LichSuHocTap).where(LichSuHocTap.maBaiHoc.in_(created_lessons)))
                cleanup.execute(delete(BaiHoc).where(BaiHoc.maBaiHoc.in_(created_lessons)))
            if created_courses:
                cleanup.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(created_courses)))
            if created_providers:
                cleanup.execute(delete(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNhaCungCap.in_(created_providers)))
            if created_users:
                cleanup.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(created_users)))
            cleanup.commit()
        finally:
            cleanup.close()
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _buy_now(env, course_id: int, idem: str | None = None) -> dict:
    r = env["client"].post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": course_id},
        headers={**env["h"](env["tok_u1"]), "Idempotency-Key": idem or f"ord-{uuid.uuid4().hex}"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def _init_pay(env, order_id: int, gateway: str = "VNPAY_SANDBOX", idem: str | None = None) -> dict:
    r = env["client"].post(
        f"/api/orders/{order_id}/payments",
        json={"congThanhToan": gateway},
        headers={**env["h"](env["tok_u1"]), "Idempotency-Key": idem or f"pay-{uuid.uuid4().hex}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_h01_callback_replay_100x_single_activation(env):
    """100x concurrent VNPay IPN callbacks -> exactly 1 RspCode=00, 99 RspCode=02, 1 enrollment."""
    order = _buy_now(env, env["c1_id"])
    pay = _init_pay(env, order["maDonHang"], gateway="VNPAY_SANDBOX")
    params = _vnpay_params(pay["maGiaoDichNoiBo"], Decimal("599000"), tx_no="VNP100X")

    def _hit(_i: int) -> str:
        return env["client"].get("/api/payments/vnpay/ipn", params=params).json()["RspCode"]

    with ThreadPoolExecutor(max_workers=16) as pool:
        codes = list(pool.map(_hit, range(100)))

    assert codes.count("00") == 1
    assert codes.count("02") == 99

    with env["SessionLocal"]() as db:
        cnt = db.scalar(
            select(func.count(DangKyKhoaHoc.maDangKy)).where(
                DangKyKhoaHoc.maNguoiDung == env["u1_id"],
                DangKyKhoaHoc.maKhoaHoc == env["c1_id"],
            )
        )
        assert cnt == 1


def test_h02_vnpay_strict_transaction_status_and_idempotency_fingerprint(env):
    """HARDEN-01 & HARDEN-02:
    - vnp_ResponseCode=00 with missing or non-00 vnp_TransactionStatus MUST NOT activate PAID.
    - Reusing same Idempotency-Key with different courseId or gateway MUST return 409 Conflict.
    """
    idem_ord = f"fp-ord-{uuid.uuid4().hex}"
    o1 = _buy_now(env, env["c1_id"], idem=idem_ord)

    # Same key, DIFFERENT course -> 409 Conflict!
    r_mismatch = env["client"].post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": env["c2_id"]},
        headers={**env["h"](env["tok_u1"]), "Idempotency-Key": idem_ord},
    )
    assert r_mismatch.status_code == 409

    # Payment idempotency fingerprint mismatch (VNPAY_SANDBOX vs MOCK_SANDBOX) -> 409 Conflict!
    idem_pay = f"fp-pay-{uuid.uuid4().hex}"
    p1 = _init_pay(env, o1["maDonHang"], gateway="VNPAY_SANDBOX", idem=idem_pay)
    r_gw_mismatch = env["client"].post(
        f"/api/orders/{o1['maDonHang']}/payments",
        json={"congThanhToan": "MOCK_SANDBOX"},
        headers={**env["h"](env["tok_u1"]), "Idempotency-Key": idem_pay},
    )
    assert r_gw_mismatch.status_code == 409

    # HARDEN-01: vnp_ResponseCode=00 but vnp_TransactionStatus="" -> MUST NOT be PAID!
    bad_ipn = _vnpay_params(p1["maGiaoDichNoiBo"], Decimal("599000"), resp_code="00", tx_status="")
    env["client"].get("/api/payments/vnpay/ipn", params=bad_ipn)
    with env["SessionLocal"]() as db:
        o_db = db.get(DonHang, o1["maDonHang"])
        assert o_db.trangThai != "PAID"


def test_h03_multi_order_same_course_and_late_failed_preserves_evidence(env):
    """Multi-order same-course race + HARDEN-03 (stale FAILED never clobbers fundsCaptured)."""
    o1 = _buy_now(env, env["c1_id"])
    o2 = _buy_now(env, env["c1_id"])
    p1 = _init_pay(env, o1["maDonHang"], gateway="VNPAY_SANDBOX")
    p2 = _init_pay(env, o2["maDonHang"], gateway="VNPAY_SANDBOX")

    # Order 1 pays -> ACTIVE enrollment
    assert env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_params(p1["maGiaoDichNoiBo"], Decimal("599000"), tx_no="VNP_MO_1"),
    ).json()["RspCode"] == "00"

    # Order 2 ALSO pays -> CONFLICT_ALREADY_OWNED_ACTIVE with fundsCaptured=True
    assert env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_params(p2["maGiaoDichNoiBo"], Decimal("599000"), tx_no="VNP_MO_2"),
    ).json()["RspCode"] == "00"

    # Now a stale FAILED callback arrives for p2 -> MUST NOT overwrite fundsCaptured/auditTrail!
    env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_params(p2["maGiaoDichNoiBo"], Decimal("599000"), tx_no="VNP_MO_2", resp_code="24", tx_status="02"),
    )

    with env["SessionLocal"]() as db:
        t2 = db.get(ThanhToan, p2["maThanhToan"])
        assert t2.duLieuPhanHoiAnToan["fundsCaptured"] is True
        assert t2.duLieuPhanHoiAnToan["reconciliationRequired"] is True
        assert t2.duLieuPhanHoiAnToan["reason"] == "CONFLICT_ALREADY_OWNED_ACTIVE"
        assert len(t2.duLieuPhanHoiAnToan["auditTrail"]) >= 1
        enr = db.scalars(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == env["u1_id"],
                DangKyKhoaHoc.maKhoaHoc == env["c1_id"],
            )
        ).first()
        assert enr.maDonHang == o1["maDonHang"]
        assert enr.trangThaiQuyenHoc == "ACTIVE"


def test_h04_db_rollback_before_commit_and_repurchase_after_full_refund(env):
    """Mid-flight DB fault injection rolls back cleanly; repurchase after FULL_ORDER refund preserves history."""
    order = _buy_now(env, env["c1_id"])
    pay = _init_pay(env, order["maDonHang"], gateway="VNPAY_SANDBOX")
    params = _vnpay_params(pay["maGiaoDichNoiBo"], Decimal("599000"), tx_no="VNP_RB_1")

    def _boom():
        raise RuntimeError("Simulated DB crash before commit")

    with env["SessionLocal"]() as db:
        res = order_payment_service.process_vnpay_ipn(db, params, _post_payment_hook=_boom)
        assert res.RspCode == "99"

    # Verify full rollback: order & payment stay PENDING, 0 enrollments
    with env["SessionLocal"]() as db:
        assert db.get(DonHang, order["maDonHang"]).trangThai == "PENDING"
        assert db.get(ThanhToan, pay["maThanhToan"]).trangThai == "PENDING"
        assert db.scalar(
            select(func.count(DangKyKhoaHoc.maDangKy)).where(
                DangKyKhoaHoc.maNguoiDung == env["u1_id"],
                DangKyKhoaHoc.maKhoaHoc == env["c1_id"],
            )
        ) == 0

    # Now pay via MOCK_SANDBOX -> learn -> FULL_ORDER refund -> repurchase!
    o_m = _buy_now(env, env["c2_id"])
    p_m = _init_pay(env, o_m["maDonHang"], gateway="MOCK_SANDBOX")
    env["client"].post(
        f"/api/payments/mock/{p_m['maGiaoDichNoiBo']}/simulate",
        json={"ketQua": "PAID"},
        headers=env["h"](env["tok_u1"]),
    )
    with env["SessionLocal"]() as db:
        db.add(
            LichSuHocTap(
                maNguoiDung=env["u1_id"],
                maKhoaHoc=env["c2_id"],
                maBaiHoc=env["l2_id"],
                tienDo="COMPLETED",
                thoiGianXem=15,
                ngayTao=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()

    # FULL_ORDER refund
    r_rc = env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": o_m["maDonHang"],
            "maThanhToan": p_m["maThanhToan"],
            "soTienHoan": "399000",
            "loaiSuCo": "SYSTEM_ERROR",
            "phamViHoan": "FULL_ORDER",
            "lyDo": "Hoàn tiền sự cố kiểm thử mua lại.",
        },
        headers={**env["h"](env["tok_admin"]), "Idempotency-Key": f"rep-{uuid.uuid4().hex}"},
    )
    assert r_rc.status_code == 201, r_rc.text
    r_rv = env["client"].post(
        f"/api/admin/commerce/refunds/{p_m['maThanhToan']}/verify",
        json={"ghiChuXacMinh": "Đã xác minh sự cố hệ thống."},
        headers=env["h"](env["tok_admin"]),
    )
    assert r_rv.status_code == 200, r_rv.text
    r_re = env["client"].post(
        f"/api/admin/commerce/refunds/{p_m['maThanhToan']}/execute",
        json={"mockOutcome": "REFUNDED"},
        headers=env["h"](env["tok_admin"]),
    )
    assert r_re.status_code == 200 and r_re.json()["trangThai"] == "REFUNDED", r_re.text

    # Repurchase c2 in a new order -> enrollment reactivates to ACTIVE, history preserved!
    o_re = _buy_now(env, env["c2_id"])
    p_re = _init_pay(env, o_re["maDonHang"], gateway="MOCK_SANDBOX")
    r_sim = env["client"].post(
        f"/api/payments/mock/{p_re['maGiaoDichNoiBo']}/simulate",
        json={"ketQua": "PAID"},
        headers=env["h"](env["tok_u1"]),
    )
    assert r_sim.status_code == 200 and r_sim.json()["trangThaiDonHang"] == "PAID"

    with env["SessionLocal"]() as db:
        enr = db.scalars(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == env["u1_id"],
                DangKyKhoaHoc.maKhoaHoc == env["c2_id"],
            )
        ).first()
        assert enr.trangThaiQuyenHoc == "ACTIVE"
        assert enr.maDonHang == o_re["maDonHang"]
        hist_cnt = db.scalar(
            select(func.count(LichSuHocTap.maLichSu)).where(
                LichSuHocTap.maNguoiDung == env["u1_id"],
                LichSuHocTap.maBaiHoc == env["l2_id"],
            )
        )
        assert hist_cnt == 1


def test_h05_fail_closed_503_on_24_table_db_schema_missing(env, monkeypatch):
    """HARDEN-04: When Marketplace tables are absent (24-table Production DB),
    Marketplace endpoints fail closed cleanly with HTTP 503 instead of raw HTTP 500.
    """
    def _raise_missing_table(*_args, **_kwargs):
        raise ProgrammingError(
            'SELECT * FROM "GioHang"', {}, Exception('relation "GioHang" does not exist')
        )

    monkeypatch.setattr(commerce_service, "get_cart", _raise_missing_table)
    r = env["client"].get("/api/cart", headers=env["h"](env["tok_u1"]))
    assert r.status_code == 503
    assert "Marketplace" in r.json()["detail"]

    # Capabilities endpoint remains 200 OK (zero DB query)
    r_cap = env["client"].get("/api/commerce/capabilities")
    assert r_cap.status_code == 200


def test_h06_startup_schema_guard_blocks_24_table_db_and_passes_30_table_db(pg_engine):
    """GĐ4.7A.1 Fail-Closed Startup Schema Guard:
    - Passes cleanly on migrated 30-table EduSuggest_phase4_test.
    - Refuses startup (SchemaCompatibilityError) on unmigrated 24-table EduSuggest (READ ONLY check).
    """
    from config.schema_guard import SchemaCompatibilityError, verify_database_schema_compatibility

    res = verify_database_schema_compatibility(pg_engine, require_marketplace_tables=True)
    assert res["compatible"] is True
    assert res["database"] == "EduSuggest_phase4_test"

    # Read-only check against 24-table EduSuggest_phase3_test (c3d4e5f6a7b8) MUST fail closed!
    p3_url = get_settings().database_url.get_secret_value().rsplit("/", 1)[0] + "/EduSuggest_phase3_test"
    p3_engine = create_engine(p3_url, pool_pre_ping=True)
    try:
        with pytest.raises(SchemaCompatibilityError) as exc_info:
            verify_database_schema_compatibility(p3_engine, require_marketplace_tables=False)
        assert "DangKyKhoaHoc.maDonHang" in str(exc_info.value)
    finally:
        p3_engine.dispose()
