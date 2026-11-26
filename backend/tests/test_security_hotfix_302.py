"""Isolated unit & security tests for GĐ3.0.2 (SEC-01, SEC-03, SEC-04, SEC-05).

CRITICAL SAFETY GUARANTEE:
- 100% in-memory mocks and SQL statement inspection.
- ZERO connections or writes to the live PostgreSQL EduSuggest database.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from schemas.workflow import CourseDecisionRequest, MaterialDecisionRequest
from service import workflow_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)


def _make_user(
    *,
    user_id: int = 10,
    role: str = "EXPERT",
    trang_thai: str = "ACTIVE",
    force_pwd: bool = False,
):
    return SimpleNamespace(
        maNguoiDung=user_id,
        tenTaiKhoan=f"user_{user_id}",
        hoTen=f"User {user_id}",
        email=f"u{user_id}@edusuggest.vn",
        soDienThoai=None,
        trangThai=trang_thai,
        batBuocDoiMatKhau=force_pwd,
        vaiTro=SimpleNamespace(tenVaiTro=role),
    )


def _make_expert_profile(
    *,
    expert_id: int = 100,
    user_id: int = 10,
    status: str = "VERIFIED",
    links=None,
):
    return SimpleNamespace(
        maChuyenGia=expert_id,
        maNguoiDung=user_id,
        trangThaiHoSo=status,
        soNamKinhNghiem=5,
        tieuSu="Kinh nghiệm kiểm duyệt",
        chuyenMon=None,
        chuyenMonLinks=links or [],
    )


def _mock_db_scalars_sequence(results: list):
    db = MagicMock()
    iter_results = iter(results)

    def _scalars(_stmt):
        res = MagicMock()
        val = next(iter_results)
        res.unique.return_value.first.return_value = val
        res.unique.return_value.all.return_value = val if isinstance(val, list) else []
        return res

    db.scalars.side_effect = _scalars
    return db


# ---------------------------------------------------------------------------
# Nhóm A: SEC-01 — _require_verified_expert blocks unverified / invalid experts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile_status", ["DRAFT", "PENDING_VERIFICATION", "NEEDS_UPDATE"])
def test_sec01_blocks_unverified_expert_profiles(profile_status: str):
    user = _make_user(role="EXPERT", trang_thai="ACTIVE", force_pwd=False)
    profile = _make_expert_profile(status=profile_status)
    db = _mock_db_scalars_sequence([user, profile])

    with pytest.raises(WorkflowForbiddenError) as exc:
        workflow_service._require_verified_expert(db, user.maNguoiDung)
    assert "chưa được Quản trị viên xác minh" in str(exc.value)


def test_sec01_blocks_locked_expert():
    user = _make_user(role="EXPERT", trang_thai="LOCKED", force_pwd=False)
    db = _mock_db_scalars_sequence([user])

    with pytest.raises(WorkflowForbiddenError) as exc:
        workflow_service._require_verified_expert(db, user.maNguoiDung)
    assert "active" in str(exc.value).lower()


def test_sec01_blocks_force_password_change_expert():
    user = _make_user(role="EXPERT", trang_thai="ACTIVE", force_pwd=True)
    db = _mock_db_scalars_sequence([user])

    with pytest.raises(WorkflowForbiddenError) as exc:
        workflow_service._require_verified_expert(db, user.maNguoiDung)
    assert "đổi mật khẩu" in str(exc.value).lower()


@pytest.mark.parametrize("wrong_role", ["USER", "PROVIDER", "ADMIN"])
def test_sec01_blocks_non_expert_roles(wrong_role: str):
    user = _make_user(role=wrong_role, trang_thai="ACTIVE", force_pwd=False)
    db = _mock_db_scalars_sequence([user])

    with pytest.raises(WorkflowForbiddenError):
        workflow_service._require_verified_expert(db, user.maNguoiDung)


def test_sec01_blocks_missing_chuyengia_profile():
    user = _make_user(role="EXPERT", trang_thai="ACTIVE", force_pwd=False)
    db = _mock_db_scalars_sequence([user, None])

    with pytest.raises(WorkflowForbiddenError):
        workflow_service._require_verified_expert(db, user.maNguoiDung)


def test_sec01_allows_verified_active_expert():
    user = _make_user(role="EXPERT", trang_thai="ACTIVE", force_pwd=False)
    profile = _make_expert_profile(status="VERIFIED")
    db = _mock_db_scalars_sequence([user, profile])

    result = workflow_service._require_verified_expert(db, user.maNguoiDung)
    assert result.maChuyenGia == profile.maChuyenGia


def test_sec01_all_six_review_services_enforce_verified_expert(monkeypatch):
    def _deny(_db, _uid, **_kwargs):
        raise WorkflowForbiddenError("Chưa xác minh")

    monkeypatch.setattr(workflow_service, "_require_verified_expert", _deny)
    monkeypatch.setattr(
        workflow_service.workflow_repository,
        "get_course_for_update",
        lambda _db, _cid: SimpleNamespace(maKhoaHoc=1, trangThaiDuyet="PENDING"),
    )
    monkeypatch.setattr(
        workflow_service.workflow_repository,
        "get_expert_material",
        lambda _db, _mid, **_kw: SimpleNamespace(maTaiLieu=1, trangThaiDuyet="PENDING"),
    )

    db = MagicMock()
    course_payload = CourseDecisionRequest(trangThai="APPROVED")
    material_payload = MaterialDecisionRequest(trangThai="APPROVED")

    with pytest.raises(WorkflowForbiddenError):
        workflow_service.list_expert_courses(db, 10)
    with pytest.raises(WorkflowForbiddenError):
        workflow_service.get_expert_course(db, 10, 1)
    with pytest.raises(WorkflowForbiddenError):
        workflow_service.decide_course(db, 10, 1, course_payload)
    with pytest.raises(WorkflowForbiddenError):
        workflow_service.list_expert_materials(db, 10)
    with pytest.raises(WorkflowForbiddenError):
        workflow_service.get_expert_material(db, 10, 1)
    with pytest.raises(WorkflowForbiddenError):
        workflow_service.decide_material(db, 10, 1, material_payload)


# ---------------------------------------------------------------------------
# Nhóm B: Onboarding Regression — DRAFT expert can still access own profile
# ---------------------------------------------------------------------------


def test_onboarding_draft_expert_can_load_profile():
    profile = _make_expert_profile(status="DRAFT")
    db = _mock_db_scalars_sequence([profile])

    loaded = workflow_service.get_expert_profile(db, 10)
    assert loaded.trangThaiHoSo == "DRAFT"


# ---------------------------------------------------------------------------
# Nhóm C: SEC-04 — Standalone material must have valid maDanhMuc on submit
# ---------------------------------------------------------------------------


def test_sec04_standalone_material_missing_category_rejected(monkeypatch):
    material = SimpleNamespace(
        maTaiLieu=500,
        maKhoaHoc=None,
        maBaiHoc=None,
        maDanhMuc=None,
        tieuDe="Tài liệu test",
        duongDanTep="https://example.com/doc.pdf",
        trangThaiDuyet="DRAFT",
        trangThaiHienThi="HIDDEN",
    )
    monkeypatch.setattr(workflow_service, "_get_provider_profile", lambda _db, _uid: SimpleNamespace(maNhaCungCap=1))
    monkeypatch.setattr(
        workflow_service.workflow_repository,
        "get_owned_material_by_id",
        lambda _db, _uid, _mid, **_kw: material,
    )
    db = MagicMock()

    with pytest.raises(WorkflowConflictError) as exc:
        workflow_service.submit_provider_material(db, 1, 500)
    assert "Vui lòng chọn danh mục" in str(exc.value)
    assert material.trangThaiDuyet == "DRAFT"
    db.commit.assert_not_called()


def test_sec04_standalone_material_nonexistent_category_rejected(monkeypatch):
    material = SimpleNamespace(
        maTaiLieu=501,
        maKhoaHoc=None,
        maBaiHoc=None,
        maDanhMuc=9999,
        tieuDe="Tài liệu test",
        duongDanTep="https://example.com/doc.pdf",
        trangThaiDuyet="DRAFT",
        trangThaiHienThi="HIDDEN",
    )
    monkeypatch.setattr(workflow_service, "_get_provider_profile", lambda _db, _uid: SimpleNamespace(maNhaCungCap=1))
    monkeypatch.setattr(
        workflow_service.workflow_repository,
        "get_owned_material_by_id",
        lambda _db, _uid, _mid, **_kw: material,
    )
    monkeypatch.setattr(workflow_service.workflow_repository, "get_category", lambda _db, _cid: None)
    db = MagicMock()

    with pytest.raises(WorkflowNotFoundError):
        workflow_service.submit_provider_material(db, 1, 501)
    assert material.trangThaiDuyet == "DRAFT"
    db.commit.assert_not_called()


def test_sec04_standalone_material_with_valid_category_submits(monkeypatch):
    material = SimpleNamespace(
        maTaiLieu=502,
        maKhoaHoc=None,
        maBaiHoc=None,
        maDanhMuc=4,
        tieuDe="Tài liệu hợp lệ",
        duongDanTep="https://example.com/doc.pdf",
        trangThaiDuyet="DRAFT",
        trangThaiHienThi="HIDDEN",
        soVongKiemDuyetHienTai=0,
        maNguoiDuyet=None,
        ngayDuyet=None,
        lyDoTuChoi=None,
        ngayCapNhat=None,
    )
    monkeypatch.setattr(workflow_service, "_get_provider_profile", lambda _db, _uid: SimpleNamespace(maNhaCungCap=1))
    monkeypatch.setattr(
        workflow_service.workflow_repository,
        "get_owned_material_by_id",
        lambda _db, _uid, _mid, **_kw: material,
    )
    monkeypatch.setattr(
        workflow_service.workflow_repository,
        "get_category",
        lambda _db, _cid: SimpleNamespace(maDanhMuc=4),
    )
    db = MagicMock()

    result = workflow_service.submit_provider_material(db, 1, 502)
    assert result.trangThaiDuyet == "PENDING"
    assert result.trangThaiHienThi == "HIDDEN"
    db.commit.assert_called_once()


def test_sec04_linked_material_without_own_category_still_submits(monkeypatch):
    material = SimpleNamespace(
        maTaiLieu=503,
        maKhoaHoc=10,
        maBaiHoc=20,
        maDanhMuc=None,
        tieuDe="Slide bài học",
        duongDanTep="https://example.com/slide.pdf",
        trangThaiDuyet="DRAFT",
        trangThaiHienThi="HIDDEN",
        maNguoiDuyet=None,
        ngayDuyet=None,
        lyDoTuChoi=None,
        ngayCapNhat=None,
    )
    monkeypatch.setattr(workflow_service, "_get_provider_profile", lambda _db, _uid: SimpleNamespace(maNhaCungCap=1))
    monkeypatch.setattr(
        workflow_service.workflow_repository,
        "get_owned_material_by_id",
        lambda _db, _uid, _mid, **_kw: material,
    )
    db = MagicMock()

    result = workflow_service.submit_provider_material(db, 1, 503)
    assert result.trangThaiDuyet == "PENDING"
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Nhóm D: SEC-05 — Role integrity enforced in SQL for experts & candidates
# ---------------------------------------------------------------------------


def test_sec05_list_admin_experts_filters_expert_role_in_sql():
    captured_sql = []
    db = MagicMock()

    def _scalars(stmt):
        captured_sql.append(str(stmt.compile(compile_kwargs={"literal_binds": True})))
        res = MagicMock()
        res.unique.return_value.all.return_value = []
        return res

    db.scalars.side_effect = _scalars
    workflow_service.list_admin_experts(db)

    assert len(captured_sql) == 1
    sql_upper = captured_sql[0].upper()
    assert 'JOIN "VAITRO"' in sql_upper
    assert "UPPER(\"VAITRO\".\"TENVAITRO\") = 'EXPERT'" in sql_upper


def test_sec05_list_expert_candidates_excludes_non_verified_and_locked(monkeypatch):
    u_verified = _make_user(user_id=1, role="EXPERT", trang_thai="ACTIVE", force_pwd=False)
    p_verified = _make_expert_profile(expert_id=101, user_id=1, status="VERIFIED")
    u_draft = _make_user(user_id=2, role="EXPERT", trang_thai="ACTIVE", force_pwd=False)
    p_draft = _make_expert_profile(expert_id=102, user_id=2, status="DRAFT")
    u_locked = _make_user(user_id=3, role="EXPERT", trang_thai="LOCKED", force_pwd=False)
    p_locked = _make_expert_profile(expert_id=103, user_id=3, status="VERIFIED")
    u_pwd = _make_user(user_id=4, role="EXPERT", trang_thai="ACTIVE", force_pwd=True)
    p_pwd = _make_expert_profile(expert_id=104, user_id=4, status="VERIFIED")

    monkeypatch.setattr(
        workflow_service,
        "list_admin_experts",
        lambda _db: [
            (u_verified, p_verified),
            (u_draft, p_draft),
            (u_locked, p_locked),
            (u_pwd, p_pwd),
        ],
    )
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    candidates = workflow_service.list_expert_candidates(db, category_id=None)
    assert [c["user"].maNguoiDung for c in candidates] == [1]


# ---------------------------------------------------------------------------
# Nhóm E: SEC-03 — Public repository queries enforce APPROVED + VISIBLE
# ---------------------------------------------------------------------------


def test_sec03_public_course_and_material_queries_require_approved_and_visible():
    from repository import workflow_repository

    captured = []
    db = MagicMock()

    def _scalars(stmt):
        captured.append(str(stmt.compile(compile_kwargs={"literal_binds": True})))
        res = MagicMock()
        res.all.return_value = []
        res.first.return_value = None
        return res

    db.scalars.side_effect = _scalars
    db.scalar.return_value = 0

    workflow_repository.list_public_courses(db, query=None, category_id=None, limit=10)
    workflow_repository.get_public_course(db, 28)
    workflow_repository.list_public_materials(db)
    workflow_repository.get_public_material(db, 132)

    assert len(captured) == 4
    for sql in captured:
        assert "'APPROVED'" in sql
        assert "'VISIBLE'" in sql
