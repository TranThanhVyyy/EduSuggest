# EDUSUGGEST – GĐ4.7A.2: DURABLE PAYMENT RECONCILIATION WORKER IMPLEMENTATION REPORT

**Ngày triển khai:** 2026-11-26  
**Phạm vi:** Triển khai thực tế PostgreSQL Durable Payment Reconciliation Worker (`service/payment_reconciliation_worker.py` + launcher độc lập `scripts/run_payment_reconciliation_worker.py`) vận hành trên bảng hàng đợi riêng `TacVuDoiSoatThanhToan`, tách biệt hoàn toàn với GĐ3 Assignment Worker (`HangDoiPhanCong`).  
**Trạng thái:** **HOÀN TẤT TRÊN `EduSuggest_phase4_test` (`e5f6a7b8c9d0`, 35 bảng). DỪNG CHỜ PHÊ DUYỆT NGHIỆM THU CUỐI CÙNG.**

---

## 1. Kiến trúc 3 Pha (Zero DB Lock During Network Calls)

Worker được triển khai trong [payment_reconciliation_worker.py](file:///D:/đồ%20án/EduSuggest/backend/service/payment_reconciliation_worker.py) theo mô hình 3 pha tách biệt hoàn toàn để không bao giờ giữ kết nối hay khóa hàng PostgreSQL trong khi gọi mạng tới cổng thanh toán:

1. **Pha 1 — Short DB Claim Transaction (`claim_next_task`):**
   - Truy vấn `TacVuDoiSoatThanhToan` bằng `FOR UPDATE SKIP LOCKED LIMIT 1` cho các tác vụ `PENDING`/`RETRY_WAIT` đến hạn (`thoiDiemChayTiepTheo <= now`) **HOẶC** các tác vụ `PROCESSING` đã hết hạn lease (`hanLease <= now` do worker cũ crash).
   - Tăng `leaseGeneration += 1`, sinh mới UUID `claimToken`, gán `trangThai = 'PROCESSING'`, `maWorker`, `hanLease = now + lease_seconds`, tăng `soLanThu += 1`, và **COMMIT ngay lập tức**.
2. **Pha 2 — Unlocked Gateway Execution (`_load_snapshots_unlocked` → `gateway_client`):**
   - Đọc snapshot tối thiểu không khóa (`ThanhToan`/`HoanTienNgoaiLe`) và gọi `gateway_client.query_payment(...)` hoặc `query_refund(...)` **ngoài transaction**.
   - Mặc định dùng `FailClosedGatewayQueryClient` (trả `UNKNOWN` khi `PAYMENT_AUTO_GATEWAY_QUERY_ENABLED=False` hoặc chưa cấu hình VNPay live).
3. **Pha 3 — Fenced Result Application Transaction (`apply_fenced_outcome`):**
   - Khóa lại hàng tác vụ với điều kiện fencing bắt buộc:
     `WHERE maTacVu = :id AND claimToken = :token AND leaseGeneration = :gen FOR UPDATE`
   - Nếu worker cũ thức dậy sau khi mất lease → câu truy vấn không khớp → trả về **`"STALE_LEASE_IGNORED"`** và **tuyệt đối không ghi đè** kết quả của worker mới.

---

## 2. Sweeper & Luồng phục hồi 4 loại tác vụ

Hàm `sweep_stale_payment_tasks(db, pending_age_minutes=5)` tự động quét và nạp tác vụ idempotent (`ON CONFLICT ("khoaChongTrung") DO NOTHING`) không phụ thuộc người dùng mở lại trang `PaymentResultView` hay ADMIN mở Dashboard:

| Loại tác vụ (`loaiTacVu`) | Nguồn phát hiện | Hành vi xử lý an toàn |
|---|---|---|
| `QUERY_PENDING_PAYMENT` | `ThanhToan.trangThai = 'PENDING'` quá 5 phút | Gọi `QueryDR`. Nếu `CAPTURED` → chạy `_apply_verified_callback` cấp quyền nguyên tử `PAID` + `ACTIVE`. Nếu `FAILED`/`CANCELLED` → cập nhật trạng thái & `DONE`. Nếu vẫn `PENDING`/`UNKNOWN` → `RETRY_WAIT` theo backoff `[60s, 180s, 600s, 1800s, 3600s]` (**không bao giờ coi thiếu IPN là thất bại!**). |
| `VERIFY_EXPIRED_ORDER` | Đơn hết hạn có giao dịch chưa rõ kết quả | Gọi `QueryDR`; nếu cổng đã thu tiền → ghi `CAPTURED_UNAPPLIED` (`daThuTien=TRUE`) để không mất tiền. |
| `RETRY_CAPTURED_UNAPPLIED` | `ThanhToan.trangThai = 'CAPTURED_UNAPPLIED'` (tự động nạp ngay lúc nhận callback) | Nếu `PAYMENT_AUTO_RESTORE_ENABLED=True` và đơn/khóa học/người dùng hợp lệ → tự động khôi phục `PAID` + `ACTIVE` + ghi `AUTO_RECONCILE_ACTIVATED`. Ngược lại (thu trùng / khóa ẩn / cờ tắt) → chuyển `ESCALATED_ADMIN`. |
| `QUERY_UNKNOWN_REFUND` | `HoanTienNgoaiLe.trangThai IN ('REFUND_PENDING', 'UNKNOWN')` (tự động nạp ngay khi gặp `UNKNOWN`) | **TUYỆT ĐỐI KHÔNG gửi lại Refund request.** Chỉ gọi `QueryDR`: nếu `REFUNDED` → chốt `REFUNDED` + đóng `LanThuHoanTien=SUCCEEDED`; nếu `NOT_REFUNDED` → chuyển `HoanTienNgoaiLe=REFUND_FAILED`, `LanThuHoanTien=FAILED`, `ESCALATED_ADMIN`; nếu vẫn `UNKNOWN` → backoff retry. |

---

## 3. Standalone CLI Launcher (`scripts/run_payment_reconciliation_worker.py`)

File [run_payment_reconciliation_worker.py](file:///D:/đồ%20án/EduSuggest/backend/scripts/run_payment_reconciliation_worker.py) cung cấp tiến trình worker độc lập:
- **Allowlist DB cứng:** `ALLOWED_TEST_DATABASES = {"EduSuggest_phase4_test", "EduSuggest_phase47a2_rehearsal"}` — từ chối ngay lập tức Production `"EduSuggest"` (`exit code 3`).
- **Feature flag bắt buộc:** Từ chối chạy nếu `PAYMENT_RECONCILIATION_WORKER_ENABLED=False` (`exit code 2`).
- **Fail-closed Schema Guard:** Chạy `verify_database_schema_compatibility` trước khi poll (`exit code 4` nếu thiếu bảng/cột).
- **Graceful Shutdown & Safe JSON Logs:** Bắt `SIGINT`/`SIGTERM`, hỗ trợ `--once`, không in secret hay thông tin nhạy cảm ra log.

---

## 4. Kết quả kiểm thử Crash Recovery, Fencing & Concurrency (`test_f04`, `test_f05`)

- **Sweeper + `QUERY_PENDING_PAYMENT` → `DONE_CAPTURED`:** **PASS** (khôi phục đơn `PAID` + đúng 1 quyền học `ACTIVE`).
- **Abrupt Crash + Stale Lease Recovery + Multi-Worker Race (`ThreadPoolExecutor` 2 workers):** **PASS** (sau khi Worker 1 mất lease, đúng 1 worker giành quyền với `leaseGeneration=2`, worker thứ 2 không tạo trùng).
- **Fencing Token Protection:** Worker 1 thức dậy trễ với `(claimToken_1, leaseGeneration=1)` bị chặn ngay lập tức (`STALE_LEASE_IGNORED`), không ghi đè kết quả `PAID` đã commit — **PASS**.
- **Refund `UNKNOWN` Recovery via QueryDR (Zero Blind Retry):** Worker xác nhận `REFUNDED` từ QueryDR, cập nhật `HoanTienNgoaiLe=REFUNDED` + `LanThuHoanTien=SUCCEEDED` + `DonHang=REFUNDED` — **PASS**.
- **Standalone CLI Guards (`test_f05`):** Production DB → `exit 3`, flag OFF → `exit 2`, flag ON trên `EduSuggest_phase4_test --once` → `exit 0` — **PASS**.

---

## 5. Giới hạn & Blocker còn lại trước Production thu tiền thật

1. **VNPay Live Sandbox (Internet):** Vẫn **`BLOCKED`** do chưa có `VNPAY_TMN_CODE`/`VNPAY_HASH_SECRET` thật và Public HTTPS IPN URL; chưa kiểm chứng thực tế HTTP transport tới máy chủ VNPay.
2. **Browser E2E tự động:** Vẫn **`BLOCKED`** do Chrome DevTools MCP (`DevToolsActivePort ENOENT`); staging `http://127.0.0.1:5176/` ↔ `http://127.0.0.1:8003/api` đang chạy sẵn để bạn nghiệm thu trực tiếp.
3. **Production `EduSuggest`:** Giữ nguyên **100% READ ONLY** (`c3d4e5f6a7b8`, `24` bảng); dừng chờ phê duyệt nghiệm thu cuối cùng trước khi mở GĐ4.7B.
