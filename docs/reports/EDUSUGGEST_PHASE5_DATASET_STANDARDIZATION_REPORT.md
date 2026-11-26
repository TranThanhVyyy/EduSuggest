# EDUSUGGEST — GĐ5.3: BÁO CÁO CHUẨN HÓA DATASET TRÊN STAGING

**Ngày thực hiện:** 2026-11-26  
**Môi trường thực thi:** Staging độc lập `edusuggest_phase53_staging` (nhân bản sạch từ Production `EduSuggest`, snapshot trước khi sửa: `media/phase53-staging/EduSuggest.pre-phase53-staging.dump`, `237,915 bytes`).  
**Trạng thái:** **HOÀN TẤT CHUẨN HÓA TRÊN STAGING, DIFF & ROLLBACK MANIFEST, RECOMMENDATION REGRESSION (8/8 PERSONAS), VITE BUILD & 266/266 BACKEND PASS. PRODUCTION `EduSuggest` GIỮ NGUYÊN 100% READ ONLY — DỪNG CHỜ PHÊ DUYỆT TRIỂN KHAI.**

---

## 1. Tóm tắt 16 thay đổi đã áp dụng trên `edusuggest_phase53_staging`

Tất cả thay đổi được ghi chi tiết từng trường trong [dataset-refinement-diff.json](dataset-refinement-diff.json) và có kịch bản hoàn tác tự động tại [dataset-refinement-rollback-manifest.json](dataset-refinement-rollback-manifest.json) (script `backend/scripts/phase53_standardize_staging.py` hỗ trợ `--dry-run`, `--apply`, `--rollback` và khóa cứng không chạy trên `EduSuggest`).

### 1.1. Khôi phục khóa học rác `#31` (giữ nguyên Course ID `#31`, `HIDDEN` + `PENDING`)
- **Xác minh 0 tham chiếu nghiệp vụ trước phục hồi:** `BaiHoc=0`, `TaiLieu=0`, `DangKyKhoaHoc=0`, `LichSuHocTap=0`, `DanhGiaChuyenGia=0`, `PhanCongKiemDuyet=0`, `HangDoiPhanCong=0`, `YeuThich=0`, `ChiTietGioHang=0`, `ChiTietDonHang=0`.
- **Trước → Sau trên Staging:**
  - `tieuDe`: `"fhahsahdáhdahshdáhdahdá"` → **`"Kiểm thử API thực chiến với Postman"`**
  - `maDanhMuc`: giữ nguyên `#11` (`Kiểm thử phần mềm & QA`), `maNhaCungCap`: giữ nguyên `#5`.
  - `trinhDo`: `NULL` → `INTERMEDIATE`; `gia`: `NULL` → `399,000 ₫`; `thoiLuong`: `NULL` → `320 phút` (khớp tổng 10 bài học).
  - `trangThaiDuyet`: `NULL` → **`PENDING`**; `trangThaiHienThi`: giữ nguyên **`HIDDEN`** (**không** tự động `APPROVED`/`VISIBLE`).
  - **Nội dung chương trình:** Bổ sung **10 bài học thực chiến** (`320 phút`) gồm REST API fundamentals, HTTP Methods, Status Codes, JSON Schema, Postman Collections, Auth (API Key/JWT/OAuth 2.0), Variables & Environments, Test Scripts (`pm.test`/Chai), Collection Runner (CSV/JSON Data-Driven), và Newman CLI + Dự án cuối khóa API Testing.
  - **Ảnh bìa mới:** `media/phase53-staging/course-031-api-testing.webp` (`1280×720` WebP, ảnh chụp thực tế nguồn Openverse `stocksnap` `CC0 1.0`, đã kiểm tra trực quan).

### 1.2. Chuẩn hóa thời lượng khóa học (`#29`)
- Kiểm toán toàn bộ 120 khóa cho thấy **chỉ duy nhất khóa `#29`** có `KhoaHoc.thoiLuong < SUM(BaiHoc.thoiLuong)` (`180 phút < 300 phút`).
- Đã sửa trên Staging: `#29` `thoiLuong`: `180` → **`300 phút`**.
- Với 92 khóa `edusuggest-official-v1` (có `thoiLuong = 360–810 phút` > tổng 3 bài giảng `150–195 phút`), giữ nguyên ý nghĩa **"Thời lượng học ước tính"** (bao gồm tự học, đọc tài liệu, bài tập) và hiển thị tách bạch với **"Tổng bài giảng"** trên `CourseDetail.vue`.

### 1.3. Sửa 2 URL tài liệu chết (xác minh nội dung trang đích, không chỉ HTTP 200)
- **`TaiLieu #110`** (khóa `#24`): `https://www.atlassian.com/software/jira/guides/bug-tracking/overview` (`404`) → **`https://www.atlassian.com/software/jira/guides/issues/overview`** (`200 OK`, trang đích: *"What are Jira Work Items? | Atlassian"*).
- **`TaiLieu #98`** (khóa `#22`): `http://www.pentest-standard.org/` (`URLError`) → **`https://owasp.org/www-project-web-security-testing-guide/`** (`200 OK`, trang đích: *"Web Security Testing Guide | OWASP Foundation"*), đồng thời cập nhật `tieuDe` và `moTa` trên Staging khớp chính xác với OWASP WSTG.
- **5 URL `dev.mysql.com` (`#43–#47`):** Giữ nguyên vì chỉ chặn script tự động (`HTTP 403`), truy cập bình thường bằng trình duyệt; không vượt cơ chế chống bot.

