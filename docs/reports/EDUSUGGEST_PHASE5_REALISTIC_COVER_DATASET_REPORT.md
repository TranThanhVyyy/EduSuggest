# EDUSUGGEST — GĐ5.1: BÁO CÁO BỘ ẢNH BÌA THỰC TẾ & QUY TRÌNH TỰ ĐỘNG HÓA

**Ngày thực hiện:** 2026-11-26  
**Trạng thái:** **HOÀN TẤT 120/120 ẢNH BÌA ĐẠT CHUẨN TRỰC QUAN & ĐÃ TRIỂN KHAI CHÍNH THỨC LÊN PRODUCTION `EduSuggest` TRONG GĐ5.2 (`/media/courses/v5-realistic/*.webp`, 120/120 HTTP 200 & `image/webp`).**

---

## 1. Khảo sát & Lựa chọn nguồn ảnh hợp lệ

| Nguồn | Cơ chế truy cập | Yêu cầu API Key trả phí | Xác minh giấy phép tự động | Quyết định sử dụng |
| :--- | :--- | :--- | :--- | :--- |
| **Openverse API** (`api.openverse.org/v1/images/`) | Public REST API (`license_type=modification`, `category=photograph`, `aspect_ratio=wide`, ưu tiên `source=stocksnap,rawpixel,wordpress`) | **Không** | **Có** (`CC0`, `PDM`, `CC BY`, `CC BY-SA` — loại bỏ toàn bộ `ND`) | **Nguồn chính (120/120 ảnh)** |
| **Wikimedia Commons API** (`commons.wikimedia.org/w/api.php`) | Public MediaWiki API (`filetype:bitmap`, kiểm tra `extmetadata.LicenseShortName`) | **Không** | **Có** (`CC0`, `Public domain`, `CC BY`, `CC BY-SA`) | **Nguồn dự phòng tự động** |
| **Pexels / Unsplash API** | REST API yêu cầu đăng ký API Key & rate-limit riêng | Có tài khoản / hạn mức | Có | Ghi nhận mở rộng khi có API key; không phụ thuộc |
| **Google Images / Scrape trực tiếp** | Không có xác minh giấy phép / dính watermark | — | **Không** | **LOẠI BỎ TUYỆT ĐỐI** |

---

## 2. Kiến trúc Pipeline tự động (`phase5_cover_pipeline.py`)

- **Mã nguồn pipeline:** `backend/scripts/phase5_cover_pipeline.py`
- **Tính năng vận hành tin cậy:**
  - Hỗ trợ `--dry-run`, `--batch-size`, `--resume`, `--rebuild-thumbnails`, `--course-ids`, `--limit`.
  - Disk HTTP request cache (`media/phase5-covers-staging/cache/api_cache.json`), Raw photo cache (`raw/`), checkpoint sau từng khóa học (`checkpoint.json`), rate limiting (`0.18s`), exponential backoff retry (`3` lần), timeout (`12–15s`), structured JSONL logs (`pipeline.jsonl`), và `rollback-manifest.json`.
  - **Chống trùng lặp toàn cục 3 lớp:** URL duy nhất (`120/120`), SHA-256 ảnh gốc duy nhất (`120/120`), SHA-256 ảnh đầu ra duy nhất (`120/120`) và **64-bit perceptual `dHash`** (`min Hamming distance = 13`, không có ảnh trùng hoặc gần trùng).
