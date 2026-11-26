# EDUSUGGEST — GĐ4.7C: BÁO CÁO KÍCH HOẠT CHÍNH THỨC MARKETPLACE

**Ngày thực hiện:** 2026-11-26  
**Phạm vi:** Kích hoạt toàn bộ giao diện & API Marketplace trên hệ thống chính thức `http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api` (Database `EduSuggest`, 35 bảng, revision `e5f6a7b8c9d0`), đồng thời bật `COMMERCE_ENROLLMENT_GATE_ENABLED=True` để khắc phục **COM-01** và giữ **TẮT** toàn bộ cổng thanh toán (`MOCK_PAYMENT_ENABLED=False`, `VNPAY_SANDBOX_ENABLED=False`) cùng các worker tài chính/tự động phân công.

---

## 1. Kết quả kiểm toán Feature Flags, Capabilities, Router & Giao diện

### 1.1. Tách bạch trạng thái Marketplace và Cổng thanh toán
- Endpoint `GET /api/commerce/capabilities` (`backend/service/order_payment_service.py`) đã tách rõ:
  - `marketplaceEnabled` & `enrollmentGateEnabled`: phụ thuộc `COMMERCE_ENROLLMENT_GATE_ENABLED`.
  - `mockPaymentEnabled`: phụ thuộc `MOCK_PAYMENT_ENABLED` **và** chặn cứng khi `APP_ENV == "production"` hoặc database khác allowlist `EduSuggest_phase4_test`.
  - `vnpaySandboxEnabled`: phụ thuộc `VNPAY_SANDBOX_ENABLED` + đủ cấu hình credentials + chặn cứng trên `EduSuggest`.
- Vì vậy, kích hoạt `COMMERCE_ENROLLMENT_GATE_ENABLED=True` trên Production `8000` bật toàn bộ Marketplace UI/API và khóa cổng đăng ký trực tiếp khóa học trả phí (**COM-01**), trong khi **không** mở bất kỳ cổng thanh toán giả lập hoặc sandbox nào.

### 1.2. Bản đồ điều kiện hiển thị Frontend đã kiểm toán
| Thành phần / Màn hình | Tệp nguồn | Điều kiện hiển thị | Trạng thái trên `5173` chính thức |
| :--- | :--- | :--- | :--- |
| Icon Yêu thích & Giỏ hàng + badge, Lịch sử mua hàng trên Header | `frontend/src/components/user/UserHeader.vue` | `isAuthenticated && isLearner && commerceState.marketplaceEnabled` | **ĐANG HOẠT ĐỘNG** |
| Icon Yêu thích trên `CourseCard` | `frontend/src/components/user/CourseCard.vue` | `USER && commerceState.marketplaceEnabled` | **ĐANG HOẠT ĐỘNG** |
| CTA Mua ngay / Thêm vào giỏ / Yêu thích trên `CourseDetail` | `frontend/src/views/user/CourseDetail.vue` | `commerceState.marketplaceEnabled && isLearner` | **ĐANG HOẠT ĐỘNG** |
| Danh sách yêu thích (`/wishlist`) & Giỏ hàng (`/cart`) | `frontend/src/router/index.js` | Role `USER` | **ĐANG HOẠT ĐỘNG** |
| Checkout (`/checkout`) | `frontend/src/views/user/CheckoutView.vue` | Role `USER`, phương thức thanh toán đọc từ `mockPaymentEnabled` / `vnpaySandboxEnabled` | **ĐANG HOẠT ĐỘNG (khóa nút thanh toán khi chưa mở cổng)** |
| Lịch sử mua hàng (`/orders`), Chi tiết đơn (`/orders/:id`) & Báo cáo sự cố thanh toán | `OrderHistoryView.vue`, `OrderDetailView.vue` | Role `USER`; nút thanh toán mô phỏng ẩn khi `mockPaymentEnabled=false` | **ĐANG HOẠT ĐỘNG** |
| ADMIN Thương mại & Doanh thu (`/admin/commerce`) | `AdminSidebar.vue`, `AdminCommerceView.vue` | Role `ADMIN` | **ĐANG HOẠT ĐỘNG** |
| PROVIDER Doanh thu & Bán hàng (`/provider/sales`) | `ProviderSidebar.vue`, `ProviderSalesView.vue` | Role `PROVIDER` | **ĐANG HOẠT ĐỘNG** |

---

## 2. Gia cố giao diện Checkout khi chưa kích hoạt cổng thanh toán

Cập nhật `frontend/src/views/user/CheckoutView.vue`:
1. **Chặn khởi tạo đơn mồ côi (`PENDING`):** Bổ sung điều kiện `!hasAvailablePaymentMethod.value || !paymentMethod.value` vào đầu hàm `handleConfirmAndPay()`, kết hợp khóa `:disabled` trên nút xác nhận để người dùng không bao giờ tạo đơn không thể thanh toán trên hệ thống chính thức.
2. **Thông báo rõ ràng chuẩn Production:** Khi chưa có cổng thanh toán trực tuyến được kích hoạt (`!hasAvailablePaymentMethod`), hiển thị hộp thông báo trạng thái rõ ràng giải thích hệ thống chính thức chưa mở cổng thanh toán trực tuyến và gợi ý người dùng tiếp tục lưu khóa học vào Danh sách yêu thích hoặc Giỏ hàng; nhãn nút chuyển thành **`Chưa mở cổng thanh toán`**.

