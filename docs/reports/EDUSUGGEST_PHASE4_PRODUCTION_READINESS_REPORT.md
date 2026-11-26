# EDUSUGGEST – GĐ4.7A.3: PRODUCTION READINESS & DEPLOYMENT REHEARSAL REPORT

**Ngày cập nhật:** 2026-11-26  
**Đối tượng đánh giá:** Nâng cấp EduSuggest (`edusuggest-official-v1`) từ revision `c3d4e5f6a7b8` (24 bảng) lên revision **`e5f6a7b8c9d0` (35 bảng — đã bao gồm 5 bảng Financial Integrity & Durable Payment Recovery)** cùng giao diện & API Marketplace GĐ4.  
**Trạng thái Production `EduSuggest` hiện tại:** **ĐÃ TRIỂN KHAI CÓ KIỂM SOÁT GĐ4.7B (`e5f6a7b8c9d0`, 35 bảng, `5173`/`8000`) VỚI TOÀN BỘ CỔNG THANH TOÁN & WORKER TÀI CHÍNH TẮT. CHƯA KÍCH HOẠT GIAO DỊCH TIỀN THẬT.**

---

## 1. Bảng quyết định Production Readiness (Tách biệt A / B / C / D)

| Phạm vi đánh giá | Quyết định | Điều kiện / Blocker & Trải nghiệm người dùng |
|---|---|---|
| **A. Marketplace Staging dùng Mock Payment (`EduSuggest_phase4_test`, `5176`/`8003`)** | **CONDITIONAL GO** | **266/266 Backend PASS**, 2 real OS worker processes PASS, Vite Build PASS (`1,911 modules`), staging `5176`/`8003` đang chạy trên 35 bảng (`e5f6a7b8c9d0`). Chờ xác nhận trực quan trên Chrome (Chrome DevTools MCP `BLOCKED`). |
| **B. Migration & Triển khai Production 35 bảng (`e5f6a7b8c9d0`) với các gateway thanh toán TẮT** | **CONDITIONAL GO (Chờ phê duyệt GĐ4.7B)** | Diễn tập nối chuỗi `c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0` trên `EduSuggest_phase47a3_rehearsal` **PASS 100%** (SHA-256 `A8C47895...`, `35` bảng, `schema_guard=True`, `150` LEGACY ACTIVE, `300` lịch sử, `0` đơn giả). **Bắt buộc chạy migration TRƯỚC khi khởi động Backend mới** (Startup Schema Guard chặn fail-closed nếu thiếu) và giữ `COMMERCE_ENROLLMENT_GATE_ENABLED=False` cùng toàn bộ cờ thanh toán `False` để người học không bị chặn mua khi chưa có cổng thanh toán. |
| **C. VNPay Sandbox thực tế qua Internet** | **BLOCKED / NO-GO** | Thiếu `VNPAY_TMN_CODE`/`VNPAY_HASH_SECRET` và Public HTTPS IPN URL; chưa nghiệm thu giao dịch trực tuyến với máy chủ VNPay Sandbox. |
| **D. Xử lý giao dịch tiền thật (Real-Money Production)** | **NO-GO** | Financial Schema & Durable Worker đã hoàn tất trên môi trường kiểm thử, nhưng còn 3 BLOCKER bắt buộc trước khi thu tiền thật: (1) Nghiệm thu VNPay Sandbox & Live Certification qua Internet, (2) Browser E2E PASS toàn bộ role/viewport, (3) Quy trình giám sát/alerting vận hành cho `run_payment_reconciliation_worker.py`. |

---

## 2. Kết quả Diễn tập Backup, Restore & Migration Rehearsal (Thực tế trên bản sao độc lập)

Diễn tập được thực thi trực tiếp trên PostgreSQL Docker container (`fd88f7ce9786`) với bản sao độc lập **`EduSuggest_phase47a_rehearsal`** (Production `EduSuggest` chỉ dùng `pg_dump` READ ONLY):

| Bước diễn tập | Kết quả thực tế | Bằng chứng xác minh |
|---|---|---|
| **1. Backup Custom Dump (`pg_dump -Fc`)** | **PASS** | File: `backend/database/backups/phase47a-rehearsal/20261126/EduSuggest.custom.dump`<br>Kích thước: **`174,043 bytes`**<br>SHA-256: **`1232C6C00E8FDB658F99C4F506D2C13E21E08C7D46ABEBE6E7051E74C40AA244`** |
| **2. Restore vào DB độc lập `EduSuggest_phase47a_rehearsal`** | **PASS** | Restore sạch từ custom dump, không ảnh hưởng `EduSuggest`, `EduSuggest_phase4_test`, `EduSuggest_phase3_test`, `EduSuggest_dataset_staging`. |
| **3. Kiểm tra Single Alembic Head** | **PASS** | `alembic heads` trả về duy nhất **`d4e5f6a7b8c9 (head)`**. |
| **4. Chạy `alembic upgrade head`** | **PASS** | `Running upgrade c3d4e5f6a7b8 -> d4e5f6a7b8c9` hoàn tất trong transactional DDL, 0 lỗi. |
| **5. Kiểm kê bảo toàn dữ liệu `edusuggest-official-v1`** | **PASS (100%)** | `tables=30` (29 bảng nghiệp vụ + `alembic_version`), `categories=24`, `courses=120`, `lessons=411`, `materials=243`, `users=78`, **`enrollments=150`** (`legacy_active=150`), **`history=300`**, **`orders=0`** (không tạo đơn giả cho LEGACY). |
| **6. Frontend Production Build** | **PASS** | `vite build --outDir dist-phase46-check` → `1,911 modules`, `2.03s`, 0 lỗi biên dịch. (Lưu ý môi trường Windows: thư mục `frontend/dist/assets` đang có tiến trình bên ngoài giữ handle EPERM; khi build chính thức cần đóng tiến trình đang giữ file hoặc build vào thư mục sạch rồi đổi tên). |

