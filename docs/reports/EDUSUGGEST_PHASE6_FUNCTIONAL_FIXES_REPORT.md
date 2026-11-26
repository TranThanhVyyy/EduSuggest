# EDUSUGGEST – GĐ6.2: FUNCTIONAL FIXES REPORT (`ISSUE-002`, `ISSUE-004`, `ISSUE-005`, `ISSUE-007`)

- **Ngày thực hiện:** 2026-11-27
- **Môi trường kiểm chứng:** Staging `edusuggest_phase62_staging` (`8004`/`5177`) & Test DB `EduSuggest_phase4_test`

## 1. `ISSUE-002` (P1) – Chi tiết khóa học công khai (`GET /api/courses/{id}` & `CourseDetail.vue`)

### Nguyên nhân
- Khi khách chưa đăng nhập hoặc học viên chưa ghi danh truy cập `/courses/{id}`, Backend trả `baiHocs = []` để bảo vệ nội dung bài học trả phí, nhưng không trả tổng số bài giảng (`soLuongBaiHoc`), tên nhà cung cấp (`tenNhaCungCap`), hay đề cương công khai (`deCuongCongKhai`).
- Frontend (`userApiService.js` & `CourseDetail.vue`) hiển thị sai thành **"0 bài giảng"** và **"Thông tin nhà cung cấp chưa được cập..."**.

### Khắc phục
- **Backend (`backend/schemas/workflow.py`, `backend/api/workflows.py`):**
  - Thêm schema `PublicSyllabusLessonResponse` (`maBaiHoc`, `tieuDe`, `thuTu`, `thoiLuong` — tuyệt đối không chứa `noiDung`, `duongDanVideo`, hay `taiLieus`).
  - Bổ sung `tenNhaCungCap`, `soLuongBaiHoc`, `deCuongCongKhai` vào `CourseDetailResponse`.
  - Trong `_course_detail()`: join `course.nhaCungCap.nguoiDung.hoTen`, đếm chính xác `len(ordered_lessons)`, và chỉ trả `baiHocs = []` khi `include_learning_content=False`.
- **Frontend (`frontend/src/service/userApiService.js`, `frontend/src/views/user/CourseDetail.vue`):**
  - Map `provider`, `lessonCount`, `publicSyllabus`.
  - Hiển thị chính xác tên nhà cung cấp (vd: **Học viện Phần mềm FPT**), số lượng bài giảng (**5 bài giảng**), tổng thời lượng bài giảng (**480 phút**), và danh sách đề cương công khai có nhãn **Khóa** + định dạng thời lượng `formatDurationMinutes(lesson.duration)`.

### Kiểm chứng bảo mật & chức năng
- **Playwright E2E trên `/courses/6` (khách):** `has_zero_lessons_bug = false`, `has_provider_fallback_bug = false`, `has_locked_syllabus_items = true`.
- **Pytest (`test_public_course_detail_exposes_provider_count_and_locked_syllabus_without_leaking_content`):** PASS — xác nhận `baiHocs == []`, 0 rò rỉ nội dung bài học hoặc đường dẫn video.

## 2. `ISSUE-004` (P2) – Khóa học nháp `#27`

- Kiểm toán dữ liệu thực tế cho thấy khóa `#27` (*"Bí quyết Lập trình Web Full-Stack Nâng cao (Khóa học đang biên soạn)"*) chứa mô tả và bài học ghi rõ *"đang trong giai đoạn hoàn thiện giáo trình nội bộ / Bản nháp"*, vô tình bị đặt `trangThaiHienThi = 'VISIBLE'`.
- **Xử lý trên staging ONLY (`edusuggest_phase62_staging`):** cập nhật `trangThaiHienThi = 'HIDDEN'` cho `#27`.
- **Kiểm chứng:**
  - `GET /courses/27` trên staging trả lỗi không tìm thấy (`blocked_or_not_found = true`).
  - `recommend_courses` trên staging tự động loại bỏ `#27` nhờ cơ chế fingerprint (`course_27_hidden_on_staging = true`).
  - **Production `EduSuggest` KHÔNG bị thay đổi** (chờ phê duyệt GĐ6.3).

## 3. `ISSUE-005` (P2) – Đánh giá truy vấn `KhoaHoc` (`EXPLAIN ANALYZE`)

- Chạy `EXPLAIN (ANALYZE, BUFFERS)` cho truy vấn danh sách khóa học công khai trên `KhoaHoc`:
  - Thời gian thực thi: **`0.097 ms`**, `shared hit = 21`, trả về `101/120` dòng (độ chọn lọc `84%`).
- **Kết luận kỹ thuật:** PostgreSQL Planner chọn `Seq Scan` là **tối ưu** ở quy mô 120 dòng với độ chọn lọc 84%. Không tạo index hoặc migration mới trong GĐ6.2; giữ nguyên schema 35 bảng (`e5f6a7b8c9d0`).

## 4. `ISSUE-007` (P2) – Nội dung chưa duyệt `#31` & `#132`

- Xác nhận khóa học `#31` (*Kiểm thử API thực chiến với Postman*) và tài liệu `#132` (`hi`/`gsdfsd`) tiếp tục giữ nguyên trạng thái `PENDING / HIDDEN`.
- Kiểm chứng rò rỉ công khai: **0 rò rỉ** trên Catalog, Detail và Recommendation.
