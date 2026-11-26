"""GĐ4.3 PostgreSQL API, state-machine, rollback-atomicity, security, and
multi-connection concurrency tests for Order, Checkout & Mock Payment Sandbox.

Strictly runs ONLY against EduSuggest_phase4_test (refuses to run on EduSuggest).
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
from sqlalchemy.orm import Session, sessionmaker

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
from schemas.commerce import (
    MockPaymentCallbackRequest,
    OrderCreateRequest,
    PaymentInitiateRequest,
)
from service import order_payment_service
from service.commerce_service import CommerceConflictError
from service.payment_providers import compute_mock_callback_signature
from utils.security import create_access_token, hash_password


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ4.3 tests require EduSuggest_phase4_test database.")
    return raw


@pytest.fixture(scope="module")
def pg_engine():
    url = _phase4_test_url()
    engine = create_engine(url, pool_pre_ping=True, pool_size=12, max_overflow=12)
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        assert db_name == "EduSuggest_phase4_test", f"Refusing to run on {db_name}"
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert rev in {"d4e5f6a7b8c9", "e5f6a7b8c9d0"}, f"Unexpected revision {rev}"
    yield engine
    engine.dispose()


@pytest.fixture
def env_data(pg_engine, monkeypatch):
    monkeypatch.setenv("MOCK_PAYMENT_ENABLED", "true")
    monkeypatch.setenv("COMMERCE_ENROLLMENT_GATE_ENABLED", "true")
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
            assert role is not None
            tag = uuid.uuid4().hex[:8]
            pwd_hash = hash_password(f"P43!{tag}99")
            u = NguoiDung(
                maVaiTro=role.maVaiTro,
                tenTaiKhoan=f"p43_{role_name.lower()}_{tag}",
                hoTen=f"P43 {role_name} {tag}",
                email=f"p43_{tag}@example.test",
                matKhau=pwd_hash,
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            db.add(u)
            db.flush()
            created_users.append(u.maNguoiDung)
            tok = create_access_token(u.maNguoiDung, pwd_hash).encoded
            return u, tok

        def _make_course(gia: Decimal | None, approval="APPROVED", visibility="VISIBLE") -> tuple[KhoaHoc, BaiHoc]:
            tag = uuid.uuid4().hex[:8]
            now = datetime.now(UTC).replace(tzinfo=None)
            c = KhoaHoc(
                maNhaCungCap=provider_id,
                maDanhMuc=category_id,
                tieuDe=f"P43 Course {tag}",
                moTa="Khóa học kiểm thử Order & Mock Payment GĐ4.3",
                gia=gia,
                trinhDo="Intermediate",
                thoiLuong=120,
                trangThaiDuyet=approval,
                trangThaiHienThi=visibility,
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add(c)
            db.flush()
            l = BaiHoc(
                maKhoaHoc=c.maKhoaHoc,
                tieuDe=f"Bài 1 {tag}",
                noiDung="Nội dung bài học",
                thoiLuong=30,
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
        c1, l1 = _make_course(Decimal("350000"))
        c2, l2 = _make_course(Decimal("550000"))
        c_revoked, l_rev = _make_course(Decimal("420000"))
        c_free, _ = _make_course(Decimal("0"))

        now = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            DangKyKhoaHoc(
                maNguoiDung=user_a.maNguoiDung,
                maKhoaHoc=c_revoked.maKhoaHoc,
                ngayDangKy=now,
                tienDo=Decimal("60"),
                nguonCapQuyen="PURCHASE",
                trangThaiQuyenHoc="REVOKED",
                ngayThuHoi=now,
                lyDoThuHoi="Hoàn tiền trước đó",
            )
        )
        db.add(
            LichSuHocTap(
                maNguoiDung=user_a.maNguoiDung,
                maKhoaHoc=c_revoked.maKhoaHoc,
                maBaiHoc=l_rev.maBaiHoc,
                tienDo="COMPLETED",
                ngayTao=now,
            )
        )
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
            "c_revoked": c_revoked.maKhoaHoc,
            "l_rev": l_rev.maBaiHoc,
            "c_free": c_free.maKhoaHoc,
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


def _signed_callback(
    *,
    txn_ref: str,
    order_id: int,
    amount: Decimal,
    outcome: str = "PAID",
    currency: str = "VND",
    gw_txn: str | None = None,
) -> dict:
    gw = gw_txn or f"MOCK-GW-{uuid.uuid4().hex[:8].upper()}"
    sig = compute_mock_callback_signature(
        internal_txn_ref=txn_ref,
        order_id=order_id,
        amount=amount,
        currency=currency,
        outcome=outcome,
        gateway_txn_id=gw,
    )
    return {
        "maGiaoDichNoiBo": txn_ref,
        "maGiaoDichCong": gw,
        "maDonHang": order_id,
        "soTien": str(amount),
        "donViTienTe": currency,
        "ketQua": outcome,
        "signature": sig,
    }


# ---------------------------------------------------------------------------
# 1. Feature flag OFF blocks Mock Payment + COM-01 blocks direct paid enroll
# ---------------------------------------------------------------------------
def test_mock_payment_flag_off_and_com01_http_402(env_data, monkeypatch):
    client = env_data["client"]
    h_a = _auth(env_data["token_a"])

    # Direct enrollment on paid course returns HTTP 402 when Commerce gate is ON
    r_bypass = client.post(f"/api/courses/{env_data['c1']}/enrollments", headers=h_a)
    assert r_bypass.status_code == 402

    # Create a Buy Now order
    r_ord = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": env_data["c1"]},
        headers=_auth(env_data["token_a"], f"ord-{uuid.uuid4().hex[:8]}"),
    )
    assert r_ord.status_code == 201
    oid = r_ord.json()["maDonHang"]

    # Turn OFF Mock Payment flag -> initiate payment MUST return 403
    monkeypatch.setenv("MOCK_PAYMENT_ENABLED", "false")
    get_settings.cache_clear()
    r_pay_off = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "MOCK_SANDBOX"},
        headers=_auth(env_data["token_a"], f"pay-{uuid.uuid4().hex[:8]}"),
    )
    assert r_pay_off.status_code == 403


# ---------------------------------------------------------------------------
# 2. Selective Cart Checkout -> Mock PAID -> Partial Cart Prune & Notification
# ---------------------------------------------------------------------------
def test_selective_cart_checkout_paid_partial_prune_and_no_cancel_after_paid(env_data):
    client = env_data["client"]
    tok = env_data["token_a"]
    c1, c2 = env_data["c1"], env_data["c2"]

    # Add BOTH c1 and c2 to cart
    assert client.post("/api/cart/items", json={"maKhoaHoc": c1}, headers=_auth(tok)).status_code == 200
    assert client.post("/api/cart/items", json={"maKhoaHoc": c2}, headers=_auth(tok)).status_code == 200

    # Preview ONLY c1
    prev = client.post(
        "/api/orders/preview",
        json={"nguonTao": "CART", "courseIds": [c1]},
        headers=_auth(tok),
    )
    assert prev.status_code == 200
    assert Decimal(str(prev.json()["tongTien"])) == Decimal("350000")

    # Create order for ONLY c1
    ord_res = client.post(
        "/api/orders",
        json={"nguonTao": "CART", "courseIds": [c1], "tongTienXacNhan": "350000"},
        headers=_auth(tok, f"sel-{uuid.uuid4().hex[:8]}"),
    )
    assert ord_res.status_code == 201
    order = ord_res.json()
    oid = order["maDonHang"]

    # Initiate Mock Payment
    pay_res = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "MOCK_SANDBOX"},
        headers=_auth(tok, f"pay-{uuid.uuid4().hex[:8]}"),
    )
    assert pay_res.status_code == 201
    pay = pay_res.json()
    assert pay["laThanhToanMoPhong"] is True

    # Signed server callback -> PAID
    cb_res = client.post(
        "/api/payments/mock/callback",
        json=_signed_callback(
            txn_ref=pay["maGiaoDichNoiBo"],
            order_id=oid,
            amount=Decimal("350000"),
            outcome="PAID",
        ),
    )
    assert cb_res.status_code == 200
    cb = cb_res.json()
    assert cb["trangThaiDonHang"] == "PAID"
    assert cb["daCapQuyenHoc"] is True
    assert cb["soKhoaHocKichHoat"] == 1

    # Cart MUST still contain c2 (only c1 pruned!)
    cart_after = client.get("/api/cart", headers=_auth(tok)).json()
    assert cart_after["tongSoLuong"] == 1
    assert cart_after["items"][0]["maKhoaHoc"] == c2

    # Cannot cancel PAID order
    assert client.post(f"/api/orders/{oid}/cancel", headers=_auth(tok)).status_code == 409

    # Learning course access works & notification created
    assert client.get(f"/api/learning/courses/{c1}", headers=_auth(tok)).status_code == 200
    db = env_data["SessionLocal"]()
    try:
        notif = db.scalar(
            select(ThongBao).where(
                ThongBao.maNguoiNhan == env_data["user_a"],
                ThongBao.loaiThongBao == "ORDER_PAID",
            )
        )
        assert notif is not None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Price Tampering, IDOR, Price Change Confirm, Snapshot Immutability
# ---------------------------------------------------------------------------
def test_price_tampering_idor_price_change_and_snapshot_immutability(env_data):
    client = env_data["client"]
    tok_a, tok_b = env_data["token_a"], env_data["token_b"]
    c1 = env_data["c1"]

    # Price tampering fields rejected (422)
    assert (
        client.post(
            "/api/orders",
            json={"nguonTao": "BUY_NOW", "maKhoaHoc": c1, "tongTien": 1000},
            headers=_auth(tok_a, "tamper-1"),
        ).status_code
        == 422
    )

    # Price changed since preview (expected 350k, DB changed to 380k) -> 409 confirm required
    db = env_data["SessionLocal"]()
    try:
        c = db.get(KhoaHoc, c1)
        c.gia = Decimal("380000")
        db.commit()
    finally:
        db.close()

    r_chg = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": c1, "tongTienXacNhan": "350000"},
        headers=_auth(tok_a, "chg-1"),
    )
    assert r_chg.status_code == 409

    # Re-confirmed at 380k -> succeeds with snapshot 380k
    r_ok = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": c1, "tongTienXacNhan": "380000"},
        headers=_auth(tok_a, "chg-2"),
    )
    assert r_ok.status_code == 201
    oid = r_ok.json()["maDonHang"]

    # IDOR: User B cannot view, check status, cancel, or pay User A's order
    assert client.get(f"/api/orders/{oid}", headers=_auth(tok_b)).status_code == 404
    assert client.get(f"/api/orders/{oid}/status", headers=_auth(tok_b)).status_code == 404
    assert client.post(f"/api/orders/{oid}/cancel", headers=_auth(tok_b)).status_code == 404
    assert (
        client.post(
            f"/api/orders/{oid}/payments",
            json={"congThanhToan": "MOCK_SANDBOX"},
            headers=_auth(tok_b, "idor-pay"),
        ).status_code
        == 404
    )

    # DB price changes AGAIN to 500k AFTER order created -> payment uses immutable snapshot 380k!
    db = env_data["SessionLocal"]()
    try:
        c = db.get(KhoaHoc, c1)
        c.gia = Decimal("500000")
        db.commit()
    finally:
        db.close()

    pay = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "MOCK_SANDBOX"},
        headers=_auth(tok_a, "snap-pay"),
    )
    assert pay.status_code == 201
    assert Decimal(str(pay.json()["soTien"])) == Decimal("380000")


# ---------------------------------------------------------------------------
# 4. Fake Callback, Invalid Signature, Amount Mismatch, Failed + Retry in TTL
# ---------------------------------------------------------------------------
def test_fake_callback_signature_amount_mismatch_and_retry_after_failure(env_data):
    client = env_data["client"]
    tok = env_data["token_a"]
    c1 = env_data["c1"]

    oid = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": c1},
        headers=_auth(tok, "retry-ord"),
    ).json()["maDonHang"]

    p1 = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "MOCK_SANDBOX"},
        headers=_auth(tok, "retry-p1"),
    ).json()

    # Invalid signature -> 403
    bad_sig = _signed_callback(txn_ref=p1["maGiaoDichNoiBo"], order_id=oid, amount=Decimal("350000"))
    bad_sig["signature"] = "0" * 64
    assert client.post("/api/payments/mock/callback", json=bad_sig).status_code == 403

    # Wrong amount -> 400 (even with valid signature for wrong amount!)
    bad_amt = _signed_callback(txn_ref=p1["maGiaoDichNoiBo"], order_id=oid, amount=Decimal("1000"))
    assert client.post("/api/payments/mock/callback", json=bad_amt).status_code == 400

    # Wrong txnRef -> 404
    bad_ref = _signed_callback(txn_ref="TXN-NONEXISTENT-999", order_id=oid, amount=Decimal("350000"))
    assert client.post("/api/payments/mock/callback", json=bad_ref).status_code == 404

    # Attempt 1 fails -> order becomes FAILED (still retryable within TTL)
    cb_fail = client.post(
        "/api/payments/mock/callback",
        json=_signed_callback(
            txn_ref=p1["maGiaoDichNoiBo"],
            order_id=oid,
            amount=Decimal("350000"),
            outcome="FAILED",
        ),
    )
    assert cb_fail.status_code == 200 and cb_fail.json()["trangThaiDonHang"] == "FAILED"

    # Attempt 2 within TTL -> succeeds and activates enrollment!
    p2 = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "MOCK_SANDBOX"},
        headers=_auth(tok, "retry-p2"),
    ).json()
    cb_ok = client.post(
        "/api/payments/mock/callback",
        json=_signed_callback(
            txn_ref=p2["maGiaoDichNoiBo"],
            order_id=oid,
            amount=Decimal("350000"),
            outcome="PAID",
        ),
    )
    assert cb_ok.status_code == 200 and cb_ok.json()["trangThaiDonHang"] == "PAID"


# ---------------------------------------------------------------------------
# 5. Rollback Atomicity (mid-flight error) + Safe Retry + REVOKED Repurchase
# ---------------------------------------------------------------------------
def test_midflight_rollback_retry_and_revoked_repurchase(env_data):
    SessionLocal = env_data["SessionLocal"]
    client = env_data["client"]
    tok = env_data["token_a"]
    c_rev = env_data["c_revoked"]

    # Buy Now on REVOKED course
    ord_res = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": c_rev},
        headers=_auth(tok, "rev-buy-1"),
    )
    assert ord_res.status_code == 201
    oid = ord_res.json()["maDonHang"]
    pay = client.post(
        f"/api/orders/{oid}/payments",
        json={"congThanhToan": "MOCK_SANDBOX"},
        headers=_auth(tok, "rev-pay-1"),
    ).json()

    cb_payload = MockPaymentCallbackRequest(
        **_signed_callback(
            txn_ref=pay["maGiaoDichNoiBo"],
            order_id=oid,
            amount=Decimal("420000"),
            outcome="PAID",
        )
    )

    # Simulate crash AFTER payment/order flush and BEFORE enrollment activation
    def _boom():
        raise RuntimeError("Simulated mid-transaction DB failure")

    s1 = SessionLocal()
    try:
        with pytest.raises(RuntimeError):
            order_payment_service.process_mock_payment_callback(
                s1, cb_payload, _post_payment_hook=_boom
            )
    finally:
        s1.close()

    # Verify clean rollback: Order & Payment still PENDING, enrollment still REVOKED!
    s2 = SessionLocal()
    try:
        assert s2.get(DonHang, oid).trangThai == "PENDING"
        assert s2.get(ThanhToan, pay["maThanhToan"]).trangThai == "PENDING"
        enr = s2.scalars(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == env_data["user_a"],
                DangKyKhoaHoc.maKhoaHoc == c_rev,
            )
        ).one()
        assert enr.trangThaiQuyenHoc == "REVOKED"

        # Retry callback cleanly -> succeeds, reactivates REVOKED, preserves tienDo=60 & LichSuHocTap!
        res = order_payment_service.process_mock_payment_callback(s2, cb_payload)
        assert res.trangThaiDonHang == "PAID" and res.daCapQuyenHoc is True
        s2.refresh(enr)
        assert enr.trangThaiQuyenHoc == "ACTIVE"
        assert enr.maDonHang == oid
        assert Decimal(enr.tienDo) == Decimal("60")
        hist_cnt = s2.scalar(
            select(func.count(LichSuHocTap.maLichSu)).where(
                LichSuHocTap.maNguoiDung == env_data["user_a"],
                LichSuHocTap.maKhoaHoc == c_rev,
            )
        )
        assert hist_cnt == 1
    finally:
        s2.close()


# ---------------------------------------------------------------------------
# 6. Course Hidden After Order, Account Locked Before Payment, Expired + Late Callback
# ---------------------------------------------------------------------------
def test_hidden_course_locked_account_and_late_callback_after_expiry(env_data):
    client = env_data["client"]
    SessionLocal = env_data["SessionLocal"]
    tok = env_data["token_a"]
    c1, c2 = env_data["c1"], env_data["c2"]

    # 6a. Order expires -> late PAID callback records reconciliation, does NOT grant enrollment
    oid_exp = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": c1},
        headers=_auth(tok, "exp-ord"),
    ).json()["maDonHang"]
    pay_exp = client.post(
        f"/api/orders/{oid_exp}/payments",
        json={"congThanhToan": "MOCK_SANDBOX"},
        headers=_auth(tok, "exp-pay"),
    ).json()

    db = SessionLocal()
    try:
        o = db.get(DonHang, oid_exp)
        o.hanThanhToan = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    assert client.get(f"/api/orders/{oid_exp}/status", headers=_auth(tok)).json()["trangThai"] == "EXPIRED"
    cb_late = client.post(
        "/api/payments/mock/callback",
        json=_signed_callback(
            txn_ref=pay_exp["maGiaoDichNoiBo"],
            order_id=oid_exp,
            amount=Decimal("350000"),
            outcome="PAID",
        ),
    )
    assert cb_late.status_code == 200
    assert cb_late.json()["canDoiSoat"] is True
    assert cb_late.json()["daCapQuyenHoc"] is False

    # 6b. Course hidden AFTER order created -> blocks payment initiation (409)
    oid_hid = client.post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": c2},
        headers=_auth(tok, "hid-ord"),
    ).json()["maDonHang"]
    db = SessionLocal()
    try:
        course2 = db.get(KhoaHoc, c2)
        course2.trangThaiHienThi = "HIDDEN"
        db.commit()
    finally:
        db.close()
    assert (
        client.post(
            f"/api/orders/{oid_hid}/payments",
            json={"congThanhToan": "MOCK_SANDBOX"},
            headers=_auth(tok, "hid-pay"),
        ).status_code
        == 409
    )

    # 6c. Account LOCKED before payment -> blocked (403)
    db = SessionLocal()
    try:
        u = db.get(NguoiDung, env_data["user_a"])
        u.trangThai = "LOCKED"
        db.commit()
    finally:
        db.close()
    assert (
        client.post(
            f"/api/orders/{oid_hid}/payments",
            json={"congThanhToan": "MOCK_SANDBOX"},
            headers=_auth(tok, "lock-pay"),
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# 7. Multi-Connection Concurrency: Double-Click, Duplicate Callback,
#    2 Orders Same Course, 2 Payments Same Order, Pay vs Cancel Race
# ---------------------------------------------------------------------------
def test_multi_connection_concurrency_invariants(env_data):
    SessionLocal = env_data["SessionLocal"]
    uid = env_data["user_b"]
    c1, c2 = env_data["c1"], env_data["c2"]

    def _user(s: Session) -> NguoiDung:
        u = s.get(NguoiDung, uid)
        _ = u.vaiTro
        return u

    # 7a. Double-click Checkout (6 threads, SAME Idempotency-Key) -> exactly 1 order
    same_key = f"dbl-{uuid.uuid4().hex[:8]}"

    def _create_same(_):
        s = SessionLocal()
        try:
            res, _ = order_payment_service.create_order(
                s,
                _user(s),
                OrderCreateRequest(nguonTao="BUY_NOW", maKhoaHoc=c1),
                idempotency_key=same_key,
            )
            return res.maDonHang
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        oids = list(pool.map(_create_same, range(6)))
    assert len(set(oids)) == 1
    oid_a = oids[0]

    # 7b. Create a SECOND distinct order for the SAME course c1 (different idempotency key)
    s = SessionLocal()
    try:
        ord_b, _ = order_payment_service.create_order(
            s,
            _user(s),
            OrderCreateRequest(nguonTao="BUY_NOW", maKhoaHoc=c1),
            idempotency_key=f"ordb-{uuid.uuid4().hex[:8]}",
        )
        pay_a1 = order_payment_service.initiate_payment(
            s, _user(s), oid_a, PaymentInitiateRequest(congThanhToan="MOCK_SANDBOX"), idempotency_key="pa1-key"
        )
        pay_a2 = order_payment_service.initiate_payment(
            s, _user(s), oid_a, PaymentInitiateRequest(congThanhToan="MOCK_SANDBOX"), idempotency_key="pa2-key"
        )
        pay_b1 = order_payment_service.initiate_payment(
            s, _user(s), ord_b.maDonHang, PaymentInitiateRequest(congThanhToan="MOCK_SANDBOX"), idempotency_key="pb1-key"
        )
    finally:
        s.close()

    # 7c. Race ALL THREE callbacks simultaneously (2 attempts on oid_a + 1 attempt on ord_b for same c1!)
    cb_specs = [
        _signed_callback(txn_ref=pay_a1.maGiaoDichNoiBo, order_id=oid_a, amount=Decimal("350000")),
        _signed_callback(txn_ref=pay_a2.maGiaoDichNoiBo, order_id=oid_a, amount=Decimal("350000")),
        _signed_callback(txn_ref=pay_b1.maGiaoDichNoiBo, order_id=ord_b.maDonHang, amount=Decimal("350000")),
        # Plus duplicate replay of pay_a1
        _signed_callback(txn_ref=pay_a1.maGiaoDichNoiBo, order_id=oid_a, amount=Decimal("350000"), gw_txn="DUP-GW-1"),
    ]

    def _run_cb(spec):
        s_local = SessionLocal()
        try:
            return order_payment_service.process_mock_payment_callback(
                s_local, MockPaymentCallbackRequest(**spec)
            )
        finally:
            s_local.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        cb_results = list(pool.map(_run_cb, cb_specs))

    # Strict invariants: EXACTLY 1 activation across all 4 concurrent callbacks, 1 PAID payment, 1 enrollment!
    assert sum(r.soKhoaHocKichHoat for r in cb_results) == 1
    s = SessionLocal()
    try:
        enr_cnt = s.scalar(
            select(func.count(DangKyKhoaHoc.maDangKy)).where(
                DangKyKhoaHoc.maNguoiDung == uid,
                DangKyKhoaHoc.maKhoaHoc == c1,
            )
        )
        assert enr_cnt == 1
        paid_pay_cnt = s.scalar(
            select(func.count(ThanhToan.maThanhToan)).where(
                ThanhToan.maDonHang.in_([oid_a, ord_b.maDonHang]),
                ThanhToan.trangThai == "PAID",
            )
        )
        assert paid_pay_cnt == 1
    finally:
        s.close()

    # 7d. Concurrent Payment vs Cancel race on c2
    s = SessionLocal()
    try:
        ord_c2, _ = order_payment_service.create_order(
            s,
            _user(s),
            OrderCreateRequest(nguonTao="BUY_NOW", maKhoaHoc=c2),
            idempotency_key=f"race-c2-{uuid.uuid4().hex[:8]}",
        )
        pay_c2 = order_payment_service.initiate_payment(
            s, _user(s), ord_c2.maDonHang, PaymentInitiateRequest(congThanhToan="MOCK_SANDBOX"), idempotency_key="race-p2"
        )
    finally:
        s.close()

    cb_c2 = _signed_callback(txn_ref=pay_c2.maGiaoDichNoiBo, order_id=ord_c2.maDonHang, amount=Decimal("550000"))

    def _do_pay():
        s_local = SessionLocal()
        try:
            return ("PAY", order_payment_service.process_mock_payment_callback(s_local, MockPaymentCallbackRequest(**cb_c2)))
        finally:
            s_local.close()

    def _do_cancel():
        s_local = SessionLocal()
        try:
            return ("CANCEL", order_payment_service.cancel_my_order(s_local, _user(s_local), ord_c2.maDonHang))
        except CommerceConflictError:
            return ("CANCEL_REJECTED", None)
        finally:
            s_local.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_do_pay)
        f2 = pool.submit(_do_cancel)
        r_pay = f1.result()
        r_cancel = f2.result()

    # Either PAID won (cancel rejected, enrollment active) OR CANCEL won (callback flagged reconciliation, 0 enrollment)
    s = SessionLocal()
    try:
        final_ord = s.get(DonHang, ord_c2.maDonHang)
        c2_enr = s.scalar(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == uid,
                DangKyKhoaHoc.maKhoaHoc == c2,
            )
        )
        if final_ord.trangThai == "PAID":
            assert r_cancel[0] == "CANCEL_REJECTED"
            assert c2_enr is not None and c2_enr.trangThaiQuyenHoc == "ACTIVE"
        else:
            assert final_ord.trangThai == "CANCELLED"
            assert r_pay[1].canDoiSoat is True
            assert c2_enr is None
    finally:
        s.close()
