"""Create removable browser-acceptance fixtures on EduSuggest_phase3_test only."""
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parents[1]
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
os.environ["DEBUG"] = "False"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from fastapi import UploadFile
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from config.config import BACKEND_DIR
from models import (
    BaiHoc,
    CauHinhPhanCong,
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
    ThongBao,
    VaiTro,
)
from service.private_file_storage import LocalPrivateFileStorage
from utils.security import hash_password

DATABASE = "EduSuggest_phase3_test"
PASSWORD = "G382-Browser!2026"
RUNTIME_DIR = BACKEND_DIR / "logs" / "gd382-staging"
MANIFEST = RUNTIME_DIR / "fixtures.json"


async def _store_pdf(storage: LocalPrivateFileStorage, filename: str, label: str) -> str:
    payload = f"%PDF-1.7\n% EduSuggest GD3.8.3 {label}\n%%EOF\n".encode()
    upload = UploadFile(
        file=BytesIO(payload),
        size=len(payload),
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )
    return (await storage.save_upload(upload)).reference


def main() -> int:
    load_dotenv(BACKEND_DIR / ".env")
    configured = make_url(os.environ["DATABASE_URL"])
    engine = create_engine(configured.set(database=DATABASE), pool_pre_ping=True)
    with Session(engine) as db:
        actual = db.execute(text("SELECT current_database()")).scalar_one()
        if actual != DATABASE:
            raise RuntimeError(f"Safety guard: expected {DATABASE}, got {actual}")
        if MANIFEST.exists():
            print(f"Fixture manifest already exists: {MANIFEST}")
            return 0
        usernames = {
            "ADMIN": "g382_browser_admin",
            "PROVIDER": "g382_browser_provider",
            "EXPERT_VERIFIED": "g382_browser_expert",
            "EXPERT_UNVERIFIED": "g382_browser_expert_unverified",
            "USER": "g382_browser_user",
        }
        if db.scalar(select(NguoiDung.maNguoiDung).where(NguoiDung.tenTaiKhoan.in_(usernames.values())).limit(1)):
            raise RuntimeError("G382 browser usernames already exist without a fixture manifest; refusing to overwrite.")
        roles = {row.tenVaiTro: row.maVaiTro for row in db.scalars(select(VaiTro)).all()}
        now = datetime.now(UTC).replace(tzinfo=None)
        users: dict[str, NguoiDung] = {}
        password_hash = hash_password(PASSWORD)
        role_for_account = {
            "ADMIN": "ADMIN",
            "PROVIDER": "PROVIDER",
            "EXPERT_VERIFIED": "EXPERT",
            "EXPERT_UNVERIFIED": "EXPERT",
            "USER": "USER",
        }
        for account_key, username in usernames.items():
            user = NguoiDung(
                tenTaiKhoan=username,
                email=f"{username}@test.example.com",
                matKhau=password_hash,
                hoTen=f"GĐ3.8.3 Browser {account_key}",
                maVaiTro=roles[role_for_account[account_key]],
                trangThai="ACTIVE",
                batBuocDoiMatKhau=account_key == "EXPERT_VERIFIED",
            )
            db.add(user)
            users[account_key] = user
        db.flush()
        provider = NhaCungCapKhoaHoc(
            maNguoiDung=users["PROVIDER"].maNguoiDung,
            tieuSu="GĐ3.8.3 browser fixture",
        )
        expert = ChuyenGia(
            maNguoiDung=users["EXPERT_VERIFIED"].maNguoiDung,
            trangThaiHoSo="VERIFIED",
            soNamKinhNghiem=6,
            maNguoiXacMinh=users["ADMIN"].maNguoiDung,
            ngayXacMinh=now,
        )
        unverified_expert = ChuyenGia(
            maNguoiDung=users["EXPERT_UNVERIFIED"].maNguoiDung,
            trangThaiHoSo="DRAFT",
            soNamKinhNghiem=2,
        )
        category = DanhMuc(tenDanhMuc="GĐ3.8.3 Browser Acceptance")
        specialty = ChuyenMon(
            tenChuyenMon="GĐ3.8.3 Course Review",
            nhomChuyenMon="GĐ3.8.3",
            trangThai="ACTIVE",
            ngayTao=now,
        )
        db.add_all([provider, expert, unverified_expert, category, specialty])
        db.flush()
        db.add(ChuyenMonDanhMuc(maChuyenMon=specialty.maChuyenMon, maDanhMuc=category.maDanhMuc, ngayTao=now))
        db.add(ChuyenGiaChuyenMon(maChuyenGia=expert.maChuyenGia, maChuyenMon=specialty.maChuyenMon, laChuyenMonChinh=True, ngayTao=now))
        db.add(
            ChuyenGiaChuyenMon(
                maChuyenGia=unverified_expert.maChuyenGia,
                maChuyenMon=specialty.maChuyenMon,
                laChuyenMonChinh=True,
                ngayTao=now,
            )
        )
        public_course = KhoaHoc(
            maNhaCungCap=provider.maNhaCungCap,
            maDanhMuc=category.maDanhMuc,
            tieuDe="GĐ3.8.3 Browser Learner Course",
            moTa="Approved visible course for manual browser acceptance.",
            gia=0,
            trangThaiDuyet="APPROVED",
            trangThaiHienThi="VISIBLE",
            soVongKiemDuyetHienTai=1,
            ngayTao=now,
            ngayCapNhat=now,
        )
        review_course = KhoaHoc(
            maNhaCungCap=provider.maNhaCungCap,
            maDanhMuc=category.maDanhMuc,
            tieuDe="GĐ3.8.3 Review Course – Accept and Decide",
            moTa="Pending course with a managed private review document.",
            gia=0,
            trangThaiDuyet="PENDING",
            trangThaiHienThi="HIDDEN",
            soVongKiemDuyetHienTai=1,
            ngayTao=now,
            ngayCapNhat=now,
        )
        decline_course = KhoaHoc(
            maNhaCungCap=provider.maNhaCungCap,
            maDanhMuc=category.maDanhMuc,
            tieuDe="GĐ3.8.3 Review Course – Decline Assignment",
            moTa="Separate assignment reserved for the decline flow.",
            gia=0,
            trangThaiDuyet="PENDING",
            trangThaiHienThi="HIDDEN",
            soVongKiemDuyetHienTai=1,
            ngayTao=now,
            ngayCapNhat=now,
        )
        db.add_all([public_course, review_course, decline_course])
        db.flush()
        public_lesson = BaiHoc(
            maKhoaHoc=public_course.maKhoaHoc,
            tieuDe="Browser file access lesson",
            noiDung="Manual acceptance fixture.",
            thuTu=1,
            ngayTao=now,
        )
        review_lesson = BaiHoc(
            maKhoaHoc=review_course.maKhoaHoc,
            tieuDe="Private review lesson",
            noiDung="Content visible to the assigned expert after acceptance.",
            thuTu=1,
            ngayTao=now,
        )
        draft_material = TaiLieu(
            maNhaCungCap=provider.maNhaCungCap,
            maDanhMuc=category.maDanhMuc,
            tieuDe="GĐ3.8.3 Upload Private File Here",
            loai="PDF",
            moTa="Upload a private PDF from the provider screen, then submit it for review.",
            trangThaiDuyet="DRAFT",
            trangThaiHienThi="HIDDEN",
            soVongKiemDuyetHienTai=0,
            ngayTao=now,
            ngayCapNhat=now,
        )
        db.add_all([public_lesson, review_lesson, draft_material])
        db.flush()
        storage = LocalPrivateFileStorage(DATABASE)
        private_references: list[str] = []
        try:
            import asyncio

            public_reference = asyncio.run(
                _store_pdf(storage, "gd383-learner-guide.pdf", "learner material")
            )
            private_references.append(public_reference)
            review_reference = asyncio.run(
                _store_pdf(storage, "gd383-private-review.pdf", "expert review material")
            )
            private_references.append(review_reference)
            public_material = TaiLieu(
                maNhaCungCap=provider.maNhaCungCap,
                maKhoaHoc=public_course.maKhoaHoc,
                maBaiHoc=public_lesson.maBaiHoc,
                maDanhMuc=category.maDanhMuc,
                tieuDe="GĐ3.8.3 Enrolled User Private Material",
                duongDanTep=public_reference,
                loai="PDF",
                trangThaiDuyet="APPROVED",
                trangThaiHienThi="VISIBLE",
                soVongKiemDuyetHienTai=1,
                ngayTao=now,
                ngayCapNhat=now,
            )
            review_material = TaiLieu(
                maNhaCungCap=provider.maNhaCungCap,
                maKhoaHoc=review_course.maKhoaHoc,
                maBaiHoc=review_lesson.maBaiHoc,
                maDanhMuc=category.maDanhMuc,
                tieuDe="GĐ3.8.3 Expert Private Review Material",
                duongDanTep=review_reference,
                loai="PDF",
                trangThaiDuyet="PENDING",
                trangThaiHienThi="HIDDEN",
                soVongKiemDuyetHienTai=1,
                ngayTao=now,
                ngayCapNhat=now,
            )
            external_material = TaiLieu(
                maNhaCungCap=provider.maNhaCungCap,
                maKhoaHoc=public_course.maKhoaHoc,
                maBaiHoc=public_lesson.maBaiHoc,
                maDanhMuc=category.maDanhMuc,
                tieuDe="GĐ3.8.3 External URL Control Sample",
                duongDanTep="https://example.com/",
                loai="URL",
                trangThaiDuyet="APPROVED",
                trangThaiHienThi="VISIBLE",
                soVongKiemDuyetHienTai=1,
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add_all([public_material, review_material, external_material])
            db.flush()
            accept_assignment = PhanCongKiemDuyet(
                maKhoaHoc=review_course.maKhoaHoc,
                maChuyenGia=expert.maChuyenGia,
                maDanhMuc=category.maDanhMuc,
                maChuyenMonKhop=specialty.maChuyenMon,
                soVongKiemDuyet=1,
                phuongThucPhanCong="MANUAL",
                maNguoiPhanCong=users["ADMIN"].maNguoiDung,
                lyDoPhanCong="GĐ3.8.3 browser acceptance fixture",
                trangThai="ASSIGNED",
                ngayPhanCong=now,
                hanTiepNhan=now + timedelta(hours=24),
                hanKiemDuyet=now + timedelta(hours=96),
                ngayCapNhat=now,
            )
            decline_assignment = PhanCongKiemDuyet(
                maKhoaHoc=decline_course.maKhoaHoc,
                maChuyenGia=expert.maChuyenGia,
                maDanhMuc=category.maDanhMuc,
                maChuyenMonKhop=specialty.maChuyenMon,
                soVongKiemDuyet=1,
                phuongThucPhanCong="MANUAL",
                maNguoiPhanCong=users["ADMIN"].maNguoiDung,
                lyDoPhanCong="GĐ3.8.3 decline-flow fixture",
                trangThai="ASSIGNED",
                ngayPhanCong=now,
                hanTiepNhan=now + timedelta(hours=24),
                hanKiemDuyet=now + timedelta(hours=96),
                ngayCapNhat=now,
            )
            db.add_all([accept_assignment, decline_assignment])
            db.flush()
            for account_key, user in users.items():
                db.add(
                    ThongBao(
                        maNguoiNhan=user.maNguoiDung,
                        loaiThongBao="GD383_ACCEPTANCE",
                        tieuDe="GĐ3.8.3 Browser Acceptance",
                        noiDung=f"Fixture notification for {account_key}.",
                        duLieuLienKet={"marker": "GD383", "courseId": public_course.maKhoaHoc},
                        daDoc=False,
                        khoaChongTrung=f"GD383:NOTICE:{account_key}:TO:{user.maNguoiDung}",
                        ngayTao=now,
                    )
                )
            db.add(
                ThongBao(
                    maNguoiNhan=users["EXPERT_VERIFIED"].maNguoiDung,
                    loaiThongBao="ASSIGNMENT_NEW",
                    tieuDe="Nhiệm vụ kiểm duyệt GĐ3.8.3",
                    noiDung="Hai nhiệm vụ fixture đã sẵn sàng cho luồng nhận và từ chối.",
                    duLieuLienKet={"maPhanCong": accept_assignment.maPhanCong},
                    daDoc=False,
                    khoaChongTrung=f"GD383:ASSIGNMENT:{accept_assignment.maPhanCong}",
                    ngayTao=now,
                )
            )
            enrollment = DangKyKhoaHoc(
                maNguoiDung=users["USER"].maNguoiDung,
                maKhoaHoc=public_course.maKhoaHoc,
                ngayDangKy=now,
                tienDo=0,
            )
            db.add(enrollment)
            config = db.get(CauHinhPhanCong, 1)
            config_snapshot = {
                column.name: getattr(config, column.name)
                for column in CauHinhPhanCong.__table__.columns
                if config is not None and column.name not in {"maCauHinh", "maNguoiCapNhat", "ngayCapNhat"}
            }
            db.commit()
        except Exception:
            db.rollback()
            for reference in private_references:
                storage.delete(reference)
            raise
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps({
            "database": DATABASE,
            "user_ids": [int(user.maNguoiDung) for user in users.values()],
            "provider_id": int(provider.maNhaCungCap),
            "expert_ids": [int(expert.maChuyenGia), int(unverified_expert.maChuyenGia)],
            "category_id": int(category.maDanhMuc),
            "specialty_id": int(specialty.maChuyenMon),
            "course_ids": [
                int(public_course.maKhoaHoc),
                int(review_course.maKhoaHoc),
                int(decline_course.maKhoaHoc),
            ],
            "lesson_ids": [int(public_lesson.maBaiHoc), int(review_lesson.maBaiHoc)],
            "material_ids": [
                int(draft_material.maTaiLieu),
                int(public_material.maTaiLieu),
                int(review_material.maTaiLieu),
                int(external_material.maTaiLieu),
            ],
            "assignment_ids": [
                int(accept_assignment.maPhanCong),
                int(decline_assignment.maPhanCong),
            ],
            "private_references": private_references,
            "config_snapshot": config_snapshot,
            "usernames": usernames,
            "password": PASSWORD,
            "manual_create_username": "g383_manual_expert_created",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Created GD3.8.2 browser fixtures in {actual}. Manifest: {MANIFEST}")
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
