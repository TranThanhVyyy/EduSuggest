# EDUSUGGEST – GĐ6.2 → GĐ6.3: CONTROLLED PRODUCTION DEPLOYMENT PLAN

> [!IMPORTANT]
> **CHƯA TRIỂN KHAI LÊN PRODUCTION.** Tài liệu này là kế hoạch triển khai có kiểm soát cho GĐ6.3 sau khi người dùng phê duyệt kết quả nghiệm thu GĐ6.2 trên staging (`5177`/`8004`).

## 1. Phạm vi thay đổi đã nghiệm thu trên Staging GĐ6.2

| Nhóm | Tệp / Đối tượng | Mô tả thay đổi | Yêu cầu Migration DB? |
|---|---|---|---|
| Backend Perf (`ISSUE-009`) | `backend/service/content_recommendation.py`, `backend/service/recommendation_service.py` | Precompute TF-IDF `O(N)` + thread-safe, DB-isolated, fingerprint-validated corpus cache | **KHÔNG** (35 bảng, `e5f6a7b8c9d0`) |
| Backend API (`ISSUE-002`) | `backend/schemas/workflow.py`, `backend/api/workflows.py` | Bổ sung `tenNhaCungCap`, `soLuongBaiHoc`, `deCuongCongKhai` cho public `GET /api/courses/{id}` | **KHÔNG** |
| Frontend UI/UX (`ISSUE-001/002/003/006`) | `userApiService.js`, `CourseDetail.vue`, `CourseCard.vue`, `UserHeader.vue`, `UserHome.vue` | Hiển thị syllabus khóa + nhà cung cấp, ảnh bìa 16:9 sạch, Header 2 tầng ở trang con, 0px overflow `320–1920px` | **KHÔNG** |
| Dữ liệu (`ISSUE-004`) | `KhoaHoc` `#27` trên `EduSuggest` | Ẩn khóa học nháp `#27` (`trangThaiHienThi = 'HIDDEN'`) | **1 dòng UPDATE có backup** |

> [!NOTE]
> **Lưu ý về Vite Dev Server `5173`:** Frontend Production hiện chạy qua Vite dev server (`task-3569`) dùng chung thư mục mã nguồn `frontend/src/`. Khi triển khai chính thức ở GĐ6.3 cần restart Production Backend `8000` (hiện đang chạy không `--reload`, nên vẫn giữ mã Backend cũ cho tới khi được phê duyệt restart) và cập nhật khóa `#27` trên `EduSuggest` sau khi backup.

## 2. Quy trình triển khai có kiểm soát (GĐ6.3 – Chỉ thực hiện khi được phê duyệt)

1. **Pre-flight & Backup Production `EduSuggest`:**
   - Xác minh `current_database() == 'EduSuggest'`, 35 bảng, revision `e5f6a7b8c9d0`, `150 LEGACY ACTIVE`, `300` lịch sử học tập.
   - Chạy `pg_dump -Fc` tạo backup trước triển khai + tính `SHA-256`.
2. **Áp dụng dữ liệu `ISSUE-004` (1 dòng):**
   - `UPDATE "KhoaHoc" SET "trangThaiHienThi" = 'HIDDEN' WHERE "maKhoaHoc" = 27;`
3. **Restart Production Backend `8000`:**
   - Giữ nguyên toàn bộ Feature Flags Production (`COMMERCE_ENROLLMENT_GATE_ENABLED=True`, toàn bộ cổng thanh toán & worker `False`).
4. **Post-deploy Smoke & Regression Check trên `5173`/`8000`:**
   - Kiểm tra `GET /api/courses/6` trả đúng `tenNhaCungCap`, `soLuongBaiHoc = 5`, `baiHocs = []`, `deCuongCongKhai` 5 bài.
   - Kiểm tra `GET /api/courses/27` trả `404`.
   - Kiểm tra `GET /api/recommendations/courses` warm latency `< 150 ms`.
   - Xác minh `150/150 LEGACY ACTIVE` và `300` lịch sử học tập nguyên vẹn 100%.

## 3. Kế hoạch Rollback (Nếu phát sinh bất thường)

- **Dữ liệu `#27`:** `UPDATE "KhoaHoc" SET "trangThaiHienThi" = 'VISIBLE' WHERE "maKhoaHoc" = 27;` (hoặc restore từ file `pg_dump` trước triển khai).
- **Mã nguồn:** Hoàn nguyên các tệp Backend/Frontend và restart uvicorn `8000`. Không có bất kỳ thay đổi schema DB nào nên rollback tức thời trong `< 30 giây`.
