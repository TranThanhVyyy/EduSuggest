# EDUSUGGEST – GĐ4.7B: CONTROLLED PRODUCTION DEPLOYMENT PLAN (35-TABLE SCHEMA, GATEWAYS OFF)

**Ngày lập kế hoạch:** 2026-11-26  
**Mục tiêu:** Quy trình bảo trì có kiểm soát để nâng cấp database chính `EduSuggest` từ `c3d4e5f6a7b8` (24 bảng) lên `e5f6a7b8c9d0` (35 bảng) và triển khai mã nguồn Backend/Frontend tương thích với **toàn bộ cổng thanh toán TẮT** (không thu tiền thật, không kích hoạt Mock Payment trên Production).  
**Trạng thái:** **CHƯA THỰC THI — CHỜ PHÊ DUYỆT GĐ4.7B.**

---

## 1. Cấu hình Runtime Flags Bắt buộc trên Production (Default Safe State)

```env
APP_ENV=production
COMMERCE_ENROLLMENT_GATE_ENABLED=False
MOCK_PAYMENT_ENABLED=False
VNPAY_SANDBOX_ENABLED=False
FINANCIAL_INTEGRITY_WORKFLOW_ENABLED=False
PAYMENT_RECONCILIATION_WORKER_ENABLED=False
PAYMENT_AUTO_GATEWAY_QUERY_ENABLED=False
PAYMENT_AUTO_RESTORE_ENABLED=False
AUTO_ASSIGNMENT_WORKFLOW_ENABLED=False
AUTO_ASSIGNMENT_WORKER_ENABLED=False
ACCOUNTABILITY_ENABLED=False
```

> **Quy tắc UX bắt buộc:** Không bao giờ bật `COMMERCE_ENROLLMENT_GATE_ENABLED=True` trên Production khi cả `VNPAY_SANDBOX_ENABLED` (hoặc cổng thật) đều đang `False`, vì sẽ chặn đăng ký trực tiếp khóa trả phí mà người dùng không có phương thức thanh toán hợp lệ nào. Khi `COMMERCE_ENROLLMENT_GATE_ENABLED=False`, `/api/commerce/capabilities` trả `marketplaceEnabled: false`, giao diện tự động ẩn các nút mua hàng/giỏ hàng và giữ nguyên trải nghiệm học tập `edusuggest-official-v1`.

---

## 2. Quy trình bảo trì từng bước (Maintenance Window ~5–10 phút)

1. **Bước 1 — Dừng các tiến trình ghi vào `EduSuggest`:**
   - Dừng Backend Production Uvicorn đang chạy trên `EduSuggest` (không chạm staging GĐ3 `8002`/`5175` hay staging Marketplace `8003`/`5176`).
2. **Bước 2 — Backup Custom Dump & Xác minh SHA-256:**
   - Chạy `pg_dump -U postgres -d EduSuggest -Fc -f EduSuggest.pre-phase47b.dump`.
   - Tính SHA-256 và lưu biên bản; kiểm tra kích thước file `> 170 KB`.
   - Kiểm tra nguyên vẹn thư mục media `media/courses` (`120` ảnh bìa) và `private_storage/EduSuggest/materials` (`243` tài liệu).
3. **Bước 3 — Kiểm tra Single Head & Chạy Migration nối chuỗi:**
   - Xác minh `alembic heads` trả duy nhất `e5f6a7b8c9d0 (head)`.
   - Chạy `alembic upgrade head` (`c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0`).
4. **Bước 4 — Xác minh Schema & Dữ liệu sau Migration:**
   - Kiểm tra `current_database() = 'EduSuggest'`, `alembic_version = 'e5f6a7b8c9d0'`, `tables = 35`.
   - Kiểm tra bảo toàn dữ liệu `edusuggest-official-v1` (và mọi dữ liệu hợp lệ phát sinh thêm): `>= 24` danh mục, `>= 120` khóa học, `>= 411` bài học, `>= 243` tài liệu, `>= 78` tài khoản, `>= 150` `DangKyKhoaHoc` (toàn bộ cũ có `nguonCapQuyen='LEGACY'`, `trangThaiQuyenHoc='ACTIVE'`), `>= 300` `LichSuHocTap`, `0` đơn hàng giả.
   - Chạy `verify_database_schema_compatibility(engine, require_marketplace_tables=True)` → xác nhận `compatible=True`.
5. **Bước 5 — Build Frontend & Khởi động Backend mới:**
   - Giải phóng khóa Windows trên `frontend/dist/assets` (hoặc build vào thư mục sạch rồi hoán đổi) → `vite build` (`1,911 modules`, 0 lỗi).
   - Khởi động Backend mới với toàn bộ cờ ở Mục 1 đều `False` (Startup Schema Guard tự động xác minh lúc boot).
6. **Bước 6 — Post-Deploy Smoke Check:**
   - `GET /api/health` → `200 OK` (`database: connected`).
   - `GET /api/commerce/capabilities` → `marketplaceEnabled: false`, `mockPaymentEnabled: false`, `vnpaySandboxEnabled: false`.
   - Kiểm tra đăng nhập, xem khóa học, bài giảng, tải tài liệu private và TF-IDF Recommendation hoạt động bình thường.

---

## 3. Kế hoạch Rollback An toàn

- **Trường hợp 1 — Lỗi ứng dụng ngay trong cửa sổ bảo trì (0 giao dịch tài chính phát sinh):**
  - Dừng Backend mới → restore từ `EduSuggest.pre-phase47b.dump` (hoặc `alembic downgrade c3d4e5f6a7b8` nếu chưa có bất kỳ dòng nào trong `DonHang`/`ThanhToan`) → khởi động lại Backend cũ.
- **Trường hợp 2 — Đã phát sinh dữ liệu học tập mới sau triển khai (thanh toán vẫn TẮT):**
  - **Không dùng restore đè toàn DB** (sẽ mất dữ liệu học mới). Giữ nguyên schema 35 bảng (tương thích dữ liệu cũ) hoặc rollback riêng Frontend/cờ runtime.
- **Trường hợp 3 — Đã phát sinh giao dịch tài chính thật (tương lai sau khi mở cổng):**
  - **CẤM dùng `alembic downgrade`** (vì sẽ xóa bảng tài chính). Chỉ khắc phục theo hướng tiến (forward-fix) kết hợp tắt cờ nhận đơn mới và chạy Durable Reconciliation Worker.
