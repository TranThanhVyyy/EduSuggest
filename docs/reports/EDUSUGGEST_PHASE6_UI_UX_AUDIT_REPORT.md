# EDUSUGGEST — GĐ6.1: BÁO CÁO KIỂM TOÁN UI/UX & DESIGN SYSTEM

**Ngày kiểm toán:** 2026-11-27  
**Phương pháp:** Áp dụng trực tiếp 3 Design Skills (`emil-design-eng`, `impeccable`, `design-taste-frontend`) kết hợp kiểm tra trực quan **`7` ảnh chụp Chrome thật** (`smoke-1440.png`, `courses-1440.png`, `course-detail-1440.png`, `materials-1440.png`, `login-1440.png`, `home-768.png`, `home-375.png`) tại `media/phase6-audit/screenshots/`.

---

## 1. Áp dụng thực tế 3 Design Skills

| Skill | Hướng dẫn đã áp dụng vào kiểm toán | Kết quả phát hiện thực tế |
| :--- | :--- | :--- |
| **`emil-design-eng`** | Micro-interactions (`:active scale(0.97)`), custom `--ease-out`, trạng thái loading/empty/error trung thực, không animation thừa | Các nút, popover và card tuân thủ tốt; phát hiện trạng thái sai sự thật `0 bài giảng` trên `CourseDetail` cho khách chưa đăng nhập (`ISSUE-002`) |
| **`impeccable`** | Verify ở kích thước thực tế (`375px`, `768px`, `1440px`), hierarchy rõ ràng, không tràn chữ, không che khuất nội dung | Phát hiện lỗi tràn ngang trên mobile `375px` tại `UserHome.vue` (`ISSUE-001`) và badge nổi đè góc trên trái ảnh bìa WebP tại `CourseCard.vue` (`ISSUE-003`) |
| **`design-taste-frontend`** | Ảnh chụp thực tế sắc nét, 1 hệ thống màu nhất quán (Deep Navy `#112233`, Smart Teal `#0D9488`, Amber `#D97706`, Canvas `#F8FAF9`, Surface `#FFFFFF`), copy trung thực không nhãn thừa | Hệ màu & Bento Grid trên `1440px`/`768px` đạt chuẩn rất cao; phát hiện khóa `#27` công khai vẫn mang chuỗi `"(Khóa học đang biên soạn)"` (`ISSUE-004`) |

---

## 2. Danh sách màn hình & điểm cần cải thiện ở GĐ6.2 (Before / After — chuẩn `emil-design-eng`)

| Màn hình | Before (Thực tế đo trên Chrome) | After (Đề xuất GĐ6.2) | Why |
|---|---|---|---|
| `UserHome.vue` (`375px`) | Hero H1, thanh search và khối KPI 3 cột tràn qua mép phải viewport `375px` (`home-375.png`) | Thêm `min-w-0`, `overflow-x-hidden`, responsive `text-3xl sm:text-5xl`, `flex-wrap` cho cụm CTA & KPI grid `grid-cols-3` gọn padding | Loại bỏ thanh cuộn ngang trên thiết bị di động `375px` |
| `CourseCard.vue` (`1440px`) | Badge `Danh mục` + `Trình độ` đặt `absolute left-3 top-3` đè trực tiếp lên phần pill/tiêu đề góc trái của ảnh bìa WebP mới (`courses-1440.png`) | Di chuyển badge `Danh mục` + `Trình độ` xuống phần thân trắng phía trên tiêu đề thẻ; chỉ giữ nút Heart góc phải trên ảnh | Ảnh bìa WebP `1280×720` hiển thị thoáng, không bị 2 lớp chữ chồng nhau |
| `CourseDetail.vue` (`1440px`) | Khách chưa đăng nhập thấy `0 bài giảng` và `Thông tin nhà cung cấp chưa được cập...` dù khóa `#6` có 5 bài giảng (`course-detail-1440.png`) | Trả `soLuongBaiHoc` và `tenNhaCungCap` (join `NhaCungCapKhoaHoc → NguoiDung.hoTen`) ngay ở public `GET /api/courses/{id}` | Đảm bảo thông tin chính xác trước khi người học quyết định mua/đăng ký |
| `UserHeader.vue` | Hiện đang là Header 1 tầng (đã bỏ tầng tìm kiếm thứ 2 theo yêu cầu trực tiếp trước đó của người dùng) | Xác nhận với người dùng ở GĐ6.2: giữ Header 1 tầng gọn như hiện tại hay khôi phục Header 2 tầng | Tôn trọng quyết định giao diện của người dùng |
