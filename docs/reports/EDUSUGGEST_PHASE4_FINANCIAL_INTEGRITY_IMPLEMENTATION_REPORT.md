# EDUSUGGEST – GĐ4.7A.2: FINANCIAL INTEGRITY IMPLEMENTATION REPORT

**Ngày triển khai:** 2026-11-26  
**Phạm vi:** Triển khai chính thức 5 bảng tài chính chuẩn hóa, 2 cột thu tiền tường minh trên `ThanhToan`, DB-level append-only trigger trên `SuKienThanhToan`, Migration + JSONB Backfill (`e5f6a7b8c9d0`, 30 → 35 bảng), hoàn tiền một phần `PARTIAL_OVERCHARGE`, VNPay v2.1.0 QueryDR/Refund response verification, Fail-Closed Schema Guard và Feature Flags mặc định `False` trên môi trường kiểm thử `EduSuggest_phase4_test`.  
**Trạng thái:** **HOÀN TẤT TRÊN `EduSuggest_phase4_test` (35 BẢNG, `e5f6a7b8c9d0`). DỪNG CHỜ PHÊ DUYỆT NGHIỆM THU CUỐI CÙNG — CHƯA TRIỂN KHAI PRODUCTION.**

---

## 1. Alembic Revision mới & Diễn tập Migration / JSONB Backfill

