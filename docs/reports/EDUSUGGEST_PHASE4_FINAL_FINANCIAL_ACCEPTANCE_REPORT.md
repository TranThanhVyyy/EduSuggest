# EDUSUGGEST – GĐ4.7A.3: FINAL FINANCIAL ACCEPTANCE REPORT

**Ngày nghiệm thu:** 2026-11-26  
**Phạm vi:** Nghiệm thu tài chính cuối cùng (Final Financial Acceptance) toàn bộ phân hệ E-Learning Marketplace (GĐ4.0 → GĐ4.7A.2), xử lý dứt điểm lỗi hồi quy cuối cùng (`266/266 PASS`), kiểm chứng tiến trình OS worker thực tế (`run_payment_reconciliation_worker.py`), diễn tập migration nối chuỗi từ Production backup (`c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0`, 35 bảng), và chốt quyết định GO/NO-GO tách biệt cho 4 phạm vi A / B / C / D.  
**Trạng thái:** **HOÀN TẤT NGHIỆM THU GĐ4.7A.3 — DỪNG CHỜ PHÊ DUYỆT GĐ4.7B. CHƯA TRIỂN KHAI PRODUCTION.**

---

## 1. Lỗi nghiêm trọng mới phát hiện & Đã sửa trong GĐ4.7A.3

