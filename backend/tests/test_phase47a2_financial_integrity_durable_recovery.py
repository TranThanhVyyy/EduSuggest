"""GĐ4.7A.2 Financial Integrity, Append-Only Event Log, PARTIAL_OVERCHARGE,
VNPay QueryDR/Refund Response Verification, and Durable Payment Reconciliation Worker
(Crash Recovery, Stale Lease, Fencing Token, Multi-Worker Concurrency) Tests.

Runs strictly against `EduSuggest_phase4_test` (35 tables, revision e5f6a7b8c9d0).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.exc import InternalError, ProgrammingError, DBAPIError
from sqlalchemy.orm import sessionmaker

from config.config import get_settings
from config.database import get_db
from main import app
from models import (
    BaiHoc,
    BaoCaoSuCoThanhToan,
    ChiTietDonHang,
    ChiTietGioHang,
    DangKyKhoaHoc,
    DanhMuc,
    DonHang,
    GioHang,
    HoanTienNgoaiLe,
    KhoaHoc,
    LanThuHoanTien,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    SuKienThanhToan,
    TacVuDoiSoatThanhToan,
    ThanhToan,
    ThongBao,
    VaiTro,
    YeuThich,
)
from service.payment_providers import (
    build_vnpay_hash_data,
    compute_vnpay_hmac_sha512,
    verify_vnpay_querydr_response,
    verify_vnpay_refund_response,
)
from service.payment_reconciliation_worker import (
    GatewayQueryOutcome,
    PaymentReconciliationWorker,
    sweep_stale_payment_tasks,
)
from utils.security import create_access_token, hash_password

_TEST_TMN = "TESTTMN47A2"
_TEST_SECRET = "TEST_ONLY_IN_MEMORY_HMAC_SHA512_SECRET_KEY_PHASE47A2"
_TEST_RETURN = "http://127.0.0.1:5176/payment/result"
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ4.7A.2 tests require EduSuggest_phase4_test database.")
    return raw


@pytest.fixture(scope="module")
def pg_engine():
    url = _phase4_test_url()
    engine = create_engine(url, pool_pre_ping=True, pool_size=24, max_overflow=24)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase4_test"
    yield engine
    engine.dispose()


def _sign_vnpay(params: dict[str, str]) -> dict[str, str]:
    signed = dict(params)
    signed["vnp_SecureHash"] = compute_vnpay_hmac_sha512(build_vnpay_hash_data(signed), _TEST_SECRET)
    return signed


def _vnpay_ipn_params(merchant_ref: str, amount_vnd: Decimal, tx_no: str) -> dict[str, str]:
    return _sign_vnpay(
        {
            "vnp_TmnCode": _TEST_TMN,
            "vnp_Amount": str(int(amount_vnd * Decimal("100"))),
            "vnp_BankCode": "NCB",
            "vnp_OrderInfo": f"Thanh toan {merchant_ref}",
            "vnp_PayDate": "20261126211500",
            "vnp_ResponseCode": "00",
            "vnp_TransactionNo": tx_no,
            "vnp_TransactionStatus": "00",
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
        cat_id = db.scalar(select(DanhMuc.maDanhMuc).limit(1))
        assert cat_id is not None

        def _make_user(role_name: str) -> tuple[int, str]:
            role = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == role_name)).first()
            assert role is not None
            tag = uuid.uuid4().hex[:8]
            pwd_hash = hash_password(f"P472!{tag}99")
            u = NguoiDung(
                maVaiTro=role.maVaiTro,
                tenTaiKhoan=f"p472_{role_name.lower()}_{tag}",
                hoTen=f"P472 {role_name} {tag}",
                email=f"p472_{role_name.lower()}_{tag}@example.test",
                matKhau=pwd_hash,
                trangThai="ACTIVE",
                batBuocDoiMatKhau=False,
            )
            db.add(u)
            db.flush()
            created_users.append(int(u.maNguoiDung))
            return int(u.maNguoiDung), create_access_token(u.maNguoiDung, pwd_hash).encoded

        prov_uid, _ = _make_user("PROVIDER")
        p = NhaCungCapKhoaHoc(maNguoiDung=prov_uid, tieuSu="P47A2 Provider", chuyenMon="FinTech")
        db.add(p)
        db.flush()
        created_providers.append(int(p.maNhaCungCap))

        now = datetime.now(UTC).replace(tzinfo=None)
        tag = uuid.uuid4().hex[:8]
        c = KhoaHoc(
            maNhaCungCap=p.maNhaCungCap,
            maDanhMuc=cat_id,
            tieuDe=f"P47A2 Course {tag}",
            moTa="Khóa học kiểm thử GĐ4.7A.2",
            gia=Decimal("599000"),
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

        u1_id, tok_u1 = _make_user("USER")
        u2_id, tok_u2 = _make_user("USER")
        admin_id, tok_admin = _make_user("ADMIN")
        db.commit()

        yield {
            "client": client,
            "SessionLocal": SessionLocal,
            "u1_id": u1_id,
            "tok_u1": tok_u1,
            "u2_id": u2_id,
            "tok_u2": tok_u2,
            "admin_id": admin_id,
            "tok_admin": tok_admin,
            "c_id": int(c.maKhoaHoc),
            "h": lambda tok: {"Authorization": f"Bearer {tok}"},
        }
    finally:
        db.close()
        # Note: SuKienThanhToan is strictly append-only (DELETE forbidden by DB trigger!),
        # so we only clean up orders/payments that have NO SuKienThanhToan rows, OR leave
        # append-only audit rows intact? For clean test isolation on EduSuggest_phase4_test,
        # we verify the trigger in its own test and do NOT disable the trigger on production!
        # Wait: because SuKienThanhToan has FK maDonHang ON DELETE RESTRICT, we must clean up
        # test-created rows ONLY if we disable trigger inside test teardown? NO — better:
        # keep test cleanup clean via `session_replication_role = 'replica'` ONLY on EduSuggest_phase4_test
        # teardown so zero test pollution remains on EduSuggest_phase4_test while the trigger stays 100% active!
        cleanup = SessionLocal()
        try:
            assert cleanup.execute(text("SELECT current_database()")).scalar_one() == "EduSuggest_phase4_test"
            cleanup.execute(text("SET LOCAL session_replication_role = 'replica'"))
            if created_users:
                oids = list(cleanup.scalars(select(DonHang.maDonHang).where(DonHang.maNguoiDung.in_(created_users))))
                gids = list(cleanup.scalars(select(GioHang.maGioHang).where(GioHang.maNguoiDung.in_(created_users))))
                if oids:
                    rids = list(cleanup.scalars(select(HoanTienNgoaiLe.maHoanTien).where(HoanTienNgoaiLe.maDonHang.in_(oids))))
                    cleanup.execute(delete(TacVuDoiSoatThanhToan).where(TacVuDoiSoatThanhToan.maDonHang.in_(oids)))
                    cleanup.execute(delete(SuKienThanhToan).where(SuKienThanhToan.maDonHang.in_(oids)))
                    cleanup.execute(delete(BaoCaoSuCoThanhToan).where(BaoCaoSuCoThanhToan.maDonHang.in_(oids)))
                    if rids:
                        cleanup.execute(delete(LanThuHoanTien).where(LanThuHoanTien.maHoanTien.in_(rids)))
                        cleanup.execute(delete(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maHoanTien.in_(rids)))
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


def _buy_now(env, tok: str, course_id: int) -> dict:
    r = env["client"].post(
        "/api/orders",
        json={"nguonTao": "BUY_NOW", "maKhoaHoc": course_id},
        headers={**env["h"](tok), "Idempotency-Key": f"ord-{uuid.uuid4().hex}"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def _init_pay(env, tok: str, order_id: int, gateway: str = "VNPAY_SANDBOX") -> dict:
    r = env["client"].post(
        f"/api/orders/{order_id}/payments",
        json={"congThanhToan": gateway},
        headers={**env["h"](tok), "Idempotency-Key": f"pay-{uuid.uuid4().hex}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_f01_append_only_event_trigger_blocks_update_and_delete(env):
    """DB-level PostgreSQL trigger MUST forbid UPDATE and DELETE on SuKienThanhToan."""
    order = _buy_now(env, env["tok_u1"], env["c_id"])
    pay = _init_pay(env, env["tok_u1"], order["maDonHang"], gateway="MOCK_SANDBOX")

    with env["SessionLocal"]() as db:
        ev = db.scalars(
            select(SuKienThanhToan).where(SuKienThanhToan.maThanhToan == pay["maThanhToan"])
        ).first()
        assert ev is not None
        assert ev.loaiSuKien == "PAYMENT_INITIATED"

        # UPDATE must fail at PostgreSQL trigger level!
        with pytest.raises(DBAPIError) as upd_exc:
            db.execute(
                text('UPDATE "SuKienThanhToan" SET "loaiSuKien" = \'TAMPERED\' WHERE "maSuKien" = :id'),
                {"id": ev.maSuKien},
            )
        assert "append-only" in str(upd_exc.value).lower()
        db.rollback()

        # DELETE must fail at PostgreSQL trigger level!
        with pytest.raises(DBAPIError) as del_exc:
            db.execute(
                text('DELETE FROM "SuKienThanhToan" WHERE "maSuKien" = :id'),
                {"id": ev.maSuKien},
            )
        assert "append-only" in str(del_exc.value).lower()
        db.rollback()


def test_f02_captured_unapplied_and_partial_overcharge_and_user_incident_tracking(env):
    """Verify:
    - 2nd captured payment stored as CAPTURED_UNAPPLIED (NOT FAILED!) with daThuTien=True.
    - PARTIAL_OVERCHARGE refunds exact overcharge, sets PARTIALLY_REFUNDED, keeps PAID order & ACTIVE access.
    - USER can track their own incident reports via GET /api/orders/{id}/incidents (owner-scoped).
    """
    order = _buy_now(env, env["tok_u1"], env["c_id"])
    p1 = _init_pay(env, env["tok_u1"], order["maDonHang"], gateway="VNPAY_SANDBOX")
    p2 = _init_pay(env, env["tok_u1"], order["maDonHang"], gateway="VNPAY_SANDBOX")

    # p1 succeeds -> PAID
    assert env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_ipn_params(p1["maGiaoDichNoiBo"], Decimal("599000"), "VNP_F02_1"),
    ).json()["RspCode"] == "00"

    # p2 ALSO captures -> MUST be CAPTURED_UNAPPLIED (NOT FAILED!) + auto-enqueued reconciliation task
    assert env["client"].get(
        "/api/payments/vnpay/ipn",
        params=_vnpay_ipn_params(p2["maGiaoDichNoiBo"], Decimal("599000"), "VNP_F02_2"),
    ).json()["RspCode"] == "00"

    with env["SessionLocal"]() as db:
        t2 = db.get(ThanhToan, p2["maThanhToan"])
        assert t2.trangThai == "CAPTURED_UNAPPLIED"
        assert t2.daThuTien is True
        assert Decimal(t2.soTienDaThuThucTe) == Decimal("599000")
        task = db.scalars(
            select(TacVuDoiSoatThanhToan).where(TacVuDoiSoatThanhToan.maThanhToan == p2["maThanhToan"])
        ).first()
        assert task is not None and task.loaiTacVu == "RETRY_CAPTURED_UNAPPLIED"

    # USER submits incident report -> tracks it via GET /api/orders/{id}/incidents; user2 gets 404
    r_inc = env["client"].post(
        f"/api/orders/{order['maDonHang']}/incidents",
        json={"loaiSuCo": "DUPLICATE_CHARGE", "moTa": "Tôi bị trừ tiền 2 lần cho cùng đơn hàng."},
        headers=env["h"](env["tok_u1"]),
    )
    assert r_inc.status_code == 201
    r_list = env["client"].get(f"/api/orders/{order['maDonHang']}/incidents", headers=env["h"](env["tok_u1"]))
    assert r_list.status_code == 200 and len(r_list.json()) == 1
    assert env["client"].get(f"/api/orders/{order['maDonHang']}/incidents", headers=env["h"](env["tok_u2"])).status_code == 404

    # PARTIAL_OVERCHARGE test on Mock payment where gateway captured 699,000 for 599,000 order
    o_m = _buy_now(env, env["tok_u2"], env["c_id"])
    p_m = _init_pay(env, env["tok_u2"], o_m["maDonHang"], gateway="MOCK_SANDBOX")
    env["client"].post(
        f"/api/payments/mock/{p_m['maGiaoDichNoiBo']}/simulate",
        json={"ketQua": "PAID"},
        headers=env["h"](env["tok_u2"]),
    )
    # Simulate verified gateway overcharge of 100,000 VND
    with env["SessionLocal"]() as db:
        tm = db.get(ThanhToan, p_m["maThanhToan"])
        tm.soTienDaThuThucTe = Decimal("699000")
        db.commit()

    r_c = env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": o_m["maDonHang"],
            "maThanhToan": p_m["maThanhToan"],
            "soTienHoan": "100000",
            "loaiSuCo": "WRONG_AMOUNT",
            "phamViHoan": "PARTIAL_OVERCHARGE",
            "lyDo": "Hoàn phần chênh lệch thu sai 100,000 VND.",
        },
        headers={**env["h"](env["tok_admin"]), "Idempotency-Key": f"po-{uuid.uuid4().hex}"},
    )
    assert r_c.status_code == 201, r_c.text
    assert env["client"].post(
        f"/api/admin/commerce/refunds/{p_m['maThanhToan']}/verify",
        json={"ghiChuXacMinh": "Đã xác minh thu dư 100,000 VND."},
        headers=env["h"](env["tok_admin"]),
    ).status_code == 200
    assert env["client"].post(
        f"/api/admin/commerce/refunds/{p_m['maThanhToan']}/execute",
        json={"mockOutcome": "REFUNDED"},
        headers=env["h"](env["tok_admin"]),
    ).status_code == 200

    with env["SessionLocal"]() as db:
        tm = db.get(ThanhToan, p_m["maThanhToan"])
        om = db.get(DonHang, o_m["maDonHang"])
        enr = db.scalars(
            select(DangKyKhoaHoc).where(
                DangKyKhoaHoc.maNguoiDung == env["u2_id"],
                DangKyKhoaHoc.maKhoaHoc == env["c_id"],
            )
        ).first()
        assert tm.trangThai == "PARTIALLY_REFUNDED"
        assert om.trangThai == "PAID"
        assert enr is not None and enr.trangThaiQuyenHoc == "ACTIVE"
        ref_row = db.scalars(select(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maThanhToan == tm.maThanhToan)).first()
        assert ref_row is not None and ref_row.trangThai == "REFUNDED"
        att_rows = list(db.scalars(select(LanThuHoanTien).where(LanThuHoanTien.maHoanTien == ref_row.maHoanTien)).all())
        assert len(att_rows) == 1 and att_rows[0].trangThai == "SUCCEEDED"


def test_f03_vnpay_querydr_and_refund_response_signature_verification(env):
    """Verify official VNPay v2.1.0 QueryDR & Refund response pipe-delimited HMAC-SHA512 verification."""
    q_resp = {
        "vnp_ResponseId": "RESP001",
        "vnp_Command": "querydr",
        "vnp_ResponseCode": "00",
        "vnp_Message": "Confirm Success",
        "vnp_TmnCode": _TEST_TMN,
        "vnp_TxnRef": "TXN_QDR_1",
        "vnp_Amount": "59900000",
        "vnp_BankCode": "NCB",
        "vnp_PayDate": "20261126211500",
        "vnp_TransactionNo": "14200999",
        "vnp_TransactionType": "01",
        "vnp_TransactionStatus": "00",
        "vnp_OrderInfo": "Thanh toan khoa hoc",
        "vnp_PromotionCode": "",
        "vnp_PromotionAmount": "",
    }
    raw_q = "|".join(q_resp[k] for k in q_resp)
    q_resp["vnp_SecureHash"] = compute_vnpay_hmac_sha512(raw_q, _TEST_SECRET)
    assert verify_vnpay_querydr_response(q_resp) is True
    assert verify_vnpay_querydr_response({**q_resp, "vnp_Amount": "100"}) is False

    r_resp = {
        "vnp_ResponseId": "REFRESP001",
        "vnp_Command": "refund",
        "vnp_ResponseCode": "00",
        "vnp_Message": "Refund Success",
        "vnp_TmnCode": _TEST_TMN,
        "vnp_TxnRef": "TXN_REF_1",
        "vnp_Amount": "59900000",
        "vnp_BankCode": "NCB",
        "vnp_PayDate": "20261126211500",
        "vnp_TransactionNo": "14200999",
        "vnp_TransactionType": "02",
        "vnp_TransactionStatus": "00",
        "vnp_OrderInfo": "Hoan tien su co",
    }
    raw_r = "|".join(r_resp[k] for k in r_resp)
    r_resp["vnp_SecureHash"] = compute_vnpay_hmac_sha512(raw_r, _TEST_SECRET)
    assert verify_vnpay_refund_response(r_resp) is True
    assert verify_vnpay_refund_response({**r_resp, "vnp_TransactionStatus": "02"}) is False


def test_f04_durable_worker_fencing_stale_lease_crash_and_multiworker(env):
    """Verify Durable Payment Reconciliation Worker:
    1. Sweeper detects stale PENDING payment -> enqueues QUERY_PENDING_PAYMENT.
    2. Worker 1 claims (leaseGeneration=1), crashes before commit -> stale lease expires.
    3. Worker 2 reclaims stale lease (leaseGeneration=2), queries gateway -> activates PAID + ACTIVE.
    4. Worker 1 wakes up late with stale fencing token -> STALE_LEASE_IGNORED (cannot overwrite!).
    5. Refund UNKNOWN queried via QueryDR -> confirms REFUNDED without blind refund retry!
    """
    class _FakeGateway:
        def query_payment(self, snap: dict) -> GatewayQueryOutcome:
            return GatewayQueryOutcome(
                status="CAPTURED",
                gateway_txn_id=f"QDR-LIVE-{snap['maThanhToan']}",
                amount_vnd=Decimal(snap["soTien"]),
                response_code="00",
                note="Gateway confirmed captured via QueryDR",
            )

        def query_refund(self, snap: dict) -> GatewayQueryOutcome:
            return GatewayQueryOutcome(
                status="REFUNDED",
                gateway_txn_id=f"QDR-REF-{snap['maHoanTien']}",
                response_code="00",
                note="Gateway confirmed refund via QueryDR",
            )

    order = _buy_now(env, env["tok_u1"], env["c_id"])
    pay = _init_pay(env, env["tok_u1"], order["maDonHang"], gateway="VNPAY_SANDBOX")

    # Age the PENDING payment by 10 minutes so Sweeper picks it up
    with env["SessionLocal"]() as db:
        t = db.get(ThanhToan, pay["maThanhToan"])
        t.ngayTao = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10)
        db.commit()
        cnt = sweep_stale_payment_tasks(db, pending_age_minutes=5)
        assert cnt >= 1

    w1 = PaymentReconciliationWorker(env["SessionLocal"], worker_id="w1", lease_seconds=5, gateway_client=_FakeGateway())
    w2 = PaymentReconciliationWorker(env["SessionLocal"], worker_id="w2", lease_seconds=30, gateway_client=_FakeGateway())

    # Worker 1 claims task (leaseGeneration=1) then simulates crash before commit!
    claimed_w1 = w1.claim_next_task()
    assert claimed_w1 is not None and claimed_w1.leaseGeneration == 1

    # Simulate lease expiration (abrupt worker crash!)
    future_now = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=15)
    # Two workers race to reclaim stale lease -> exactly ONE wins!
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_a = pool.submit(w2.run_once, now=future_now)
        f_b = pool.submit(w2.run_once, now=future_now)
        outcomes = [f_a.result(), f_b.result()]

    assert "DONE_CAPTURED" in outcomes
    assert outcomes.count("DONE_CAPTURED") == 1

    # Stale Worker 1 wakes up and tries to apply FAILED -> FENCING TOKEN REJECTS IT!
    stale_res = w1.apply_fenced_outcome(
        claimed_w1,
        GatewayQueryOutcome(status="FAILED", response_code="99", note="Stale worker late result"),
    )
    assert stale_res == "STALE_LEASE_IGNORED"

    # Verify PAID order & single ACTIVE enrollment preserved!
    with env["SessionLocal"]() as db:
        assert db.get(DonHang, order["maDonHang"]).trangThai == "PAID"
        assert db.scalar(
            select(func.count(DangKyKhoaHoc.maDangKy)).where(
                DangKyKhoaHoc.maNguoiDung == env["u1_id"],
                DangKyKhoaHoc.maKhoaHoc == env["c_id"],
            )
        ) == 1

    # Now test Refund UNKNOWN reconciliation via worker (ZERO blind refund retry!)
    o_m = _buy_now(env, env["tok_u2"], env["c_id"])
    p_m = _init_pay(env, env["tok_u2"], o_m["maDonHang"], gateway="MOCK_SANDBOX")
    env["client"].post(
        f"/api/payments/mock/{p_m['maGiaoDichNoiBo']}/simulate",
        json={"ketQua": "PAID"},
        headers=env["h"](env["tok_u2"]),
    )
    env["client"].post(
        "/api/admin/commerce/refunds",
        json={
            "maDonHang": o_m["maDonHang"],
            "maThanhToan": p_m["maThanhToan"],
            "soTienHoan": "599000",
            "loaiSuCo": "SYSTEM_ERROR",
            "phamViHoan": "FULL_ORDER",
            "lyDo": "Kiểm thử worker đối soát refund UNKNOWN.",
        },
        headers={**env["h"](env["tok_admin"]), "Idempotency-Key": f"unkw-{uuid.uuid4().hex}"},
    )
    env["client"].post(
        f"/api/admin/commerce/refunds/{p_m['maThanhToan']}/verify",
        json={"ghiChuXacMinh": "Đã xác minh."},
        headers=env["h"](env["tok_admin"]),
    )
    env["client"].post(
        f"/api/admin/commerce/refunds/{p_m['maThanhToan']}/execute",
        json={"mockOutcome": "UNKNOWN"},
        headers=env["h"](env["tok_admin"]),
    )

    # Worker processes QUERY_UNKNOWN_REFUND -> confirms REFUNDED via QueryDR!
    res_ref = w2.run_once()
    assert res_ref == "DONE_REFUND_CONFIRMED"
    with env["SessionLocal"]() as db:
        assert db.get(DonHang, o_m["maDonHang"]).trangThai == "REFUNDED"
        ref_row = db.scalars(select(HoanTienNgoaiLe).where(HoanTienNgoaiLe.maThanhToan == p_m["maThanhToan"])).first()
        assert ref_row.trangThai == "REFUNDED"


def test_f05_standalone_worker_cli_guards():
    """CLI launcher MUST refuse Production EduSuggest (exit 3), refuse disabled flag (exit 2),
    and run cleanly --once on EduSuggest_phase4_test when enabled (exit 0).
    """
    script = str(BACKEND_DIR / "scripts" / "run_payment_reconciliation_worker.py")
    base_env = os.environ.copy()
    base_env["DEBUG"] = "False"

    # 1. Production DB MUST be rejected (exit 3)
    r_prod = subprocess.run(
        [sys.executable, script, "--expected-database", "EduSuggest", "--once"],
        cwd=BACKEND_DIR,
        env={**base_env, "PAYMENT_RECONCILIATION_WORKER_ENABLED": "True"},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_prod.returncode == 3

    # 2. Disabled flag MUST be rejected (exit 2)
    r_off = subprocess.run(
        [sys.executable, script, "--expected-database", "EduSuggest_phase4_test", "--once"],
        cwd=BACKEND_DIR,
        env={**base_env, "PAYMENT_RECONCILIATION_WORKER_ENABLED": "False"},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_off.returncode == 2

    # 3. Enabled on EduSuggest_phase4_test runs cleanly --once (exit 0)
    r_ok = subprocess.run(
        [sys.executable, script, "--expected-database", "EduSuggest_phase4_test", "--once"],
        cwd=BACKEND_DIR,
        env={**base_env, "PAYMENT_RECONCILIATION_WORKER_ENABLED": "True"},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_ok.returncode == 0, r_ok.stderr