### 1.4. Xử lý hồ sơ Nhà cung cấp `#5` & Đối chiếu Chuyên gia `20 vs 21`
- **Nhà cung cấp `#5` (`tranphuctk`, sở hữu 12 khóa):** Cập nhật trên Staging `tieuSu` và `chuyenMon` từ `"h"` sang mô tả mô phỏng rõ ràng khớp 12 khóa đang quản lý (không giả mạo tổ chức/chứng chỉ thật).
- **Giải trình đối chiếu `20 vs 21` Chuyên gia (100% hợp lệ, không phải lỗi):**
  - Tài khoản có vai trò `EXPERT`: **`20`** tài khoản (`13` `official_expert_01..13` trạng thái `VERIFIED` + `7` `EXPERT` trạng thái `DRAFT`).
  - Bảng `ChuyenGia`: **`21`** bản ghi — chênh lệch `+1` là bản ghi `#4` (`maNguoiDung=27`, `linhphuong123`, vai trò **`USER`**, trạng thái **`DRAFT`** — người học đã tạo nháp hồ sơ chuyên gia). Không xóa và không tự động chuyển `VERIFIED`.

---

## 2. Cải thiện Frontend hiển thị Cấp độ & Thời lượng
- Bổ sung helper dùng chung `frontend/src/utils/courseDisplay.js` (`formatCourseLevel`, `formatDurationMinutes`) và tích hợp vào `CourseCard.vue`, `CourseDetail.vue`:
  - Chuẩn hóa hiển thị tiếng Việt thống nhất (`Cơ bản`, `Trung cấp`, `Nâng cao`, `Mọi cấp độ`) mà **không sửa enum DB** và **không tác động TF-IDF**.
  - Hiển thị rõ **`Thời lượng học ước tính`** kèm dòng phụ **`Tổng bài giảng: X phút`** trên `CourseDetail.vue`.

---

## 3. So sánh Recommendation BEFORE vs AFTER (8 Official Personas)

Chạy trực tiếp `recommend_courses` và `recommend_standalone_materials` trên `edusuggest_phase53_staging` trước và sau khi áp dụng 16 thay đổi (không sửa TF-IDF + Cosine Similarity):

| Persona | Course Strategy (Trước → Sau) | Course Top-5 khớp | Material Strategy (Trước → Sau) | Material Top-5 khớp |
|---|---|---|---|---|
| `official_persona_ai` | `content_based → content_based` | **100% ổn định** | `content_based → content_based` | **100% ổn định** |
| `official_persona_backend` | `content_based → content_based` | **100% ổn định** | `content_based → content_based` | **100% ổn định** |
| `official_persona_data` | `content_based → content_based` | **100% ổn định** | `content_based → content_based` | **100% ổn định** |
| `official_persona_devops` | `content_based → content_based` | **100% ổn định** | `content_based → content_based` | **100% ổn định** |
| `official_persona_frontend` | `content_based → content_based` | **100% ổn định** | `content_based → content_based` | **100% ổn định** |
| `official_persona_fullstack` | `content_based → content_based` | **100% ổn định** | `content_based → content_based` | **100% ổn định** |
| `official_persona_mobile` | `content_based → content_based` | **100% ổn định** | `content_based → content_based` | **100% ổn định** |
| `official_persona_new` (Cold-start) | `latest → latest` | **100% ổn định** | `latest → latest` | **100% ổn định** |

---

## 4. Kiểm thử, An toàn Production & Kế hoạch triển khai

- **Backend Regression (`EduSuggest_phase4_test`):** **`266 passed, 0 failed, 0 skipped` (`91.20s`)** — gồm Recommendation, RBAC, Marketplace, Payment Safety và Private File Authorization.
- **Frontend Vite Production Build:** **PASS** (`1,912 modules`, `2.17s`).
- **Production `EduSuggest` READ-ONLY Verification:** Giữ nguyên `100%` (`#31` vẫn là bản ghi gốc `HIDDEN`, `#29` vẫn `180`, `#110`/`#98` giữ nguyên, `#5` giữ nguyên `"h"`, `120/120` ảnh WebP GĐ5.2 nguyên vẹn, `150/150 LEGACY ACTIVE`, `300` lịch sử học tập).
- **Trình duyệt tự động:** Chrome DevTools MCP vẫn `BLOCKED` (`DevToolsActivePort ENOENT`).
- **Kế hoạch triển khai lên Production (khi được phê duyệt GĐ5.4):** Backup Production DB → sao chép `course-031-api-testing.webp` vào `media/courses/v5-realistic/` → áp dụng 16 thay đổi nguyên tử từ `dataset-refinement-diff.json` (giữ khóa `#31` ở `HIDDEN`/`PENDING` để đi qua luồng kiểm duyệt chuyên gia hợp lệ) → kiểm chứng `266/266` & rollback sẵn sàng qua `dataset-refinement-rollback-manifest.json`.
