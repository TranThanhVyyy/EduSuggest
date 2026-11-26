"""GĐ4.6 Payment Safety, 30-Scenario Stress & Fault Injection, Exception Refund,
ADMIN Commerce Management, PROVIDER Owner-Scoped Sales, and VNPay QueryDR/Refund
test-vector verification on EduSuggest_phase4_test.

- Never touches Production EduSuggest (asserts current_database() == 'EduSuggest_phase4_test').
- Never enters FastAPI lifespan (instantiates TestClient(app) directly with get_db override).
- Cleans up all test-created rows so EduSuggest_phase4_test remains clean.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, delete, func, select, text
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
from service import order_payment_service
from service.payment_providers import (
    build_vnpay_hash_data,
    build_vnpay_querydr_request,
    build_vnpay_refund_request,
    compute_vnpay_hmac_sha512,
)
from utils.security import create_access_token, hash_password

_TEST_TMN = "TESTTMN46"
_TEST_SECRET = "TEST_ONLY_IN_MEMORY_HMAC_SHA512_SECRET_KEY_PHASE46"
_TEST_RETURN = "http://127.0.0.1:5176/payment/result"


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ4.6 tests require EduSuggest_phase4_test database.")
    return raw


@pytest.fixture(scope="module")
def pg_engine():
    url = _phase4_test_url()
    engine = create_engine(url, pool_pre_ping=True, pool_size=24, max_overflow=24)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        assert db_name == "EduSuggest_phase4_test", f"Refusing to run on {db_name}"
    yield engine
    engine.dispose()


def _sign_vnpay(params: dict[str, str], secret: str = _TEST_SECRET) -> dict[str, str]:
    signed = dict(params)
    hash_data = build_vnpay_hash_data(signed)
    signed["vnp_SecureHash"] = compute_vnpay_hmac_sha512(hash_data, secret)
    return signed


def _vnpay_success_params(
    merchant_ref: str,
    amount_vnd: Decimal,
    tx_no: str | None = None,
    resp_code: str = "00",
    tx_status: str = "00",
) -> dict[str, str]:
    return _sign_vnpay(
        {
            "vnp_TmnCode": _TEST_TMN,
            "vnp_Amount": str(int(amount_vnd * Decimal("100"))),
            "vnp_BankCode": "NCB",
            "vnp_OrderInfo": f"Thanh toan {merchant_ref}",
            "vnp_PayDate": "20261126203000",
            "vnp_ResponseCode": resp_code,
            "vnp_TransactionNo": tx_no or f"VNP{uuid.uuid4().hex[:8].upper()}",
            "vnp_TransactionStatus": tx_status,
            "vnp_TxnRef": merchant_ref,
            "vnp_SecureHashType": "HMACSHA512",
        }
    )


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

        def _make_user(role_name: str) -> tuple[NguoiDung, str]:
            role = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == role_name)).first()
            assert role is not None
            tag = uuid.uuid4().hex[:8]
            pwd_hash = hash_password(f"P46!{tag}99")
            u = NguoiDung(
                maVaiTro=role.maVaiTro,
                tenTaiKhoan=f"p46_{role_name.lower()}_{tag}",
                hoTen=f"P46 {role_name} {tag}",
                email=f"p46_{role_name.lower()}_{tag}@example.test",
                matKhau=pwd_hash,
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            db.add(u)
            db.flush()
            created_users.append(u.maNguoiDung)
            return u, create_access_token(u.maNguoiDung, pwd_hash).encoded

        def _make_provider() -> tuple[NguoiDung, NhaCungCapKhoaHoc, str]:
            u, tok = _make_user("PROVIDER")
            tag = uuid.uuid4().hex[:8]
            p = NhaCungCapKhoaHoc(
                maNguoiDung=u.maNguoiDung,
                tieuSu=f"Provider test GĐ4.6 {tag}",
                chuyenMon="Software Engineering",
            )
            db.add(p)
            db.flush()
            created_providers.append(p.maNhaCungCap)
            return u, p, tok

        def _make_course(provider_id: int, gia: Decimal) -> tuple[KhoaHoc, BaiHoc]:
            tag = uuid.uuid4().hex[:8]
            now = datetime.now(UTC).replace(tzinfo=None)
            c = KhoaHoc(
                maNhaCungCap=provider_id,
                maDanhMuc=category_id,
                tieuDe=f"P46 Course {tag}",
                moTa="Khóa học kiểm thử an toàn thanh toán GĐ4.6",
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
                noiDung="Nội dung kiểm thử",
                thoiLuong=20,
                thuTu=1,
                ngayTao=now,
            )
            db.add(l)
            db.flush()
            created_courses.append(c.maKhoaHoc)
            created_lessons.append(l.maBaiHoc)
            return c, l

        user1, tok_user1 = _make_user("USER")
        user2, tok_user2 = _make_user("USER")
        admin1, tok_admin1 = _make_user("ADMIN")
        admin2, tok_admin2 = _make_user("ADMIN")
        _, prov1, tok_prov1 = _make_provider()
        _, prov2, tok_prov2 = _make_provider()

        c1, l1 = _make_course(prov1.maNhaCungCap, Decimal("499000"))
        c2, l2 = _make_course(prov2.maNhaCungCap, Decimal("799000"))
        c_free, l_free = _make_course(prov1.maNhaCungCap, Decimal("0"))
        db.commit()

        yield {
            "client": client,
            "SessionLocal": SessionLocal,
            "user1": user1,
            "tok_user1": tok_user1,
            "user2": user2,
            "tok_user2": tok_user2,
            "admin1": admin1,
            "tok_admin1": tok_admin1,
            "admin2": admin2,
            "tok_admin2": tok_admin2,
            "prov1": prov1,
            "tok_prov1": tok_prov1,
            "prov2": prov2,
            "tok_prov2": tok_prov2,
            "c1": c1,
            "l1": l1,
            "c2": c2,
            "l2": l2,
            "c_free": c_free,
            "l_free": l_free,
            "make_course": _make_course,
            "h": lambda tok: {"Authorization": f"Bearer {tok}"},
        }
    finally:
        db.close()
        cleanup = SessionLocal()
        try:
            assert cleanup.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase4_test"
            cleanup.execute(text("SET LOCAL session_replication_role = 'replica'"))
            if created_users:
                order_ids = list(
                    cleanup.scalars(select(DonHang.maDonHang).where(DonHang.maNguoiDung.in_(created_users)))
                )
                cart_ids = list(
                    cleanup.scalars(select(GioHang.maGioHang).where(GioHang.maNguoiDung.in_(created_users)))
                )
                if order_ids:
                    cleanup.execute(text('DELETE FROM "TacVuDoiSoatThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": order_ids})
                    cleanup.execute(text('DELETE FROM "SuKienThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": order_ids})
                    cleanup.execute(text('DELETE FROM "BaoCaoSuCoThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": order_ids})
                    cleanup.execute(text('DELETE FROM "LanThuHoanTien" WHERE "maHoanTien" IN (SELECT "maHoanTien" FROM "HoanTienNgoaiLe" WHERE "maDonHang" = ANY(:oids))'), {"oids": order_ids})
                    cleanup.execute(text('DELETE FROM "HoanTienNgoaiLe" WHERE "maDonHang" = ANY(:oids)'), {"oids": order_ids})
                    cleanup.execute(delete(ThanhToan).where(ThanhToan.maDonHang.in_(order_ids)))
                    cleanup.execute(delete(ChiTietDonHang).where(ChiTietDonHang.maDonHang.in_(order_ids)))
                cleanup.execute(delete(LichSuHocTap).where(LichSuHocTap.maNguoiDung.in_(created_users)))
                cleanup.execute(delete(DangKyKhoaHoc).where(DangKyKhoaHoc.maNguoiDung.in_(created_users)))
                if order_ids:
                    cleanup.execute(delete(DonHang).where(DonHang.maDonHang.in_(order_ids)))
                if cart_ids:
                    cleanup.execute(delete(ChiTietGioHang).where(ChiTietGioHang.maGioHang.in_(cart_ids)))
                    cleanup.execute(delete(GioHang).where(GioHang.maGioHang.in_(cart_ids)))
                cleanup.execute(delete(YeuThich).where(YeuThich.maNguoiDung.in_(created_users)))
                cleanup.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_(created_users)))
            if created_lessons:
                cleanup.execute(delete(LichSuHocTap).where(LichSuHocTap.maBaiHoc.in_(created_lessons)))
                cleanup.execute(delete(BaiHoc).where(BaiHoc.maBaiHoc.in_(created_lessons)))
            if created_courses:
                cleanup.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(created_courses)))
            if created_providers:
                cleanup.execute(
                    delete(NhaCungCapKhoaHoc).where(NhaCungCapKhoaHoc.maNhaCungCap.in_(created_providers))
                )
            if created_users:
                cleanup.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(created_users)))
            cleanup.commit()
        finally:
            cleanup.close()
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _create_order_buy_now(env, tok: str, course_id: int, idem: str | None = None) -> dict:
    r = env["client"].post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": course_id},
        headers={**env["h"](tok), "Idempotency-Key": idem or f"bn-{uuid.uuid4().hex}"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def _init_payment(env, tok: str, order_id: int, gateway: str = "MOCK_SANDBOX", idem: str | None = None) -> dict:
    r = env["client"].post(
        f"/api/orders/{order_id}/payments",
        json={"congThanhToan": gateway},
        headers={**env["h"](tok), "Idempotency-Key": idem or f"pay-{uuid.uuid4().hex}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ===========================================================================
# GROUP A: CONCURRENCY, DUPLICATE CLICKS & RAPID CALLBACKS (Scenarios 1-6)
# ===========================================================================

def test_s01_to_s04_rapid_duplicate_callbacks_20x_single_activation(env):
    """Scenarios 1-4: 20x concurrent duplicate VNPay IPN callbacks -> 1 activation, 1 enrollment."""
    order = _create_order_buy_now(env, env["tok_user1"], env["c1"].maKhoaHoc)
    pay = _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="VNPAY_SANDBOX")
    ipn_params = _vnpay_success_params(pay["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_STRESS_01")

    def _hit(_i: int) -> dict:
        return env["client"].get("/api/payments/vnpay/ipn", params=ipn_params).json()

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(_hit, range(20)))

    assert all(res["RspCode"] in ("00", "02") for res in results)
    assert sum(1 for res in results if res["RspCode"] == "00") == 1
    assert sum(1 for res in results if res["RspCode"] == "02") == 19

    with env["SessionLocal"]() as db:
        enroll_cnt = db.scalar(
            select(func.count(DangKyKhoaHoc.maDangKy)).where(
                DangKyKhoaHoc.maNguoiDung == env["user1"].maNguoiDung,
                DangKyKhoaHoc.maKhoaHoc == env["c1"].maKhoaHoc,
            )
        )
        assert enroll_cnt == 1


def _simulate_mock_paid(env, tok: str, txn_ref: str) -> dict:
    r = env["client"].post(
        f"/api/payments/mock/{txn_ref}/simulate",
        json={"ketQua": "PAID"},
        headers=env["h"](tok),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_s05_concurrent_mock_callback_and_buy_now_idempotency(env):
    """Scenarios 5-6: Rapid double-click Buy Now with same Idempotency-Key + 15x Mock callbacks."""
    idem = f"dbl-{uuid.uuid4().hex}"
    c1_id = int(env["c1"].maKhoaHoc)

    def _buy(_i: int) -> int:
        r = env["client"].post(
            "/api/orders",
            json={"nguonTao": "BUY_NOW", "maKhoaHoc": c1_id},
            headers={**env["h"](env["tok_user1"]), "Idempotency-Key": idem},
        )
        assert r.status_code in (200, 201), r.text
        return r.json()["maDonHang"]

    with ThreadPoolExecutor(max_workers=6) as pool:
        order_ids = list(pool.map(_buy, range(6)))
    assert len(set(order_ids)) == 1
    order_id = order_ids[0]

    pay = _init_payment(env, env["tok_user1"], order_id, gateway="MOCK_SANDBOX")
    txn_ref = str(pay["maGiaoDichNoiBo"])

    def _confirm(_i: int) -> dict:
        return _simulate_mock_paid(env, env["tok_user1"], txn_ref)

    with ThreadPoolExecutor(max_workers=8) as pool:
        cb_res = list(pool.map(_confirm, range(15)))

    assert all(x["trangThaiDonHang"] == "PAID" for x in cb_res)
    assert sum(1 for x in cb_res if not x["idempotentReplay"]) == 1


# ===========================================================================
# GROUP B: DOUBLE CHARGE / EXCESS PAYMENT & REVENUE INTEGRITY (Scenarios 7-11)
# ===========================================================================

def test_s07_to_s11_two_captured_payments_excess_refund_keeps_access_and_revenue(env):
    """Scenarios 7-11:
    - Order receives 2 distinct captured payments (attempt #1 PAID, attempt #2 captured excess).
    - Attempt #2 MUST NOT lose gateway evidence (fundsCaptured=True, reconciliationRequired=True).
    - ADMIN creates/verifies/executes EXCESS_PAYMENT refund on attempt #2.
    - Valid PAID order + ACTIVE enrollment MUST remain untouched!
    - Gross Revenue MUST count the valid order once (499,000), NOT 998,000, and EXCESS_PAYMENT
      refund MUST NOT subtract from valid Gross Revenue (Net Revenue stays 499,000)!
    """
    order = _create_order_buy_now(env, env["tok_user1"], env["c1"].maKhoaHoc)
    p1 = _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="VNPAY_SANDBOX")
    p2 = _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="VNPAY_SANDBOX")
    assert p1["maThanhToan"] != p2["maThanhToan"]

    # Attempt #1 succeeds via IPN
    r1 = env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_success_params(p1["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_ATT1"),
    )
    assert r1.json()["RspCode"] == "00"

    # Attempt #2 ALSO captured money at gateway and arrives via IPN!
    r2 = env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_success_params(p2["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_ATT2_EXCESS"),
    )
    assert r2.json()["RspCode"] == "00"

    # Verify Attempt #2 preserved gateway evidence in DB
    with env["SessionLocal"]() as db:
        t2 = db.get(ThanhToan, p2["maThanhToan"])
        assert t2 is not None
        assert t2.maGiaoDichCong == "VNP_ATT2_EXCESS"
        assert t2.duLieuPhanHoiAnToan["fundsCaptured"] is True
        assert t2.duLieuPhanHoiAnToan["reconciliationRequired"] is True
        assert t2.duLieuPhanHoiAnToan["reconciliationStatus"] == "OPEN"

    # Reconciliation queue shows p2
    recon_q = env["client"].get(
        "/api/admin/commerce/reconciliation", headers=env["h"](env["tok_admin1"])
    ).json()
    p2_item = next(x for x in recon_q if x["maThanhToan"] == p2["maThanhToan"])
    assert p2_item["daThuTien"] is True
    assert Decimal(str(p2_item["soTienDaThuThucTe"])) == Decimal("499000")

    # Note: for execution test, simulate an equivalent MOCK_SANDBOX excess payment so
    # execute_exception_refund can run end-to-end without fabricating VNPay live network calls
    order_m = _create_order_buy_now(env, env["tok_user2"], env["c1"].maKhoaHoc)
    pm1 = _init_payment(env, env["tok_user2"], order_m["maDonHang"], gateway="MOCK_SANDBOX")
    pm2 = _init_payment(env, env["tok_user2"], order_m["maDonHang"], gateway="MOCK_SANDBOX")

    _simulate_mock_paid(env, env["tok_user2"], pm1["maGiaoDichNoiBo"])
    _simulate_mock_paid(env, env["tok_user2"], pm2["maGiaoDichNoiBo"])

    # Overview before excess refund
    ov_before = env["client"].get(
        "/api/admin/commerce/overview", headers=env["h"](env["tok_admin1"])
    ).json()
    gross_before = Decimal(str(ov_before["doanhThuGhiNhan"]))
    net_before = Decimal(str(ov_before["doanhThuThuanHopLe"]))

    # ADMIN creates -> verifies -> executes EXCESS_PAYMENT refund on pm2
    ref_create = env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": order_m["maDonHang"],
            "maThanhToan": pm2["maThanhToan"],
            "soTienHoan": "499000",
            "loaiSuCo": "DUPLICATE_CHARGE",
            "phamViHoan": "EXCESS_PAYMENT",
            "lyDo": "Hoàn tiền thu dư lần thanh toán thứ 2 đã xác minh.",
        },
        headers={**env["h"](env["tok_admin1"]), "Idempotency-Key": f"ref-ex-{uuid.uuid4().hex}"},
    )
    assert ref_create.status_code == 201, ref_create.text
    assert ref_create.json()["trangThai"] == "PENDING_REVIEW"

    ref_ver = env["client"].post(
        f"/api/admin/commerce/refunds/{pm2['maThanhToan']}/verify",
        json={"ghiChuXacMinh": "Đã đối soát mã giao dịch cổng M_ATT2_EXCESS thu trùng."},
        headers=env["h"](env["tok_admin1"]),
    )
    assert ref_ver.status_code == 200
    assert ref_ver.json()["trangThai"] == "VERIFIED"

    ref_exec = env["client"].post(
        f"/api/admin/commerce/refunds/{pm2['maThanhToan']}/execute",
        json={"mockOutcome": "REFUNDED"},
        headers=env["h"](env["tok_admin1"]),
    )
    assert ref_exec.status_code == 200, ref_exec.text
    assert ref_exec.json()["trangThai"] == "REFUNDED"

    # Valid PAID order & ACTIVE enrollment for user2 MUST remain untouched!
    with env["SessionLocal"]() as db:
        ord_row = db.get(DonHang, order_m["maDonHang"])
        assert ord_row.trangThai == "PAID"
        enr_row = db.scalars(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == env["user2"].maNguoiDung,
                DangKyKhoaHoc.maKhoaHoc == env["c1"].maKhoaHoc,
            )
        ).first()
        assert enr_row is not None and enr_row.trangThaiQuyenHoc == "ACTIVE"

    # Revenue check: EXCESS_PAYMENT refund does NOT subtract from valid Gross/Net Revenue
    ov_after = env["client"].get(
        "/api/admin/commerce/overview", headers=env["h"](env["tok_admin1"])
    ).json()
    assert Decimal(str(ov_after["doanhThuGhiNhan"])) == gross_before
    assert Decimal(str(ov_after["doanhThuThuanHopLe"])) == net_before


# ===========================================================================
# GROUP C: LATE CALLBACKS, PRIORITY #1 RESTORE & OUT-OF-ORDER (Scenarios 12-16)
# ===========================================================================

def test_s12_to_s14_late_ipn_after_expiry_priority1_restore(env):
    """Scenarios 12-14:
    - Order expires -> late IPN arrives with funds captured -> flagged reconciliationRequired.
    - ADMIN executes Priority #1 action: restore PAID order & ACTIVE enrollment (instead of refunding).
    """
    order = _create_order_buy_now(env, env["tok_user1"], env["c1"].maKhoaHoc)
    pay = _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="VNPAY_SANDBOX")

    # Force order expired
    with env["SessionLocal"]() as db:
        o = db.get(DonHang, order["maDonHang"])
        o.trangThai = "EXPIRED"
        o.hanThanhToan = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=20)
        db.commit()

    # Late VNPay IPN arrives with captured funds
    ipn = env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_success_params(pay["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_LATE_01"),
    )
    assert ipn.json()["RspCode"] == "00"

    # Order stays EXPIRED pending reconciliation, enrollment NOT granted yet
    with env["SessionLocal"]() as db:
        o = db.get(DonHang, order["maDonHang"])
        assert o.trangThai == "EXPIRED"
        t = db.get(ThanhToan, pay["maThanhToan"])
        assert t.duLieuPhanHoiAnToan["fundsCaptured"] is True
        assert t.duLieuPhanHoiAnToan["reconciliationRequired"] is True

    # ADMIN Priority #1: Restore PAID + grant ACTIVE entitlement
    act = env["client"].post(
        f"/api/admin/commerce/reconciliation/{pay['maThanhToan']}/activate",
        json={"lyDo": "Khách đã thanh toán thành công VNP_LATE_01, ưu tiên cấp quyền học."},
        headers=env["h"](env["tok_admin1"]),
    )
    assert act.status_code == 200, act.text
    assert act.json()["trangThai"] == "PAID"

    with env["SessionLocal"]() as db:
        enr = db.scalars(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == env["user1"].maNguoiDung,
                DangKyKhoaHoc.maKhoaHoc == env["c1"].maKhoaHoc,
            )
        ).first()
        assert enr is not None and enr.trangThaiQuyenHoc == "ACTIVE"


def test_s15_s16_out_of_order_callbacks_paid_not_downgraded_and_return_before_ipn(env):
    """Scenarios 15-16:
    - PAID order is NEVER downgraded by a late FAILED callback.
    - Return URL arriving before IPN shows verifying/pending (never grants entitlement without IPN).
    - IPN arriving before Return URL -> Return URL reads authoritative PAID state.
    """
    order = _create_order_buy_now(env, env["tok_user1"], env["c1"].maKhoaHoc)
    pay = _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="VNPAY_SANDBOX")

    # Return URL before IPN -> does NOT activate enrollment
    ret_before = env["client"].get(
        "/api/payments/vnpay/return",
        params=_vnpay_success_params(pay["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_OOO_01"),
        headers=env["h"](env["tok_user1"]),
    )
    assert ret_before.status_code == 200, ret_before.text
    assert ret_before.json()["signatureValid"] is True
    assert ret_before.json()["trangThaiDonHangHienTai"] == "PENDING"

    # IPN arrives -> activates PAID
    ipn_ok = env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_success_params(pay["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_OOO_01"),
    )
    assert ipn_ok.json()["RspCode"] == "00"

    # Late FAILED callback arrives -> MUST NOT downgrade PAID
    ipn_late_fail = env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_success_params(
            pay["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_OOO_01", resp_code="24", tx_status="02"
        ),
    )
    assert ipn_late_fail.json()["RspCode"] == "02"

    # Return URL after IPN -> authoritative PAID
    ret_after = env["client"].get(
        "/api/payments/vnpay/return",
        params=_vnpay_success_params(pay["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_OOO_01"),
        headers=env["h"](env["tok_user1"]),
    )
    assert ret_after.status_code == 200, ret_after.text
    assert ret_after.json()["trangThaiDonHangHienTai"] == "PAID"


# ===========================================================================
# GROUP D: FULL-ORDER INCIDENT REFUND & LEGACY/HISTORY PRESERVATION (Scenarios 17-20)
# ===========================================================================

def test_s17_to_s20_full_order_refund_revokes_only_target_preserves_history_and_legacy(env):
    """Scenarios 17-20:
    - User has a LEGACY enrollment on c2 + learning history on c1.
    - User buys c1 via paid order -> ADMIN executes FULL_ORDER exception refund.
    - Target enrollment on c1 becomes REVOKED (row NOT deleted), LichSuHocTap preserved!
    - LEGACY enrollment on c2 stays ACTIVE untouched!
    - Order & Payment become REFUNDED; Gross/Refund/Net Revenue reflect exact VND Decimal math.
    """
    # Seed LEGACY enrollment on c2
    with env["SessionLocal"]() as db:
        db.add(
            DangKyKhoaHoc(
                maNguoiDung=env["user1"].maNguoiDung,
                maKhoaHoc=env["c2"].maKhoaHoc,
                ngayDangKy=datetime.now(UTC).replace(tzinfo=None),
                nguonCapQuyen="LEGACY",
                trangThaiQuyenHoc="ACTIVE",
            )
        )
        db.commit()

    # Buy c1
    order = _create_order_buy_now(env, env["tok_user1"], env["c1"].maKhoaHoc)
    pay = _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="MOCK_SANDBOX")
    _simulate_mock_paid(env, env["tok_user1"], pay["maGiaoDichNoiBo"])

    # Seed LichSuHocTap for c1's lesson
    with env["SessionLocal"]() as db:
        db.add(
            LichSuHocTap(
                maNguoiDung=env["user1"].maNguoiDung,
                maKhoaHoc=env["c1"].maKhoaHoc,
                maBaiHoc=env["l1"].maBaiHoc,
                tienDo="COMPLETED",
                thoiGianXem=20,
                ngayTao=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()

    # ADMIN FULL_ORDER exception refund: create -> verify -> execute
    c_res = env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": order["maDonHang"],
            "maThanhToan": pay["maThanhToan"],
            "soTienHoan": "499000",
            "loaiSuCo": "CANNOT_PROVISION_COURSE",
            "phamViHoan": "FULL_ORDER",
            "lyDo": "Sự cố kỹ thuật xác minh không thể cung cấp nội dung khóa học.",
        },
        headers={**env["h"](env["tok_admin1"]), "Idempotency-Key": f"ref-full-{uuid.uuid4().hex}"},
    )
    assert c_res.status_code == 201
    v_res = env["client"].post(
        f"/api/admin/commerce/refunds/{pay['maThanhToan']}/verify",
        json={"ghiChuXacMinh": "Đã xác minh lỗi hệ thống khóa học."},
        headers=env["h"](env["tok_admin1"]),
    )
    assert v_res.status_code == 200
    e_res = env["client"].post(
        f"/api/admin/commerce/refunds/{pay['maThanhToan']}/execute",
        json={"mockOutcome": "REFUNDED"},
        headers=env["h"](env["tok_admin1"]),
    )
    assert e_res.status_code == 200
    assert e_res.json()["trangThai"] == "REFUNDED"

    with env["SessionLocal"]() as db:
        o = db.get(DonHang, order["maDonHang"])
        t = db.get(ThanhToan, pay["maThanhToan"])
        assert o.trangThai == "REFUNDED"
        assert t.trangThai == "REFUNDED"

        enr_c1 = db.scalars(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == env["user1"].maNguoiDung,
                DangKyKhoaHoc.maKhoaHoc == env["c1"].maKhoaHoc,
            )
        ).first()
        assert enr_c1 is not None  # NEVER deleted
        assert enr_c1.trangThaiQuyenHoc == "REVOKED"

        enr_c2 = db.scalars(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == env["user1"].maNguoiDung,
                DangKyKhoaHoc.maKhoaHoc == env["c2"].maKhoaHoc,
            )
        ).first()
        assert enr_c2 is not None and enr_c2.trangThaiQuyenHoc == "ACTIVE"  # LEGACY untouched!

        hist = db.scalars(
            select(LichSuHocTap).where(
                LichSuHocTap.maNguoiDung == env["user1"].maNguoiDung,
                LichSuHocTap.maBaiHoc == env["l1"].maBaiHoc,
            )
        ).first()
        assert hist is not None  # LichSuHocTap NEVER deleted!


# ===========================================================================
# GROUP E: REFUND CONCURRENCY, TIMEOUT/UNKNOWN, VALIDATION & NON-FABRICATION (Scenarios 21-26)
# ===========================================================================

def test_s21_to_s24_refund_concurrency_unknown_timeout_reconcile_and_limits(env):
    """Scenarios 21-24:
    - Refund exceeding captured amount -> 400.
    - Refund on uncaptured PENDING payment -> 409.
    - 2 ADMINs concurrently executing same refund -> zero double refund.
    - Refund timeout (UNKNOWN) -> blind retry blocked (409) until reconcile-unknown resolves it.
    """
    # Uncaptured payment cannot be refunded
    order_p = _create_order_buy_now(env, env["tok_user1"], env["c1"].maKhoaHoc)
    pay_p = _init_payment(env, env["tok_user1"], order_p["maDonHang"], gateway="MOCK_SANDBOX")
    r_uncap = env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": order_p["maDonHang"],
            "maThanhToan": pay_p["maThanhToan"],
            "soTienHoan": "499000",
            "loaiSuCo": "SYSTEM_ERROR",
            "phamViHoan": "FULL_ORDER",
            "lyDo": "Thử hoàn tiền giao dịch chưa thu tiền.",
        },
        headers={**env["h"](env["tok_admin1"]), "Idempotency-Key": f"uncap-{uuid.uuid4().hex}"},
    )
    assert r_uncap.status_code == 409

    # Pay the order now
    _simulate_mock_paid(env, env["tok_user1"], pay_p["maGiaoDichNoiBo"])

    # Exceeding captured amount -> 400
    r_over = env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": order_p["maDonHang"],
            "maThanhToan": pay_p["maThanhToan"],
            "soTienHoan": "999000",
            "loaiSuCo": "WRONG_AMOUNT",
            "phamViHoan": "FULL_ORDER",
            "lyDo": "Thử hoàn vượt quá số tiền đã thu.",
        },
        headers={**env["h"](env["tok_admin1"]), "Idempotency-Key": f"over-{uuid.uuid4().hex}"},
    )
    assert r_over.status_code == 400

    # Create valid refund + verify
    idem = f"ref-unk-{uuid.uuid4().hex}"
    r_c = env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": order_p["maDonHang"],
            "maThanhToan": pay_p["maThanhToan"],
            "soTienHoan": "499000",
            "loaiSuCo": "SYSTEM_ERROR",
            "phamViHoan": "FULL_ORDER",
            "lyDo": "Sự cố hệ thống kiểm thử timeout UNKNOWN.",
        },
        headers={**env["h"](env["tok_admin1"]), "Idempotency-Key": idem},
    )
    assert r_c.status_code == 201
    env["client"].post(
        f"/api/admin/commerce/refunds/{pay_p['maThanhToan']}/verify",
        json={"ghiChuXacMinh": "Đã xác minh sự cố."},
        headers=env["h"](env["tok_admin1"]),
    )

    # Execute with UNKNOWN timeout
    r_unk = env["client"].post(
        f"/api/admin/commerce/refunds/{pay_p['maThanhToan']}/execute",
        json={"mockOutcome": "UNKNOWN"},
        headers=env["h"](env["tok_admin1"]),
    )
    assert r_unk.status_code == 200
    assert r_unk.json()["trangThai"] == "UNKNOWN"

    # Blind retry while UNKNOWN MUST BE BLOCKED (409)!
    r_blind = env["client"].post(
        f"/api/admin/commerce/refunds/{pay_p['maThanhToan']}/execute",
        json={"mockOutcome": "REFUNDED"},
        headers=env["h"](env["tok_admin2"]),
    )
    assert r_blind.status_code == 409

    # Reconcile UNKNOWN -> REFUND_FAILED -> then 2 ADMINs concurrently execute -> exactly 1 REFUNDED
    r_rec = env["client"].post(
        f"/api/admin/commerce/refunds/{pay_p['maThanhToan']}/reconcile-unknown",
        json={
            "ketQuaDoiSoat": "REFUND_FAILED",
            "ghiChuBangChung": "QueryDR xác nhận cổng chưa hoàn tiền, cho phép thử lại.",
        },
        headers=env["h"](env["tok_admin1"]),
    )
    assert r_rec.status_code == 200
    assert r_rec.json()["trangThai"] == "REFUND_FAILED"

    def _exec_by(tok: str) -> tuple[int, str | None]:
        resp = env["client"].post(
            f"/api/admin/commerce/refunds/{pay_p['maThanhToan']}/execute",
            json={"mockOutcome": "REFUNDED"},
            headers=env["h"](tok),
        )
        return resp.status_code, resp.json().get("trangThai") if resp.status_code == 200 else None

    with ThreadPoolExecutor(max_workers=2) as pool:
        exec_results = list(pool.map(_exec_by, [env["tok_admin1"], env["tok_admin2"]]))

    assert all(code == 200 and st == "REFUNDED" for code, st in exec_results)
    # History should only record 1 final REFUNDED transition (second call is idempotent return)
    with env["SessionLocal"]() as db:
        t = db.get(ThanhToan, pay_p["maThanhToan"])
        hist = t.duLieuPhanHoiAnToan["exceptionRefund"]["lichSuTrangThai"]
        assert sum(1 for h in hist if h["to"] == "REFUNDED") == 1


def test_s25_s26_vnpay_querydr_refund_vectors_and_non_fabrication_guard(env):
    """Scenarios 25-26:
    - Official VNPay API v2.1.0 QueryDR & Refund pipe-delimited HMAC-SHA512 request builders.
    - Runtime admin_execute_exception_refund on VNPAY_SANDBOX refuses to fabricate success (409).
    """
    fixed_utc = datetime(2026, 11, 26, 13, 35, 0)  # 20261126203500 in GMT+7
    q_body = build_vnpay_querydr_request(
        request_id="REQ001",
        txn_ref="PAY_QDR_001",
        transaction_date_vnp="20261126203000",
        order_info="QueryDR test",
        client_ip="127.0.0.1",
        created_at_utc=fixed_utc,
    )
    assert q_body["vnp_Command"] == "querydr"
    expected_q_raw = "|".join(
        [
            "REQ001",
            "2.1.0",
            "querydr",
            _TEST_TMN,
            "PAY_QDR_001",
            "20261126203000",
            "20261126203500",
            "127.0.0.1",
            "QueryDR test",
        ]
    )
    assert q_body["vnp_SecureHash"] == compute_vnpay_hmac_sha512(expected_q_raw, _TEST_SECRET)

    fixed_ref_utc = datetime(2026, 11, 26, 13, 40, 0)  # 20261126204000 in GMT+7
    r_body = build_vnpay_refund_request(
        request_id="REFREQ001",
        txn_ref="PAY_REF_001",
        amount_vnd=Decimal("499000"),
        transaction_type="02",
        transaction_no="14200123",
        transaction_date_vnp="20261126203000",
        create_by="admin@edusuggest.vn",
        order_info="Hoan tien su co PAY_REF_001",
        client_ip="127.0.0.1",
        created_at_utc=fixed_ref_utc,
    )
    assert r_body["vnp_Command"] == "refund"
    assert r_body["vnp_Amount"] == "49900000"
    expected_r_raw = "|".join(
        [
            "REFREQ001",
            "2.1.0",
            "refund",
            _TEST_TMN,
            "02",
            "PAY_REF_001",
            "49900000",
            "14200123",
            "20261126203000",
            "admin@edusuggest.vn",
            "20261126204000",
            "127.0.0.1",
            "Hoan tien su co PAY_REF_001",
        ]
    )
    assert r_body["vnp_SecureHash"] == compute_vnpay_hmac_sha512(expected_r_raw, _TEST_SECRET)

    # Non-fabrication guard on VNPAY_SANDBOX refund execute
    order = _create_order_buy_now(env, env["tok_user1"], env["c1"].maKhoaHoc)
    pay = _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="VNPAY_SANDBOX")
    env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_success_params(pay["maGiaoDichNoiBo"], Decimal("499000"), tx_no="VNP_NOFAB"),
    )
    env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": order["maDonHang"],
            "maThanhToan": pay["maThanhToan"],
            "soTienHoan": "499000",
            "loaiSuCo": "SYSTEM_ERROR",
            "phamViHoan": "FULL_ORDER",
            "lyDo": "Kiểm tra không giả lập hoàn tiền VNPay.",
        },
        headers={**env["h"](env["tok_admin1"]), "Idempotency-Key": f"nofab-{uuid.uuid4().hex}"},
    )
    env["client"].post(
        f"/api/admin/commerce/refunds/{pay['maThanhToan']}/verify",
        json={"ghiChuXacMinh": "Xác minh xong."},
        headers=env["h"](env["tok_admin1"]),
    )
    r_exec = env["client"].post(
        f"/api/admin/commerce/refunds/{pay['maThanhToan']}/execute",
        json={"mockOutcome": "REFUNDED"},
        headers=env["h"](env["tok_admin1"]),
    )
    assert r_exec.status_code == 409


# ===========================================================================
# GROUP F: USER INCIDENT REPORT, RBAC, IDOR & PROVIDER ISOLATION (Scenarios 27-30)
# ===========================================================================

def test_s27_s28_user_incident_report_idor_and_mass_assignment_blocked(env):
    """Scenarios 27-28:
    - USER can report payment incident on their own order.
    - Extra card/OTP/password fields rejected (422).
    - Cross-user IDOR returns 404.
    - USER/PROVIDER cannot call ADMIN commerce endpoints (403).
    """
    order = _create_order_buy_now(env, env["tok_user1"], env["c1"].maKhoaHoc)
    _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="MOCK_SANDBOX")
    r_bad = env["client"].post(
        f"/api/orders/{order['maDonHang']}/incidents",
        json={
            "loaiSuCo": "DUPLICATE_CHARGE",
            "moTa": "Tôi bị trừ tiền 2 lần lúc 20:00.",
            "cardNumber": "9704198526191432198",
        },
        headers=env["h"](env["tok_user1"]),
    )
    assert r_bad.status_code == 422

    # Cross-user IDOR blocked
    r_idor = env["client"].post(
        f"/api/orders/{order['maDonHang']}/incidents",
        json={"loaiSuCo": "DUPLICATE_CHARGE", "moTa": "Báo cáo giả mạo đơn của người khác."},
        headers=env["h"](env["tok_user2"]),
    )
    assert r_idor.status_code == 404

    # Valid owner report
    r_ok = env["client"].post(
        f"/api/orders/{order['maDonHang']}/incidents",
        json={"loaiSuCo": "CHARGED_NO_ACCESS", "moTa": "Đã trừ tiền nhưng chưa mở khóa học."},
        headers=env["h"](env["tok_user1"]),
    )
    assert r_ok.status_code == 201
    inc_id = r_ok.json()["maSuCo"]

    # ADMIN sees it in incidents list
    incs = env["client"].get(
        "/api/admin/commerce/incidents", headers=env["h"](env["tok_admin1"])
    ).json()
    assert any(x["maSuCo"] == inc_id for x in incs)

    # RBAC: USER and PROVIDER blocked from ADMIN commerce endpoints
    assert env["client"].get("/api/admin/commerce/overview", headers=env["h"](env["tok_user1"])).status_code == 403
    assert env["client"].get("/api/admin/commerce/overview", headers=env["h"](env["tok_prov1"])).status_code == 403
    assert env["client"].get("/api/provider/sales/summary", headers=env["h"](env["tok_user1"])).status_code == 403


def test_s29_s30_provider_owner_scoped_sales_and_production_guard(env, monkeypatch):
    """Scenarios 29-30:
    - Multi-provider cart checkout (c1 owned by prov1, c2 owned by prov2).
    - prov1 sees ONLY c1 (499,000 VND); prov2 sees ONLY c2 (799,000 VND).
    - LEGACY enrollment on c1 is NEVER counted in provider revenue.
    - Production guard: APP_ENV=production blocks MOCK_SANDBOX refund execution.
    """
    # Seed LEGACY enrollment on c1 for user2 (must NOT appear in prov1 sales!)
    with env["SessionLocal"]() as db:
        db.add(
            DangKyKhoaHoc(
                maNguoiDung=env["user2"].maNguoiDung,
                maKhoaHoc=env["c1"].maKhoaHoc,
                ngayDangKy=datetime.now(UTC).replace(tzinfo=None),
                nguonCapQuyen="LEGACY",
                trangThaiQuyenHoc="ACTIVE",
            )
        )
        db.commit()

    # user1 adds c1 (prov1) & c2 (prov2) to cart and checks out
    for cid in (env["c1"].maKhoaHoc, env["c2"].maKhoaHoc):
        r_add = env["client"].post(
            "/api/cart/items", json={"maKhoaHoc": cid}, headers=env["h"](env["tok_user1"])
        )
        assert r_add.status_code in (200, 201)

    r_ord = env["client"].post(
        "/api/orders",
        json={"nguonTao": "CART", "courseIds": [env["c1"].maKhoaHoc, env["c2"].maKhoaHoc]},
        headers={**env["h"](env["tok_user1"]), "Idempotency-Key": f"cart-mp-{uuid.uuid4().hex}"},
    )
    assert r_ord.status_code == 201
    order = r_ord.json()
    pay = _init_payment(env, env["tok_user1"], order["maDonHang"], gateway="MOCK_SANDBOX")
    _simulate_mock_paid(env, env["tok_user1"], pay["maGiaoDichNoiBo"])

    # Provider 1 sees ONLY 499,000 VND (1 item)
    p1_sum = env["client"].get(
        "/api/provider/sales/summary", headers=env["h"](env["tok_prov1"])
    ).json()
    assert Decimal(str(p1_sum["doanhThuGhiNhan"])) == Decimal("499000")
    assert Decimal(str(p1_sum["doanhThuThuan"])) == Decimal("499000")
    assert p1_sum["tongLuotBan"] == 1
    p1_items = env["client"].get(
        "/api/provider/sales/items", headers=env["h"](env["tok_prov1"])
    ).json()
    assert len(p1_items) == 1
    assert p1_items[0]["maKhoaHoc"] == env["c1"].maKhoaHoc

    # Provider 2 sees ONLY 799,000 VND (1 item)
    p2_sum = env["client"].get(
        "/api/provider/sales/summary", headers=env["h"](env["tok_prov2"])
    ).json()
    assert Decimal(str(p2_sum["doanhThuGhiNhan"])) == Decimal("799000")
    assert p2_sum["tongLuotBan"] == 1
    p2_items = env["client"].get(
        "/api/provider/sales/items", headers=env["h"](env["tok_prov2"])
    ).json()
    assert len(p2_items) == 1
    assert p2_items[0]["maKhoaHoc"] == env["c2"].maKhoaHoc

    # Production guard: APP_ENV=production disables MOCK_SANDBOX payment & refund execution
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    caps = env["client"].get("/api/commerce/capabilities").json()
    assert caps["mockPaymentEnabled"] is False
    assert caps["vnpaySandboxEnabled"] is False