1. **[CRITICAL — PRODUCTION OVERFLOW FIX] Tràn số nguyên 32-bit `int4` trong `commerce_service._lock_user_course`:**
   - **Phát hiện:** Trong quá trình chạy full regression 266 tests trên `EduSuggest_phase4_test`, khi `maNguoiDung` vượt mốc `2,148`, biểu thức cũ `(user_id * 1_000_000) + course_id` vượt giới hạn `int4` (`2,147,483,647`), làm psycopg truyền kiểu `bigint` và PostgreSQL ném lỗi `UndefinedFunction: function pg_advisory_xact_lock(smallint, bigint) does not exist`.
   - **Sửa triệt để ([commerce_service.py](file:///D:/đồ%20án/EduSuggest/backend/service/commerce_service.py)):** Chuyển sang không gian khóa gốc `(int4, int4)` của PostgreSQL: `SELECT pg_advisory_xact_lock(CAST(:u AS integer), CAST(:c AS integer))` — hỗ trợ an toàn `2.1 tỷ × 2.1 tỷ` cặp `(user_id, course_id)` không tràn số.
2. **Xử lý dứt điểm 100% tranh chấp worker GĐ3 trong bộ test hồi quy (`test_phase33` & `test_phase38`):**
   - Bổ sung `EDUSUGGEST_TEST_DB_NAME` (mặc định `EduSuggest_phase3_test`, chặn cứng `!= "EduSuggest"`) cho `test_phase33_durable_queue_lifecycle_security.py` và `test_phase38_final_acceptance_concurrency.py` (không sửa assertion, không tăng timeout, không migrate `EduSuggest_phase3_test`).

---

## 2. Kết quả Full Backend Regression (`EDUSUGGEST_TEST_DB_NAME=EduSuggest_phase4_test`)

| Chỉ số | Kết quả thực tế |
|---|---:|
| **Collected** | **266** |
| **Passed** | **266** |
| **Failed** | **0** |
| **Skipped** | **0** |
| **Xfailed** | **0** |
| **Thời gian chạy** | `94.73s` (`0:01:34`) |

- **Marketplace & Financial Integrity & Worker Recovery (GĐ4.1 → GĐ4.7A.3):** **49 / 49 PASS (100%)**.
- **GĐ3 Durable Queue, Automatic Assignment, Abrupt Worker Recovery, Recommendation, Private File Auth, Auth/RBAC:** **217 / 217 PASS (100%)**.

---

## 3. Kiểm toán Financial Integrity Invariants & Real OS-Process Worker Acceptance

### 3.1. Kiểm toán 5 bảng tài chính & `ThanhToan`
- **Append-Only DB Trigger (`trg_SuKienThanhToan_append_only`):** Đã chứng minh chặn cứng `UPDATE` và `DELETE` ở tầng PostgreSQL (`test_f01` **PASS**).
- **Chống lạm dụng cleanup test trong runtime:** `test_p47a3_no_session_replication_role_in_runtime_code` quét toàn bộ `api/`, `service/`, `repository/`, `config/`, `models/`, `scripts/` xác nhận **0** xuất hiện `session_replication_role` trong mã nguồn runtime (**PASS**).
- **Trạng thái `CAPTURED_UNAPPLIED` & `PARTIALLY_REFUNDED`:**
  - Mọi khoản thu trùng / IPN trễ đều lưu `trangThai='CAPTURED_UNAPPLIED'`, `daThuTien=True`, `soTienDaThuThucTe`, không bao giờ bị mất bằng chứng hoặc gắn nhãn `FAILED`.
  - Khi thanh toán chuyển `PARTIALLY_REFUNDED` (do `PARTIAL_OVERCHARGE`), `DonHang.trangThai` vẫn là `PAID`; nhánh `if order.trangThai == "PAID"` trong `_apply_verified_callback` đảm bảo mọi giao dịch thu tiền thứ 2 vẫn đi vào `CAPTURED_UNAPPLIED` (không ghi nhận doanh thu trùng). *(Ghi chú khuyến nghị không bắt buộc trước tiền thật: ở lần tối ưu DB tương lai có thể mở rộng partial unique index `uq_ThanhToan_one_paid_per_order` từ `= 'PAID'` sang `IN ('PAID', 'PARTIALLY_REFUNDED')` để bảo vệ thêm ở tầng DDL; chưa tạo migration mới).*
- **Hoàn tiền ngoại lệ (`EXCESS_PAYMENT`, `PARTIAL_OVERCHARGE`, `FULL_ORDER`):** Kiểm soát tổng tiền hoàn dưới khóa hàng `FOR UPDATE` + `CHECK (soTienHoan > 0 AND soTienHoan <= soTienDaThu)` + partial unique index `uq_HoanTienNgoaiLe_active_per_payment` + `uq_LanThuHoanTien_inflight_per_refund`. Tuyệt đối không có nút hoàn tiền đổi ý.

### 3.2. Nghiệm thu Tiến trình OS Worker thực tế (`test_phase47a3_real_worker_process_acceptance.py`)
- Khởi chạy **2 tiến trình OS thực tế song song** của [run_payment_reconciliation_worker.py](file:///D:/đồ%20án/EduSuggest/backend/scripts/run_payment_reconciliation_worker.py) đối với `EduSuggest_phase4_test`:
  - Xác nhận xử lý đồng thời qua `SKIP LOCKED` (`leaseGeneration == 1`, không trùng lặp).
  - Xác nhận thu hồi lease hết hạn (`stale lease recovery`) từ worker bị dừng đột ngột (`leaseGeneration >= 2`, `claimToken` được xoay vòng, không mất job).
  - Xác nhận `kill()` đột ngột tiến trình #1 và `terminate()` duyên dáng tiến trình #2 không làm hỏng hàng đợi.
  - Xác nhận không giữ khóa DB khi gọi gateway và không retry mù `REFUND UNKNOWN` (`test_f04`, `test_f05` **PASS**).

---

## 4. Kết quả Final Migration Rehearsal (`EduSuggest_phase47a3_rehearsal`)

- **Backup mới nhất từ Production `EduSuggest` (READ ONLY):**
  - File: `backend/database/backups/phase47a3-final-rehearsal/20261126/EduSuggest.custom.dump`
  - Kích thước: **`174,043 bytes`** · SHA-256: **`A8C47895F12B32AE5F95DB1A5003C154736749C10547BDA014028D54F76FAFA1`**
- **Nâng cấp nối chuỗi:** `c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0` (1 single head `e5f6a7b8c9d0`) — **PASS**.
- **Xác minh dữ liệu `edusuggest-official-v1`:** `tables=35`, `categories=24`, `courses=120`, `lessons=411`, `materials=243`, `users=78`, `enrollments=150` (`legacy_active=150`), `history=300`, `orders=0` (0 giao dịch giả cho LEGACY), `Startup Schema Guard = True`.
- **Diễn tập rollback trên bản sao sạch (0 dữ liệu tài chính):** `e5f6a7b8c9d0 → d4e5f6a7b8c9 → c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0` — **PASS**.

---

## 5. Browser E2E, VNPay Sandbox & Quyết định GO / NO-GO (A / B / C / D)

- **Browser Automation (Chrome DevTools MCP):** Vẫn **`BLOCKED` (`NOT TESTED`)** do `DevToolsActivePort ENOENT` trên máy cục bộ. Staging `http://127.0.0.1:5176/` ↔ `http://127.0.0.1:8003/api` đang hoạt động (`200 OK`) kèm [docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md](docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md).
- **VNPay Sandbox Live (Internet):** Vẫn **`BLOCKED` (`NOT TESTED`)** do thiếu `VNPAY_TMN_CODE`/`VNPAY_HASH_SECRET` và Public HTTPS IPN URL (request/response HMAC-SHA512 test vectors đều **PASS**).

| Phạm vi | Quyết định | Lý do & Điều kiện |
|---|---|---|
| **A. Marketplace Staging dùng Mock Payment (`5176`/`8003`)** | **CONDITIONAL GO** | **266/266 Backend PASS**, 2 real OS worker processes PASS, Vite Build PASS (`1,911 modules`); chờ bạn xác nhận trực quan trên Chrome do Chrome DevTools MCP bị `BLOCKED`. |
| **B. Migration & Triển khai Production 35 bảng (`e5f6a7b8c9d0`) với các gateway thanh toán TẮT** | **CONDITIONAL GO (Chờ phê duyệt GĐ4.7B)** | Chạy theo [EDUSUGGEST_PHASE4_CONTROLLED_DEPLOYMENT_PLAN.md](EDUSUGGEST_PHASE4_CONTROLLED_DEPLOYMENT_PLAN.md) với **tất cả cờ thanh toán = `False`** (`COMMERCE_ENROLLMENT_GATE_ENABLED=False`, `MOCK_PAYMENT_ENABLED=False`, `VNPAY_SANDBOX_ENABLED=False`). **Trải nghiệm người dùng:** Khi `COMMERCE_ENROLLMENT_GATE_ENABLED=False`, Frontend ẩn toàn bộ nút giỏ hàng/mua hàng và giữ luồng đăng ký hiện hành hoạt động bình thường; KHÔNG bật `COMMERCE_ENROLLMENT_GATE_ENABLED=True` khi cả Mock và VNPay đều tắt để tránh khóa người dùng không có phương thức thanh toán. |
| **C. VNPay Sandbox thực tế qua Internet** | **BLOCKED / NO-GO** | Thiếu credentials & Public HTTPS IPN URL; chưa nghiệm thu giao dịch thật với máy chủ VNPay Sandbox. |
| **D. Giao dịch tiền thật trên Production** | **NO-GO** | Bắt buộc hoàn thành trước khi thu tiền thật: (1) Nghiệm thu VNPay Sandbox & Live Certification qua Internet, (2) Browser E2E PASS đầy đủ, (3) Triển khai giám sát & cảnh báo vận hành cho `run_payment_reconciliation_worker.py`. |