- **Alembic Head mới (Single Head):** `e5f6a7b8c9d0` (parent: `d4e5f6a7b8c9`) — file [e5f6a7b8c9d0_add_phase47_financial_integrity_and_recovery.py](file:///D:/đồ%20án/EduSuggest/backend/migrations/versions/e5f6a7b8c9d0_add_phase47_financial_integrity_and_recovery.py).
- **Tổng số bảng trên `EduSuggest_phase4_test`:** **35 bảng** (34 bảng nghiệp vụ + `alembic_version`).
- **Backup trước migration (`EduSuggest_phase4_test`):**
  - File: `backend/database/backups/phase47a2-pre-financial/20261126/EduSuggest_phase4_test.custom.dump`
  - Kích thước: **`205,076 bytes`** · SHA-256: **`7E539870B5E3A8EAA4A8FEF2ADE66F3702B015EE9C19C3B648B846BEA4317F9F`**
  - Restore rehearsal thành công vào DB cô lập `EduSuggest_phase47a2_rehearsal`.
- **Diễn tập Migration (`upgrade → downgrade → re-upgrade`) trên `EduSuggest_phase47a2_rehearsal`:** **PASS 100%** (30 → 35 → 30 → 35 bảng).
- **Nâng cấp `EduSuggest_phase4_test`:** `d4e5f6a7b8c9 → e5f6a7b8c9d0` **PASS**, bảo toàn `120` khóa học, `150` đăng ký (`LEGACY/ACTIVE`), `300` lịch sử học tập.
- **JSONB Backfill (Idempotent, không xóa bằng chứng gốc):**
  - Tự động điền `daThuTien = TRUE`, `soTienDaThuThucTe = soTien` cho các giao dịch `PAID`/`REFUNDED`.
  - Tự động chuyển các giao dịch `FAILED` có `duLieuPhanHoiAnToan->>'fundsCaptured' = 'true'` sang `CAPTURED_UNAPPLIED` + `daThuTien = TRUE` + `soTienDaThuThucTe`.
  - Backfill `exceptionRefund` → `HoanTienNgoaiLe` (`ON CONFLICT ("khoaChongTrung") DO NOTHING`) và `incidentReports` → `BaoCaoSuCoThanhToan` (`ON CONFLICT ("maSoSuCo") DO NOTHING`) mà **giữ nguyên toàn bộ JSONB gốc**.

---

## 2. Cấu trúc 5 Bảng Tài chính & Ràng buộc Bất biến (Financial Invariants)

### 2.1. Mở rộng `ThanhToan`
- Bổ sung `daThuTien BOOLEAN NOT NULL DEFAULT FALSE` và `soTienDaThuThucTe NUMERIC(12,0) NOT NULL DEFAULT 0 CHECK (soTienDaThuThucTe >= 0)`.
- Mở rộng `ck_ThanhToan_trangThai`: `('PENDING', 'PAID', 'CAPTURED_UNAPPLIED', 'FAILED', 'CANCELLED', 'EXPIRED', 'REFUNDED', 'PARTIALLY_REFUNDED')`.
- **Bất biến:** Không bao giờ dùng `FAILED` cho giao dịch đã xác minh thu tiền; `uq_ThanhToan_one_paid_per_order` tiếp tục chống 2 dòng `PAID`/đơn trong khi giao dịch thu trùng lưu sạch ở `CAPTURED_UNAPPLIED`.

### 2.2. 5 Bảng mới đã triển khai (`backend/models/entities.py`)
1. **`HoanTienNgoaiLe`:** Lưu hồ sơ hoàn tiền ngoại lệ (`EXCESS_PAYMENT`, `FULL_ORDER`, `PARTIAL_OVERCHARGE`), `UNIQUE(maSoHoanTien)`, `UNIQUE(khoaChongTrung)`, `CHECK(soTienHoan > 0 AND soTienHoan <= soTienDaThu)`, partial unique index `uq_HoanTienNgoaiLe_active_per_payment` chặn mở 2 yêu cầu hoàn tiền đồng thời trên cùng 1 `maThanhToan`.
2. **`LanThuHoanTien`:** Lưu từng lần gọi cổng hoàn tiền (`thuTuLanThu`, `maYeuCauCong UNIQUE`, `trangThai IN ('SENT','SUCCEEDED','FAILED','UNKNOWN')`), partial unique index `uq_LanThuHoanTien_inflight_per_refund` chặn ở tầng DB việc gửi lần thử hoàn mới khi lần trước đang `SENT` hoặc `UNKNOWN`.
3. **`BaoCaoSuCoThanhToan`:** Lưu báo cáo sự cố của `USER` (`maSoSuCo UNIQUE`), hỗ trợ `GET /api/orders/{id}/incidents` (owner-scoped) để người học theo dõi tiến trình xử lý.
4. **`SuKienThanhToan` (DB-Level Append-Only):** Nhật ký tài chính bất biến cho mọi sự kiện (`PAYMENT_INITIATED`, `CAPTURED_UNAPPLIED`, `ENTITLEMENT_ACTIVATED`, `USER_INCIDENT_REPORTED`, `RECONCILE_ACTIVATED`, `AUTO_RECONCILE_ACTIVATED`, `REFUND_CREATED`, `REFUND_VERIFIED`, `REFUND_UNKNOWN`, `REFUND_CONFIRMED`), bảo vệ ở tầng PostgreSQL bằng trigger **`trg_SuKienThanhToan_append_only`** chặn cứng mọi lệnh `UPDATE` và `DELETE`, kèm `financial_event_service._sanitize_event_payload` lọc sạch khóa nhạy cảm (secret/OTP/CVV/cardNumber/password).
5. **`TacVuDoiSoatThanhToan`:** Hàng đợi đối soát bền vững riêng biệt (chi tiết trong báo cáo Durable Payment Recovery).

---

## 3. Hoàn tiền ngoại lệ (`EXCESS_PAYMENT`, `PARTIAL_OVERCHARGE`, `FULL_ORDER`) & VNPay v2.1.0

- **Chính sách bất biến:** Giữ nguyên **không có hoàn tiền đổi ý**; chỉ hoàn tiền ngoại lệ đã xác minh bởi `ADMIN`.
- **`PARTIAL_OVERCHARGE`:** Đã kiểm chứng hoàn đúng khoản thu sai (`100,000 VND` trên giao dịch thu `699,000 VND` cho đơn `599,000 VND`), chuyển `ThanhToan.trangThai = 'PARTIALLY_REFUNDED'`, giữ nguyên đơn `PAID` + quyền học `ACTIVE`, lưu đủ `HoanTienNgoaiLe` + `LanThuHoanTien`, và chặn tổng số tiền hoàn vượt `soTienDaThuThucTe`.
- **VNPay v2.1.0 Response Verification (`backend/service/payment_providers.py`):**
  - Bổ sung `verify_vnpay_querydr_response` và `verify_vnpay_refund_response` xác minh chữ ký HMAC-SHA512 nối bằng `|` đúng thứ tự trường theo tài liệu chính thức VNPay v2.1.0 (`test_f03` **PASS**).
  - Giao dịch VNPay Sandbox trực tuyến qua Internet tiếp tục ở trạng thái **`BLOCKED`** (thiếu credentials & public HTTPS IPN; không giả lập thành công).

---

## 4. Feature Flags & Fail-Closed Startup Schema Guard

- **`backend/config/config.py`:** Tách riêng 4 cờ mới đều mặc định **`False`**: `FINANCIAL_INTEGRITY_WORKFLOW_ENABLED`, `PAYMENT_RECONCILIATION_WORKER_ENABLED`, `PAYMENT_AUTO_GATEWAY_QUERY_ENABLED`, `PAYMENT_AUTO_RESTORE_ENABLED`.
- **`backend/config/schema_guard.py`:** Cập nhật `REQUIRED_ALEMBIC_REVISION = "e5f6a7b8c9d0"`, kiểm tra bắt buộc đủ 5 cột `DangKyKhoaHoc`, 2 cột mới `ThanhToan` (`daThuTien`, `soTienDaThuThucTe`) và đủ 5 bảng tài chính — fail-closed chặn khởi động nếu thiếu.

---

## 5. Kết quả Kiểm chứng Tổng thể

| Hạng mục | Kết quả thực tế |
|---|---|
| **GĐ4.7A.2 Financial Integrity & Worker Recovery Suite** (`test_phase47a2_financial_integrity_durable_recovery.py`) | **5 / 5 PASS** (`10.75s`) — DB append-only trigger, `CAPTURED_UNAPPLIED`, `PARTIAL_OVERCHARGE`, VNPay response verify, Worker fencing/stale lease/crash/refund UNKNOWN, CLI guards |
| **Full Backend Regression (`EDUSUGGEST_TEST_DB_NAME=EduSuggest_phase4_test`)** | **`264 collected / 263 PASSED / 1 FAILED / 0 SKIPPED / 0 XFAILED`** (`89.54s`). **100% Marketplace & Financial Integrity (`47/47`) PASS**, `test_recommendation_integration` (`7/7`) PASS, `test_private_file_security` (`2/2`) PASS, `test_phase383_abrupt_worker_recovery` (`1/1`) PASS. Duy nhất 1 FAIL ở `test_phase33_durable_queue_lifecycle_security.py` trên `EduSuggest_phase3_test` do tranh chấp trực tiếp với tiến trình staging worker GĐ3.8.3 đang chạy nền. |
| **Frontend Vite Production Build** (`--outDir dist-phase47a2-check`) | **PASS** (`1,911 modules`, `2.45s`, thư mục tạm đã dọn) |
| **Staging Marketplace (`5176` ↔ `8003`)** | Đang hoạt động (`200 OK`) trên `EduSuggest_phase4_test` (35 bảng, `e5f6a7b8c9d0`) |
| **Browser E2E & VNPay Sandbox Live** | **BLOCKED (`NOT TESTED`)** — giữ checklist thủ công tại `docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md` |
| **Production `EduSuggest` & `EduSuggest_phase3_test`** | Giữ nguyên **100% READ ONLY / UNTOUCHED** (`c3d4e5f6a7b8`, `24` bảng) |
