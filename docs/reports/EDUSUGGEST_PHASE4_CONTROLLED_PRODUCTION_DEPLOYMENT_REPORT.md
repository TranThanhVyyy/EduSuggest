# EDUSUGGEST – GĐ4.7B: CONTROLLED PRODUCTION DEPLOYMENT REPORT

**Ngày triển khai:** 2026-11-26  
**Phạm vi:** Triển khai có kiểm soát chuỗi migration `c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0` (24 → 35 bảng) và mã nguồn Backend/Frontend GĐ4 lên hệ thống chính thức `EduSuggest` (`http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api`) với **toàn bộ cổng thanh toán, Commerce Gate, Worker tài chính và Automatic Assignment TẮT (`False`)**.  
**Trạng thái:** **TRIỂN KHAI THÀNH CÔNG TRÊN PRODUCTION (`5173`/`8000`) — THANH TOÁN & TIỀN THẬT VẪN TẮT.**

---

## 1. Pre-Deployment Audit & Advisory Lock Verification

- **Single Alembic Head:** `e5f6a7b8c9d0 (head)` — xác minh hợp lệ.
- **Advisory Lock `USER–Course` Audit:** Xác minh toàn bộ `backend/service/*.py`, `repository/*.py`, `api/*.py`:
  - `commerce_service._lock_user_course` (dùng bởi `order_payment_service`, `commerce_admin_service`, `payment_reconciliation_worker`) dùng `pg_advisory_xact_lock(CAST(:u AS integer), CAST(:c AS integer))`.
  - `workflow_service.enroll_user_in_course` (dòng 1592) dùng `pg_advisory_xact_lock(:user_id, :course_id)`.
  - **Kết luận:** 100% thống nhất cùng không gian khóa `(int4, int4)` `(user_id, course_id)`, không còn công thức tràn `int4` cũ.

---

## 2. Backup Production & Restore Verification (SHA-256)

Thư mục backup: `D:\đồ án\EduSuggest\backend\database\backups\phase47b-prod-deploy\20261126\`

| Hạng mục sao lưu | Kích thước | SHA-256 | Kiểm chứng |
|---|---:|---|---|
| `EduSuggest.pre-phase47b.dump` (PostgreSQL `-Fc`) | `174,109 bytes` | `C6C0B731B1D4A1CACACD1DD288AE1A050205476F4B0A5A89C34AAE3E663DF533` | `pg_restore --list`: `251` dòng TOC; restore vào `EduSuggest_phase47b_backup_verify` **PASS** (`c3d4e5f6a7b8`, `24` bảng, `120` khóa học, `150` đăng ký, `300` lịch sử) |
| `media_courses.zip` (`120` ảnh bìa) | `595,071 bytes` | `4742BA22B87E5832A39F10EF73EF13ABD58D4FD4FC2DB1E669808CB2ACC82091` | Đóng gói thành công 100% |
| `private_materials.zip` (`242` file private) | `116,317 bytes` | `67531C96DCA61008BE265B77DB2CA4040DE1240C004D0A51D9636BD6F543AA57` | Đóng gói thành công 100% *(1 bản ghi legacy #132 HIDDEN không có file vật lý)* |

---

## 3. Maintenance Window & Production Migration Logs

- **Dừng đúng tiến trình Production cũ:** PID `22268` (port `8000`) và PID `24856` (port `5173`). Các tiến trình staging (`8002`/`5175`, `8003`/`5176`) không bị dừng hay ảnh hưởng.
- **Database Guard trước migration:** `SELECT current_database()` → **`EduSuggest`**.
- **Chuỗi Migration đã chạy:**
  - `c3d4e5f6a7b8 → d4e5f6a7b8c9` (`add phase 4 marketplace commerce tables, enrollment entitlements, and pricing constraints`) — **PASS**.
  - `d4e5f6a7b8c9 → e5f6a7b8c9d0` (`add phase 4.7a.2 financial integrity tables, append-only event log, durable recovery queue, and JSONB backfill`) — **PASS**.
- **Xác minh sau migration:**
  - Revision: **`e5f6a7b8c9d0`** · Tổng số bảng: **`35`** (34 bảng nghiệp vụ + `alembic_version`).
  - `Startup Schema Guard` (`verify_database_schema_compatibility`): **`True` (PASS)**.
  - DB Append-Only Trigger: **`trg_sukienthanhtoan_append_only`** hiện diện và hoạt động trên `SuKienThanhToan`.

---

## 4. Đối chiếu Bảo toàn Dữ liệu Trước & Sau Migration (`edusuggest-official-v1`)

| Bảng dữ liệu | Trước (`c3d4e5f6a7b8`) | Sau (`e5f6a7b8c9d0`) | Chênh lệch / Ghi chú |
|---|---:|---:|---|
| `DanhMuc` | 24 | **24** | 0 — Bảo toàn 100% |
| `KhoaHoc` | 120 | **120** | 0 — Học phí & trạng thái giữ nguyên |
| `BaiHoc` | 411 | **411** | 0 — Bảo toàn 100% |
| `TaiLieu` | 243 | **243** | 0 — Bảo toàn 100% |
| `NguoiDung` | 78 | **78** | 0 — Bảo toàn 100% |
| `DangKyKhoaHoc` | 150 | **150** | **150/150 là `LEGACY` + `ACTIVE`** (không yêu cầu mua lại) |
| `LichSuHocTap` | 300 | **300** | 0 — Bảo toàn 100% |
| `ChuyenMon` / `ChuyenGia` / `NhaCungCapKhoaHoc` | 30 / 20 / 8 | **30 / 20 / 8** | 0 — Bảo toàn 100% |
| `ThongBao` / `DanhGiaChuyenGia` | 12 / 20 | **12 / 20** | 0 — Bảo toàn 100% |
| `DonHang` / `ThanhToan` / `HoanTienNgoaiLe` / `SuKienThanhToan` / `TacVuDoiSoatThanhToan` | N/A | **0 / 0 / 0 / 0 / 0** | **0 đơn hàng / giao dịch giả cho LEGACY** |

---

## 5. Runtime Flags thực tế & Chính sách Bảo mật trên Production

Website chính thức khởi chạy tại **`http://127.0.0.1:5173/`** ↔ **`http://127.0.0.1:8000/api`** (Database `EduSuggest`, không sửa `.env`, dùng `VITE_CACHE_DIR=.vite-prod-5173`):