- **Thiết kế đồ họa chuyên nghiệp bằng Python Pillow (áp dụng `emil-design-eng`, `impeccable`, `design-taste-frontend`):**
  - Định dạng **1280×720 (16:9) WebP** (`quality=84, method=6`), font tiếng Việt chuẩn (`Segoe UI Bold/Semibold`, không lỗi dấu).
  - **6 chủ đề bố cục đa dạng theo lĩnh vực** (Editorial EdTech Modernism):
    - `ai_data` (Bottom-Left Editorial Card — Slate + Copper): **41** khóa học
    - `cloud_devops` (Diagonal Petrol Scrim — Petrol + Cyan): **30** khóa học
    - `software_web` (Editorial Left Scrim — Navy + Teal): **23** khóa học
    - `design_creative` (Full-Bleed Bottom Gradient — Charcoal + Terracotta): **17** khóa học
    - `product_career` (Academic Lower-Third Band — Navy + Gold): **5** khóa học
    - `security_iot` (Split Editorial Frame — Obsidian + Emerald): **4** khóa học
  - **Tuân thủ nội dung trung thực:** Không dùng SVG sơ sài, không gắn giảm giá giả / chứng chỉ giả / nhãn Bestseller giả, không gán tên giảng viên lên ảnh stock, không sao chép nhận diện thương hiệu nền tảng khác.

---

## 3. Thống kê kết quả thu thập, giấy phép & dung lượng

| Chỉ số | Trước GĐ5.1 (Hiện tại trên Production) | Sau GĐ5.1 (Staging `phase5-covers-staging`) |
| :--- | :--- | :--- |
| Tổng số ảnh bìa | `120` (`119` SVG sơ sài + `1` JPG) | `120` (`120` WebP thực tế `1280×720`, 16:9) |
| Số ảnh duy nhất (URL / SHA-256) | `120` | **`120 / 120`** (`0` trùng lặp, `min dHash HD = 13`) |
| Nguồn ảnh | Nội bộ tự vẽ SVG | Openverse (`stocksnap`: 66, `flickr`: 28, `rawpixel`: 26) |
| Giấy phép xác minh | Nội bộ | `CC0 1.0`: **94**, `CC BY 2.0`: **19**, `Public Domain Mark 1.0`: **4**, `CC BY-SA 2.0`: **3** |
| Tổng dung lượng | `662,422 bytes` (`0.63 MB`) | `8,385,776 bytes` (`8.00 MB`) |
| Dung lượng trung bình / ảnh | `5.4 KB` (SVG vector) | **`68.2 KB`** (`17.1 KB` – `193.6 KB`) |

---

## 4. Kết quả Kiểm tra trực quan (Visual Audit — 2 vòng trên 4 Contact Sheets)

- **Vòng 1:** Kiểm tra toàn bộ 4 Contact Sheets (`contact-sheet-1.png` .. `contact-sheet-4.png`) phát hiện **59 ảnh nền lệch chủ đề** (poster hội nghị, slide chữ, ảnh AI-art ngọn hải đăng, chính trị gia/quân đội từ nguồn Flickr). Đã bổ sung bộ lọc chặn từ khóa poster/slide/AI-art/chính trị và ưu tiên nguồn nhiếp ảnh `stocksnap,rawpixel,wordpress`, sau đó chạy lại pipeline thay thế toàn bộ 59 ảnh.
- **Vòng 2 (Hiện tại):**
  - **Đạt chuẩn ngay lập tức:** **`114 / 120` ảnh bìa** (sắc nét, đúng chủ đề công nghệ/học tập, chữ tiếng Việt rõ ràng không lỗi font, độ tương phản cao, không trùng lặp).
  - **6 ảnh nền còn lệch nhẹ / đề xuất đổi nhanh trước khi lên Production** (có thể chạy 1 lệnh `phase5_cover_pipeline.py --course-ids "29,136,142,176,177,179"` nếu người dùng đồng ý):
    - `#29` (*Hacker Mũ Trắng và Tấn công Thử nghiệm Web*): ảnh cột biển báo cáp quang ngoài trời.
    - `#136` (*Flutter và Dart từ nền tảng đến ứng dụng*): ảnh chụp ngoài trời chưa sát lập trình di động.
    - `#142` (*Thiết kế AI và hành vi nhân vật trong Game*): ảnh minh họa ngọn hải đăng.
    - `#176` (*Microsoft Azure căn bản thực hành*): ảnh ánh sáng trừu tượng.
    - `#177` (*Google Cloud cho ứng dụng dữ liệu*): ảnh bản đồ vệ tinh vùng núi.
    - `#179` (*Mạng máy tính từ TCP/IP đến HTTP*): ảnh phòng họp cổ điển.
  - **Lưu ý riêng `#31`:** Ảnh bìa WebP sạch, nhưng bản thân bản ghi khóa học `#31` (`"fhahsahdáhdahshdáhdahdá"`) là dữ liệu test rác — được báo cáo riêng trong `EDUSUGGEST_PHASE5_DATA_QUALITY_AUDIT_REPORT.md` (chưa tự ý xóa).

