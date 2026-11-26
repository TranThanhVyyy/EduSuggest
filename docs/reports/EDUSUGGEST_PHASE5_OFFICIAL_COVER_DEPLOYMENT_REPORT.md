# EDUSUGGEST — GĐ5.2: BÁO CÁO TRIỂN KHAI CHÍNH THỨC 120 ẢNH BÌA THỰC TẾ

**Ngày thực hiện:** 2026-11-26  
**Trạng thái:** **HOÀN TẤT TRIỂN KHAI CHÍNH THỨC 120/120 ẢNH BÌA WEBP `1280×720` LÊN PRODUCTION `EduSuggest` (`http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api`). DỪNG LẠI CHỜ PHÊ DUYỆT GĐ5.3 CHO CÁC ĐỀ XUẤT CẢI THIỆN DỮ LIỆU NỘI DUNG.**

---

## 1. Hoàn thiện 6 ảnh bìa còn lại & Final Visual Audit (`120/120 PASS`)

Đã xử lý chọn lọc bằng `phase5_cover_pipeline.py --course-ids` (không làm thay đổi 114 ảnh đã đạt chuẩn):

| Course ID | Khóa học | Ảnh mới đã nghiệm thu trực quan | Nguồn & Giấy phép |
|---:|---|---|---|
| `#29` | Hacker Mũ Trắng và Tấn công Thử nghiệm Web | Cáp mạng RJ45 nền tối sắc nét | Openverse (`stocksnap` / `CC0 1.0`) |
| `#136` | Flutter và Dart từ nền tảng đến ứng dụng | Bàn thiết kế ứng dụng di động & máy tính bảng | Openverse (`stocksnap` / `CC0 1.0`) |
| `#142` | Thiết kế AI và hành vi nhân vật trong Game | Bo mạch điện tử / phần cứng cận cảnh | Openverse (`flickr` / xác minh `200 OK`) |
| `#176` | Microsoft Azure căn bản thực hành | Laptop hiện đại trong không gian làm việc văn phòng | Openverse (`stocksnap` / `CC0 1.0`) |
| `#177` | Google Cloud cho ứng dụng dữ liệu | Hệ thống tủ server & quạt tản nhiệt doanh nghiệp | Openverse (`stocksnap` / `CC0 1.0`) |
| `#179` | Mạng máy tính từ TCP/IP đến HTTP | Switch mạng & hệ thống cáp Ethernet xanh/trắng | Openverse (`stocksnap` / `CC0 1.0`) |

### Kết quả Final Visual Audit & Origin License Verification
- **120 / 120 ảnh bìa đạt chuẩn trực quan:** Đúng chủ đề công nghệ/học tập, `1280×720` (16:9) WebP, font tiếng Việt sắc nét không lỗi dấu, không cắt chữ, không watermark, không quảng cáo/giảm giá/chứng chỉ giả.
- **Chống trùng lặp tuyệt đối:** `120/120` URL nguồn duy nhất, `120/120` SHA-256 duy nhất, `0` trùng/gần trùng (`dHash`).
- **Xác minh trang nguồn gốc (`source_url`):** `24/24` trang nguồn của toàn bộ ảnh `Public Domain Mark 1.0` (`#10, #11, #20, #196`), `CC BY 2.0` (`17` ảnh) và `CC BY-SA 2.0` (`3` ảnh) trả **`HTTP 200 OK`**; toàn bộ `96` ảnh `CC0 1.0` đều thuộc nguồn mở cho phép chỉnh sửa & sử dụng thương mại.
- **Thống kê cuối cùng:** Tổng `8,300,444 bytes` (`7.92 MB`, trung bình `69.2 KB`/ảnh), phân bổ nguồn: `stocksnap` (`69`), `rawpixel` (`26`), `flickr` (`25`).

---

## 2. Sao lưu Production & Kiểm chứng khôi phục trước triển khai

