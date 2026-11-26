# EDUSUGGEST — BÁO CÁO PHÁT HÀNH OFFICIAL DATASET V2 (`edusuggest-official-v2`)

**Ngày phát hành:** 2026-11-27  
**Thư mục phát hành:** `backend/database/backups/official-dataset/20261127-official-v2-snapshot/`  
*(Snapshot `20261126-official-v1-snapshot/` được giữ nguyên 100% để đối chiếu và phục hồi.)*

---

## 1. Thành phần gói phát hành `edusuggest-official-v2`
- **Database dump (`PostgreSQL 16`, `35` bảng, revision `e5f6a7b8c9d0`):** `EduSuggest-official-v2.custom.dump` (`254,958 bytes`) — đã kiểm chứng restore thành công trên `edusuggest_official_v2_verify`.
- **Public Media Archive:** `media-v2.zip` (`8,979,466 bytes` — gồm 120 ảnh bìa WebP `1280×720` trong `v5-realistic/` + 119 SVG & 1 JPG cũ).
- **Private Storage Archive:** `private-storage-v2.zip` (`277,869 bytes` — `121/121` tệp `.bin` + `.json`).
- **Provenance & Attribution:** `course-cover-manifest.json`, `COURSE_COVER_SOURCE_ATTRIBUTION.md`, `learning-content-provenance.json`, `SHA256SUMS.txt`.
- **Bảo mật:** Không chứa mật khẩu, JWT token, secret key hay thông tin cá nhân thực.

---

## 2. So sánh `edusuggest-official-v1` → `edusuggest-official-v2`

| Chỉ số | `edusuggest-official-v1` | `edusuggest-official-v2` |
| :--- | :--- | :--- |
| Schema / Revision | `24` bảng (`c3d4e5f6a7b8`) | **`35` bảng (`e5f6a7b8c9d0`)** (đầy đủ Marketplace & Financial Integrity) |
| Ảnh bìa khóa học | `119` SVG sơ sài + `1` JPG | **`120/120` WebP `1280×720` thực tế** (xác minh giấy phép mở, `image/webp`) |
| Khóa học / Bài học | `120` khóa (`#31` rác) / `411` bài | **`120` khóa (`#31` khôi phục Postman 10 bài `HIDDEN`/`PENDING`) / `421` bài** |
| Chất lượng bài học | TB `539.3` ký tự · `20` video 404 · `50` video SQL lệch | **TB `1,414.7` ký tự · `421/421` nội dung duy nhất · `65` video sống đúng chủ đề · `0` video lỗi** |
| Tài liệu học tập | `243` (`2` link ngoài chết) | **`243` (`116/121` ngoài `200 OK` + `121/121` private `.bin`/`.json`, `#132` giữ `HIDDEN`/`PENDING`)** |
| Quyền học & Lịch sử | `150` đăng ký · `300` lịch sử | **`150/150 LEGACY ACTIVE` · `300` lịch sử (bảo toàn 100%)** |
