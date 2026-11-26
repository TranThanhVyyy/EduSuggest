# EDUSUGGEST – GĐ6.3C: CONTROLLED PRODUCTION DEPLOYMENT REPORT

- **Ngày triển khai:** 2026-11-27
- **Hệ thống chính thức đã cập nhật:**
  - **Frontend:** `http://127.0.0.1:5173/` (`HTTP 200 OK`)
  - **Backend:** `http://127.0.0.1:8000/api` (`HTTP 200 OK`, `APP_ENV=production`, `DEBUG=False`)
  - **Database:** `EduSuggest` (PostgreSQL 16, **35 bảng**, revision **`e5f6a7b8c9d0`**, không chạy migration)
- **Rollback Manifest:** [`docs/reports/production-phase63-rollback-manifest.json`](./production-phase63-rollback-manifest.json)
- **Kết quả kiểm chứng sau triển khai:** [`media/phase63-staging/production_post_deploy_verification.json`](../../media/phase63-staging/production_post_deploy_verification.json)

## 1. Điều kiện cổng trước triển khai (Pre-Deployment Gates)

| Cổng kiểm duyệt | Kết quả |
|---|---|
| Full Backend Regression (`pytest`, `EDUSUGGEST_TEST_DB_NAME=EduSuggest_phase4_test`) | **`274/274 PASS` (100%, 0 FAIL, 0 SKIPPED)** |
| `test_phase383_abrupt_worker_recovery.py` (3× liên tiếp + trong full suite) | **PASS 100%** |
| Recommendation Cache Correctness (16 kịch bản incl. raw SQL & rollback) | **PASS** |
| Mathematical Equivalence (`1e-12` trên 8 Official Personas) | **PASS (`max_diff = 0.0`)** |
| Frontend Vite Production Build | **PASS (`1,912 modules`, `1.83s`)** |
| Course `#27` Production Safety Audit | **PASS (`0` enrollments, `0` history, `0` orders/payments/wishlist/cart)** |

## 2. Sao lưu & Restore Verification (Non-Git)

Thư mục backup: `D:\đồ án\EduSuggest\backups\phase63-pre-deploy-20261127\` (`SHA256SUMS.txt` đã lưu):
- `EduSuggest.pre-phase63.dump` (`254,958 bytes`, SHA-256 `ab27cd62...`) — **Restore Verify PASS** trên DB tạm `edusuggest_phase63_backup_verify` (35 bảng, `e5f6a7b8c9d0`, 150 LEGACY ACTIVE, 300 history; đã xóa DB tạm sau kiểm tra).
- `private-storage-pre-phase63.zip` (`282,432 bytes`, 560 tệp).
- `deployed-source-phase63.zip` (`52,072 bytes`, 9 tệp nguồn Backend/Frontend đã triển khai).

## 3. Thay đổi áp dụng lên Production

1. **Dữ liệu (`ISSUE-004`):** `UPDATE "KhoaHoc" SET "trangThaiHienThi" = 'HIDDEN' WHERE "maKhoaHoc" = 27;` (0 học viên bị ảnh hưởng).
2. **Backend `8000`:** Khởi động lại uvicorn `8000` với bản tối ưu `content_recommendation.py`, `recommendation_service.py` (content-hash fingerprint), và public CourseDetail `schemas/workflow.py` + `api/workflows.py`. **Giữ nguyên 100% Feature Flags Production** (`COMMERCE_ENROLLMENT_GATE_ENABLED=True`, `MOCK_PAYMENT_ENABLED=False`, `VNPAY_SANDBOX_ENABLED=False`, toàn bộ background worker `False`).
3. **Frontend `5173`:** Đã cập nhật `userApiService.js`, `CourseDetail.vue`, `CourseCard.vue`, `UserHeader.vue`, `UserHome.vue`.

## 4. Kết quả kiểm chứng sau triển khai (Production READ-ONLY Verification)

| Hạng mục kiểm chứng trên `5173`/`8000` | Kết quả thực tế | Trạng thái |
|---|---|---|
| DB Integrity (`EduSuggest`) | `35` bảng, `e5f6a7b8c9d0`, `120` khóa, `421` bài, `243` tài liệu, **`150 LEGACY ACTIVE`**, **`300` lịch sử** | **PASS** |
| **Recommendation HTTP Warm p50 / p95 (`8000`)** | **`101.71 ms` / `144.50 ms`** (nhanh hơn **149.8×** so với `15,232 ms`; Cold **`346.13 ms`**) | **PASS** |
| Public `GET /api/courses/6` | `"Học viện Phần mềm FPT"`, `5 bài giảng`, `baiHocs = []`, `5` bài đề cương khóa | **PASS** |
| Ẩn nội dung nháp (`#27`, `#31`, `#132`) | Đều trả **`HTTP 404`** công khai | **PASS** |
| `120/120` ảnh bìa WebP | **`120/120`** `HTTP 200` + `image/webp` | **PASS** |
| Capabilities & Payment Safety | `marketplaceEnabled=true`, `enrollmentGateEnabled=true`, `mockPayment=false`, `vnpay=false` | **PASS** |
| RBAC Security Probes | Anon `/api/admin/analytics/summary` → `401`; Learner → `403` | **PASS** |
| Playwright READ-ONLY trên `5173` (`375px`, `1440px`) | `0px` overflow, `course6_ui_verified = true`, **`0` page errors** | **PASS** |
