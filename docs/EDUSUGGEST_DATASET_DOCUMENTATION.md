# TÀI LIỆU BỘ DỮ LIỆU CHÍNH THỨC – EDUSUGGEST (`edusuggest-official-v2` & `v1`)

> **Cập nhật 2026-11-27 (`edusuggest-official-v2`):** Phiên bản chính thức hiện hành trên Production `EduSuggest` (`35` bảng, Alembic revision `e5f6a7b8c9d0`) đã nâng cấp toàn bộ `120/120` ảnh bìa sang WebP `1280×720` thực tế (`/media/courses/v5-realistic/*.webp`), khôi phục khóa `#31` (`HIDDEN`/`PENDING`, `+10` bài học → `421` bài học), làm sạch `70` video chết/lệch chủ đề (giữ `65` video sống đúng chủ đề), chuẩn hóa `346` bài học kèm nguồn tài liệu chính thức, và phát hành snapshot khôi phục tại `backend/database/backups/official-dataset/20261127-official-v2-snapshot/` (giữ nguyên `20261126-official-v1-snapshot/`). Xem [EDUSUGGEST_OFFICIAL_DATASET_V2_REPORT.md](reports/EDUSUGGEST_OFFICIAL_DATASET_V2_REPORT.md) và [EDUSUGGEST_OFFICIAL_DATASET_V2_RESTORE_GUIDE.md](reports/EDUSUGGEST_OFFICIAL_DATASET_V2_RESTORE_GUIDE.md).

## 1. Tổng quan kiến trúc dữ liệu (`edusuggest-official-v1` gốc)

Bộ dữ liệu `edusuggest-official-v1` được thiết kế dùng lâu dài cho phát triển, demo, đánh giá thuật toán gợi ý và bảo vệ đồ án EduSuggest trên PostgreSQL 16 (Alembic revision `c3d4e5f6a7b8`, 24 bảng):

- **24 danh mục CNTT chuẩn hóa** (bao gồm 8 danh mục cũ được chuẩn hóa tên và 16 danh mục bổ sung).
- **120 khóa học** (bảo toàn 28 khóa học cũ + 92 khóa học mới biên soạn) kèm **120 ảnh bìa nội bộ** (119 SVG nguyên bản + 1 JPG hiện hữu).
- **411 bài học** và **243 tài liệu học tập** (bảo toàn dữ liệu cũ + bổ sung tài liệu thực hành lưu trong `private_storage` qua URI `private://materials/<object_id>`).
- **30 chuyên môn**, **20 hồ sơ chuyên gia**, **8 nhà cung cấp**, **78 người dùng** (gồm 50+ người học), **150 lượt đăng ký khóa học**, **300 bản ghi lịch sử học tập** và **12 thông báo mẫu**.

## 2. Bộ 8 Persona đánh giá Recommendation (TF-IDF + Cosine Similarity)

Thuật toán gợi ý nội dung (`backend/service/content_recommendation.py`) sử dụng TF-IDF + Cosine Similarity kết hợp tín hiệu danh mục, trình độ, thời lượng và giá. Chỉ bổ sung ánh xạ `hinhAnh` trong `recommendation_service.py` để hiển thị ảnh bìa trên thẻ gợi ý (không thay đổi công thức tính điểm):

| Tài khoản Persona | Nhóm hồ sơ học tập | Chiến lược thực tế | Cá nhân hóa |
|---|---|---|---|
| `official_persona_ai` | Machine Learning / AI | `content_based` | Có (`True`) |
| `official_persona_backend` | Web Backend / Kiến trúc | `content_based` | Có (`True`) |
| `official_persona_data` | Khoa học dữ liệu & Analytics | `content_based` | Có (`True`) |
| `official_persona_devops` | DevOps & Điện toán đám mây | `content_based` | Có (`True`) |
| `official_persona_frontend` | Web Frontend & UI/UX | `content_based` | Có (`True`) |
| `official_persona_fullstack` | Fullstack Development | `content_based` | Có (`True`) |
| `official_persona_mobile` | Lập trình Mobile | `content_based` | Có (`True`) |
| `official_persona_new` | Người học mới (Cold-start) | `latest` | Không (`False`) |

Chi tiết kết quả đầu ra JSON thực tế trên database chính `EduSuggest` được lưu tại:  
`backend/database/official_dataset/generated/reports/production-import-validation.json`  
và bản snapshot chính thức được lưu tại `backend/database/backups/official-dataset/20261126-official-v1-snapshot/`.

## 3. Quy trình vận hành & Bảo mật lưu trữ

- **Sao lưu trước import:** `backend/scripts/backup_official_dataset.ps1` xuất `EduSuggest.custom.dump`, `media.zip`, `private-storage.zip` kèm manifest SHA-256 tại `backend/database/backups/official-dataset/20261126-official-v1/`.
- **Khởi tạo & Restore Staging:** `backend/scripts/prepare_dataset_staging.ps1` kiểm tra SHA-256, chuẩn hóa tên database `"EduSuggest_dataset_staging"` và khôi phục an toàn (tương thích dump PG17 -> PG16).
- **Import & Kiểm chứng:** `backend/scripts/import_official_dataset.py` (yêu cầu `--dry-run` hoặc `--confirm-import`, khóa cứng đích `EduSuggest_dataset_staging`) và `backend/scripts/validate_official_dataset.py`.
- **Bảo vệ tài liệu riêng tư:** Đường dẫn `private://materials/<id>` không thể truy cập trực tiếp qua static URL; yêu cầu gọi API kèm Bearer JWT hợp lệ (truy cập ẩn danh trả `401 Unauthorized`).
- **Thông tin đăng nhập cục bộ:** Lưu riêng tại `backend/logs/official-dataset/demo-credentials.json` (không commit vào mã nguồn).
