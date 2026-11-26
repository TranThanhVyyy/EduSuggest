# EDUSUGGEST – GĐ4.6: PAYMENT SAFETY AUDIT & 30-SCENARIO STRESS REPORT

**Ngày kiểm toán:** 2026-11-26  
**Phạm vi:** Kiểm toán an toàn luồng thanh toán end-to-end (`Cart → Checkout → Order → Payment → IPN → Enrollment → Payment Result → Exception Refund`), kiểm thử 30 kịch bản chịu tải/bơm lỗi trên PostgreSQL thật (`EduSuggest_phase4_test`), và đánh giá khoảng trống schema cho giai đoạn thu tiền thật.  
**Trạng thái:** **HOÀN TẤT KIỂM TOÁN & KIỂM THỬ TRÊN `EduSuggest_phase4_test` (137/137 Backend PASS); CHƯA TRIỂN KHAI LÊN PRODUCTION.**

---

## 1. Tóm tắt điều hành (Executive Summary)

EduSuggest áp dụng chính sách **mua khóa học một lần, sở hữu lâu dài — không hoàn tiền thông thường do đổi ý**, nhưng **bắt buộc bảo vệ quyền lợi người học** khi phát sinh sự cố thanh toán đã xác minh (trừ tiền nhiều lần, thu sai số tiền, đã trừ tiền nhưng chưa cấp quyền học, thanh toán trễ sau khi đơn hủy/hết hạn).

Qua kiểm toán toàn diện kiến trúc GĐ4.1–GĐ4.5 và gia cố ở GĐ4.6:

1. **Không bao giờ làm mất bằng chứng tiền đã thu (Zero Lost-Capture Guarantee):**
   - Trong GĐ4.1, chỉ mục `uq_ThanhToan_one_paid_per_order` (`UNIQUE (maDonHang) WHERE trangThai = 'PAID'`) đảm bảo mỗi đơn hàng chỉ có tối đa 1 giao dịch `PAID`.
   - Tuy nhiên, nếu khách hàng vô tình thanh toán thành công **2 lần** trên 2 `maThanhToan` khác nhau của cùng 1 `DonHang` (hoặc IPN đến trễ sau khi đơn `EXPIRED`/`CANCELLED`), giao dịch thứ 2 không thể gán `trangThai = 'PAID'`.
   - **Gia cố GĐ4.6 (`backend/service/order_payment_service.py` — `_record_reconciliation`):** Mọi giao dịch đã thu tiền ở cổng nhưng không thể áp dụng vào đơn đều lưu đầy đủ vào `ThanhToan.duLieuPhanHoiAnToan (JSONB)`:
     - `fundsCaptured: true`
     - `capturedAmountVnd: "<Decimal VND>"`
     - `reconciliationRequired: true`
     - `reconciliationStatus: "OPEN"`
     - `auditTrail: [...]` (kèm `maGiaoDichCong`, `maPhanHoiCong`, timestamp UTC).
   - Nhờ đó, hệ thống **không bao giờ đánh mất tiền hay bằng chứng đối soát cổng thanh toán** dù chưa thêm migration mới.

2. **Tách bạch hoàn toàn 2 phạm vi hoàn tiền ngoại lệ (`EXCESS_PAYMENT` vs `FULL_ORDER`):**
   - **`EXCESS_PAYMENT` (Hoàn tiền thu dư / thu trùng):** Hoàn đúng khoản tiền thu dư trên giao dịch dư; **GIỮ NGUYÊN** đơn hàng `PAID` hợp lệ và quyền học `ACTIVE` của người dùng; **KHÔNG** cộng trùng vào Doanh thu ghi nhận (`Gross Revenue`) và **KHÔNG** trừ nhầm vào Doanh thu thuần (`Net Revenue`) của đơn hợp lệ.
   - **`FULL_ORDER` (Hoàn tiền sự cố toàn đơn):** Chuyển `DonHang` và `ThanhToan` sang `REFUNDED`, chỉ thu hồi (`trangThaiQuyenHoc = 'REVOKED'`) đúng bản ghi `DangKyKhoaHoc` gắn với `maDonHang` đó; **KHÔNG XÓA** dòng `DangKyKhoaHoc`, **KHÔNG XÓA** `LichSuHocTap`, và **KHÔNG BAO GIỜ** đụng chạm bản ghi `LEGACY` hay `FREE`.

3. **Ưu tiên #1 khi đối soát: Khôi phục quyền học trước khi hoàn tiền (`Priority #1 Entitlement Restore`):**
   - Với các sự cố thanh toán trễ sau khi đơn `EXPIRED` hoặc lỗi cấp quyền mà khóa học vẫn hợp lệ (`APPROVED + VISIBLE`), ADMIN có nút hành động ưu tiên `POST /api/admin/commerce/reconciliation/{payment_id}/activate` để đưa đơn về `PAID` và kích hoạt quyền học `ACTIVE` ngay lập tức mà không cần hoàn tiền.