- `APP_ENV=production`, `DEBUG=False`
- `COMMERCE_ENROLLMENT_GATE_ENABLED=False`
- `MOCK_PAYMENT_ENABLED=False`
- `VNPAY_SANDBOX_ENABLED=False`
- `FINANCIAL_INTEGRITY_WORKFLOW_ENABLED=False`
- `PAYMENT_RECONCILIATION_WORKER_ENABLED=False`
- `PAYMENT_AUTO_GATEWAY_QUERY_ENABLED=False`
- `PAYMENT_AUTO_RESTORE_ENABLED=False`
- `AUTO_ASSIGNMENT_WORKFLOW_ENABLED=False`, `AUTO_ASSIGNMENT_WORKER_ENABLED=False`, `ACCOUNTABILITY_ENABLED=False`

> **Ghi chú trung thực về COM-01 khi `COMMERCE_ENROLLMENT_GATE_ENABLED=False`:** Do Production chưa có cổng thanh toán thật nào được bật, `COMMERCE_ENROLLMENT_GATE_ENABLED` đang giữ `False` để giao diện ẩn toàn bộ nút giỏ hàng/mua hàng và không làm kẹt người học. Điều này có nghĩa hành vi đăng ký trực tiếp cũ vẫn đang mở trên Production — **không tuyên bố COM-01 đã đóng trên Production** cho đến khi bạn phê duyệt kích hoạt cổng thanh toán thực tế cùng `COMMERCE_ENROLLMENT_GATE_ENABLED=True`.

---

## 6. Post-Deployment Read-Only Validation, Regression & Trạng thái Các Môi trường

| Kiểm tra | Kết quả |
|---|---|
| `GET http://127.0.0.1:8000/api/health` | `200 OK` (`{"status":"ok","application":"EduSuggest","database":"connected"}`) |
| `GET http://127.0.0.1:8000/api/commerce/capabilities` | `200 OK` (`marketplaceEnabled: false`, `enrollmentGateEnabled: false`, `mockPaymentEnabled: false`, `vnpaySandboxEnabled: false`) |
| `GET /api/categories` · `GET /api/courses?limit=100` · `GET /api/courses/{id}` | `200 OK` (`24` danh mục, `100` khóa công khai, chi tiết `200 OK`, `100/100` ảnh bìa `HTTP 200`, 0 lỗi `UndefinedColumn`/`UndefinedTable`) |
| `GET /api/payments/vnpay/ipn?vnp_TxnRef=CHECK` (Fail-closed check) | `200 OK` (`{"RspCode":"99","Message":"VNPay sandbox disabled"}`) |
| **Production Frontend (`http://127.0.0.1:5173/`)** | `200 OK` (đang hoạt động) |
| **Marketplace Staging (`http://127.0.0.1:5176/` ↔ `http://127.0.0.1:8003/api`)** | `200 OK` (`mockPaymentEnabled: true` trên `EduSuggest_phase4_test` để trình diễn Mock Payment) |
| **Dataset Staging (`http://127.0.0.1:5175/` ↔ `http://127.0.0.1:8002/api`)** | `200 OK` (không bị ảnh hưởng) |
| **Full Backend Regression (trên `EduSuggest_phase4_test`)** | **266 / 266 PASS** (`0` code thay đổi kể từ GĐ4.7A.3) |
| **Frontend Vite Production Build (`--outDir dist-phase47b-check`)** | **PASS** (`1,911 modules`, `1.43s`) |
| **Browser Automation (Chrome DevTools MCP)** | **BLOCKED (`NOT TESTED`)** — sử dụng [docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md](file:///D:/đồ%20án/EduSuggest/docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md) để kiểm tra trực tiếp trên trình duyệt |

---

## 7. Chức năng chưa kích hoạt, Rủi ro còn tồn tại & Sẵn sàng Rollback

- **Chức năng chưa kích hoạt trên Production:** Mua khóa học trả phí (`COMMERCE_ENROLLMENT_GATE_ENABLED=False`), Mock Payment (chặn cứng trên Production), VNPay Sandbox/Live, Durable Payment Reconciliation Worker, và GĐ3 Automatic Assignment.
- **Rủi ro còn tồn tại:** (1) `COM-01` vẫn mở khi `COMMERCE_ENROLLMENT_GATE_ENABLED=False`; (2) VNPay Sandbox chưa nghiệm thu trực tuyến; (3) Browser E2E tự động chưa chạy do Chrome DevTools MCP `BLOCKED`; (4) khóa handle Windows trên `frontend/dist/assets`.
- **Rollback Readiness:** Bản backup `EduSuggest.pre-phase47b.dump` (SHA-256 đã xác minh & restore test PASS) + `media_courses.zip` + `private_materials.zip` luôn sẵn sàng. Nếu phát sinh dữ liệu học tập mới sau thời điểm triển khai, ưu tiên giữ nguyên schema 35 bảng và rollback riêng tầng ứng dụng để không mất dữ liệu mới.
