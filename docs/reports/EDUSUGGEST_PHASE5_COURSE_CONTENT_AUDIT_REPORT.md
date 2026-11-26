# EDUSUGGEST — GĐ5.3: BÁO CÁO KIỂM TOÁN CHẤT LƯỢNG NỘI DUNG 120 KHÓA HỌC & 411 BÀI HỌC

**Ngày kiểm toán:** 2026-11-26  
**Phạm vi:** Kiểm toán toàn diện 120 khóa học, 411 bài học, 243 tài liệu, 8 nhà cung cấp và 21 hồ sơ chuyên gia (READ ONLY trên Production, áp dụng thử nghiệm trên `edusuggest_phase53_staging`).

---

## 1. Kiểm toán 120 khóa học (Nội dung, Thời lượng, Học phí, Cấp độ)

| Tiêu chí | Kết quả kiểm toán thực tế | Đánh giá & Hành động |
| :--- | :--- | :--- |
| **Tên khóa học & trùng lặp** | `119/120` tên rõ ràng, đúng công nghệ; `0` trùng lặp; `1` khóa rác (`#31`) | Đã khôi phục `#31` trên Staging thành *"Kiểm thử API thực chiến với Postman"* (`HIDDEN`/`PENDING`) |
| **Mô tả & khớp danh mục** | `119/120` mô tả khớp danh mục và kỹ năng mục tiêu; `0` placeholder `lorem ipsum` | Không sửa hàng loạt các khóa đã có nội dung tốt và đã có người học |
| **Thời lượng (`KhoaHoc.thoiLuong`)** | `1` khóa (`#29`) có `thoiLuong < SUM(BaiHoc.thoiLuong)` (`180 < 300`); `92` khóa official-v1 có thời lượng ước tính `360–810 phút` (> tổng 3 bài giảng `150–195 phút`) | Đã sửa `#29` → `300 phút` trên Staging; hiển thị tách bạch **"Thời lượng học ước tính"** và **"Tổng bài giảng"** trên `CourseDetail.vue` |
| **Học phí (`KhoaHoc.gia`)** | `23` khóa miễn phí (`0 ₫`), `97` khóa trả phí (`199,000 – 899,000 ₫`, TB `493,845 ₫`); **`0` khóa học phí >= 700,000 ₫ có <= 3 bài học** | Học phí hiện tại hợp lý, không có giảm giá giả; giữ nguyên 100% trên Production (chỉ đề xuất `#31` mới = `399,000 ₫` cho 10 bài thực hành) |
| **Cấp độ (`trinhDo`)** | Trộn lẫn Việt (`Cơ bản: 9`, `Trung cấp: 10`, `Nâng cao: 8`) và Anh (`BEGINNER: 24`, `INTERMEDIATE: 36`, `ADVANCED: 16`, `ALL_LEVELS: 16`) + `NULL: 1` (`#31`) | Chuẩn hóa hiển thị thống nhất tiếng Việt tại Frontend (`courseDisplay.js`), không làm thay đổi TF-IDF |
| **Ảnh bìa (`hinhAnh`)** | `120/120` ảnh WebP `1280×720` thực tế đã triển khai ở GĐ5.2 (`HTTP 200`, `image/webp`) | Bổ sung ảnh bìa mới riêng cho `#31` trên Staging khớp chủ đề API Testing |

---

## 2. Kiểm toán chất lượng nội dung 411 bài học

- **Phân loại theo nội dung thực tế:**
  - **Video Lecture (`135` bài, 27 khóa legacy):** Có `duongDanVideo` và mô tả bài giảng; có `15` bài có phần văn bản `noiDung < 120 ký tự` cần bổ sung tóm tắt mục tiêu học tập.
  - **Bài đọc / Lý thuyết (`78` bài) & Thực hành (`99` bài) & Kiểm tra (`84` bài) & Dự án (`15` bài) — thuộc 92 khóa `edusuggest-official-v1`:** Độ dài trung bình **`539.3 ký tự/bài`**, có cấu trúc rõ theo 3 chặng (*Nền tảng và thiết lập → Thực hành có hướng dẫn → Bài toán tích hợp và đánh giá*), không có văn bản rác/placeholder, nhưng cấu trúc câu giữa các khóa cùng danh mục còn mang tính khuôn mẫu và chưa có câu hỏi kiểm tra/tiêu chí chấm chi tiết.

---

## 3. Kiểm toán 243 tài liệu & Data Provenance

- **Phân loại 3 nhóm nguồn gốc dữ liệu (Data Provenance):**
  1. **Nguồn tham khảo thực tế (`121` URL ngoài):** MDN Web Docs, PostgreSQL, Python, FastAPI, React, Vue, AWS, OWASP, Atlassian (`114/121` `HTTP 200`, `5` MySQL `403` bot-filter, `2` link chết `#98`/`#110` đã sửa trên Staging).
  2. **Nội dung do EduSuggest biên soạn (`120` khóa học, `411` bài học + `10` bài mới khóa `#31`, `121` tệp `private://` với `532` tệp vật lý trong `backend/private_storage/`).**
  3. **Dữ liệu mô phỏng phục vụ nghiên cứu & trình diễn (`79` tài khoản, `8` nhà cung cấp, `21` bản ghi `ChuyenGia`, `20` đánh giá, `150` đăng ký `LEGACY ACTIVE`, `300` lịch sử học tập, `8` Persona TF-IDF).** Không trình bày dữ liệu mô phỏng là người dùng/giao dịch thật, không giả mạo đối tác thương mại.
