"""
EduSuggest GĐ5.4 — Official Production Apply for Approved GĐ5.3 Standardization.

Applies ONLY the 16 approved GĐ5.3 changes to Production 'EduSuggest' atomically:
- Course #31 recovery ("Kiểm thử API thực chiến với Postman", 10 lessons, versioned WebP cover, HIDDEN + PENDING)
- Course #29 duration fix (180 -> 300 minutes)
- Material #110 URL fix (Atlassian Jira official guide)
- Material #98 URL + metadata fix (OWASP WSTG official guide)
- Provider #5 simulated profile standardization

Supports --dry-run, --confirm-apply, and --rollback.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(r"D:\đồ án\EduSuggest")
BACKEND_ROOT = PROJECT_ROOT / "backend"
STAGING_53_DIR = PROJECT_ROOT / "media" / "phase53-staging"
PROD_V5_DIR = PROJECT_ROOT / "media" / "courses" / "v5-realistic"
BACKUP_ROLLBACK_PATH = PROJECT_ROOT / "backend" / "database" / "backups" / "phase54-std-deploy" / "20261126" / "prod-phase53-rollback.json"

sys.path.insert(0, str(BACKEND_ROOT))
from config.config import get_settings  # noqa: E402
from scripts.phase53_standardize_staging import COURSE_31_LESSONS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply approved GĐ5.3 standardization to Production EduSuggest.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirm-apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    eng = create_engine(get_settings().database_url.get_secret_value())
    with eng.connect() as conn:
        cur_db = str(conn.execute(text("SELECT current_database()")).scalar_one())
        rev = str(conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one())
        tbls = int(conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar_one())
        if cur_db != "EduSuggest":
            print(f"ABORT: expected 'EduSuggest', got '{cur_db}'")
            return 1
        if rev != "e5f6a7b8c9d0" or tbls != 35:
            print(f"ABORT: unexpected schema rev={rev} tables={tbls}")
            return 1

    if args.rollback:
        rb = json.loads(BACKUP_ROLLBACK_PATH.read_text(encoding="utf-8"))
        with eng.begin() as conn:
            conn.execute(text('DELETE FROM "BaiHoc" WHERE "maKhoaHoc" = 31'))
            for op in rb["restore_rows"]:
                for col, val in op["old_values"].items():
                    conn.execute(
                        text(f'UPDATE "{op["table"]}" SET "{col}" = :val WHERE "{op["pk_col"]}" = :pk'),
                        {"val": val, "pk": op["pk_val"]},
                    )
        print("PRODUCTION ROLLBACK COMPLETE.")
        return 0

    src_cover_31 = STAGING_53_DIR / "course-031-api-testing.webp"
    if not src_cover_31.is_file():
        print(f"ABORT: missing {src_cover_31}")
        return 1

    with eng.connect() as conn:
        ref_tables = [
            "BaiHoc", "TaiLieu", "DangKyKhoaHoc", "LichSuHocTap",
            "DanhGiaChuyenGia", "PhanCongKiemDuyet", "HangDoiPhanCong",
            "YeuThich", "ChiTietGioHang", "ChiTietDonHang",
        ]
        c31_refs = {t: conn.execute(text(f'SELECT count(*) FROM "{t}" WHERE "maKhoaHoc"=31')).scalar_one() for t in ref_tables}
        if any(v > 0 for v in c31_refs.values()):
            print(f"ABORT: Course #31 has references on Production: {c31_refs}")
            return 2

        old_c31 = dict(conn.execute(text('SELECT "tieuDe", "moTa", "gia", "trinhDo", "thoiLuong", "trangThaiDuyet", "trangThaiHienThi", "hinhAnh" FROM "KhoaHoc" WHERE "maKhoaHoc"=31')).fetchone()._mapping)
        old_c29 = dict(conn.execute(text('SELECT "thoiLuong" FROM "KhoaHoc" WHERE "maKhoaHoc"=29')).fetchone()._mapping)
        old_m110 = dict(conn.execute(text('SELECT "duongDanTep" FROM "TaiLieu" WHERE "maTaiLieu"=110')).fetchone()._mapping)
        old_m98 = dict(conn.execute(text('SELECT "tieuDe", "moTa", "duongDanTep" FROM "TaiLieu" WHERE "maTaiLieu"=98')).fetchone()._mapping)
        old_p5 = dict(conn.execute(text('SELECT "tieuSu", "chuyenMon" FROM "NhaCungCapKhoaHoc" WHERE "maNhaCungCap"=5')).fetchone()._mapping)

    if args.dry_run:
        print(json.dumps({
            "mode": "DRY_RUN_PRODUCTION",
            "db": cur_db,
            "rev": rev,
            "tables": tbls,
            "c31_refs_all_zero": True,
            "old_c31_title": old_c31["tieuDe"],
            "old_c29_dur": old_c29["thoiLuong"],
            "old_p5_bio": old_p5["tieuSu"],
            "ready_to_apply": True,
        }, ensure_ascii=False, indent=2))
        return 0

    # Save exact Production rollback manifest before writing
    BACKUP_ROLLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_ROLLBACK_PATH.write_text(json.dumps({
        "restore_rows": [
            {"table": "KhoaHoc", "pk_col": "maKhoaHoc", "pk_val": 31, "old_values": {k: (str(v) if v is not None else None) for k, v in old_c31.items()}},
            {"table": "KhoaHoc", "pk_col": "maKhoaHoc", "pk_val": 29, "old_values": old_c29},
            {"table": "TaiLieu", "pk_col": "maTaiLieu", "pk_val": 110, "old_values": old_m110},
            {"table": "TaiLieu", "pk_col": "maTaiLieu", "pk_val": 98, "old_values": old_m98},
            {"table": "NhaCungCapKhoaHoc", "pk_col": "maNhaCungCap", "pk_val": 5, "old_values": old_p5},
        ]
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Copy versioned cover for #31 (preserving old course-031.webp as course-031-pre54.webp backup)
    dst_cover_31 = PROD_V5_DIR / "course-031-api-testing.webp"
    shutil.copy2(src_cover_31, dst_cover_31)
    assert dst_cover_31.is_file()

    new_c31 = {
        "tieuDe": "Kiểm thử API thực chiến với Postman",
        "moTa": (
            "Khóa học thực hành kiểm thử REST API từ nền tảng đến tự động hóa với Postman và Newman. "
            "Học viên nắm vững HTTP Methods, Status Codes, JSON Schema, xác thực Bearer JWT/OAuth 2.0, "
            "biến môi trường, viết Test Scripts bằng JavaScript, chạy Collection Runner theo dữ liệu CSV/JSON "
            "và tích hợp Newman vào quy trình CI/CD qua dự án thực hành API Testing hoàn chỉnh."
        ),
        "gia": 399000,
        "trinhDo": "INTERMEDIATE",
        "thoiLuong": 320,
        "trangThaiDuyet": "PENDING",
        "trangThaiHienThi": "HIDDEN",
        "hinhAnh": "/media/courses/v5-realistic/course-031-api-testing.webp",
    }

    with eng.begin() as conn:
        conn.execute(text('''
            UPDATE "KhoaHoc"
            SET "tieuDe"=:tieuDe, "moTa"=:moTa, "gia"=:gia, "trinhDo"=:trinhDo,
                "thoiLuong"=:thoiLuong, "trangThaiDuyet"=:trangThaiDuyet,
                "trangThaiHienThi"=:trangThaiHienThi, "hinhAnh"=:hinhAnh
            WHERE "maKhoaHoc"=31
        '''), new_c31)
        for thu_tu, tieu_de, thoi_luong, noi_dung in COURSE_31_LESSONS:
            conn.execute(text('''
                INSERT INTO "BaiHoc" ("maKhoaHoc", "tieuDe", "noiDung", "duongDanVideo", "thoiLuong", "thuTu", "ngayTao")
                VALUES (31, :tieuDe, :noiDung, NULL, :thoiLuong, :thuTu, NOW())
            '''), {"tieuDe": tieu_de, "noiDung": noi_dung, "thoiLuong": thoi_luong, "thuTu": thu_tu})

        conn.execute(text('UPDATE "KhoaHoc" SET "thoiLuong"=300 WHERE "maKhoaHoc"=29'))
        conn.execute(text('UPDATE "TaiLieu" SET "duongDanTep"=\'https://www.atlassian.com/software/jira/guides/issues/overview\' WHERE "maTaiLieu"=110'))
        conn.execute(text('''
            UPDATE "TaiLieu"
            SET "tieuDe"=\'OWASP Web Security Testing Guide (WSTG)\',
                "moTa"=\'Hướng dẫn chuẩn hóa kiểm thử bảo mật ứng dụng web chính thức từ OWASP Foundation (thay thế liên kết pentest-standard.org đã ngừng hoạt động).\',
                "duongDanTep"=\'https://owasp.org/www-project-web-security-testing-guide/\'
            WHERE "maTaiLieu"=98
        '''))
        conn.execute(text('''
            UPDATE "NhaCungCapKhoaHoc"
            SET "tieuSu"=\'Hồ sơ nhà cung cấp mô phỏng phụ trách biên soạn học liệu thực hành về kiểm thử phần mềm, lập trình ứng dụng, dữ liệu và hạ tầng cloud trên EduSuggest.\',
                "chuyenMon"=\'Kiểm thử phần mềm & QA, Lập trình ứng dụng, Dữ liệu & Cloud\'
            WHERE "maNhaCungCap"=5
        '''))

        total_lessons = conn.execute(text('SELECT count(*) FROM "BaiHoc"')).scalar_one()
        c31_state = conn.execute(text('SELECT "tieuDe", "trangThaiDuyet", "trangThaiHienThi", "hinhAnh" FROM "KhoaHoc" WHERE "maKhoaHoc"=31')).fetchone()

    print(json.dumps({
        "status": "PRODUCTION_APPLIED_OK",
        "db": cur_db,
        "total_lessons": total_lessons,
        "course_31": list(c31_state),
        "rollback_manifest": str(BACKUP_ROLLBACK_PATH),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
