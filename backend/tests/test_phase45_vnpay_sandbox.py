"""GĐ4.5 VNPay Sandbox (API v2.1.0) test-vector, security, IPN/Return URL,
and multi-connection concurrency tests on EduSuggest_phase4_test.

Uses synthetic test-only credentials strictly in-memory via monkeypatch (never touches .env
and never claims live VNPay Sandbox network execution).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
from urllib.parse import parse_qs, urlparse
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
    compute_vnpay_hmac_sha512,
)
from utils.security import create_access_token, hash_password

_TEST_TMN = "TESTTMN01"
_TEST_SECRET = "TEST_ONLY_IN_MEMORY_HMAC_SHA512_SECRET_KEY_NOT_REAL"
_TEST_RETURN = "http://127.0.0.1:5176/payment/result"


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ4.5 tests require EduSuggest_phase4_test database.")
    return raw


@pytest.fixture(scope="module")
def pg_engine():
    url = _phase4_test_url()
    engine = create_engine(url, pool_pre_ping=True, pool_size=12, max_overflow=12)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        assert db_name == "EduSuggest_phase4_test", f"Refusing to run on {db_name}"
    yield engine
    engine.dispose()


def _sign_vnpay_params(params: dict[str, str], secret: str = _TEST_SECRET) -> dict[str, str]:
    signed = dict(params)
    hash_data = build_vnpay_hash_data(signed)
    signed["vnp_SecureHash"] = compute_vnpay_hmac_sha512(hash_data, secret)
    return signed


@pytest.fixture
def env_data(pg_engine, monkeypatch):
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
    created_courses: list[int] = []
    created_lessons: list[int] = []

    try:
        provider_id = db.scalar(select(NhaCungCapKhoaHoc.maNhaCungCap).limit(1))
        category_id = db.scalar(select(DanhMuc.maDanhMuc).limit(1))
        assert provider_id is not None and category_id is not None

        def _make_user(role_name: str) -> tuple[NguoiDung, str]:
            role = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == role_name)).first()
            tag = uuid.uuid4().hex[:8]
            pwd_hash = hash_password(f"P45!{tag}99")
            u = NguoiDung(
                maVaiTro=role.maVaiTro,
                tenTaiKhoan=f"p45_{tag}",
                hoTen=f"P45 User {tag}",
                email=f"p45_{tag}@example.test",
                matKhau=pwd_hash,
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            db.add(u)
            db.flush()
            created_users.append(u.maNguoiDung)
            return u, create_access_token(u.maNguoiDung, pwd_hash).encoded

        def _make_course(gia: Decimal) -> tuple[KhoaHoc, BaiHoc]:
            tag = uuid.uuid4().hex[:8]
            now = datetime.now(UTC).replace(tzinfo=None)
            c = KhoaHoc(
                maNhaCungCap=provider_id,
                maDanhMuc=category_id,
                tieuDe=f"P45 VNPay Course {tag}",
                moTa="Khóa học kiểm thử VNPay Sandbox GĐ4.5",
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

        user_a, token_a = _make_user("USER")
        user_b, token_b = _make_user("USER")
        c1, _ = _make_course(Decimal("499000"))
        c2, _ = _make_course(Decimal("299000"))
        db.commit()

        yield {
            "client": client,
            "SessionLocal": SessionLocal,
            "user_a": user_a.maNguoiDung,
            "token_a": token_a,
            "user_b": user_b.maNguoiDung,
            "token_b": token_b,
            "c1": c1.maKhoaHoc,
            "c2": c2.maKhoaHoc,
        }
    finally:
        app.dependency_overrides.pop(get_db, None)
        get_settings.cache_clear()
        db.rollback()
        if created_users:
            db.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_(created_users)))
            db.execute(delete(LichSuHocTap).where(LichSuHocTap.maNguoiDung.in_(created_users)))
            db.execute(delete(DangKyKhoaHoc).where(DangKyKhoaHoc.maNguoiDung.in_(created_users)))
            db.execute(delete(YeuThich).where(YeuThich.maNguoiDung.in_(created_users)))
            cart_ids = list(db.scalars(select(GioHang.maGioHang).where(GioHang.maNguoiDung.in_(created_users))))
            if cart_ids:
                db.execute(delete(ChiTietGioHang).where(ChiTietGioHang.maGioHang.in_(cart_ids)))
                db.execute(delete(GioHang).where(GioHang.maGioHang.in_(cart_ids)))
            order_ids = list(db.scalars(select(DonHang.maDonHang).where(DonHang.maNguoiDung.in_(created_users))))
            if order_ids:
                db.execute(text("SET LOCAL session_replication_role = 'replica'"))
                db.execute(text('DELETE FROM "TacVuDoiSoatThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": order_ids})
                db.execute(text('DELETE FROM "SuKienThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": order_ids})
                db.execute(text('DELETE FROM "BaoCaoSuCoThanhToan" WHERE "maDonHang" = ANY(:oids)'), {"oids": order_ids})
                db.execute(text('DELETE FROM "LanThuHoanTien" WHERE "maHoanTien" IN (SELECT "maHoanTien" FROM "HoanTienNgoaiLe" WHERE "maDonHang" = ANY(:oids))'), {"oids": order_ids})
                db.execute(text('DELETE FROM "HoanTienNgoaiLe" WHERE "maDonHang" = ANY(:oids)'), {"oids": order_ids})
                db.execute(delete(ThanhToan).where(ThanhToan.maDonHang.in_(order_ids)))
                db.execute(delete(ChiTietDonHang).where(ChiTietDonHang.maDonHang.in_(order_ids)))
                db.execute(delete(DonHang).where(DonHang.maDonHang.in_(order_ids)))
        if created_lessons:
            db.execute(delete(BaiHoc).where(BaiHoc.maBaiHoc.in_(created_lessons)))
        if created_courses:
            db.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(created_courses)))
        if created_users:
            db.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(created_users)))
        db.commit()
        db.close()


def _auth(tok: str, idem: str | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {tok}"}
    if idem:
        h["Idempotency-Key"] = idem
    return h


# ---------------------------------------------------------------------------
# 1. Feature Flag OFF & Production Safety Guard
# ---------------------------------------------------------------------------
def test_vnpay_flag_off_and_production_guard(env_data, monkeypatch):
    client = env_data["client"]
    tok = env_data["token_a"]

    oid = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": env_data["c1"]},
        headers=_auth(tok, "vnp-off-ord"),
    ).json()["maDonHang"]

    # Turn OFF VNPAY_SANDBOX_ENABLED
    monkeypatch.setenv("VNPAY_SANDBOX_ENABLED", "false")
    get_settings.cache_clear()
    assert client.get("/api/commerce/capabilities").json()["vnpaySandboxEnabled"] is False
    assert (
        client.post(
            f"/api/orders/{oid}/payments",
            json={"congThanhToan": "VNPAY_SANDBOX"},
            headers=_auth(tok, "vnp-off-pay"),
        ).status_code
        == 403
    )
    assert client.get("/api/payments/vnpay/ipn", params={"vnp_TxnRef": "X"}).json()["RspCode"] == "99"

    # Re-enable flag but set APP_ENV=production -> STILL blocked!
    monkeypatch.setenv("VNPAY_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    assert client.get("/api/commerce/capabilities").json()["vnpaySandboxEnabled"] is False
    assert (
        client.post(
            f"/api/orders/{oid}/payments",
            json={"congThanhToan": "VNPAY_SANDBOX"},
            headers=_auth(tok, "vnp-prod-pay"),
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# 2. Official VNPay v2.1.0 URL Generation, HMAC-SHA512 & Return URL Read-Only
# ---------------------------------------------------------------------------
def test_vnpay_url_generation_return_readonly_and_tampering(env_data):
    client = env_data["client"]
    tok_a, tok_b = env_data["token_a"], env_data["token_b"]

    assert client.get("/api/commerce/capabilities").json()["vnpaySandboxEnabled"] is True

    oid = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": env_data["c1"]},
        headers=_auth(tok_a, "vnp-url-ord"),
    ).json()["maDonHang"]

    pay_res = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "VNPAY_SANDBOX"},
        headers=_auth(tok_a, "vnp-url-pay"),
    )
    assert pay_res.status_code == 201
    pay = pay_res.json()
    assert pay["congThanhToan"] == "VNPAY_SANDBOX"
    assert pay["laThanhToanMoPhong"] is False
    assert _TEST_SECRET not in pay["paymentUrl"]

    # Validate VNPay v2.1.0 query params & independent HMAC-SHA512 verification
    parsed = urlparse(pay["paymentUrl"])
    assert parsed.scheme == "https" and parsed.netloc == "sandbox.vnpayment.vn"
    qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert qs["vnp_Version"] == "2.1.0"
    assert qs["vnp_Command"] == "pay"
    assert qs["vnp_TmnCode"] == _TEST_TMN
    assert qs["vnp_Amount"] == "49900000"  # 499,000 VND * 100
    assert qs["vnp_CurrCode"] == "VND"
    assert qs["vnp_TxnRef"] == pay["maGiaoDichNoiBo"]
    assert len(qs["vnp_CreateDate"]) == 14 and len(qs["vnp_ExpireDate"]) == 14
    assert qs["vnp_ExpireDate"] > qs["vnp_CreateDate"]
    expected_sig = compute_vnpay_hmac_sha512(build_vnpay_hash_data(qs), _TEST_SECRET)
    assert qs["vnp_SecureHash"] == expected_sig

    # Signed Return URL with vnp_ResponseCode=00 MUST remain strictly READ ONLY (does NOT grant enrollment!)
    ret_params = _sign_vnpay_params(
        {
            "vnp_TmnCode": _TEST_TMN,
            "vnp_Amount": "49900000",
            "vnp_TxnRef": pay["maGiaoDichNoiBo"],
            "vnp_ResponseCode": "00",
            "vnp_TransactionStatus": "00",
            "vnp_TransactionNo": "144556677",
            "vnp_BankCode": "NCB",
        }
    )
    ret_ok = client.get("/api/payments/vnpay/return", params=ret_params, headers=_auth(tok_a)).json()
    assert ret_ok["signatureValid"] is True
    assert ret_ok["maDonHang"] == oid
    assert ret_ok["trangThaiDonHangHienTai"] == "PENDING"
    assert client.get(f"/api/learning/courses/{env_data['c1']}", headers=_auth(tok_a)).status_code == 403

    # Cross-user Return URL check -> zero leakage of User A's order ID
    ret_cross = client.get("/api/payments/vnpay/return", params=ret_params, headers=_auth(tok_b)).json()
    assert ret_cross["maDonHang"] is None

    # Return URL tampering (change amount) -> signatureValid=False
    tampered = dict(ret_params)
    tampered["vnp_Amount"] = "100000"
    ret_bad = client.get("/api/payments/vnpay/return", params=tampered, headers=_auth(tok_a)).json()
    assert ret_bad["signatureValid"] is False


# ---------------------------------------------------------------------------
# 3. VNPay IPN: Invalid Sig (97), Not Found (01), Amount Mismatch (04),
#    Success (00) + Atomic Enrollment, Duplicate IPN (02), Concurrent IPNs
# ---------------------------------------------------------------------------
def test_vnpay_ipn_validation_atomic_enrollment_and_concurrency(env_data):
    client = env_data["client"]
    SessionLocal = env_data["SessionLocal"]
    tok = env_data["token_a"]
    c1 = env_data["c1"]

    oid = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": c1},
        headers=_auth(tok, "vnp-ipn-ord"),
    ).json()["maDonHang"]
    pay = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "VNPAY_SANDBOX"},
        headers=_auth(tok, "vnp-ipn-pay"),
    ).json()
    txn_ref = pay["maGiaoDichNoiBo"]

    # 3a. Invalid signature -> RspCode 97
    bad_sig = _sign_vnpay_params(
        {"vnp_TmnCode": _TEST_TMN, "vnp_Amount": "49900000", "vnp_TxnRef": txn_ref, "vnp_ResponseCode": "00"}
    )
    bad_sig["vnp_SecureHash"] = "f" * 128
    assert client.get("/api/payments/vnpay/ipn", params=bad_sig).json()["RspCode"] == "97"

    # 3b. Unknown TxnRef -> RspCode 01
    unknown = _sign_vnpay_params(
        {"vnp_TmnCode": _TEST_TMN, "vnp_Amount": "49900000", "vnp_TxnRef": "TXN-UNKNOWN-999", "vnp_ResponseCode": "00"}
    )
    assert client.get("/api/payments/vnpay/ipn", params=unknown).json()["RspCode"] == "01"

    # 3c. Amount mismatch -> RspCode 04
    wrong_amt = _sign_vnpay_params(
        {"vnp_TmnCode": _TEST_TMN, "vnp_Amount": "1000000", "vnp_TxnRef": txn_ref, "vnp_ResponseCode": "00"}
    )
    assert client.get("/api/payments/vnpay/ipn", params=wrong_amt).json()["RspCode"] == "04"

    # 3d. Concurrent valid PAID IPNs (6 parallel threads) -> 1x RspCode 00, 5x RspCode 02, 1 enrollment!
    valid_ipn = _sign_vnpay_params(
        {
            "vnp_TmnCode": _TEST_TMN,
            "vnp_Amount": "49900000",
            "vnp_TxnRef": txn_ref,
            "vnp_ResponseCode": "00",
            "vnp_TransactionStatus": "00",
            "vnp_TransactionNo": "VNP99887766",
            "vnp_BankCode": "NCB",
        }
    )

    def _call_ipn(_):
        s = SessionLocal()
        try:
            return order_payment_service.process_vnpay_ipn(s, valid_ipn).RspCode
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(_call_ipn, range(6)))

    assert codes.count("00") == 1
    assert codes.count("02") == 5

    # Verify atomic enrollment & learning access
    assert client.get(f"/api/learning/courses/{c1}", headers=_auth(tok)).status_code == 200
    s = SessionLocal()
    try:
        cnt = s.scalar(
            select(func.count(DangKyKhoaHoc.maDangKy)).where(
                DangKyKhoaHoc.maNguoiDung == env_data["user_a"],
                DangKyKhoaHoc.maKhoaHoc == c1,
            )
        )
        assert cnt == 1
    finally:
        s.close()


# ---------------------------------------------------------------------------
# 4. VNPay Failure (99), Cancel (24), Timeout (11), Late IPN Reconciliation
# ---------------------------------------------------------------------------
def test_vnpay_failure_cancel_timeout_and_late_ipn_reconciliation(env_data):
    client = env_data["client"]
    SessionLocal = env_data["SessionLocal"]
    tok = env_data["token_a"]
    c2 = env_data["c2"]

    oid = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": c2},
        headers=_auth(tok, "vnp-states-ord"),
    ).json()["maDonHang"]

    # Attempt 1: Cancelled by user (vnp_ResponseCode=24) -> order stays PENDING for retry
    p1 = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "VNPAY_SANDBOX"},
        headers=_auth(tok, "vnp-st-p1"),
    ).json()
    ipn_cancel = _sign_vnpay_params(
        {"vnp_TmnCode": _TEST_TMN, "vnp_Amount": "29900000", "vnp_TxnRef": p1["maGiaoDichNoiBo"], "vnp_ResponseCode": "24", "vnp_TransactionStatus": "02"}
    )
    assert client.get("/api/payments/vnpay/ipn", params=ipn_cancel).json()["RspCode"] == "00"
    assert client.get(f"/api/orders/{oid}/status", headers=_auth(tok)).json()["trangThai"] == "PENDING"

    # Attempt 2: Bank failure (vnp_ResponseCode=51) -> order FAILED (retryable within TTL)
    p2 = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "VNPAY_SANDBOX"},
        headers=_auth(tok, "vnp-st-p2"),
    ).json()
    ipn_fail = _sign_vnpay_params(
        {"vnp_TmnCode": _TEST_TMN, "vnp_Amount": "29900000", "vnp_TxnRef": p2["maGiaoDichNoiBo"], "vnp_ResponseCode": "51", "vnp_TransactionStatus": "02"}
    )
    assert client.get("/api/payments/vnpay/ipn", params=ipn_fail).json()["RspCode"] == "00"
    assert client.get(f"/api/orders/{oid}/status", headers=_auth(tok)).json()["trangThai"] == "FAILED"

    # Attempt 3: Order expires, then late PAID IPN arrives -> reconciliationRequired, 0 enrollment!
    p3 = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "VNPAY_SANDBOX"},
        headers=_auth(tok, "vnp-st-p3"),
    ).json()
    db = SessionLocal()
    try:
        o = db.get(DonHang, oid)
        o.hanThanhToan = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=2)
        db.commit()
    finally:
        db.close()

    ipn_late = _sign_vnpay_params(
        {"vnp_TmnCode": _TEST_TMN, "vnp_Amount": "29900000", "vnp_TxnRef": p3["maGiaoDichNoiBo"], "vnp_ResponseCode": "00", "vnp_TransactionStatus": "00", "vnp_TransactionNo": "VNP-LATE-01"}
    )
    assert client.get("/api/payments/vnpay/ipn", params=ipn_late).json()["RspCode"] == "00"
    detail = client.get(f"/api/orders/{oid}", headers=_auth(tok)).json()
    assert detail["trangThai"] == "EXPIRED"
    assert any(p["canDoiSoat"] is True for p in detail["thanhToans"])
    assert client.get(f"/api/learning/courses/{c2}", headers=_auth(tok)).status_code == 403
