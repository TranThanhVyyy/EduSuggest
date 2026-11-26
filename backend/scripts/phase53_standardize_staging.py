"""
EduSuggest GĐ5.3 — Controlled Staging Dataset Standardization Script.

SAFETY:
- HARD-BLOCKED against Production 'EduSuggest'. Only executes on 'edusuggest_phase53_staging'.
- Supports --dry-run, --apply, and --rollback.
- Records every single field change in docs/reports/dataset-refinement-diff.json
  and docs/reports/dataset-refinement-rollback-manifest.json.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(r"D:\đồ án\EduSuggest")
BACKEND_ROOT = PROJECT_ROOT / "backend"
STAGING_DIR = PROJECT_ROOT / "media" / "phase53-staging"
REPORTS_DIR = PROJECT_ROOT / "docs" / "reports"
DIFF_PATH = REPORTS_DIR / "dataset-refinement-diff.json"
ROLLBACK_PATH = REPORTS_DIR / "dataset-refinement-rollback-manifest.json"
ALLOWED_STAGING_DBS = {"edusuggest_phase53_staging"}

sys.path.insert(0, str(BACKEND_ROOT))
from config.config import get_settings  # noqa: E402
import scripts.phase5_cover_pipeline as p5  # noqa: E402


COURSE_31_LESSONS: list[tuple[int, str, int, str]] = [
    (
        1,
        "Tổng quan REST API và kiến trúc Client–Server",
        25,
        "Mục tiêu: Hiểu bản chất giao tiếp HTTP giữa Client và Server, tài nguyên (Resource), Endpoint và nguyên tắc Stateless của REST API.\n\n"
        "Nội dung chính:\n- Cấu trúc một HTTP Request (Method, URL, Headers, Body) và HTTP Response (Status Code, Headers, Payload).\n"
        "- Sự khác biệt giữa REST API, GraphQL và SOAP trong thực tế kiểm thử phần mềm.\n\n"
        "Bài tập nhanh: Xác định 5 endpoint tiêu biểu của một hệ thống quản lý khóa học và phân loại tài nguyên tương ứng.",
    ),
    (
        2,
        "HTTP Methods (GET, POST, PUT, PATCH, DELETE) và tính Idempotent",
        30,
        "Mục tiêu: Phân biệt chính xác hành vi chuẩn của từng HTTP Method và cách kiểm thử tính Idempotent.\n\n"
        "Nội dung chính:\n- GET (truy vấn không làm đổi trạng thái), POST (tạo mới), PUT (thay thế toàn phần), PATCH (cập nhật một phần), DELETE (xóa).\n"
        "- Các lỗi phổ biến cần kiểm tra: gửi trùng POST gây tạo dữ liệu lặp, dùng GET làm thay đổi dữ liệu.\n\n"
        "Thực hành: Gửi chuỗi request CRUD tới API mẫu và đối chiếu trạng thái trước/sau.",
    ),
    (
        3,
        "Đọc hiểu HTTP Status Codes và xử lý lỗi API chuẩn",
        25,
        "Mục tiêu: Kiểm chứng chính xác mã trạng thái 2xx, 3xx, 4xx, 5xx và thông điệp lỗi an toàn.\n\n"
        "Nội dung chính:\n- 200 OK, 201 Created, 204 No Content.\n- 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests.\n"
        "- 500 Internal Server Error và dấu hiệu rò rỉ stack trace cần báo lỗi bảo mật.\n\n"
        "Kết quả mong đợi: Lập bảng ma trận kiểm thử Status Code cho một endpoint đăng ký/đặt hàng.",
    ),
    (
        4,
        "Làm việc với JSON Payload, Schema và Kiểm thử biên dữ liệu",
        30,
        "Mục tiêu: Thiết kế bộ dữ liệu kiểm thử JSON cho các trường hợp hợp lệ, thiếu trường bắt buộc, sai kiểu và giá trị biên.\n\n"
        "Nội dung chính:\n- Cấu trúc JSON Object, Array, Nested Object, null và kiểu dữ liệu số/chuỗi/boolean.\n"
        "- Kiểm thử biên: chuỗi rỗng, vượt độ dài tối đa, số âm, ký tự đặc biệt Unicode tiếng Việt.\n\n"
        "Thực hành: Viết JSON Schema xác thực cấu trúc phản hồi của API danh sách khóa học.",
    ),
    (
        5,
        "Tổ chức Postman Workspace, Collections và Folders khoa học",
        30,
        "Mục tiêu: Xây dựng bộ Postman Collection chuẩn dự án theo luồng nghiệp vụ và dễ bảo trì.\n\n"
        "Nội dung chính:\n- Tạo Workspace, phân chia Collection theo module (Auth, Catalog, Cart, Order).\n"
        "- Viết tài liệu trực tiếp trên Request/Folder, lưu Example Responses và xuất/nhập JSON Collection.\n\n"
        "Kết quả mong đợi: Hoàn thiện một Collection gồm tối thiểu 8 request có mô tả và ví dụ phản hồi.",
    ),
    (
        6,
        "Kiểm thử xác thực và phân quyền API (API Key, Bearer JWT, OAuth 2.0)",
        35,
        "Mục tiêu: Cấu hình xác thực tự động trong Postman và kiểm thử các lỗ hổng phân quyền (RBAC/IDOR).\n\n"
        "Nội dung chính:\n- Thiết lập Authorization kế thừa ở cấp Collection/Folder.\n"
        "- Kiểm thử token hết hạn, token bị thu hồi, thiếu header Authorization (401) và truy cập chéo tài nguyên người khác (403).\n\n"
        "Thực hành: Tự động lấy `access_token` từ API đăng nhập và lưu vào biến môi trường cho các request kế tiếp.",
    ),
    (
        7,
        "Biến (Variables), Environments và Chuỗi dữ liệu động (Chaining Requests)",
        30,
        "Mục tiêu: Tách biệt cấu hình Dev/Staging/Production bằng Environments và truyền dữ liệu giữa các API.\n\n"
        "Nội dung chính:\n- Phạm vi biến trong Postman: Global, Collection, Environment, Data, Local.\n"
        "- Truyền `id` vừa tạo từ POST sang GET/PATCH/DELETE để tạo luồng kiểm thử khép kín.\n\n"
        "Thực hành: Xây dựng 2 Environment (Local & Staging) không hard-code URL hay mật khẩu trong Collection.",
    ),
    (
        8,
        "Viết Test Scripts tự động với pm.test và Chai Assertions",
        40,
        "Mục tiêu: Tự động hóa kiểm chứng Status Code, thời gian phản hồi, JSON Schema và logic nghiệp vụ bằng JavaScript.\n\n"
        "Nội dung chính:\n- Sử dụng `pm.test`, `pm.expect`, `pm.response.json()` và Pre-request Scripts tạo dữ liệu động.\n"
        "- Kiểm tra cấu trúc JSON, kiểm tra danh sách không rỗng, xác minh giá trị tính toán chính xác.\n\n"
        "Thực hành: Viết tối thiểu 12 assertions cho luồng Auth + CRUD.",
    ),
    (
        9,
        "Chạy kiểm thử hàng loạt với Collection Runner và Data-Driven Testing (CSV/JSON)",
        35,
        "Mục tiêu: Chạy tự động toàn bộ bộ test theo bộ dữ liệu đầu vào CSV/JSON để phát hiện hồi quy nhanh.\n\n"
        "Nội dung chính:\n- Thiết lập Collection Runner, thứ tự chạy, delay giữa các request và đọc biến từ tệp CSV/JSON.\n"
        "- Phân tích báo cáo Pass/Fail và cô lập nguyên nhân lỗi dữ liệu so với lỗi API.\n\n"
        "Thực hành: Chạy 10 bộ dữ liệu kiểm thử biên bằng tệp JSON trong Collection Runner.",
    ),
    (
        10,
        "Tích hợp Newman CLI vào CI/CD và Dự án cuối khóa API Testing",
        40,
        "Mục tiêu: Chạy bộ Postman Collection bằng dòng lệnh Newman, xuất báo cáo HTML và hoàn thiện dự án kiểm thử API.\n\n"
        "Đề bài dự án cuối khóa:\n- Thiết kế bộ kiểm thử API đầy đủ (Positive, Negative, Security 401/403, Boundary) cho một ứng dụng RESTful.\n"
        "- Chạy toàn bộ bằng `newman run collection.json -e env.json --reporters cli,htmlextra`.\n\n"
        "Tiêu chí hoàn thành: 100% test case trọng yếu có assertion rõ ràng, không hard-code bí mật, có báo cáo Newman hoàn chỉnh.",
    ),
]


def generate_course_31_cover() -> tuple[str, dict[str, Any]]:
    """Generate a dedicated QA/API Testing 1280x720 WebP cover for Course #31 in staging."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STAGING_DIR / "course-031-api-testing.webp"
    meta_path = STAGING_DIR / "course-031-cover-meta.json"
    if out_path.is_file() and meta_path.is_file():
        return str(out_path), json.loads(meta_path.read_text(encoding="utf-8"))

    fetcher = p5.RateLimitedFetcher(min_interval_sec=0.18)
    cp = json.loads(p5.CHECKPOINT_PATH.read_text(encoding="utf-8"))
    used_urls = {v["original_image_url"] for v in cp.values() if v.get("original_image_url")}
    chosen = None
    for q in ("software testing", "coding monitor", "developer laptop"):
        for cand in p5.search_openverse(fetcher, q, page=1, curated_sources=True):
            if cand["original_image_url"] in used_urls or cand["source_origin"] != "stocksnap":
                continue
            data = fetcher.download_bytes(cand["original_image_url"])
            if not data:
                continue
            img = Image.open(io.BytesIO(data))
            w, h = img.size
            if w >= 800 and h >= 450 and 1.25 <= (w / h) <= 2.1:
                chosen = (cand, img)
                break
        if chosen:
            break
    assert chosen is not None, "Could not fetch clean stocksnap photo for Course #31"
    cand, img = chosen
    course_obj = {
        "maKhoaHoc": 31,
        "tieuDe": "Kiểm thử API thực chiến với Postman",
        "tenDanhMuc": "Kiểm thử phần mềm & QA",
    }
    composed, tmeta = p5.compose_editorial_cover(img, course_obj, "product_career")
    composed.save(out_path, format="WEBP", quality=84, method=6)
    ob = out_path.read_bytes()
    meta = {
        "source_provider": cand["source_provider"],
        "source_origin": cand["source_origin"],
        "source_url": cand["source_url"],
        "original_image_url": cand["original_image_url"],
        "author": cand["author"],
        "license": cand["license"],
        "license_url": cand["license_url"],
        "sha256": hashlib.sha256(ob).hexdigest(),
        "size_bytes": len(ob),
        "transformation": tmeta,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_path), meta


