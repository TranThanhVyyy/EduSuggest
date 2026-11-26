# EDUSUGGEST – GĐ4: MANUAL BROWSER ACCEPTANCE CHECKLIST

**Mục đích:** Hướng dẫn nghiệm thu trực tiếp trên trình duyệt Chrome cho phân hệ Marketplace (do Chrome DevTools MCP bị `BLOCKED` bởi lỗi `DevToolsActivePort ENOENT` trong phiên tự động).  
**Môi trường Staging đang chạy sẵn:**
- **Frontend:** `http://127.0.0.1:5176/`
- **Backend API:** `http://127.0.0.1:8003/api` (`EduSuggest_phase4_test`, `35` bảng — revision `e5f6a7b8c9d0`, `MOCK_PAYMENT_ENABLED=True`, `VNPAY_SANDBOX_ENABLED=False`, `FINANCIAL_INTEGRITY_WORKFLOW_ENABLED=True`)
- **Tài khoản mẫu trên `EduSuggest_phase4_test`:**
  - `USER`: `linhphuong123`
  - `PROVIDER`: `tranphuctk`
  - `ADMIN`: `admin`
  - *(Mật khẩu demo nội bộ lưu tại `backend/logs/official-dataset/demo-credentials.json` — không ghi trực tiếp vào tài liệu công khai).*

---

## 1. Luồng Người học (USER)

- [ ] **Trang chủ (`/`) & Header (`UserHeader.vue`):**
  - Biểu tượng Trái tim (Wishlist) và Giỏ hàng (Cart) hiển thị rõ, badge số lượng đồng bộ ngay sau khi F5 reload trang.
  - Dropdown tài khoản có mục *Lịch sử mua hàng* (`/orders`).
- [ ] **Danh mục khóa học (`/courses`) & `CourseCard.vue`:**
  - Khóa học trả phí hiển thị đúng giá VND (`499.000 ₫`), nút Trái tim góc ảnh bìa toggle mượt mà, không tạo bản ghi trùng.
  - Khóa học đã sở hữu hiển thị trạng thái *Đã sở hữu* (không hiển thị nút mua lại).
- [ ] **Chi tiết khóa học (`/courses/:id`) — `CourseDetail.vue`:**
  - Khóa miễn phí (`0 ₫`): chỉ hiện nút *Đăng ký miễn phí*.
  - Khóa trả phí chưa sở hữu: hiện nút *Mua ngay* (Deep Navy `#112233` / Smart Teal `#0D9488`) và *Thêm vào giỏ hàng* + nút Yêu thích.
  - Khóa đã sở hữu (`LEGACY` hoặc đã mua): hiện nút *Vào học ngay*.
- [ ] **Danh sách yêu thích (`/wishlist`):**
  - Hiển thị danh sách đã lưu, nút *Chuyển sang giỏ hàng* di chuyển mục sang giỏ nguyên tử, nút *Xóa* cập nhật badge tức thì.
- [ ] **Giỏ hàng (`/cart`):**
  - Chọn/bỏ chọn khóa học, tổng tiền VND tự động tính lại từ Backend, xóa từng mục hoặc xóa toàn bộ hoạt động chính xác.
- [ ] **Thanh toán (`/checkout` → `/payment/mock/:txnRef` → `/payment/result`):**
  - Trang Checkout hiển thị snapshot giá, thời hạn thanh toán (TTL 15 phút), chọn cổng *Mock Payment Sandbox* (có nhãn rõ là mô phỏng, không thu tiền thật).
  - Trang Mock Payment thử cả 2 kịch bản: (1) *Thanh toán thất bại / Hủy* → đơn giữ `FAILED`/`PENDING`, không cấp quyền học; (2) *Thanh toán thành công* → chuyển sang `PaymentResultView.vue`.
  - Trang `PaymentResultView.vue`: hiển thị trạng thái chính thức lấy từ Backend, có thông điệp trấn an *"Giao dịch của bạn đang được xác minh. Vui lòng không thanh toán lại cho đến khi có kết quả."* khi đang xác minh.
- [ ] **Lịch sử đơn hàng (`/orders`) & Chi tiết đơn hàng (`/orders/:id`):**
  - Hiển thị đầy đủ danh sách đơn hàng, trạng thái, lịch sử lần thử thanh toán.
  - Mở chi tiết đơn hàng → kiểm tra khối **Báo cáo sự cố thanh toán** (tuyệt đối KHÔNG có nút hoàn tiền đổi ý thông thường; có cảnh báo không nhập số thẻ/OTP/mật khẩu). Gửi thử 1 báo cáo sự cố → nhận mã sự cố xác nhận.
