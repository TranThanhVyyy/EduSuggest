# EDUSUGGEST — GĐ5.5: BÁO CÁO TRIỂN KHAI CHÍNH THỨC NỘI DUNG HỌC TẬP LÊN PRODUCTION

**Ngày triển khai:** 2026-11-27  
**Mục tiêu:** Áp dụng nguyên tử `346` bài học đã kiểm chứng từ `edusuggest_phase54_staging` lên Production `EduSuggest` sau khi sao lưu đầy đủ và kiểm tra xung đột từng bản ghi.

---

## 1. Sao lưu Production & Kiểm chứng khôi phục trước triển khai
Thư mục sao lưu: `backend/database/backups/phase55-content-deploy/20261127/`
- **PostgreSQL custom dump:** `EduSuggest.pre-phase55.dump` (`240,825 bytes`, SHA-256 `970200E78B45171B56B6CA65E70D0C75DC4E5ABF3622F6AAC7FDF3188D48E271`).
- **Media archive:** `media_courses_pre_phase55.zip` (`8,381,271 bytes`, SHA-256 `B317C5E350B5A0C847D6354D15C8FD72C50B9C6A6E50798ADDF2CCB276091B83`).
- **Private storage archive:** `private_storage_pre_phase55.zip` (`277,869 bytes`, SHA-256 `4F27628B3C3631DB65954DA83380C7BEC81D57B3E439E04CA757D88C19A57529A`).
- **Restore Verification:** Khôi phục kiểm chứng thành công trên `edusuggest_phase55_backup_verify`.

---

## 2. Quá trình áp dụng & Bảo toàn toàn vẹn Production
- **Script:** `backend/scripts/apply_phase54_to_production.py` (`--dry-run` → `--confirm-apply`).
- **Conflict Guard:** Kiểm tra giá trị cũ của từng bài học trong số `346` bài trước khi ghi → **`0` xung đột (`conflicts = 0`)**.
- **Phạm vi ghi duy nhất:** Chỉ cập nhật `BaiHoc.noiDung` và `BaiHoc.duongDanVideo` cho `346` bài học đã kiểm chứng trong 1 transaction nguyên tử (`346` bài nâng cấp nội dung, gỡ `20` video chết `404` và `50` video SQL lệch chủ đề, giữ nguyên `65` bài video hợp lệ).
- **Bảo toàn tuyệt đối:** `35` bảng, revision `e5f6a7b8c9d0`, `120` Course IDs, `421` Lesson IDs, `243` Material IDs, `120/120` ảnh bìa WebP (`HTTP 200` + `image/webp`), `150/150 LEGACY ACTIVE`, `300` lịch sử học tập, toàn bộ trạng thái kiểm duyệt/hiển thị (`#31` & `#132` vẫn `HIDDEN`/`PENDING`), Feature Flags (`COMMERCE_ENROLLMENT_GATE_ENABLED=True`, toàn bộ cổng thanh toán & worker `False`).

---

## 3. Phương án Rollback tức thì
Chạy `python backend/scripts/apply_phase54_to_production.py --rollback` để khôi phục nguyên trạng `346` bài học từ `backend/database/backups/phase55-content-deploy/20261127/prod-phase54-rollback.json` trong `< 5 giây`.
