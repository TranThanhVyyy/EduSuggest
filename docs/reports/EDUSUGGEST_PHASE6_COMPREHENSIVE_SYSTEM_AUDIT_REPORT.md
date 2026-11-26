# EDUSUGGEST — GĐ6.1: BÁO CÁO KIỂM TOÁN TOÀN DIỆN HỆ THỐNG

**Ngày kiểm toán:** 2026-11-27  
**Chế độ kiểm toán:** **100% READ ONLY trên Production `EduSuggest`** (`35` bảng, Alembic `e5f6a7b8c9d0`, `edusuggest-official-v2`, `http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api`) + đối chiếu kiểm thử trên Staging cô lập `EduSuggest_phase4_test` (`5176`/`8003`). **DỪNG CHỜ PHÊ DUYỆT GĐ6.2 — CHƯA TỰ ĐỘNG TRIỂN KHAI BẢN SỬA LÊN PRODUCTION.**

---

## 1. Tóm tắt điều hành (Executive Summary)

| Hạng mục kiểm toán | Kết quả thực tế |
| :--- | :--- |
| **Baseline Production `edusuggest-official-v2`** | `35` bảng · `e5f6a7b8c9d0` · `24` danh mục · `120` khóa học · `120/120` ảnh WebP · `421` bài học (`65` video hợp lệ) · `243` tài liệu · `150/150 LEGACY ACTIVE` · `300` lịch sử |
| **Quy mô mã nguồn đã kiểm toán** | `67` màn hình Vue (`frontend/src/views/`) · `168` Backend API endpoints · `111` PostgreSQL indexes |
| **Khôi phục Browser Automation** | **KHÔI PHỤC THÀNH CÔNG** chụp ảnh trình duyệt thật bằng **Chrome `--headless=new` với profile cô lập** (`media/phase6-audit/isolated-browser-profile`, không đụng trình duyệt cá nhân) → xuất `7/7` ảnh PNG thực tế (`1440px`, `768px`, `375px`). *(Interactive CDP/Playwright click-flow vẫn `NOT TESTED` do `playwright` chưa cài & Chrome DevTools MCP `DevToolsActivePort ENOENT`.)* |
| **Tổng số chức năng đã kiểm toán (4 vai trò + liên vai trò)** | **`74` hạng mục:** **`64` PASS** · **`2` FAIL (tái hiện thực tế)** · **`8` PARTIAL / NOT TESTED** (xem Ma trận phủ chức năng) |
| **Phân loại lỗi trong Issue Registry (`9` issues)** | **`0` P0** · **`2` P1** (`ISSUE-002` CourseDetail hiện `0 bài giảng` + thiếu tên NCC khi chưa đăng nhập; `ISSUE-009` `recommend_courses` mất `p50 = 15.23s` do tính lại TF-IDF không cache trên 421 bài dài) · **`6` P2** (`ISSUE-001` tràn ngang mobile `375px` ở `UserHome`; `ISSUE-003` badge đè ảnh bìa ở `CourseCard`; `ISSUE-004` tiêu đề `#27` còn chữ `(Khóa học đang biên soạn)`; `ISSUE-005` `Seq Scan` trên `KhoaHoc`; `ISSUE-006` xác nhận Header 1 tầng vs 2 tầng; `ISSUE-007` `#31`/`#132` đang `HIDDEN`/`PENDING`) · **`1` P3** (`ISSUE-008` cài Playwright cho interactive E2E & video playback) |
| **Full Backend Regression (`EduSuggest_phase4_test`)** | `269 collected` · **`269 PASSED` · `0 FAILED` · `0 SKIPPED` · `0 XFAILED`** (`106.04s`) |
| **Frontend Vite Production Build** | **PASS** (`1,912 modules`, `2.06s`) |
| **Bảo mật (Static + 10 Live Probes trên `8000`)** | `0` `v-html` XSS · `0` raw f-string SQL · `0` hardcoded API URL · `0` `TODO/MOCK` · `401` cho toàn bộ endpoint cần auth · `404` cho path traversal & khóa `#31` `HIDDEN` · `0` lỗ hổng P0 |

---

## 2. Xác minh Official Dataset V2 Integrity
- Khóa `#31` (*Kiểm thử API thực chiến với Postman*) và Tài liệu `#132` (`"hi"`/`"gsdfsd"`) giữ nguyên **`HIDDEN` / `PENDING`**, truy cập công khai `/api/courses/31` trả **`404 Not Found`** (`0` rò rỉ trong catalog & Recommendation).
- `120/120` ảnh bìa WebP trả `HTTP 200` & `image/webp`; `121/121` tệp `private://` tồn tại & không rỗng; `150/150 LEGACY ACTIVE` và `300` lịch sử học tập bảo toàn 100%.

---

## 3. Hồ sơ đính kèm GĐ6.1
- [EDUSUGGEST_PHASE6_FUNCTIONAL_COVERAGE_MATRIX.md](EDUSUGGEST_PHASE6_FUNCTIONAL_COVERAGE_MATRIX.md)
- [EDUSUGGEST_PHASE6_UI_UX_AUDIT_REPORT.md](EDUSUGGEST_PHASE6_UI_UX_AUDIT_REPORT.md)
- [EDUSUGGEST_PHASE6_SECURITY_AUDIT_REPORT.md](EDUSUGGEST_PHASE6_SECURITY_AUDIT_REPORT.md)
- [EDUSUGGEST_PHASE6_PERFORMANCE_AUDIT_REPORT.md](EDUSUGGEST_PHASE6_PERFORMANCE_AUDIT_REPORT.md)
- [EDUSUGGEST_PHASE6_RECOMMENDATION_EVALUATION_PLAN.md](EDUSUGGEST_PHASE6_RECOMMENDATION_EVALUATION_PLAN.md)
- [EDUSUGGEST_PHASE6_ISSUE_REGISTRY.json](EDUSUGGEST_PHASE6_ISSUE_REGISTRY.json)
- [EDUSUGGEST_PHASE6_IMPLEMENTATION_ROADMAP.md](EDUSUGGEST_PHASE6_IMPLEMENTATION_ROADMAP.md)
