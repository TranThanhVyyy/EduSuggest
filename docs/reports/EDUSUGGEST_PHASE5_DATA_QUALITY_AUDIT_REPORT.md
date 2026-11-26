# EDUSUGGEST — GĐ5.1: BÁO CÁO KIỂM TOÁN CHẤT LƯỢNG DỮ LIỆU TOÀN DỰ ÁN

**Ngày kiểm toán:** 2026-11-26  
**Chế độ kiểm toán:** **100% READ ONLY** trên Production `EduSuggest` (35 bảng, revision `e5f6a7b8c9d0`, dataset `edusuggest-official-v1`). Không chỉnh sửa giá, tên, nội dung, tài khoản, lượt đăng ký hay lịch sử học tập.

---

## 1. Phân loại nguồn gốc dữ liệu hiện có

| Nhóm dữ liệu | Phạm vi bảng / bản ghi | Phân loại nguồn gốc |
| :--- | :--- | :--- |
| Tài liệu tham khảo bên ngoài (`121` URL tài liệu) | `TaiLieu` (`https://...` từ MDN, PostgreSQL, Python, FastAPI, React, AWS, OWASP, v.v.) | **Dữ liệu thu thập từ nguồn thực tế** |
| Danh mục (`24`), Khóa học (`120`), Bài học (`411`), Tài liệu nội bộ (`121` tệp `private://`), Chuyên môn (`26`) | `DanhMuc`, `KhoaHoc`, `BaiHoc`, `TaiLieu`, `ChuyenGiaChuyenMon` | **Nội dung do dự án biên soạn (`edusuggest-official-v1` + 28 khóa legacy)** |
| Tài khoản (`79`: 1 ADMIN, 8 PROVIDER, 20 EXPERT, 50 USER), Đánh giá chuyên gia (`20`), Đăng ký (`150` LEGACY ACTIVE), Lịch sử học tập (`300`), 8 Persona Recommendation | `NguoiDung`, `NhaCungCapKhoaHoc`, `DanhGiaChuyenGia`, `DangKyKhoaHoc`, `LichSuHocTap` | **Dữ liệu mô phỏng phục vụ nghiên cứu, đánh giá TF-IDF và trình diễn** |

---

## 2. Kết quả kiểm toán toàn vẹn & chất lượng

### 2.1. Các hạng mục ĐẠT CHUẨN (0 lỗi)
- **Trùng lặp tiêu đề khóa học:** `0` khóa trùng tên (`120/120` duy nhất).
- **Trình tự bài học (`BaiHoc.thuTu`):** `0` lỗi đứt quãng hoặc trùng thứ tự trên tất cả khóa học có bài học.
- **Văn bản placeholder (`lorem ipsum`, `TODO`, `mô tả mẫu`):** `0` ở mô tả khóa học và `0` ở nội dung bài học.
- **Tài liệu nội bộ (`private_storage`):** `532` tệp vật lý hiện diện trong `backend/private_storage/`.
- **Tính nhất quán đánh giá chuyên gia (`DanhGiaChuyenGia`):** `0/20` mâu thuẫn giữa điểm kỹ thuật/nội dung và trạng thái duyệt.
- **Tính hợp lý lịch sử học tập (`LichSuHocTap`):** `0/300` bản ghi học khi chưa đăng ký; `0/300` bản ghi trỏ sai bài học ngoài khóa.
- **Phổ học phí (`KhoaHoc.gia`):** Hợp lý với thị trường Việt Nam — `23` khóa miễn phí (`0 ₫`), `97` khóa trả phí dao động `199,000 ₫ – 899,000 ₫` (trung bình `493,845 ₫`).

### 2.2. Các vấn đề chất lượng dữ liệu đã phát hiện (Cần phê duyệt xử lý riêng ở GĐ5.2)