---

## 3. Trạng thái kích hoạt hệ thống chính thức & môi trường Staging

### 3.1. Cấu hình Runtime Production (`127.0.0.1:8000` ↔ `127.0.0.1:5173`)
Khởi động lại Production Backend trên cổng `8000` (không sửa `.env`, không tạo migration mới, không sửa Recommendation Engine):
- `APP_ENV=production`, `DEBUG=False`
- `COMMERCE_ENROLLMENT_GATE_ENABLED=True` (**BẬT** — đóng **COM-01** trên hệ thống chính thức)
- `MOCK_PAYMENT_ENABLED=False` (**TẮT**)
- `VNPAY_SANDBOX_ENABLED=False` (**TẮT**)
- `FINANCIAL_INTEGRITY_WORKFLOW_ENABLED=False` (**TẮT**)
- `PAYMENT_RECONCILIATION_WORKER_ENABLED=False` (**TẮT**)
- `PAYMENT_AUTO_GATEWAY_QUERY_ENABLED=False` (**TẮT**)
- `PAYMENT_AUTO_RESTORE_ENABLED=False` (**TẮT**)
- `AUTO_ASSIGNMENT_WORKFLOW_ENABLED=False`, `AUTO_ASSIGNMENT_WORKER_ENABLED=False`, `ACCOUNTABILITY_ENABLED=False` (**TẮT**)

### 3.2. Kết quả kiểm chứng Live Endpoints
| Môi trường | URL | Kết quả thực tế |
| :--- | :--- | :--- |
| Production Backend Health | `http://127.0.0.1:8000/api/health` | `200 OK` (`database: connected`) |
| Production Capabilities | `http://127.0.0.1:8000/api/commerce/capabilities` | `200 OK` → `marketplaceEnabled: true`, `enrollmentGateEnabled: true`, `mockPaymentEnabled: false`, `vnpaySandboxEnabled: false`, `orderTtlMinutes: 15` |
| Production Frontend | `http://127.0.0.1:5173/` | `200 OK` |
| Marketplace Staging Backend | `http://127.0.0.1:8003/api/commerce/capabilities` | `200 OK` → `marketplaceEnabled: true`, `mockPaymentEnabled: true`, `vnpaySandboxEnabled: false` |
| Marketplace Staging Frontend | `http://127.0.0.1:5176/` | `200 OK` |
| Dataset Staging | `http://127.0.0.1:8002/api/health` & `http://127.0.0.1:5175/` | `200 OK` |

---

## 4. Kiểm chứng toàn vẹn dữ liệu Production & Kiểm thử hồi quy

### 4.1. Bảo toàn dữ liệu Production `EduSuggest` (`edusuggest-official-v1`)
- **Database:** `EduSuggest` | **Revision:** `e5f6a7b8c9d0` | **Số bảng:** `35` | **Startup Schema Guard:** `PASS`
- **Thống kê thực tế sau kích hoạt:**
  - `24` danh mục
  - `120` khóa học (`97` khóa có phí, `23` khóa miễn phí)
  - `411` bài học, `243` tài liệu, `78` tài khoản
  - **`150/150` lượt đăng ký `LEGACY ACTIVE`** được bảo toàn nguyên vẹn 100%
  - **`300` bản ghi lịch sử học tập** được bảo toàn nguyên vẹn 100%
  - **`120/120` ảnh bìa khóa học** trả `HTTP 200` (`bad=0`)
  - **`0` đơn hàng / giao dịch / báo cáo sự cố giả**

### 4.2. Build & Regression Verification
- **Frontend Vite Production Build** (`vite build --outDir dist-phase47c-check`, dọn sạch sau build): **PASS** (`1,911 modules transformed`, `3.58s`, exit code `0`).
- **Full Backend Regression (`EDUSUGGEST_TEST_DB_NAME=EduSuggest_phase4_test`):** **`266 passed, 0 failed, 0 skipped` (`92.04s`)** — bao gồm đầy đủ kiểm thử **COM-01** (chặn đăng ký trực tiếp khóa học trả phí bằng `HTTP 402`), kiểm thử an toàn cổng thanh toán, hoàn tiền ngoại lệ, tài chính bền vững và toàn bộ hồi quy Core/GĐ3.
- **Lưu ý trình duyệt tự động:** Chrome DevTools MCP trong phiên vẫn chưa kết nối được (`DevToolsActivePort ENOENT`), nên không tuyên bố Browser E2E tự động PASS; người dùng có thể mở trực tiếp `http://127.0.0.1:5173/` để trải nghiệm các tính năng Marketplace chính thức (và `http://127.0.0.1:5176/` khi cần kiểm thử luồng Mock Payment Sandbox).
