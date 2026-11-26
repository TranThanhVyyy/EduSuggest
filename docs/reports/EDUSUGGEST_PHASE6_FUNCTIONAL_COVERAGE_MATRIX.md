# EDUSUGGEST — GĐ6.1: MA TRẬN PHỦ CHỨC NĂNG 4 VAI TRÒ & LIÊN VAI TRÒ

**Tổng cộng:** `74` hạng mục chức năng (`64` PASS · `2` FAIL · `8` PARTIAL / NOT TESTED).

| Nhóm / Vai trò | Chức năng kiểm toán | Trạng thái | Bằng chứng / Ghi chú |
|---|---|---|---|
| **USER (25)** | Đăng ký, Đăng nhập, Đăng xuất, JWT Revocation, Argon2id | **PASS** | `269/269` Backend tests + `login-1440.png` |
| USER | Hồ sơ cá nhân, Đổi mật khẩu, Sở thích học tập | **PASS** | `UserProfile.vue`, `api/users.py`, regression PASS |
| USER | Trang chủ, Danh mục, Tìm kiếm, Lọc, Sắp xếp | **PARTIAL** | Desktop `1440px`/`768px` PASS; **Mobile `375px` tràn ngang (`ISSUE-001`)** |
| USER | Chi tiết khóa học (`CourseDetail.vue`) | **FAIL** | Khách chưa đăng nhập thấy **`0 bài giảng`** & **`Thông tin nhà cung cấp chưa được cập...`** (`ISSUE-002`) |
| USER | Chi tiết tài liệu (`MaterialDetail.vue`, `MaterialCatalog.vue`) | **PASS** | `materials-1440.png` hiển thị `226` tài liệu công khai sắc nét |
| USER | Recommendation Khóa học & Tài liệu + Cold-start | **FAIL (Hiệu năng)** | Chính xác chiến lược `7 content_based + 1 latest`, `0` rò rỉ `HIDDEN`; **nhưng độ trễ `p50 = 15.23s` (`ISSUE-009`)** |
| USER | Wishlist, Cart, Mua ngay, Checkout, Order History, Incident Report | **PASS** | Đã kích hoạt GĐ4.7C (`5173`/`8000`) & kiểm thử đầy đủ trên `5176`/`8003` (`49/49` Marketplace tests PASS) |
| USER | COM-01 Enrollment Gate (chặn đăng ký free khóa có phí) & Bảo toàn `150 LEGACY` | **PASS** | `COMMERCE_ENROLLMENT_GATE_ENABLED=True` LIVE trên `8000` |
| USER | `LearningView` (Video allowlist, Đọc, Thực hành, Kiểm tra, Dự án, Tiến độ, Lịch sử, Tài liệu) | **PARTIAL** | Allowlist `youtube-nocookie.com` + anti-XSS PASS (`test_phase55`); **Phát video thực tế trên trình duyệt: `NOT TESTED` (`ISSUE-008`)** |
| USER | Thông báo & Đánh giá | **PASS** | `UserHeader.vue`, `api/availability_notifications.py` |
| **ADMIN (18)** | Dashboard KPI, Quản lý User/Role/Category/Course/Material/Provider/Expert/Specialty | **PASS** | `AdminDashboard.vue`, `AdminManagementView.vue`, `AdminSpecialtiesView.vue`, KPI đối chiếu DB thật |
| ADMIN | Xác minh chuyên gia, Kiểm duyệt, Phân công, Accountability, Thông báo | **PASS** | `217/217` Core & GĐ3 tests PASS |
| ADMIN | Commerce Overview, Revenue, Orders, Transactions, Reconciliation, Exception Refund, Incidents | **PASS** | `AdminCommerceView.vue`, `api/commerce_admin.py` — chặn cứng tự đánh dấu `PAID`/`REFUNDED` không bằng chứng |
| **PROVIDER (13)** | Dashboard, Hồ sơ NCC, Tạo/Sửa khóa học, Upload ảnh bìa, Quản lý bài học/tài liệu/private files | **PASS** | `ProviderCourseEditor.vue`, `ProviderAssetManager.vue`, `ProviderMaterialsView.vue` |
| PROVIDER | Học phí, Gửi kiểm duyệt, Chỉnh sửa nội dung bị từ chối, Thống kê doanh thu & bán hàng | **PASS** | `ProviderSalesView.vue`, ownership & cross-provider IDOR PASS (`test_phase46`) |
| **EXPERT (13)** | Dashboard, Hồ sơ, Chuyên môn chính/phụ, Nhận/Từ chối nhiệm vụ, Kiểm duyệt khóa & tài liệu | **PASS** | `ReviewerDashboard.vue`, `ReviewerAssignmentsView.vue`, `ReviewDetailView.vue` |
| EXPERT | Durable Queue, Lease, Fencing token, Stale lease recovery, Concurrency (Staging) | **PASS** | `test_phase33`, `test_phase383`, Real OS Worker Acceptance PASS; tắt trên Production |
| **CROSS-ROLE (5)** | Cung cấp khóa học, Cung cấp tài liệu, Phân công chuyên gia, Marketplace Mock (`8003`), Sự cố thanh toán & Hoàn tiền ngoại lệ | **PASS (API/Backend)** · **NOT TESTED (Interactive Browser)** | 100% Backend/API/Stress tests PASS (`269/269`); interactive browser click-through chờ Playwright ở GĐ6.2 (`ISSUE-008`) |


---

## Cập nhật Nghiệm thu GĐ6.2 (2026-11-27 – Staging `5177`/`8004`)

- **2 lỗi P1 đã khắc phục & kiểm chứng 100% trên Staging:**
  - `ISSUE-009`: `recommend_courses` warm `p50 = 113.31 ms` (`p95 = 166.68 ms`, cold `584.02 ms`, **134.4× nhanh hơn**), `16/16` (100%) Exact Equivalence trên 8 Official Personas.
  - `ISSUE-002`: Public `GET /api/courses/{id}` & `CourseDetail.vue` hiển thị đúng `tenNhaCungCap`, `soLuongBaiHoc` (`5 bài giảng`), `deCuongCongKhai` khóa, `0` rò rỉ nội dung trả phí/video.
- **8 hạng mục `PARTIAL/NOT TESTED` ở GĐ6.1 đã được kiểm thử tương tác trực tiếp bằng Playwright E2E:**
  - USER (`/dashboard`, `/wishlist`, `/cart`, `/learning/6` với YouTube embed `804×451`), ADMIN (`/admin/dashboard`), PROVIDER (`/provider/dashboard`), EXPERT (`/reviewer/dashboard`), Header 2 tầng search interaction, và **21/21** multi-viewport checks (`320–1920px`) đạt **`0px` horizontal overflow**, `0` page errors.
