"""GĐ4.2 PostgreSQL API, security, business-rule, and concurrency tests for
Wishlist, Shopping Cart, and Buy Now preparation.

Strictly runs ONLY against EduSuggest_phase4_test (refuses to run on EduSuggest).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
import os
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import Session, sessionmaker

from config.config import get_settings
from config.database import get_db
from main import app
from models import (
    BaiHoc,
    ChiTietGioHang,
    DangKyKhoaHoc,
    DanhMuc,
    DonHang,
    GioHang,
    KhoaHoc,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    VaiTro,
    YeuThich,
)
from service import commerce_service, recommendation_service
from service.commerce_service import CommerceNotFoundError
from utils.security import create_access_token, hash_password


def _phase4_test_url() -> str:
    raw = os.environ.get("PHASE4_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raw = get_settings().database_url.get_secret_value()
    if raw.endswith("/EduSuggest"):
        raw = raw.rsplit("/", 1)[0] + "/EduSuggest_phase4_test"
    if not raw.endswith("/EduSuggest_phase4_test"):
        pytest.skip("GĐ4.2 tests require EduSuggest_phase4_test database.")
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
def test_client(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        # Do not enter TestClient context manager so lifespan cleanup never touches EduSuggest
        client = TestClient(app)
        yield client, SessionLocal
    finally:
        app.dependency_overrides.pop(get_db, None)


def _make_user(db: Session, role_name: str, *, status_value: str = "ACTIVE") -> tuple[NguoiDung, str]:
    role = db.scalars(select(VaiTro).where(VaiTro.tenVaiTro == role_name)).first()
    assert role is not None
    tag = uuid.uuid4().hex[:8]
    pwd_hash = hash_password(f"Pass!{tag}99")
    user = NguoiDung(
        maVaiTro=role.maVaiTro,
        tenTaiKhoan=f"p42_{role_name.lower()}_{tag}",
        hoTen=f"P42 {role_name} {tag}",
        email=f"p42_{tag}@example.test",
        matKhau=pwd_hash,
        trangThai=status_value,
        batBuocDoiMatKhau=False,
    )
    db.add(user)
    db.flush()
    token = create_access_token(user.maNguoiDung, pwd_hash).encoded
    return user, token


def _make_course(
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
        tieuDe=f"P42 Course {tag}",
        moTa="Khóa học kiểm thử Wishlist và Giỏ hàng GĐ4.2",
        hinhAnh=f"/media/courses/p42-{tag}.jpg",
        gia=gia,
        trinhDo="Intermediate",
        thoiLuong=90,
        trangThaiDuyet=approval,
        trangThaiHienThi=visibility,
        ngayTao=now,
        ngayCapNhat=now,
    )
    db.add(course)
    db.flush()
    lesson = BaiHoc(
        maKhoaHoc=course.maKhoaHoc,
        tieuDe=f"Bài học {tag}",
        noiDung="Nội dung kiểm thử",
        thoiLuong=20,
        thuTu=1,
        ngayTao=now,
    )
    db.add(lesson)
    db.flush()
    return course, lesson


@pytest.fixture
def env_data(test_client):
    client, SessionLocal = test_client
    db = SessionLocal()
    created_users: list[int] = []
    created_courses: list[int] = []
    created_lessons: list[int] = []
    try:
        provider_id = db.scalar(select(NhaCungCapKhoaHoc.maNhaCungCap).limit(1))
        category_id = db.scalar(select(DanhMuc.maDanhMuc).limit(1))
        assert provider_id is not None and category_id is not None

        user_a, token_a = _make_user(db, "USER")
        user_b, token_b = _make_user(db, "USER")
        locked_user, token_locked = _make_user(db, "USER", status_value="LOCKED")
        admin_u, token_admin = _make_user(db, "ADMIN")
        expert_u, token_expert = _make_user(db, "EXPERT")
        provider_u, token_provider = _make_user(db, "PROVIDER")
        for u in (user_a, user_b, locked_user, admin_u, expert_u, provider_u):
            created_users.append(u.maNguoiDung)

        paid1, l1 = _make_course(db, provider_id=provider_id, category_id=category_id, gia=Decimal("399000"))
        paid2, l2 = _make_course(db, provider_id=provider_id, category_id=category_id, gia=Decimal("599000"))
        paid_owned, l3 = _make_course(db, provider_id=provider_id, category_id=category_id, gia=Decimal("299000"))
        paid_revoked, l4 = _make_course(db, provider_id=provider_id, category_id=category_id, gia=Decimal("450000"))
        free_c, l5 = _make_course(db, provider_id=provider_id, category_id=category_id, gia=Decimal("0"))
        null_c, l6 = _make_course(db, provider_id=provider_id, category_id=category_id, gia=None)
        hidden_c, l7 = _make_course(
            db,
            provider_id=provider_id,
            category_id=category_id,
            gia=Decimal("499000"),
            approval="PENDING",
            visibility="HIDDEN",
        )
        for c, l in (
            (paid1, l1),
            (paid2, l2),
            (paid_owned, l3),
            (paid_revoked, l4),
            (free_c, l5),
            (null_c, l6),
            (hidden_c, l7),
        ):
            created_courses.append(c.maKhoaHoc)
            created_lessons.append(l.maBaiHoc)

        now = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            DangKyKhoaHoc(
                maNguoiDung=user_a.maNguoiDung,
                maKhoaHoc=paid_owned.maKhoaHoc,
                ngayDangKy=now,
                tienDo=Decimal("50"),
                nguonCapQuyen="LEGACY",
                trangThaiQuyenHoc="ACTIVE",
            )
        )
        db.add(
            DangKyKhoaHoc(
                maNguoiDung=user_a.maNguoiDung,
                maKhoaHoc=paid_revoked.maKhoaHoc,
                ngayDangKy=now,
                tienDo=Decimal("20"),
                nguonCapQuyen="PURCHASE",
                trangThaiQuyenHoc="REVOKED",
                ngayThuHoi=now,
                lyDoThuHoi="Hoàn tiền kiểm thử",
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
            "token_locked": token_locked,
            "token_admin": token_admin,
            "token_expert": token_expert,
            "token_provider": token_provider,
            "paid1": paid1.maKhoaHoc,
            "paid2": paid2.maKhoaHoc,
            "paid_owned": paid_owned.maKhoaHoc,
            "paid_revoked": paid_revoked.maKhoaHoc,
            "free_c": free_c.maKhoaHoc,
            "null_c": null_c.maKhoaHoc,
            "hidden_c": hidden_c.maKhoaHoc,
        }
    finally:
        db.rollback()
        if created_users:
            db.execute(delete(LichSuHocTap).where(LichSuHocTap.maNguoiDung.in_(created_users)))
            db.execute(delete(DangKyKhoaHoc).where(DangKyKhoaHoc.maNguoiDung.in_(created_users)))
            db.execute(delete(YeuThich).where(YeuThich.maNguoiDung.in_(created_users)))
            cart_ids = list(
                db.scalars(select(GioHang.maGioHang).where(GioHang.maNguoiDung.in_(created_users)))
            )
            if cart_ids:
                db.execute(delete(ChiTietGioHang).where(ChiTietGioHang.maGioHang.in_(cart_ids)))
                db.execute(delete(GioHang).where(GioHang.maGioHang.in_(cart_ids)))
        if created_lessons:
            db.execute(delete(BaiHoc).where(BaiHoc.maBaiHoc.in_(created_lessons)))
        if created_courses:
            db.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(created_courses)))
        if created_users:
            db.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(created_users)))
        db.commit()
        db.close()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Anonymous, RBAC (ADMIN/EXPERT/PROVIDER), and LOCKED account guards
# ---------------------------------------------------------------------------
def test_anonymous_rbac_and_locked_guards(env_data):
    client = env_data["client"]
    cid = env_data["paid1"]

    endpoints = [
        ("GET", "/api/wishlist", None),
        ("GET", "/api/wishlist/count", None),
        ("GET", f"/api/wishlist/{cid}/status", None),
        ("POST", f"/api/wishlist/{cid}", None),
        ("DELETE", f"/api/wishlist/{cid}", None),
        ("POST", f"/api/wishlist/{cid}/move-to-cart", None),
        ("GET", "/api/cart", None),
        ("GET", "/api/cart/count", None),
        ("POST", "/api/cart/items", {"maKhoaHoc": cid}),
        ("DELETE", f"/api/cart/items/{cid}", None),
        ("DELETE", "/api/cart", None),
        ("GET", f"/api/commerce/buy-now/validate/{cid}", None),
    ]

    for method, path, body in endpoints:
        res_anon = client.request(method, path, json=body)
        assert res_anon.status_code == 401, f"{method} {path} expected 401, got {res_anon.status_code}"

        for role_tok in (env_data["token_admin"], env_data["token_expert"], env_data["token_provider"]):
            res_role = client.request(method, path, json=body, headers=_auth(role_tok))
            assert res_role.status_code == 403, f"{method} {path} non-USER expected 403, got {res_role.status_code}"

        res_locked = client.request(method, path, json=body, headers=_auth(env_data["token_locked"]))
        assert res_locked.status_code == 403, f"{method} {path} LOCKED expected 403, got {res_locked.status_code}"


# ---------------------------------------------------------------------------
# 2. Mass assignment & Price tampering rejected (422)
# ---------------------------------------------------------------------------
def test_mass_assignment_and_price_tampering_rejected(env_data):
    client = env_data["client"]
    headers = _auth(env_data["token_a"])
    cid = env_data["paid1"]

    for bad_payload in (
        {"maKhoaHoc": cid, "gia": 0},
        {"maKhoaHoc": cid, "giaLucThem": 1000},
        {"maKhoaHoc": cid, "tongTien": 0},
        {"maKhoaHoc": cid, "maNguoiDung": env_data["user_b"]},
        {"maKhoaHoc": cid, "maGioHang": 999},
    ):
        res = client.post("/api/cart/items", json=bad_payload, headers=headers)
        assert res.status_code == 422, f"Expected 422 for {bad_payload}, got {res.status_code}"


# ---------------------------------------------------------------------------
# 3. Wishlist CRUD, idempotency, pagination, and hidden course preservation
# ---------------------------------------------------------------------------
def test_wishlist_lifecycle_pagination_and_hidden_preservation(env_data):
    client = env_data["client"]
    headers = _auth(env_data["token_a"])
    p1, p2, hidden_c = env_data["paid1"], env_data["paid2"], env_data["hidden_c"]

    # Cannot add hidden/unapproved course to wishlist
    assert client.post(f"/api/wishlist/{hidden_c}", headers=headers).status_code == 404

    # Idempotent add
    r1 = client.post(f"/api/wishlist/{p1}", headers=headers)
    assert r1.status_code == 200 and r1.json()["trongYeuThich"] is True and r1.json()["tongSoYeuThich"] == 1
    r1_dup = client.post(f"/api/wishlist/{p1}", headers=headers)
    assert r1_dup.status_code == 200 and r1_dup.json()["tongSoYeuThich"] == 1

    r2 = client.post(f"/api/wishlist/{p2}", headers=headers)
    assert r2.status_code == 200 and r2.json()["tongSoYeuThich"] == 2

    # Pagination
    page1 = client.get("/api/wishlist?page=1&page_size=1", headers=headers)
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1["total"] == 2 and body1["totalPages"] == 2 and len(body1["items"]) == 1

    # Hide p2 AFTER adding to wishlist -> MUST remain in wishlist with khaDung=False (NOT auto-deleted)
    db = env_data["SessionLocal"]()
    try:
        c2 = db.get(KhoaHoc, p2)
        c2.trangThaiHienThi = "HIDDEN"
        db.commit()
    finally:
        db.close()

    wl_all = client.get("/api/wishlist?page=1&page_size=10", headers=headers).json()
    assert wl_all["total"] == 2
    item_p2 = next(i for i in wl_all["items"] if i["maKhoaHoc"] == p2)
    assert item_p2["khaDung"] is False
    assert item_p2["lyDoKhongKhaDung"]

    # Idempotent delete
    assert client.delete(f"/api/wishlist/{p1}", headers=headers).json()["tongSoYeuThich"] == 1
    assert client.delete(f"/api/wishlist/{p1}", headers=headers).json()["tongSoYeuThich"] == 1


# ---------------------------------------------------------------------------
# 4. Cart rules: free/NULL/hidden/owned/REVOKED/price-change/unavailable/IDOR
# ---------------------------------------------------------------------------
def test_cart_business_rules_price_change_and_cross_user_isolation(env_data):
    client = env_data["client"]
    h_a = _auth(env_data["token_a"])
    h_b = _auth(env_data["token_b"])

    # Reject free, NULL price, hidden, and ACTIVE owned
    assert client.post("/api/cart/items", json={"maKhoaHoc": env_data["free_c"]}, headers=h_a).status_code == 400
    assert client.post("/api/cart/items", json={"maKhoaHoc": env_data["null_c"]}, headers=h_a).status_code == 400
    assert client.post("/api/cart/items", json={"maKhoaHoc": env_data["hidden_c"]}, headers=h_a).status_code == 404
    assert client.post("/api/cart/items", json={"maKhoaHoc": env_data["paid_owned"]}, headers=h_a).status_code == 409

    # REVOKED enrollment IS allowed to be added to cart for repurchase!
    r_rev = client.post("/api/cart/items", json={"maKhoaHoc": env_data["paid_revoked"]}, headers=h_a)
    assert r_rev.status_code == 200
    assert Decimal(str(r_rev.json()["tongTien"])) == Decimal("450000")

    # Add paid1 + paid2 (399,000 + 599,000 + 450,000 = 1,448,000)
    client.post("/api/cart/items", json={"maKhoaHoc": env_data["paid1"]}, headers=h_a)
    r_cart = client.post("/api/cart/items", json={"maKhoaHoc": env_data["paid2"]}, headers=h_a)
    assert r_cart.status_code == 200
    data = r_cart.json()
    assert data["tongSoLuong"] == 3 and data["soLuongHopLe"] == 3
    assert Decimal(str(data["tongTien"])) == Decimal("1448000")

    # Cross-user isolation: User B sees empty cart and cannot clear/delete User A's items
    assert client.get("/api/cart", headers=h_b).json()["tongSoLuong"] == 0
    client.delete(f"/api/cart/items/{env_data['paid1']}", headers=h_b)
    client.delete("/api/cart", headers=h_b)
    assert client.get("/api/cart/count", headers=h_a).json()["tongSoLuong"] == 3

    # Price change on paid1 (399k -> 420k) AND hide paid2 -> live recalc excludes paid2!
    db = env_data["SessionLocal"]()
    try:
        c1 = db.get(KhoaHoc, env_data["paid1"])
        c1.gia = Decimal("420000")
        c2 = db.get(KhoaHoc, env_data["paid2"])
        c2.trangThaiHienThi = "HIDDEN"
        db.commit()
    finally:
        db.close()

    cart_after = client.get("/api/cart", headers=h_a).json()
    assert cart_after["tongSoLuong"] == 3
    assert cart_after["soLuongHopLe"] == 2
    assert cart_after["soLuongKhongHopLe"] == 1
    assert cart_after["coThayDoiGia"] is True
    assert cart_after["coMucKhongHopLe"] is True
    # Expected valid total: 420,000 (live paid1) + 450,000 (paid_revoked) = 870,000 (paid2 excluded)
    assert Decimal(str(cart_after["tongTien"])) == Decimal("870000")

    # Clear cart
    cleared = client.delete("/api/cart", headers=h_a).json()
    assert cleared["daXoaSoLuong"] == 3 and cleared["tongSoLuong"] == 0


# ---------------------------------------------------------------------------
# 5. Atomic Move Wishlist -> Cart (preserves wishlist on failure!)
# ---------------------------------------------------------------------------
def test_move_wishlist_to_cart_atomic_and_preserves_on_failure(env_data):
    client = env_data["client"]
    h_a = _auth(env_data["token_a"])
    p1, free_c = env_data["paid1"], env_data["free_c"]

    # Add free course & paid course to wishlist
    client.post(f"/api/wishlist/{free_c}", headers=h_a)
    client.post(f"/api/wishlist/{p1}", headers=h_a)

    # Moving free course to cart MUST fail (400) and MUST NOT lose the wishlist item!
    res_fail = client.post(f"/api/wishlist/{free_c}/move-to-cart", headers=h_a)
    assert res_fail.status_code == 400
    assert client.get(f"/api/wishlist/{free_c}/status", headers=h_a).json()["trongYeuThich"] is True

    # Moving paid course succeeds atomically: in cart + removed from wishlist
    res_ok = client.post(f"/api/wishlist/{p1}/move-to-cart", headers=h_a)
    assert res_ok.status_code == 200
    body = res_ok.json()
    assert body["daChuyenVaoGioHang"] is True
    assert body["daXoaKhoiYeuThich"] is True
    assert body["tongSoYeuThich"] == 1
    assert body["tongSoGioHang"] == 1
    assert Decimal(str(body["tongTienGioHang"])) == Decimal("399000")
    assert client.get(f"/api/wishlist/{p1}/status", headers=h_a).json()["trongYeuThich"] is False


# ---------------------------------------------------------------------------
# 6. Buy Now Preparation (no cart required, no order/enrollment created)
# ---------------------------------------------------------------------------
def test_buy_now_preparation_validation(env_data):
    client = env_data["client"]
    h_a = _auth(env_data["token_a"])

    # Paid course works directly without adding to cart
    res = client.get(f"/api/commerce/buy-now/validate/{env_data['paid1']}", headers=h_a)
    assert res.status_code == 200
    body = res.json()
    assert body["hopLe"] is True
    assert body["muaLaiSauHoanTien"] is False
    assert Decimal(str(body["giaHienTai"])) == Decimal("399000")
    assert client.get("/api/cart/count", headers=h_a).json()["tongSoLuong"] == 0

    # REVOKED course allowed with muaLaiSauHoanTien=True
    res_rev = client.get(f"/api/commerce/buy-now/validate/{env_data['paid_revoked']}", headers=h_a)
    assert res_rev.status_code == 200 and res_rev.json()["muaLaiSauHoanTien"] is True

    # Reject free, NULL, hidden, ACTIVE owned
    assert client.get(f"/api/commerce/buy-now/validate/{env_data['free_c']}", headers=h_a).status_code == 400
    assert client.get(f"/api/commerce/buy-now/validate/{env_data['null_c']}", headers=h_a).status_code == 400
    assert client.get(f"/api/commerce/buy-now/validate/{env_data['hidden_c']}", headers=h_a).status_code == 404
    assert client.get(f"/api/commerce/buy-now/validate/{env_data['paid_owned']}", headers=h_a).status_code == 409

    # Confirm zero orders created during GĐ4.2 Buy Now validation
    db = env_data["SessionLocal"]()
    try:
        cnt = db.scalar(select(DonHang.maDonHang).where(DonHang.maNguoiDung == env_data["user_a"]))
        assert cnt is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. Concurrency: Wishlist add, Cart creation/add, Delete, Move-to-Cart
# ---------------------------------------------------------------------------
def test_concurrent_wishlist_cart_and_move_operations(env_data):
    SessionLocal = env_data["SessionLocal"]
    uid = env_data["user_b"]
    p1 = env_data["paid1"]

    def _get_user(s: Session) -> NguoiDung:
        u = s.get(NguoiDung, uid)
        assert u is not None
        _ = u.vaiTro
        return u

    # 7a. Concurrent Wishlist add (6 threads)
    def _wl_add(_):
        s = SessionLocal()
        try:
            res = commerce_service.add_to_wishlist(s, _get_user(s), p1)
            return res.trongYeuThich
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert all(pool.map(_wl_add, range(6)))

    # 7b. Concurrent Move Wishlist -> Cart (6 threads, also races cart creation!)
    def _move(_):
        s = SessionLocal()
        try:
            commerce_service.move_wishlist_to_cart(s, _get_user(s), p1)
            return "MOVED"
        except CommerceNotFoundError:
            return "ALREADY_MOVED"
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        move_results = list(pool.map(_move, range(6)))
    assert move_results.count("MOVED") == 1
    assert move_results.count("ALREADY_MOVED") == 5

    # 7c. Concurrent Cart add same course (6 threads) -> 1 item, no duplicates
    def _cart_add(_):
        s = SessionLocal()
        try:
            res = commerce_service.add_to_cart(s, _get_user(s), p1)
            return res.tongSoLuong
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert all(cnt == 1 for cnt in pool.map(_cart_add, range(6)))

    # 7d. Concurrent Cart item delete (6 threads) -> idempotent, 0 errors
    def _cart_del(_):
        s = SessionLocal()
        try:
            res = commerce_service.remove_from_cart(s, _get_user(s), p1)
            return res.tongSoLuong
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert all(cnt == 0 for cnt in pool.map(_cart_del, range(6)))


# ---------------------------------------------------------------------------
# 8. Recommendation Isolation: Wishlist & Cart do NOT pollute learning history
# ---------------------------------------------------------------------------
def test_wishlist_and_cart_do_not_affect_learning_history_or_recommendations(env_data):
    client = env_data["client"]
    h_b = _auth(env_data["token_b"])
    db = env_data["SessionLocal"]()
    try:
        before_rec = recommendation_service.recommend_courses(db, env_data["user_b"], limit=5)
        before_ids = [item.maKhoaHoc for item in before_rec.items]

        client.post(f"/api/wishlist/{env_data['paid1']}", headers=h_b)
        client.post("/api/cart/items", json={"maKhoaHoc": env_data["paid2"]}, headers=h_b)

        after_rec = recommendation_service.recommend_courses(db, env_data["user_b"], limit=5)
        after_ids = [item.maKhoaHoc for item in after_rec.items]

        assert before_rec.strategy == after_rec.strategy == "latest"
        assert before_rec.personalized is False and after_rec.personalized is False
        assert before_ids == after_ids

        # Zero enrollments or learning history created by Wishlist/Cart actions
        assert db.scalar(select(DangKyKhoaHoc.maDangKy).where(DangKyKhoaHoc.maNguoiDung == env_data["user_b"])) is None
        assert db.scalar(select(LichSuHocTap.maLichSu).where(LichSuHocTap.maNguoiDung == env_data["user_b"])) is None
    finally:
        db.close()