def main() -> int:
    parser = argparse.ArgumentParser(description="EduSuggest GĐ5.3 Staging Standardization")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    base_url = get_settings().database_url.get_secret_value().rsplit("/", 1)[0]
    eng = create_engine(base_url + "/edusuggest_phase53_staging")

    with eng.connect() as conn:
        cur_db = str(conn.execute(text("SELECT current_database()")).scalar_one())
        if cur_db == "EduSuggest" or cur_db not in ALLOWED_STAGING_DBS:
            print(f"SAFETY ABORT: Refusing to run on database '{cur_db}'!")
            return 1

    if args.rollback:
        rb = json.loads(ROLLBACK_PATH.read_text(encoding="utf-8"))
        with eng.begin() as conn:
            for item in reversed(rb["operations"]):
                if item["action"] == "DELETE_INSERTED_LESSONS":
                    conn.execute(text('DELETE FROM "BaiHoc" WHERE "maKhoaHoc" = :cid'), {"cid": item["course_id"]})
                elif item["action"] == "RESTORE_ROW":
                    tbl = item["table"]
                    pk_col = item["pk_column"]
                    pk_val = item["pk_value"]
                    for col, old_val in item["old_values"].items():
                        conn.execute(text(f'UPDATE "{tbl}" SET "{col}" = :val WHERE "{pk_col}" = :pk'), {"val": old_val, "pk": pk_val})
        print("ROLLBACK COMPLETE on edusuggest_phase53_staging.")
        return 0

    # Verify Course #31 still has 0 business references before doing anything
    with eng.connect() as conn:
        ref_tables = [
            "BaiHoc", "TaiLieu", "DangKyKhoaHoc", "LichSuHocTap",
            "DanhGiaChuyenGia", "PhanCongKiemDuyet", "HangDoiPhanCong",
            "YeuThich", "ChiTietGioHang", "ChiTietDonHang",
        ]
        c31_refs = {t: conn.execute(text(f'SELECT count(*) FROM "{t}" WHERE "maKhoaHoc" = 31')).scalar_one() for t in ref_tables}
        if any(v > 0 for v in c31_refs.values()):
            print(f"ABORT Course #31 recovery: found existing references {c31_refs}")
            return 2

        old_c31 = dict(conn.execute(text('SELECT "tieuDe", "moTa", "gia", "trinhDo", "thoiLuong", "trangThaiDuyet", "trangThaiHienThi", "hinhAnh" FROM "KhoaHoc" WHERE "maKhoaHoc"=31')).fetchone()._mapping)
        old_c29 = dict(conn.execute(text('SELECT "thoiLuong" FROM "KhoaHoc" WHERE "maKhoaHoc"=29')).fetchone()._mapping)
        old_m110 = dict(conn.execute(text('SELECT "tieuDe", "duongDanTep" FROM "TaiLieu" WHERE "maTaiLieu"=110')).fetchone()._mapping)
        old_m98 = dict(conn.execute(text('SELECT "tieuDe", "moTa", "duongDanTep" FROM "TaiLieu" WHERE "maTaiLieu"=98')).fetchone()._mapping)
        old_p5 = dict(conn.execute(text('SELECT "tieuSu", "chuyenMon" FROM "NhaCungCapKhoaHoc" WHERE "maNhaCungCap"=5')).fetchone()._mapping)

    cover31_path, cover31_meta = generate_course_31_cover()
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
        "hinhAnh": "/media/phase53-staging/course-031-api-testing.webp",
    }
    new_c29 = {"thoiLuong": 300}
    new_m110 = {"duongDanTep": "https://www.atlassian.com/software/jira/guides/issues/overview"}
    new_m98 = {
        "tieuDe": "OWASP Web Security Testing Guide (WSTG)",
        "moTa": "Hướng dẫn chuẩn hóa kiểm thử bảo mật ứng dụng web chính thức từ OWASP Foundation (thay thế liên kết pentest-standard.org đã ngừng hoạt động).",
        "duongDanTep": "https://owasp.org/www-project-web-security-testing-guide/",
    }
    new_p5 = {
        "tieuSu": "Hồ sơ nhà cung cấp mô phỏng phụ trách biên soạn học liệu thực hành về kiểm thử phần mềm, lập trình ứng dụng, dữ liệu và hạ tầng cloud trên EduSuggest.",
        "chuyenMon": "Kiểm thử phần mềm & QA, Lập trình ứng dụng, Dữ liệu & Cloud",
    }

    diffs: list[dict[str, Any]] = []
    def add_diff(table: str, rec_id: int, field: str, old_v: Any, new_v: Any, reason: str, source: str) -> None:
        diffs.append({
            "table": table,
            "record_id": rec_id,
            "field": field,
            "old_value": str(old_v) if old_v is not None else None,
            "new_value": str(new_v) if new_v is not None else None,
            "reason": reason,
            "source": source,
            "validation_result": "PLANNED" if args.dry_run else "APPLIED_STAGING",
        })

    for k, nv in new_c31.items():
        add_diff("KhoaHoc", 31, k, old_c31.get(k), nv, "Khôi phục khóa học rác #31 (0 tham chiếu nghiệp vụ), giữ HIDDEN + PENDING chờ kiểm duyệt", "EduSuggest authored + Openverse CC0 cover")
    add_diff("BaiHoc", 31, "inserted_lessons_count", 0, len(COURSE_31_LESSONS), "Bổ sung 10 bài học thực chiến API Testing với Postman & Newman cho khóa #31", "EduSuggest authored")
    add_diff("KhoaHoc", 29, "thoiLuong", old_c29["thoiLuong"], new_c29["thoiLuong"], "Sửa lỗi logic thời lượng khóa (180 phút) nhỏ hơn tổng 5 bài học bắt buộc (300 phút)", "Computed from SUM(BaiHoc.thoiLuong)")
    add_diff("TaiLieu", 110, "duongDanTep", old_m110["duongDanTep"], new_m110["duongDanTep"], "Thay thế URL Jira 404 bằng tài liệu chính thức Atlassian Jira (verified 200 OK)", "Official Atlassian Documentation")
    for k, nv in new_m98.items():
        add_diff("TaiLieu", 98, k, old_m98.get(k), nv, "Thay thế liên kết pentest-standard.org ngừng hoạt động bằng OWASP WSTG chính thức (verified 200 OK) và cập nhật metadata khớp nội dung", "Official OWASP Foundation Documentation")
    for k, nv in new_p5.items():
        add_diff("NhaCungCapKhoaHoc", 5, k, old_p5.get(k), nv, "Thay thế dữ liệu placeholder 'h' bằng hồ sơ mô phỏng rõ ràng khớp 12 khóa học đang quản lý", "EduSuggest simulated profile")

    if args.dry_run:
        print(json.dumps({"mode": "DRY_RUN", "target_db": cur_db, "planned_changes": len(diffs), "c31_refs": c31_refs}, ensure_ascii=False, indent=2))
        return 0

    with eng.begin() as conn:
        # 1. Update Course #31 + insert 10 lessons
        conn.execute(text('''
            UPDATE "KhoaHoc"
            SET "tieuDe" = :tieuDe, "moTa" = :moTa, "gia" = :gia, "trinhDo" = :trinhDo,
                "thoiLuong" = :thoiLuong, "trangThaiDuyet" = :trangThaiDuyet,
                "trangThaiHienThi" = :trangThaiHienThi, "hinhAnh" = :hinhAnh
            WHERE "maKhoaHoc" = 31
        '''), new_c31)
        for thu_tu, tieu_de, thoi_luong, noi_dung in COURSE_31_LESSONS:
            conn.execute(text('''
                INSERT INTO "BaiHoc" ("maKhoaHoc", "tieuDe", "noiDung", "duongDanVideo", "thoiLuong", "thuTu", "ngayTao")
                VALUES (31, :tieuDe, :noiDung, NULL, :thoiLuong, :thuTu, NOW())
            '''), {"tieuDe": tieu_de, "noiDung": noi_dung, "thoiLuong": thoi_luong, "thuTu": thu_tu})

        # 2. Fix Course #29 duration
        conn.execute(text('UPDATE "KhoaHoc" SET "thoiLuong" = :thoiLuong WHERE "maKhoaHoc" = 29'), new_c29)

        # 3. Fix Material #110 and #98
        conn.execute(text('UPDATE "TaiLieu" SET "duongDanTep" = :duongDanTep WHERE "maTaiLieu" = 110'), new_m110)
        conn.execute(text('UPDATE "TaiLieu" SET "tieuDe" = :tieuDe, "moTa" = :moTa, "duongDanTep" = :duongDanTep WHERE "maTaiLieu" = 98'), new_m98)

        # 4. Fix Provider #5 placeholder bio/specialty
        conn.execute(text('UPDATE "NhaCungCapKhoaHoc" SET "tieuSu" = :tieuSu, "chuyenMon" = :chuyenMon WHERE "maNhaCungCap" = 5'), new_p5)

        # Verify FK / counts on staging
        total_lessons = conn.execute(text('SELECT count(*) FROM "BaiHoc"')).scalar_one()
        c31_lessons = conn.execute(text('SELECT count(*) FROM "BaiHoc" WHERE "maKhoaHoc" = 31')).scalar_one()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DIFF_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_db": cur_db,
        "production_modified": False,
        "course_31_cover_meta": cover31_meta,
        "total_changes": len(diffs),
        "changes": diffs,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    ROLLBACK_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_db": cur_db,
        "operations": [
            {"action": "RESTORE_ROW", "table": "KhoaHoc", "pk_column": "maKhoaHoc", "pk_value": 31, "old_values": {k: (str(v) if v is not None else None) for k, v in old_c31.items()}},
            {"action": "DELETE_INSERTED_LESSONS", "course_id": 31},
            {"action": "RESTORE_ROW", "table": "KhoaHoc", "pk_column": "maKhoaHoc", "pk_value": 29, "old_values": old_c29},
            {"action": "RESTORE_ROW", "table": "TaiLieu", "pk_column": "maTaiLieu", "pk_value": 110, "old_values": old_m110},
            {"action": "RESTORE_ROW", "table": "TaiLieu", "pk_column": "maTaiLieu", "pk_value": 98, "old_values": old_m98},
            {"action": "RESTORE_ROW", "table": "NhaCungCapKhoaHoc", "pk_column": "maNhaCungCap", "pk_value": 5, "old_values": old_p5},
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "APPLIED_STAGING",
        "target_db": cur_db,
        "total_changes": len(diffs),
        "total_lessons_staging": total_lessons,
        "course_31_lessons": c31_lessons,
        "course_31_cover": cover31_path,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