---

## 5. Môi trường Staging độc lập & Kiểm tra tương thích Frontend

- **Staging DB độc lập:** `EduSuggest_phase5_cover_staging` (nhân bản sạch từ bản sao `e5f6a7b8c9d0` 35 bảng, đã cập nhật `120/120` `KhoaHoc.hinhAnh` → `/media/courses/course-XXX.webp`). Không ảnh hưởng Production `EduSuggest`, Marketplace Staging (`5176`/`8003`) hay Dataset Staging (`5175`/`8002`).
- **Tương thích Frontend:** Các màn hình `CourseCard`, `CourseDetail`, `WishlistView`, `CartView`, `CheckoutView`, `UserHome`, `Recommendations`, `UserDashboard` đều sử dụng `object-cover` trên khung tỷ lệ ngang và `resolveMediaUrl(...)` (vừa đồng bộ cho `WishlistView`, `CartView`, `CheckoutView`), đảm bảo ảnh `1280×720` (16:9) hiển thị sắc nét không kéo giãn.
- **Kiểm tra Production READ ONLY:** Xác nhận Production `EduSuggest` giữ nguyên `119` `.svg` + `1` `.jpg`, `150` đăng ký `LEGACY ACTIVE`, `300` lịch sử học tập.

---

## 6. Phương án cập nhật Production & Rollback (CHỜ PHÊ DUYỆT)

1. **Dry-run đã kiểm chứng:** `python scripts/apply_phase5_covers.py --dry-run` → `120 verified WebP covers ready to apply (0 missing). Old covers preserved.`
2. **Khi được phê duyệt:**
   - (Tùy chọn) Thay nhanh 6 ảnh gợi ý bằng `--course-ids "29,136,142,176,177,179"`.
   - Sao lưu DB `EduSuggest` trước khi ghi.
   - Chạy `python scripts/apply_phase5_covers.py --confirm-apply` (sao chép 120 file `.webp` vào `media/courses/` mà **không xóa** 120 ảnh cũ, chỉ cập nhật cột `KhoaHoc.hinhAnh`).
   - Kiểm tra `120/120` URL `http://127.0.0.1:8000/media/courses/course-*.webp` trả `HTTP 200`.
3. **Phương án Rollback tức thì (< 5 giây):**
   - Chạy `python scripts/apply_phase5_covers.py --rollback` để khôi phục nguyên trạng 120 đường dẫn `KhoaHoc.hinhAnh` từ `media/phase5-covers-staging/rollback-manifest.json` (120 ảnh cũ trong `media/courses/` vẫn được giữ nguyên vẹn).

---

## 7. Danh mục hồ sơ bàn giao
- Manifest đầy đủ provenance (120 ảnh): `docs/reports/course-cover-manifest.json`
- Bảng ghi nguồn & giấy phép: `docs/reports/COURSE_COVER_SOURCE_ATTRIBUTION.md`
- Gallery HTML so sánh ảnh cũ & mới (120 khóa học): `docs/reports/course-cover-comparison-gallery.html`
- 4 Contact Sheets kiểm tra trực quan: `media/phase5-covers-staging/contact-sheets/contact-sheet-1..4.png`
- Rollback manifest: `media/phase5-covers-staging/rollback-manifest.json`
