# HƯỚNG DẪN KHÔI PHỤC OFFICIAL DATASET V2 (`edusuggest-official-v2`)

**Thư mục gói phát hành:** `D:\đồ án\EduSuggest\backend\database\backups\official-dataset\20261127-official-v2-snapshot\`

---

## 1. Kiểm tra toàn vẹn SHA-256 trước khi khôi phục
```powershell
Set-Location "D:\đồ án\EduSuggest\backend\database\backups\official-dataset\20261127-official-v2-snapshot"
Get-Content SHA256SUMS.txt
```
So sánh giá trị hash với `Get-FileHash <filename> -Algorithm SHA256`.

## 2. Khôi phục Database vào cơ sở dữ liệu cô lập (khuyến nghị kiểm thử trước)
```powershell
$dump = "D:\đồ án\EduSuggest\backend\database\backups\official-dataset\20261127-official-v2-snapshot\EduSuggest-official-v2.custom.dump"
docker exec pg psql -U postgres -c 'CREATE DATABASE edusuggest_v2_restore;'
docker cp $dump pg:/tmp/v2_restore.dump
docker exec pg pg_restore -U postgres -d edusuggest_v2_restore --no-owner --no-privileges /tmp/v2_restore.dump
docker exec pg rm -f /tmp/v2_restore.dump
```

## 3. Khôi phục Media & Private Storage
```powershell
Expand-Archive -Path "media-v2.zip" -DestinationPath "D:\đồ án\EduSuggest\media\courses" -Force
Expand-Archive -Path "private-storage-v2.zip" -DestinationPath "D:\đồ án\EduSuggest\backend\private_storage" -Force
```

## 4. Xác minh sau khôi phục
- Kiểm tra `SELECT version_num FROM alembic_version;` → `e5f6a7b8c9d0` (`35` bảng).
- Kiểm tra số lượng bản ghi: `24` danh mục, `120` khóa học, `421` bài học, `243` tài liệu, `150` đăng ký `LEGACY ACTIVE`, `300` lịch sử học tập.
- Kiểm tra `GET http://127.0.0.1:8000/api/health` và `HEAD http://127.0.0.1:8000/media/courses/v5-realistic/course-003.webp` trả `HTTP 200` + `Content-Type: image/webp`.
