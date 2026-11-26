# EDUSUGGEST – GĐ6.2: COMPREHENSIVE UI/UX POLISH REPORT (`ISSUE-001`, `ISSUE-003`, `ISSUE-006`)

- **Ngày thực hiện:** 2026-11-27
- **Design Skills áp dụng thực tế:** `emil-design-eng`, `impeccable`, `design-taste-frontend`

## 1. Các nguyên tắc Design Skills đã áp dụng cụ thể

1. **`impeccable` (Responsive Geometry & Anti-Overflow):**
   - Áp dụng `min-w-0` chuẩn mực trên mọi grid track (`lg:grid-cols-[minmax(0,1fr)_360px]`, `<main>`, `<aside>`, `<form>`, `<label>`) thay vì dùng hack `overflow-x: hidden`.
   - Thu gọn typography Hero theo breakpoint (`text-[1.75rem] sm:text-4xl lg:text-[2.75rem]`) và tối ưu padding 3 ô KPI (`p-2.5 sm:p-3`) để vừa vặn tuyệt đối từ `320px` đến `1920px`.
2. **`design-taste-frontend` (Visual Hierarchy & Clean Photography):**
   - Loại bỏ hoàn toàn badge nổi che chữ góc trên trái trên ảnh bìa WebP 1280×720 (`CourseCard.vue`); chuẩn hóa tỷ lệ khung ảnh `aspect-video` (16:9) khớp ảnh gốc không cắt xén dọc.
   - Chuyển pill Danh mục và Trình độ vào phần thân thẻ trắng phía trên tiêu đề, giữ ảnh bìa sạch sẽ như một nền tảng EdTech chuyên nghiệp.
3. **`emil-design-eng` (Tactile Polish & Micro-Interactions):**
   - Khôi phục **Header 2 tầng** gọn nhẹ (`UserHeader.vue`): tầng 1 giữ nguyên điều hướng + Wishlist/Cart/Bell/Avatar; tầng 2 hiển thị thanh tìm kiếm toàn cục (`Khóa học` / `Tài liệu`) trên mọi trang con và tự ẩn trên Trang chủ (tránh trùng lặp với Hero Search) và Checkout/Auth.
   - Giữ `active:scale-[0.97]`, `tabular-nums`, và định dạng thời lượng nhất quán (`formatDurationMinutes`) trên cả Card lẫn Đề cương chi tiết.

## 2. Danh sách hạng mục UI/UX đã hoàn thiện

| Issue | Tệp nguồn | Thay đổi chính | Kết quả kiểm chứng |
|---|---|---|---|
| `ISSUE-001` (P2) | `UserHome.vue`, `CourseDetail.vue` | `min-w-0`, responsive Hero H1, compact 3-col KPI, `minmax(0,1fr)` grid | **0px overflow** trên toàn bộ 7 viewport (`320–1920px`) |
| `ISSUE-003` (P2) | `CourseCard.vue` | Khung `aspect-video` 16:9, bỏ overlay badge góc trên trái, đưa badge vào thân thẻ | **6/6** ảnh bìa sạch, không đè chữ |
| `ISSUE-006` (P2) | `UserHeader.vue` | Tầng 2 compact global search cho trang con, ẩn trên Home/Checkout/Auth | Search `/courses?q=Python` hoạt động 100%, 0px overflow |
| Polish bổ sung | `CourseDetail.vue` | Định dạng thời lượng bài giảng (`60 phút`, `90 phút` thay vì số trần) | Đề cương rõ ràng, đồng nhất ngôn ngữ |

## 3. Kiểm chứng Build Production Frontend

- Lệnh: `.\node_modules\.bin\vite.cmd build --outDir dist-phase62-check` (và dọn thư mục tạm).
- Kết quả: **`✓ 1912 modules transformed. ✓ built in 1.57s` — 0 lỗi, 0 cảnh báo chặn.**
