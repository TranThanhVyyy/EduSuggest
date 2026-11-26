"""Delete only IDs recorded by the GĐ3.8.2 staging fixture manifest."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parents[1]
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
os.environ["DEBUG"] = "False"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from config.config import BACKEND_DIR
from models import (
    BaiHoc,
    CauHinhPhanCong,
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    DangKyKhoaHoc,
    DanhGiaChuyenGia,
    DanhMuc,
    HangDoiPhanCong,
    KhoaHoc,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    NhatKyKyLuatChuyenGia,
    PhanCongKiemDuyet,
    TaiLieu,
    ThongBao,
    ViPhamChuyenGia,
    YeuCauTamNgungChuyenGia,
)
from service.private_file_storage import LocalPrivateFileStorage

DATABASE = "EduSuggest_phase3_test"
MANIFEST = BACKEND_DIR / "logs" / "gd382-staging" / "fixtures.json"


def main() -> int:
    if not MANIFEST.is_file():
        print("No GD3.8.2 fixture manifest; nothing to clean.")
        return 0
    fixture = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if fixture.get("database") != DATABASE:
        raise RuntimeError("Fixture manifest database guard failed.")
    load_dotenv(BACKEND_DIR / ".env")
    engine = create_engine(make_url(os.environ["DATABASE_URL"]).set(database=DATABASE), pool_pre_ping=True)
    with Session(engine) as db:
        actual = db.execute(text("SELECT current_database()")).scalar_one()
        if actual != DATABASE:
            raise RuntimeError(f"Safety guard: expected {DATABASE}, got {actual}")
        expected_usernames = list(fixture.get("usernames", {}).values())
        expected_usernames.append(str(fixture.get("manual_create_username", "g383_manual_expert_created")))
        user_ids = sorted(
            {
                *[int(value) for value in fixture.get("user_ids", [])],
                *[
                    int(value)
                    for value in db.scalars(
                        select(NguoiDung.maNguoiDung).where(
                            NguoiDung.tenTaiKhoan.in_(expected_usernames)
                        )
                    ).all()
                ],
            }
        )
        provider_ids = list(
            db.scalars(
                select(NhaCungCapKhoaHoc.maNhaCungCap).where(
                    NhaCungCapKhoaHoc.maNguoiDung.in_(user_ids)
                )
            ).all()
        )
        expert_ids = list(
            db.scalars(
                select(ChuyenGia.maChuyenGia).where(ChuyenGia.maNguoiDung.in_(user_ids))
            ).all()
        )
        course_ids = sorted(
            {
                *[int(value) for value in fixture.get("course_ids", [])],
                *[
                    int(value)
                    for value in db.scalars(
                        select(KhoaHoc.maKhoaHoc).where(KhoaHoc.maNhaCungCap.in_(provider_ids))
                    ).all()
                ],
            }
        )
        material_ids = sorted(
            {
                *[int(value) for value in fixture.get("material_ids", [])],
                *[
                    int(value)
                    for value in db.scalars(
                        select(TaiLieu.maTaiLieu).where(TaiLieu.maNhaCungCap.in_(provider_ids))
                    ).all()
                ],
            }
        )
        private_references = {
            str(value) for value in fixture.get("private_references", []) if value
        }
        if material_ids:
            private_references.update(
                str(value)
                for value in db.scalars(
                    select(TaiLieu.duongDanTep).where(TaiLieu.maTaiLieu.in_(material_ids))
                ).all()
                if value and str(value).startswith("private://materials/")
            )
        assignment_ids = list(
            db.scalars(
                select(PhanCongKiemDuyet.maPhanCong).where(
                    (PhanCongKiemDuyet.maKhoaHoc.in_(course_ids))
                    | (PhanCongKiemDuyet.maTaiLieu.in_(material_ids))
                    | (PhanCongKiemDuyet.maChuyenGia.in_(expert_ids))
                )
            ).all()
        )
        db.execute(delete(ThongBao).where(ThongBao.maNguoiNhan.in_(user_ids)))
        db.execute(
            delete(NhatKyKyLuatChuyenGia).where(
                NhatKyKyLuatChuyenGia.maChuyenGia.in_(expert_ids)
            )
        )
        db.execute(
            delete(ViPhamChuyenGia).where(
                (ViPhamChuyenGia.maChuyenGia.in_(expert_ids))
                | (ViPhamChuyenGia.maPhanCong.in_(assignment_ids))
            )
        )
        db.execute(
            delete(YeuCauTamNgungChuyenGia).where(
                YeuCauTamNgungChuyenGia.maChuyenGia.in_(expert_ids)
            )
        )
        db.execute(
            delete(DanhGiaChuyenGia).where(
                (DanhGiaChuyenGia.maKhoaHoc.in_(course_ids))
                | (DanhGiaChuyenGia.maTaiLieu.in_(material_ids))
                | (DanhGiaChuyenGia.maChuyenGia.in_(expert_ids))
                | (DanhGiaChuyenGia.maPhanCong.in_(assignment_ids))
            )
        )
        db.execute(
            delete(HangDoiPhanCong).where(
                (HangDoiPhanCong.maKhoaHoc.in_(course_ids))
                | (HangDoiPhanCong.maTaiLieu.in_(material_ids))
            )
        )
        db.execute(
            delete(PhanCongKiemDuyet).where(
                (PhanCongKiemDuyet.maPhanCong.in_(assignment_ids))
                | (PhanCongKiemDuyet.maKhoaHoc.in_(course_ids))
                | (PhanCongKiemDuyet.maTaiLieu.in_(material_ids))
                | (PhanCongKiemDuyet.maChuyenGia.in_(expert_ids))
            )
        )
        db.execute(delete(LichSuHocTap).where(LichSuHocTap.maKhoaHoc.in_(course_ids)))
        db.execute(delete(DangKyKhoaHoc).where(DangKyKhoaHoc.maKhoaHoc.in_(course_ids)))
        db.execute(delete(TaiLieu).where(TaiLieu.maTaiLieu.in_(material_ids)))
        db.execute(delete(BaiHoc).where(BaiHoc.maKhoaHoc.in_(course_ids)))
        db.execute(delete(KhoaHoc).where(KhoaHoc.maKhoaHoc.in_(course_ids)))
        db.execute(
            delete(ChuyenGiaChuyenMon).where(
                ChuyenGiaChuyenMon.maChuyenGia.in_(expert_ids)
            )
        )
        db.execute(delete(ChuyenMonDanhMuc).where(ChuyenMonDanhMuc.maChuyenMon == int(fixture["specialty_id"])))
        db.execute(delete(ChuyenGia).where(ChuyenGia.maChuyenGia.in_(expert_ids)))
        db.execute(
            delete(NhaCungCapKhoaHoc).where(
                NhaCungCapKhoaHoc.maNhaCungCap.in_(provider_ids)
            )
        )
        config = db.get(CauHinhPhanCong, 1)
        if config is not None:
            for field, value in fixture.get("config_snapshot", {}).items():
                setattr(config, field, value)
            config.maNguoiCapNhat = None
        db.execute(delete(ChuyenMon).where(ChuyenMon.maChuyenMon == int(fixture["specialty_id"])))
        db.execute(delete(DanhMuc).where(DanhMuc.maDanhMuc == int(fixture["category_id"])))
        db.execute(delete(NguoiDung).where(NguoiDung.maNguoiDung.in_(user_ids)))
        db.commit()
        storage = LocalPrivateFileStorage(DATABASE)
        for reference in private_references:
            storage.delete(reference)
        MANIFEST.unlink(missing_ok=True)
        print(f"Removed GD3.8.2 fixtures from {actual}.")
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