---

## 3. Khả năng tương thích 24 bảng vs 30 bảng (Critical Deployment-Order Finding)

- **Khi DB còn ở 24 bảng (`c3d4e5f6a7b8`):**
  - `GET /api/commerce/capabilities` trả `200 OK` (0 DB query) và Frontend tự ẩn toàn bộ nút Wishlist/Cart/Checkout khi `marketplaceEnabled=false`.
  - Các API Marketplace (`/api/cart`, `/api/wishlist`, `/api/admin/commerce/*`) đã được gia cố fail-closed sang `HTTP 503 Service Unavailable` (HARDEN-04) thay vì 500.
  - **NHƯNG** các API cốt lõi có truy vấn `DangKyKhoaHoc` (Recommendation, Private File Access, Learning, Enrollment) **SẼ LỖI `UndefinedColumn: column DangKyKhoaHoc.maDonHang does not exist`** (đã chứng minh thực nghiệm bởi 7/7 test trên `EduSuggest_phase3_test` trong Full Regression).
- **Kết luận bắt buộc về thứ tự triển khai (Deployment Order):**
  1. Dừng Backend cũ (cửa sổ bảo trì ngắn ~2–5 phút).
  2. Chạy `pg_dump -Fc` + kiểm tra SHA-256 trên `EduSuggest`.
  3. Chạy `alembic upgrade head` (`c3d4e5f6a7b8 → d4e5f6a7b8c9`) trên `EduSuggest`.
  4. Khởi động Backend mới với **Runtime Flags an toàn**:
     - `APP_ENV=production`
     - `COMMERCE_ENROLLMENT_GATE_ENABLED=False` (hoặc `True` chỉ khi phê duyệt mở cổng thanh toán sau này)
     - `MOCK_PAYMENT_ENABLED=False`
     - `VNPAY_SANDBOX_ENABLED=False`
     - `AUTO_ASSIGNMENT_WORKFLOW_ENABLED=False`
     - `AUTO_ASSIGNMENT_WORKER_ENABLED=False`
     - `ACCOUNTABILITY_ENABLED=False`
  5. Kiểm tra `/api/health`, `/api/commerce/capabilities`, Recommendation, Private Materials và đếm đủ `150` đăng ký + `300` lịch sử học tập.

---

## 4. Kế hoạch Rollback & Bảo toàn dữ liệu phát sinh

1. **Rollback mức ứng dụng (không mất dữ liệu):** Nếu gặp lỗi giao diện/API sau khi triển khai với thanh toán TẮT, có thể giữ nguyên schema `d4e5f6a7b8c9` (tương thích ngược cho dữ liệu hiện có vì 5 cột mới có default `LEGACY`/`ACTIVE`) và chỉ rollback Frontend/feature flags.
2. **Rollback mức Schema (`alembic downgrade c3d4e5f6a7b8`):** Chỉ thực hiện khi **chưa phát sinh bất kỳ `DonHang`/`ThanhToan` thật nào** (`SELECT count(*) FROM "DonHang" == 0`), vì downgrade sẽ drop 6 bảng Marketplace và 5 cột mới trên `DangKyKhoaHoc`.
3. **Rollback khẩn cấp từ Backup Dump:** Nếu phát sinh sự cố nghiêm trọng trong cửa sổ bảo trì, restore từ file `EduSuggest.custom.dump` (đã xác minh SHA-256) và giữ nguyên 100% thư mục `media/courses` và `private_storage/EduSuggest/materials` (không nằm trong DB).
4. **Dữ liệu phát sinh trong thời gian vận hành:** Nếu triển khai với thanh toán TẮT, mọi đăng ký học mới (`DangKyKhoaHoc`) và lịch sử học tập (`LichSuHocTap`) phát sinh sau migration đều nằm trong các bảng gốc và vẫn được bảo toàn kể cả khi chạy `alembic downgrade c3d4e5f6a7b8`.

---

## 5. Danh sách Blocker còn tồn tại trước khi mở GĐ4.7B / Thu tiền thật

1. **Browser E2E thủ công trên Chrome (`http://127.0.0.1:5176/`):** Cần người dùng kiểm tra trực tiếp theo [docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md](docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md).
2. **VNPay Sandbox Live Acceptance (cho phạm vi C):** Cần `VNPAY_TMN_CODE`, `VNPAY_HASH_SECRET` và Public HTTPS IPN URL.
3. **Financial Schema Migration + Durable Reconciliation Worker (cho phạm vi D — tiền thật):** Cần phê duyệt migration tách bảng `HoanTienNgoaiLe`, `LanThuHoanTien`, `BaoCaoSuCoThanhToan`, `CAPTURED_UNAPPLIED` và triển khai worker gọi `QueryDR` tự động.
4. **Windows `frontend/dist/assets` EPERM lock:** Cần đóng tiến trình bên ngoài đang giữ file trong `frontend/dist/assets` trước khi chạy lệnh `npm run build` mặc định vào `dist/`.