4. **Chống hoàn tiền trùng & chống thử lại mù khi gặp `UNKNOWN`:**
   - Vòng đời hoàn tiền ngoại lệ tuân thủ máy trạng thái chặt chẽ dưới row lock `SELECT ... FOR UPDATE`:
     `PENDING_REVIEW → VERIFIED → REFUND_PENDING → REFUNDED | REFUND_FAILED | UNKNOWN`
   - Khi gặp timeout mạng/cổng (`UNKNOWN`), mọi yêu cầu gọi lại `execute` mù đều bị chặn cứng (`HTTP 409 Conflict`). ADMIN bắt buộc phải đối soát bằng chứng cổng qua `POST /api/admin/commerce/refunds/{payment_id}/reconcile-unknown` (kèm QueryDR) trước khi quyết định thử lại (`REFUND_FAILED`) hoặc chốt hoàn (`REFUNDED`).

5. **Không giả lập thành công cho cổng thật (Non-Fabrication Guard):**
   - Đã xây dựng bộ tạo payload chuẩn **VNPay API v2.1.0 QueryDR & Refund** (JSON body + chữ ký HMAC-SHA512 nối bằng ký tự `|` theo tài liệu chính thức VNPay) trong `backend/service/payment_providers.py`.
   - Tại runtime, `admin_execute_exception_refund` **từ chối trả về thành công giả** (`HTTP 409`) đối với `VNPAY_SANDBOX` khi chưa có kết nối live sandbox / credentials thật.

---

## 2. Kết quả kiểm thử 30 kịch bản Payment Stress & Fault Injection

Toàn bộ 30 kịch bản được đóng gói trong `backend/tests/test_phase46_payment_safety_stress_admin_provider.py` và thực thi trực tiếp trên PostgreSQL thật (`EduSuggest_phase4_test`) với `ThreadPoolExecutor` đa kết nối:

| Nhóm kịch bản | Phạm vi 30 kịch bản kiểm thử | Hàm pytest | Kết quả |
|---|---|---|---|
| **Nhóm A (S01–S06)** | 20x VNPay IPN trùng lặp đồng thời (10 threads), 6x double-click Buy Now cùng `Idempotency-Key`, 15x Mock callback đồng thời → đúng 1 lần kích hoạt, 1 bản ghi `DangKyKhoaHoc`, còn lại idempotent replay | `test_s01_to_s04_rapid_duplicate_callbacks_20x_single_activation`, `test_s05_concurrent_mock_callback_and_buy_now_idempotency` | **PASS** |
| **Nhóm B (S07–S11)** | 2 giao dịch thu tiền thực khác nhau trên cùng 1 đơn hàng (VNPay & Mock) → giao dịch #2 lưu `fundsCaptured=True` + `reconciliationRequired=True`; ADMIN tạo/xác minh/thực thi hoàn tiền `EXCESS_PAYMENT` → đơn `PAID` & quyền học `ACTIVE` giữ nguyên, Gross/Net Revenue không bị cộng trùng hay trừ nhầm | `test_s07_to_s11_two_captured_payments_excess_refund_keeps_access_and_revenue` | **PASS** |
| **Nhóm C (S12–S16)** | IPN đến trễ sau khi đơn `EXPIRED` → đánh dấu cần đối soát; ADMIN thực thi Priority #1 Restore (`activate`) → đơn về `PAID`, cấp `ACTIVE`; Return URL đến trước IPN không cấp quyền; callback `FAILED` đến sau `PAID` không hạ trạng thái `PAID`; Return URL sau IPN đọc trạng thái `PAID` | `test_s12_to_s14_late_ipn_after_expiry_priority1_restore`, `test_s15_s16_out_of_order_callbacks_paid_not_downgraded_and_return_before_ipn` | **PASS** |
| **Nhóm D (S17–S20)** | Hoàn tiền ngoại lệ `FULL_ORDER` → `DonHang`/`ThanhToan` chuyển `REFUNDED`, chỉ thu hồi `DangKyKhoaHoc` đúng `maDonHang` thành `REVOKED` (không xóa dòng), giữ nguyên `LichSuHocTap` và giữ nguyên bản ghi `LEGACY` (`ACTIVE`) trên khóa khác | `test_s17_to_s20_full_order_refund_revokes_only_target_preserves_history_and_legacy` | **PASS** |
| **Nhóm E (S21–S26)** | Chặn hoàn tiền cho giao dịch chưa thu tiền (`409`), chặn hoàn vượt số tiền đã thu (`400`), timeout `UNKNOWN` chặn retry mù (`409`), `reconcile-unknown` → `REFUND_FAILED` rồi 2 ADMIN bấm `execute` đồng thời → đúng 1 lần `REFUNDED`; xác minh test vector HMAC-SHA512 nối `|` chuẩn VNPay v2.1.0 QueryDR & Refund; chặn giả lập hoàn tiền VNPay (`409`) | `test_s21_to_s24_refund_concurrency_unknown_timeout_reconcile_and_limits`, `test_s25_s26_vnpay_querydr_refund_vectors_and_non_fabrication_guard` | **PASS** |
| **Nhóm F (S27–S30)** | USER báo cáo sự cố thanh toán (`POST /api/orders/{id}/incidents`), chặn mass assignment / trường nhạy cảm thẻ (`422`), chặn IDOR chéo user (`404`), chặn RBAC USER/PROVIDER vào ADMIN (`403`); PROVIDER sales trên đơn đa nhà cung cấp tách bạch 100% theo `maNhaCungCap`, loại trừ `LEGACY`; Production guard (`APP_ENV=production`) tắt cứng `mockPaymentEnabled` & `vnpaySandboxEnabled` | `test_s27_s28_user_incident_report_idor_and_mass_assignment_blocked`, `test_s29_s30_provider_owner_scoped_sales_and_production_guard` | **PASS** |

