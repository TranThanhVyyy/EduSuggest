# EDUSUGGEST — GĐ6.1: LỘ TRÌNH TRIỂN KHAI GĐ6.2 – GĐ6.7 (ĐỀ XUẤT CHỜ PHÊ DUYỆT)

Dựa hoàn toàn trên **9 vấn đề thực tế** đã đo đạc và tái hiện ở GĐ6.1 (không phát minh hạng mục thừa):

| Giai đoạn | Trọng tâm thực hiện | Giải quyết Issue ID |
| :--- | :--- | :--- |
| **GĐ6.2 — P1/P2 Functional & UI Polish (Staging → Prod)** | Sửa public `GET /api/courses/{id}` trả đúng `soLuongBaiHoc` & `tenNhaCungCap`; sửa tràn ngang `375px` trên `UserHome.vue`; di chuyển badge `CourseCard.vue` khỏi vùng ảnh bìa WebP; làm sạch tiêu đề khóa `#27`; xác nhận thiết kế Header 1 tầng/2 tầng; cài Playwright chạy E2E 4 vai trò + xác minh phát video YouTube iframe thực tế | `ISSUE-001`, `ISSUE-002`, `ISSUE-003`, `ISSUE-004`, `ISSUE-006`, `ISSUE-008` |
| **GĐ6.3 — Scientific Recommendation Evaluation** | Chạy thực nghiệm Holdout + Domain Ground Truth cho 8 Official Personas, tính đầy đủ `Precision@K`, `Recall@K`, `Hit Rate@K`, `NDCG@K`, `Coverage`, `Diversity` (`K=5, 10`) không rò rỉ dữ liệu | Kế hoạch đánh giá khoa học |
| **GĐ6.4 — Content Review Workflow Acceptance** | Đưa khóa `#31` (*Kiểm thử API thực chiến với Postman*) đi qua luồng kiểm duyệt EXPERT → ADMIN hợp lệ trên giao diện; xử lý lưu trữ/ẩn tài liệu `#132` theo phê duyệt | `ISSUE-007` |
| **GĐ6.5 — Security & Operational Hardening** | Bổ sung middleware rate-limit thống nhất theo IP cho auth/search và kiểm toán log bảo mật | Security P3 |
| **GĐ6.6 — Performance Optimization (P1 Recommendation Latency)** | Loại bỏ N+1 query + thêm in-memory versioned TF-IDF corpus cache giảm `recommend_courses` từ **`15.23s` → `< 150 ms`** (giữ nguyên 100% công thức TF-IDF); bổ sung composite index cho `KhoaHoc` catalog | `ISSUE-009`, `ISSUE-005` |
| **GĐ6.7 — Final Production Acceptance & Defense Package** | Nghiệm thu tổng thể cuối cùng (`269+` tests PASS, Playwright E2E PASS, hiệu năng `< 150 ms`), đóng gói hồ sơ bảo vệ đồ án hoàn chỉnh | Tổng nghiệm thu |
