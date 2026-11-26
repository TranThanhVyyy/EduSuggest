# EDUSUGGEST — GĐ5.2: KẾ HOẠCH CẢI THIỆN CHẤT LƯỢNG DỮ LIỆU (CHỜ PHÊ DUYỆT GĐ5.3)

**Trạng thái:** **CHỈ ĐỀ XUẤT — CHƯA GHI BẤT KỲ THAY ĐỔI NỘI DUNG NÀO LÊN PRODUCTION `EduSuggest`.**  
Tất cả số liệu dưới đây được kiểm toán trực tiếp (READ ONLY) từ Production `EduSuggest` (`e5f6a7b8c9d0`, `35` bảng).

---

## 1. Xử lý khóa học rác `#31` (`fhahsahdáhdahshdáhdahdá`)

- **Thực trạng toàn diện trên DB:**
  - `maKhoaHoc = 31`, `maNhaCungCap = 5` (`tranphuctk`), `maDanhMuc = 11` (`Kiểm thử phần mềm & QA`), `moTa = NULL`, `gia = NULL`, `trinhDo = NULL`, `thoiLuong = NULL`, `trangThaiDuyet = NULL`, **`trangThaiHienThi = 'HIDDEN'`**.
  - **Liên kết nghiệp vụ trên toàn bộ 10 bảng tham chiếu `maKhoaHoc`:** `BaiHoc = 0`, `TaiLieu = 0`, `DangKyKhoaHoc = 0`, `LichSuHocTap = 0`, `DanhGiaChuyenGia = 0`, `PhanCongKiemDuyet = 0`, `HangDoiPhanCong = 0`, `YeuThich = 0`, `ChiTietGioHang = 0`, `ChiTietDonHang = 0`.
- **Ảnh hưởng hiện tại:** Đã ở trạng thái `HIDDEN` nên không hiển thị cho người học và không xuất hiện trong Recommendation, nhưng vẫn tồn tại trong danh sách quản trị ADMIN/PROVIDER và tổng số `120` khóa học.
- **Đề xuất GĐ5.3 (chọn 1 phương án khi phê duyệt):**
  - **Phương án A (Khuyến nghị — an toàn 100%, giữ đủ 120 khóa học và Course ID `#31`):** Khôi phục `#31` thành một khóa học kiểm thử phần mềm hợp lệ (ví dụ *"Kiểm thử API tự động với Postman và Newman"*, có đủ mô tả, học phí, cấp độ, 3 bài học chuẩn) vì hoàn toàn `0` người học/giao dịch phụ thuộc.
  - **Phương án B (Lưu trữ mềm):** Giữ nguyên trạng thái `HIDDEN` và đánh dấu lưu trữ nội bộ (không xóa vật lý).

---

## 2. Chuẩn hóa thời lượng khóa học (`KhoaHoc.thoiLuong` vs `BaiHoc.thoiLuong`)

- **Phát hiện đơn vị & ý nghĩa nghiệp vụ:**
  - Cả `KhoaHoc.thoiLuong` và `BaiHoc.thoiLuong` đều lưu theo đơn vị **phút** (số nguyên).
  - Có `93/120` khóa khác tổng bài học, trong đó **`86/120` khóa lệch lớn** (> 50% hoặc > 60 phút):
    - Nhóm 92 khóa `edusuggest-official-v1`: `KhoaHoc.thoiLuong` phản ánh **tổng thời lượng học ước tính toàn khóa** (bao gồm đọc tài liệu + bài tập thực hành + đồ án, từ `360–810 phút`), trong khi mỗi khóa có 3 bài học tóm tắt (`150–195 phút`).
    - Nhóm 27 khóa legacy: một số khóa như `#29` ghi `180 phút` nhưng tổng 5 bài học là `300 phút` (nhỏ hơn tổng bài học — **lỗi logic rõ ràng**).
- **Đề xuất GĐ5.3:**
  - Không ép cộng cơ học cho 92 khóa `official-v1` (tránh làm mất thông tin thời lượng học ước tính thực tế); thay vào đó:
    1. Sửa các khóa có `KhoaHoc.thoiLuong < SUM(BaiHoc.thoiLuong)` (như `#29`: `180 → 300 phút`).
    2. Hiển thị nhãn rõ trên UI: `Thời lượng học ước tính` (từ `KhoaHoc.thoiLuong`) và `Tổng thời lượng bài giảng` (từ tổng `BaiHoc.thoiLuong`).
- **Ảnh hưởng TF-IDF Recommendation:** `content_recommendation.py` sử dụng `thoiLuong` làm một tín hiệu phụ; giữ nguyên khung `360–810 phút` cho 92 khóa official-v1 tránh làm lệch điểm gợi ý hiện tại.

---

## 3. Phân loại 411 bài học & Kế hoạch chuẩn hóa nội dung / video

- **Phân loại tự động toàn bộ 411 bài học:**
  - `video_lecture` (đã có URL video): **`135`** bài (thuộc 27 khóa legacy).
  - `practical_exercise` (bài thực hành / lab / tối ưu): **`99`** bài.
  - `quiz_assessment` (kiểm tra / đánh giá): **`84`** bài.
  - `text_reading_lesson` (bài học lý thuyết / đọc hiểu): **`78`** bài.
  - `project_based` (dự án / triển khai): **`15`** bài.
