# EDUSUGGEST — GĐ5.4: BÁO CÁO TRIỂN KHAI CHÍNH THỨC CHUẨN HÓA DỮ LIỆU GĐ5.3

**Ngày thực hiện:** 2026-11-26  
**Mục tiêu:** Áp dụng chính thức 16 thay đổi chuẩn hóa GĐ5.3 đã được phê duyệt lên database chính `EduSuggest` sau khi sao lưu và kiểm chứng khôi phục. **Không áp dụng nội dung GĐ5.4 lên Production.**

---

## 1. Sao lưu Production & Kiểm chứng khôi phục trước triển khai

Thư mục sao lưu: `backend/database/backups/phase54-std-deploy/20261126/`
- **PostgreSQL custom dump:** `EduSuggest.pre-phase54.dump` (`237,915 bytes`, SHA-256 `9AF76733357B99A226E90754536566B532D6A3F1BCBB772E3E4DAEC4D6563937`).
- **Backup ảnh WebP GĐ5.2:** `media_v5_pre_phase54.zip` (`8,313,364 bytes`, SHA-256 `102AB8F84F2C2ECCB8B609E0E1C48FB6BFAF13DE0BA9139158163AA857A4662A`).
- **Backup Private Storage:** `private_materials_pre_phase54.zip` (`276,727 bytes`, SHA-256 `597597AA1C62D35C7DC6B23F69F2A92EB1923A8A4A4BAD466F6986491F814587`).
- **Restore Verification:** Khôi phục kiểm chứng thành công trên `edusuggest_phase54_backup_verify`.
- **Rollback Manifest Production:** `prod-phase53-rollback.json` (hỗ trợ `python backend/scripts/apply_phase53_to_production.py --rollback`).

---

## 2. Kết quả áp dụng nguyên tử 16 thay đổi GĐ5.3 lên `EduSuggest`

Script thực thi: `backend/scripts/apply_phase53_to_production.py` (`--dry-run` → `--confirm-apply`):
1. **Khôi phục khóa `#31` (xác nhận `0` tham chiếu trên 10 bảng trước khi ghi):**
   - `tieuDe`: `"fhahsahdáhdahshdáhdahdá"` → **`"Kiểm thử API thực chiến với Postman"`** (`399,000 ₫`, `INTERMEDIATE`, `320 phút`).
   - Bổ sung **10 bài học thực chiến** Postman & Newman (`411 → 421` bài học).
   - Ảnh bìa versioned mới: `/media/courses/v5-realistic/course-031-api-testing.webp` (`HTTP 200`, `image/webp`).
   - Giữ nguyên **`trangThaiDuyet = 'PENDING'`** và **`trangThaiHienThi = 'HIDDEN'`** (không tự động công khai).
2. **Thời lượng khóa `#29`:** `180 → 300 phút` (khớp tổng 5 bài học).
3. **Tài liệu `#110` & `#98`:** Cập nhật `#110` → `https://www.atlassian.com/software/jira/guides/issues/overview` (`200 OK`); cập nhật `#98` → `https://owasp.org/www-project-web-security-testing-guide/` (`200 OK`) kèm tiêu đề & mô tả khớp OWASP WSTG.
4. **Nhà cung cấp `#5` (`tranphuctk`):** Thay thế `"h"`/`"h"` bằng hồ sơ mô phỏng rõ ràng khớp 12 khóa đang quản lý (không đổi trạng thái hồ sơ chuyên gia).

---

## 3. Kiểm chứng Production sau triển khai

| Hạng mục | Kết quả thực tế trên Production `EduSuggest` |
| :--- | :--- |
| Database / Revision / Bảng | `EduSuggest` · `e5f6a7b8c9d0` · `35` bảng (không migration mới) |
| Tổng dữ liệu bảo toàn | `120` khóa học · **`421` bài học** · `243` tài liệu · **`150/150 LEGACY ACTIVE`** · **`300` lịch sử học tập** |
| Ảnh bìa WebP trực tiếp (`8000`) | **`120/120` `HTTP 200`** · **`120/120` `image/webp`** |
| Cô lập GĐ5.4 khỏi Production | **`0`** bài học trên Production bị ghi nội dung GĐ5.4 |
| Dịch vụ đang hoạt động | Production `5173`/`8000` `200 OK` · Marketplace Staging `5176`/`8003` `200 OK` |
| Full Backend Regression (`EduSuggest_phase4_test`) | **`266/266 PASS`** (`129.84s`, `0 FAIL`, `0 SKIPPED`) |
| Frontend Vite Production Build | **PASS** (`1,912 modules`, `3.93s`) |