- [ ] **Học tập của tôi (`/dashboard`) & Bài học / Tài liệu sau mua:**
  - Khóa học vừa mua xuất hiện ngay trong *Học tập của tôi*; mở vào học bài giảng và tải tài liệu private thành công (`200 OK`).
  - Hệ thống gợi ý (`/recommendations`) hoạt động bình thường, không gợi ý lại khóa vừa mua.

---

## 2. Luồng Quản trị viên (ADMIN — `/admin/commerce`)

- [ ] Truy cập *Quản lý Thương mại* trên `AdminSidebar.vue`.
- [ ] **Tab 1 — Doanh thu & Phân tích:** Hiển thị KPI Doanh thu ghi nhận, Hoàn tiền sự cố, Doanh thu thuần, Tiền thu dư chờ xử lý, Top khóa học, biểu đồ/chuỗi doanh thu theo ngày, nhãn rõ không tính `150` lượt `LEGACY` và chưa bật payout.
- [ ] **Tab 2 — Đơn hàng:** Tìm kiếm theo mã đơn/tên người mua, lọc theo trạng thái (`PAID`, `PENDING`, `FAILED`, `CANCELLED`, `EXPIRED`, `REFUNDED`), phân trang hoạt động mượt.
- [ ] **Tab 3 — Đối soát & Hoàn tiền ngoại lệ:** Hiển thị giao dịch cần đối soát, kiểm tra nút Ưu tiên #1 (*Khôi phục quyền học*) và luồng tạo → xác minh → thực thi hoàn tiền ngoại lệ (`EXCESS_PAYMENT` vs `FULL_ORDER`).
- [ ] **Tab 4 — Báo cáo sự cố:** Hiển thị báo cáo sự cố vừa gửi từ tài khoản `USER` ở mục 1.

---

## 3. Luồng Nhà cung cấp (PROVIDER — `/provider/sales`)

- [ ] Truy cập *Doanh thu khóa học* trên `ProviderSidebar.vue`.
- [ ] Xác minh 4 KPI cốt lõi (Doanh thu ghi nhận, Hoàn tiền sự cố, Doanh thu thuần, Tổng lượt bán) chỉ phản ánh khóa học của chính `tranphuctk` (không lộ dữ liệu của Provider khác, không tính `LEGACY`).
- [ ] Xác minh bảng hiệu quả theo từng khóa học, lịch sử bán hàng và thông báo minh bạch chưa áp dụng chi trả tự động (Payout).

---

## 4. Kiểm tra Responsive & Chất lượng Thiết kế (Design Skills Audit)

Mở Chrome DevTools (`F12` → Toggle Device Toolbar) và kiểm tra tại **5 độ phân giải**:

| Viewport | Kiểm tra bắt buộc | Kết quả |
|---|---|---|
| **375px** (Mobile) | Không tràn ngang (`scrollWidth <= innerWidth`), bảng có cuộn ngang riêng, nút CTA đủ vùng chạm (`>= 44px`). | [ ] |
| **768px** (Tablet) | Bento Grid tự co 1–2 cột cân đối, sidebar thu gọn/chuyển đổi mượt. | [ ] |
| **1024px** (Small Laptop) | Header không xuống dòng gãy bố cục, bảng ADMIN/PROVIDER đọc rõ. | [ ] |
| **1440px** (Desktop) | Tỷ lệ whitespace, căn lề trái/phải đồng đều, hệ màu `#112233` / `#0D9488` / `#D97706` / `#F8FAF9` / `#FFFFFF` nhất quán. | [ ] |
| **1920px** (Wide Desktop) | Container max-width giữ bố cục gọn gàng, không bị kéo giãn quá mức. | [ ] |

- [ ] **Console & Network:** 0 lỗi JavaScript đỏ trong Console, 0 request `500` trong tab Network xuyên suốt 3 vai trò.
- [ ] **Accessibility:** Tab/Shift+Tab qua các nút, form, modal có focus ring rõ ràng; các trạng thái Loading / Empty / Error hiển thị lịch sự, có nút thử lại.