- **Đề xuất GĐ5.3:**
  - **Không ép 100% bài học phải có video** — giữ đúng bản chất sư phạm (Bài đọc / Thực hành / Kiểm tra / Dự án) và hiển thị biểu tượng loại bài học rõ ràng trên `LearningView` & `CourseDetail`.
  - Với các bài giảng nền tảng thực sự cần video minh họa (ưu tiên 1 bài giới thiệu/thực hành tiêu biểu cho mỗi chủ đề chính), chỉ nhúng video có quyền nhúng hợp lệ từ kênh chính thức của công nghệ (ví dụ: Python Software Foundation, FastAPI/Vue/React official talks, AWS/GCP/CNCF official channels) và **ghi rõ nguồn kênh chính thức**, không mạo nhận là video do EduSuggest tự quay.

---

## 4. Xử lý 7 URL tài liệu ngoài (`TaiLieu`)

| `maTaiLieu` | Khóa học | URL hiện tại | Phân loại lỗi | URL thay thế đề xuất (đã kiểm tra live `200 OK`) |
|---:|---:|---|---|---|
| `110` | `#24` | `https://www.atlassian.com/software/jira/guides/bug-tracking/overview` | **Link chết (`HTTP 404`)** | `https://www.atlassian.com/software/jira/guides/issues/overview` (**`HTTP 200 OK`** — tài liệu chính thức Atlassian Jira) |
| `98` | `#22` | `http://www.pentest-standard.org/` | **Link chết (`URLError` / không kết nối được)** | `https://owasp.org/www-project-web-security-testing-guide/` (**`HTTP 200 OK`** — chuẩn kiểm thử bảo mật chính thức OWASP WSTG) |
| `43–47` | `#11` | 5 URL `https://dev.mysql.com/doc/refman/8.0/en/...` | **Cơ chế chống bot (`HTTP 403` với script, hoạt động bình thường trên trình duyệt)** | **Giữ nguyên** (không vượt cơ chế chống bot, tài liệu chính thức Oracle MySQL 8.0 vẫn hợp lệ cho người học mở trên trình duyệt) |

---

## 5. Chất lượng hồ sơ Nhà cung cấp (`8`) & Chuyên gia (`21`)

- **Kiểm toán 21 hồ sơ Chuyên gia (`ChuyenGia`):** `0` hồ sơ thiếu họ tên hoặc chứa ký tự rác; các hồ sơ đang phân biệt rõ trạng thái xác minh (`trangThaiHoSo`). Không tự động chuyển hồ sơ sang `VERIFIED`.
- **Kiểm toán 8 hồ sơ Nhà cung cấp (`NhaCungCapKhoaHoc`):**
  - **`maNhaCungCap = 5` (`tranphuctk` — Trần Phú Phúc, sở hữu 12 khóa học):** Hiện có `tieuSu = "h"`, `chuyenMon = "h"` (**placeholder vô nghĩa**).
    - **Đề xuất GĐ5.3:** Cập nhật thành hồ sơ mô phỏng rõ ràng: `tieuSu = "Đội ngũ biên soạn học liệu lập trình và kỹ thuật phần mềm (hồ sơ mô phỏng đào tạo trên EduSuggest)."`, `chuyenMon = "Lập trình Web, Kiểm thử phần mềm & Kỹ thuật dữ liệu"`.
  - **Phân biệt minh bạch dữ liệu mô phỏng:** Các tổ chức `techmaster_vn`, `vnu_it_center`, `fpt_software_academy`, `codegym_center` là dữ liệu mô phỏng học thuật phục vụ đồ án — đề xuất bổ sung ghi chú phân loại rõ trong tài liệu dataset, không giả mạo xác nhận đối tác thương mại thật.

---

## 6. Chuẩn hóa cấp độ (`KhoaHoc.trinhDo`)

- **Thực trạng hiện tại:**
  - Tiếng Việt: `Cơ bản` (`9`), `Trung cấp` (`10`), `Nâng cao` (`8`).
  - Tiếng Anh: `BEGINNER` (`24`), `INTERMEDIATE` (`36`), `ADVANCED` (`16`), `ALL_LEVELS` (`16`).
  - `NULL`: `1` (khóa `#31`).
- **Đề xuất GĐ5.3 (Ưu tiên mapping hiển thị — zero rủi ro cho Recommendation Engine):**
  - **Không sửa dữ liệu gốc ngay hoặc chỉ chuẩn hóa sau khi kiểm thử TF-IDF:** Thêm helper `formatCourseLevel(value)` dùng chung trên toàn bộ Frontend (`CourseCard`, `CourseDetail`, `CourseCatalog`, `WishlistView`, `Recommendations`) ánh xạ thống nhất:
    - `BEGINNER` / `Cơ bản` → **`Cơ bản`**
    - `INTERMEDIATE` / `Trung cấp` → **`Trung cấp`**
    - `ADVANCED` / `Nâng cao` → **`Nâng cao`**
    - `ALL_LEVELS` → **`Mọi cấp độ`**
  - Chuẩn hóa filter trên API `/api/courses` chấp nhận cả giá trị Việt & Anh tương đương, đảm bảo **không làm thay đổi** công thức TF-IDF + Cosine Similarity.