---

## 3. Đánh giá khoảng trống Schema & Kiến nghị trước khi thu tiền thật (No Auto-Migration)

Theo đúng yêu cầu GĐ4.6 (**không tự tạo migration mới khi chưa được phê duyệt**), toàn bộ dữ liệu đối soát, báo cáo sự cố và hồ sơ hoàn tiền ngoại lệ hiện đang được lưu an toàn trong `ThanhToan.duLieuPhanHoiAnToan (JSONB)` và bảo vệ bằng khóa hàng PostgreSQL `SELECT ... FOR UPDATE`.

Tuy nhiên, trước khi đưa hệ thống lên môi trường **Production thu tiền thật**, kiến nghị phê duyệt một migration bổ sung (dự kiến GĐ4.7+) gồm 3 nâng cấp mức cơ sở dữ liệu:

1. **Mở rộng `CHECK` trên `ThanhToan.trangThai`:** Bổ sung trạng thái `'CAPTURED_UNAPPLIED'` để tách biệt rõ ở mức cột quan hệ giữa giao dịch thất bại chưa thu tiền (`FAILED`) và giao dịch đã thu tiền tại cổng nhưng chưa áp dụng được vào đơn (`CAPTURED_UNAPPLIED`).
2. **Tạo bảng quan hệ `HoanTienNgoaiLe`:**
   - Cột chuẩn hóa: `maHoanTien`, `maDonHang (FK)`, `maThanhToan (FK)`, `khoaChongTrung (UNIQUE NOT NULL)`, `phamViHoan` (`EXCESS_PAYMENT`/`FULL_ORDER`), `loaiSuCo`, `soTienDaThu NUMERIC(12,0)`, `soTienHoan NUMERIC(12,0)`, `trangThai` (`PENDING_REVIEW`, `VERIFIED`, `REFUND_PENDING`, `REFUNDED`, `REFUND_FAILED`, `UNKNOWN`), `maGiaoDichHoanCong`, `maNguoiXuLy`, `lichSuTrangThai JSONB`.
   - Ràng buộc `UNIQUE` ở mức DB trên `khoaChongTrung` và chỉ mục partial unique chặn tạo 2 yêu cầu hoàn tiền đang mở trên cùng 1 `maThanhToan`.
3. **Tạo bảng quan hệ `BaoCaoSuCoThanhToan`:** Lưu tách biệt báo cáo sự cố người dùng thay vì lồng trong `ThanhToan.duLieuPhanHoiAnToan`, hỗ trợ phân công SLA, tìm kiếm và báo cáo vận hành quy mô lớn.

---

## 4. Kết luận kiểm toán

- **Mức độ an toàn hiện tại trên `EduSuggest_phase4_test`:** **ĐẠT (PASS 10/10 nhóm — 30/30 kịch bản, 137/137 hồi quy toàn bộ Backend).**
- **VNPay Live Sandbox (QueryDR / Refund qua Internet):** **BLOCKED** (chưa có `VNPAY_TMN_CODE`/`VNPAY_HASH_SECRET` và public HTTPS IPN URL); đã xác minh đầy đủ chữ ký & cấu trúc gói tin theo đặc tả VNPay v2.1.0 bằng test vector.
- **Database Production `EduSuggest`:** Giữ nguyên **100% READ ONLY** (`c3d4e5f6a7b8`, `24` bảng, `120` khóa học, `150` đăng ký, `300` lịch sử học tập).
