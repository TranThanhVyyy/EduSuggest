"""GĐ3.8.2 private file HTTP authorization and storage validation tests.

All database writes are isolated to EduSuggest_phase3_test and rolled back.
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse, urlunparse

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from config.database import get_db
from main import app
from models import (
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    DangKyKhoaHoc,
    DanhMuc,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    PhanCongKiemDuyet,
    TaiLieu,
    VaiTro,
)
from service.private_file_storage import LocalPrivateFileStorage
from utils.security import create_access_token


TEST_DB_NAME = os.getenv("EDUSUGGEST_TEST_DB_NAME", "EduSuggest_phase3_test").strip()
assert TEST_DB_NAME and TEST_DB_NAME != "EduSuggest", (
    "SAFETY VIOLATION: Private file security tests must NEVER target production 'EduSuggest'."
)


def _test_engine():
    load_dotenv(r"d:\đồ án\EduSuggest\backend\.env")
    configured = urlparse(os.getenv("DATABASE_URL") or "")
    assert configured.path.lstrip("/") in ("EduSuggest", TEST_DB_NAME)
    engine = create_engine(
        urlunparse(configured._replace(path=f"/{TEST_DB_NAME}")),
        pool_pre_ping=True,
    )
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_database()")).scalar_one() == TEST_DB_NAME
    return engine


TEST_ENGINE = _test_engine()


def _token(user: NguoiDung) -> dict[str, str]:
    value = create_access_token(int(user.maNguoiDung), user.matKhau).encoded
    return {"Authorization": f"Bearer {value}"}


def _user(db: Session, role_ids: dict[str, int], role: str, tag: str) -> NguoiDung:
    user = NguoiDung(
        tenTaiKhoan=f"g382_{role.lower()}_{tag}_{uuid.uuid4().hex[:5]}",
        email=f"g382_{role.lower()}_{uuid.uuid4().hex[:10]}@test.local",
        matKhau="$2b$12$dummyhashvalueforphase382test0000000000000000000",
        hoTen=f"G382 {role}",
        maVaiTro=role_ids[role],
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def private_file_fixture():
    connection = TEST_ENGINE.connect()
    transaction = connection.begin()
    assert connection.execute(text("SELECT current_database()")).scalar_one() == TEST_DB_NAME
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    reference: str | None = None
    try:
        now = datetime.now(UTC).replace(tzinfo=None)
        tag = uuid.uuid4().hex[:7]
        role_ids = {row.tenVaiTro: row.maVaiTro for row in db.scalars(select(VaiTro)).all()}
        admin = _user(db, role_ids, "ADMIN", tag)
        provider_user = _user(db, role_ids, "PROVIDER", tag)
        other_provider_user = _user(db, role_ids, "PROVIDER", tag)
        expert_user = _user(db, role_ids, "EXPERT", tag)
        other_expert_user = _user(db, role_ids, "EXPERT", tag)
        learner = _user(db, role_ids, "USER", tag)
        outsider = _user(db, role_ids, "USER", tag)

        provider = NhaCungCapKhoaHoc(maNguoiDung=provider_user.maNguoiDung, tieuSu="G382 provider")
        other_provider = NhaCungCapKhoaHoc(maNguoiDung=other_provider_user.maNguoiDung, tieuSu="G382 other")
        category = DanhMuc(tenDanhMuc=f"G382 Private {tag}")
        specialty = ChuyenMon(
            tenChuyenMon=f"G382 Private Spec {tag}",
            nhomChuyenMon="G382",
            trangThai="ACTIVE",
            ngayTao=now,
        )
        expert = ChuyenGia(maNguoiDung=expert_user.maNguoiDung, trangThaiHoSo="VERIFIED", soNamKinhNghiem=5)
        other_expert = ChuyenGia(maNguoiDung=other_expert_user.maNguoiDung, trangThaiHoSo="VERIFIED", soNamKinhNghiem=5)
        db.add_all([provider, other_provider, category, specialty, expert, other_expert])
        db.flush()
        db.add(ChuyenMonDanhMuc(maChuyenMon=specialty.maChuyenMon, maDanhMuc=category.maDanhMuc, ngayTao=now))
        db.add_all([
            ChuyenGiaChuyenMon(maChuyenGia=expert.maChuyenGia, maChuyenMon=specialty.maChuyenMon, laChuyenMonChinh=True, ngayTao=now),
            ChuyenGiaChuyenMon(maChuyenGia=other_expert.maChuyenGia, maChuyenMon=specialty.maChuyenMon, laChuyenMonChinh=True, ngayTao=now),
        ])
        course = KhoaHoc(
            maNhaCungCap=provider.maNhaCungCap,
            maDanhMuc=category.maDanhMuc,
            tieuDe=f"G382 Private Course {tag}",
            gia=0,
            trangThaiDuyet="APPROVED",
            trangThaiHienThi="VISIBLE",
            soVongKiemDuyetHienTai=1,
        )
        material = TaiLieu(
            maNhaCungCap=provider.maNhaCungCap,
            maKhoaHoc=course.maKhoaHoc,
            maDanhMuc=category.maDanhMuc,
            tieuDe=f"G382 Private Material {tag}",
            loai="PDF",
            trangThaiDuyet="DRAFT",
            trangThaiHienThi="HIDDEN",
            soVongKiemDuyetHienTai=1,
            ngayTao=now,
            ngayCapNhat=now,
        )
        db.add(course)
        db.flush()
        material.maKhoaHoc = course.maKhoaHoc
        db.add(material)
        db.commit()

        def override_db():
            assert db.execute(text("SELECT current_database()")).scalar_one() == TEST_DB_NAME
            yield db

        app.dependency_overrides[get_db] = override_db
        client = TestClient(app)
        upload = client.post(
            f"/api/provider/materials/{material.maTaiLieu}/file",
            headers=_token(provider_user),
            files={"file": ("guide.pdf", b"%PDF-1.7\nG382 private test\n%%EOF", "application/pdf")},
        )
        assert upload.status_code == 200, upload.text
        db.refresh(material)
        reference = material.duongDanTep
        assert reference and reference.startswith("private://materials/")
        material.trangThaiDuyet = "APPROVED"
        material.trangThaiHienThi = "VISIBLE"
        assignment = PhanCongKiemDuyet(
            maTaiLieu=material.maTaiLieu,
            maChuyenGia=expert.maChuyenGia,
            maDanhMuc=category.maDanhMuc,
            maChuyenMonKhop=specialty.maChuyenMon,
            soVongKiemDuyet=1,
            phuongThucPhanCong="AUTO",
            trangThai="ACCEPTED",
            ngayPhanCong=now,
            hanTiepNhan=now + timedelta(hours=2),
            hanKiemDuyet=now + timedelta(hours=24),
            ngayChapNhan=now,
            ngayCapNhat=now,
        )
        db.add(assignment)
        db.commit()
        yield {
            "db": db,
            "client": client,
            "material": material,
            "assignment": assignment,
            "admin": admin,
            "provider": provider_user,
            "other_provider": other_provider_user,
            "expert": expert_user,
            "other_expert": other_expert_user,
            "learner": learner,
            "outsider": outsider,
            "course": course,
            "specialty": specialty,
        }
    finally:
        app.dependency_overrides.pop(get_db, None)
        if "client" in locals():
            client.close()
        if reference:
            LocalPrivateFileStorage("EduSuggest_phase3_test").delete(reference)
        db.close()
        transaction.rollback()
        connection.close()


def test_private_file_access_matrix_and_revocation(private_file_fixture):
    f = private_file_fixture
    db, client, material = f["db"], f["client"], f["material"]
    path = f"/api/materials/{material.maTaiLieu}/file"

    assert client.get(path).status_code == 401
    owner = client.get(path, headers=_token(f["provider"]))
    assert owner.status_code == 200 and owner.content.startswith(b"%PDF-")
    assert owner.headers["cache-control"] == "private, no-store, max-age=0"
    assert owner.headers["x-content-type-options"] == "nosniff"
    assert client.get(path, headers=_token(f["other_provider"])).status_code == 403
    assert client.get(path, headers=_token(f["admin"])).status_code == 200
    assert client.get(path, headers=_token(f["expert"])).status_code == 200
    assert client.get(path, headers=_token(f["other_expert"])).status_code == 403
    assert client.get(path, headers=_token(f["learner"])).status_code == 403

    db.add(
        DangKyKhoaHoc(
            maNguoiDung=f["learner"].maNguoiDung,
            maKhoaHoc=f["course"].maKhoaHoc,
            ngayDangKy=datetime.now(UTC).replace(tzinfo=None),
            tienDo=0,
        )
    )
    db.commit()
    assert client.get(path, headers=_token(f["learner"])).status_code == 200
    assert client.get(path, headers=_token(f["outsider"])).status_code == 403

    material.trangThaiDuyet = "PENDING"
    db.commit()
    assert client.get(path, headers=_token(f["learner"])).status_code == 403
    material.trangThaiDuyet = "APPROVED"
    f["specialty"].trangThai = "INACTIVE"
    db.commit()
    assert client.get(path, headers=_token(f["expert"])).status_code == 403
    blocked_write = client.put(
        f"/api/expert/assignments/{f['assignment'].maPhanCong}/draft",
        headers=_token(f["expert"]),
        json={"banNhapDanhGia": {"ghiChu": "must be blocked by ACC-15"}},
    )
    assert blocked_write.status_code == 403
    f["specialty"].trangThai = "ACTIVE"
    db.commit()

    f["assignment"].trangThai = "CANCELLED"
    course_assignment = PhanCongKiemDuyet(
        maKhoaHoc=f["course"].maKhoaHoc,
        maChuyenGia=f["assignment"].maChuyenGia,
        maDanhMuc=f["course"].maDanhMuc,
        maChuyenMonKhop=f["specialty"].maChuyenMon,
        soVongKiemDuyet=1,
        phuongThucPhanCong="AUTO",
        trangThai="ACCEPTED",
        ngayPhanCong=datetime.now(UTC).replace(tzinfo=None),
        hanTiepNhan=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2),
        hanKiemDuyet=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24),
        ngayChapNhan=datetime.now(UTC).replace(tzinfo=None),
        ngayCapNhat=datetime.now(UTC).replace(tzinfo=None),
    )
    material.maDanhMuc = None
    db.add(course_assignment)
    db.commit()
    assert client.get(path, headers=_token(f["expert"])).status_code == 200
    course_assignment.trangThai = "CANCELLED"
    db.commit()
    assert client.get(path, headers=_token(f["expert"])).status_code in (403, 409)

    f["assignment"].trangThai = "CANCELLED"
    db.commit()
    assert client.get(path, headers=_token(f["expert"])).status_code in (403, 409)
    f["assignment"].trangThai = "COMPLETED"
    db.commit()
    assert client.get(path, headers=_token(f["expert"])).status_code in (403, 409)

    f["provider"].trangThai = "LOCKED"
    db.commit()
    assert client.get(path, headers=_token(f["provider"])).status_code == 403


def test_private_upload_rejects_unsafe_names_and_content(private_file_fixture):
    f = private_file_fixture
    f["material"].trangThaiDuyet = "DRAFT"
    f["db"].commit()
    endpoint = f"/api/provider/materials/{f['material'].maTaiLieu}/file"
    headers = _token(f["provider"])
    bad_name = f["client"].post(
        endpoint,
        headers=headers,
        files={"file": ("../escape.pdf", b"%PDF-1.7\n%%EOF", "application/pdf")},
    )
    assert bad_name.status_code == 400
    executable = f["client"].post(
        endpoint,
        headers=headers,
        files={"file": ("payload.exe", b"MZ\x00\x00", "application/octet-stream")},
    )
    assert executable.status_code == 400
    spoofed = f["client"].post(
        endpoint,
        headers=headers,
        files={"file": ("spoof.pdf", b"MZ not a PDF", "application/pdf")},
    )
    assert spoofed.status_code == 400