Thư mục sao lưu: `backend/database/backups/phase52-cover-deploy/20261126/`
- **PostgreSQL custom dump:** `EduSuggest.pre-phase52.dump` (`239,865 bytes`, SHA-256 `B049EE81692ECA222C15E2A704C7AD5784F626E4A6D879EB21D1876621FB0F7F`).
- **Backup ảnh bìa cũ:** `media_courses_pre_phase52.zip` (`595,071 bytes`, SHA-256 `4742BA22B87E5832A39F10EF73EF13ABD58D4FD4FC2DB1E669808CB2ACC82091`).
- **Mapping rollback:** `rollback-manifest.json` lưu đủ 120 cặp `Course ID → đường dẫn ảnh cũ + SHA-256`.
- **Restore Verification:** Khôi phục kiểm chứng thành công trên database cô lập `edusuggest_phase52_backup_verify` → **`35` bảng, revision `e5f6a7b8c9d0`, `120` khóa học, `150` `LEGACY ACTIVE`, `300` lịch sử học tập**.

---

## 3. Triển khai chính thức (Versioned Directory) & Sửa lỗi MIME `.webp`

1. **Dry-run:** `apply_phase5_covers.py --dry-run` trên `EduSuggest` → `120 verified WebP covers ready to apply (0 missing). Old covers preserved.`
2. **Apply nguyên tử:** Sao chép 120 file `.webp` vào thư mục versioned **`media/courses/v5-realistic/`** (giữ nguyên 100% `119` `.svg` + `1` `.jpg` cũ ở `media/courses/`), xác minh đủ 120 file vật lý rồi cập nhật duy nhất cột `KhoaHoc.hinhAnh` trong 1 transaction.
3. **Sửa MIME type `.webp` trên Windows (`backend/main.py`):** Kiểm tra thực tế sau deploy phát hiện Starlette `StaticFiles` trên Windows trả `application/octet-stream` cho `.webp`. Đã bổ sung `mimetypes.add_type("image/webp", ".webp")` trong `backend/main.py` và khởi động lại Production Backend `8000` (giữ nguyên toàn bộ cờ runtime GĐ4.7C: `COMMERCE_ENROLLMENT_GATE_ENABLED=True`, toàn bộ cổng thanh toán & worker `False`).

---

## 4. Kết quả kiểm chứng sau triển khai

| Hạng mục kiểm chứng | Kết quả thực tế |
| :--- | :--- |
| Database & Schema Production | `EduSuggest`, `35` bảng, revision `e5f6a7b8c9d0` (không migration mới) |
| Đường dẫn ảnh WebP trong DB | **`120 / 120`** (`/media/courses/v5-realistic/course-*.webp`) |
| Kiểm tra Live HTTP trên `127.0.0.1:8000` | **`120 / 120` `HTTP 200 OK`** |
| Kiểm tra MIME type trên `127.0.0.1:8000` | **`120 / 120` `image/webp`** |
| Bảo toàn ảnh cũ & Orphan check | **`119` `.svg` + `1` `.jpg` cũ còn nguyên** · `120` file trong `v5-realistic/` · **`0` orphan files** |
| Bảo toàn dữ liệu Production | `24` danh mục, `120` khóa học, `411` bài học, `243` tài liệu, **`150/150 LEGACY ACTIVE`**, **`300` lịch sử học tập** |
| Frontend Vite Production Build | **PASS** (`1,911 modules`, `6.76s`) |
| Full Backend Regression (`EduSuggest_phase4_test`) | **`266 passed, 0 failed, 0 skipped` (`109.61s`)** — gồm Recommendation, RBAC & Private File Authorization |
| Trạng thái dịch vụ | Production `5173`/`8000` `200 OK`; Marketplace Staging `5176`/`8003` `200 OK` |
| Trình duyệt tự động (Chrome DevTools MCP) | `BLOCKED` (`DevToolsActivePort ENOENT`) — cung cấp Gallery HTML & Checklist kiểm tra trực tiếp tại `http://127.0.0.1:5173/` |

---

## 5. Phương án Rollback tức thì
Chạy `python backend/scripts/apply_phase5_covers.py --rollback` để khôi phục 120 đường dẫn `KhoaHoc.hinhAnh` về nguyên trạng từ `rollback-manifest.json` trong `< 5 giây` (toàn bộ 119 `.svg` + 1 `.jpg` cũ vẫn nằm nguyên trong `media/courses/`).