| Mức độ | Hạng mục | Thực trạng đo được trên `EduSuggest` | Đề xuất phương án xử lý (chờ phê duyệt) |
| :--- | :--- | :--- | :--- |
| **CAO** | **Khóa học rác / thử nghiệm `#31`** | Course ID `31` có tiêu đề vô nghĩa `"fhahsahdáhdahshdáhdahdá"`, `trinhDo = null`, **`0` bài học** | Ẩn hiển thị (`trangThaiHienThi`) hoặc thay bằng khóa học hợp lệ sau khi xác nhận không có đăng ký/lịch sử phụ thuộc |
| **CAO** | **Hồ sơ nhà cung cấp placeholder `#5`** | `NhaCungCapKhoaHoc` ID `5` (`maNguoiDung=26`) có `tieuSu = "h"`, `chuyenMon = "h"`; một số trang hiển thị `"Thông tin nhà cung cấp chưa được cập nhật"` | Cập nhật hồ sơ tổ chức đào tạo chuẩn hóa và kiểm tra ánh xạ `tenNhaCungCap` trên `CourseDetail` |
| **TRUNG BÌNH** | **Chuẩn hóa cấp độ (`trinhDo`) không đồng nhất** | Trộn lẫn 2 hệ ngôn ngữ: Tiếng Việt (`Cơ bản: 9`, `Trung cấp: 10`, `Nâng cao: 8`) + Tiếng Anh (`BEGINNER: 24`, `INTERMEDIATE: 36`, `ADVANCED: 16`, `ALL_LEVELS: 16`) + `null: 1` | Chuẩn hóa về 1 chuẩn enum duy nhất (`BEGINNER`, `INTERMEDIATE`, `ADVANCED`, `ALL_LEVELS`) và dịch nhãn hiển thị thống nhất ở Frontend |
| **TRUNG BÌNH** | **Lệch thời lượng khóa học vs tổng bài học (`86/120` khóa)** | Ví dụ: khóa `#129` ghi `810 phút` nhưng tổng 3 bài học là `165 phút`; khóa `#29` ghi `180 phút` nhưng tổng bài là `300 phút` | Đồng bộ lại `KhoaHoc.thoiLuong` theo tổng `BaiHoc.thoiLuong` (hoặc bổ sung bài học thực tế cho đủ chương trình) |
| **TRUNG BÌNH** | **Thiếu đường dẫn video bài học (`276/411` bài)** | 92 khóa mới (mỗi khóa 3 bài = `276` bài) có `duongDanVideo = NULL/EMPTY`; 27 khóa legacy (`135` bài) có URL video | Ghi chú rõ bài học dạng đọc (text-based) trên UI hoặc bổ sung video mẫu hợp lệ cho các khóa trọng tâm |
| **THẤP** | **URL tài liệu ngoài lỗi / chặn bot (`7/121` URL)** | Kiểm tra trực tiếp `121` URL duy nhất: **`114/121` (94.2%) `HTTP 200 OK`**; `5` URL `dev.mysql.com` trả `HTTP 403` (chặn User-Agent tự động); `1` URL `HTTP 404` (`atlassian.com/software/jira/guides/bug-tracking/overview`); `1` `URLError` (`http://www.pentest-standard.org/`) | Thay 2 URL chết (`404` Atlassian Jira & `URLError` pentest-standard) bằng đường dẫn tài liệu chính thức đang hoạt động |
| **ĐÃ TRIỂN KHAI GĐ5.2** | **Ảnh bìa SVG sơ sài (`119/120` khóa)** | `119` ảnh `.svg` đơn điệu + `1` `.jpg` | **Đã thay thế 120/120 bằng ảnh WebP `1280×720` thực tế trong `/media/courses/v5-realistic/` ở GĐ5.2** (giữ nguyên 120 ảnh cũ để rollback). Chi tiết kế hoạch xử lý các mục còn lại xem [EDUSUGGEST_PHASE5_DATASET_REFINEMENT_PLAN.md](EDUSUGGEST_PHASE5_DATASET_REFINEMENT_PLAN.md). |
