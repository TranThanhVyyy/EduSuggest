# BÁO CÁO IMPORT CÓ KIỂM SOÁT BỘ DỮ LIỆU CHÍNH THỨC (`edusuggest-official-v1`) VÀO `EduSuggest`

**Ngày thực hiện:** 2026-11-26  
**Cơ sở dữ liệu chính:** `EduSuggest` (PostgreSQL 16, Alembic revision `c3d4e5f6a7b8`, 24 bảng)  
**Trạng thái:** **HOÀN TẤT AN TOÀN & ĐÃ XÁC MINH**  
**Runtime Flags trên Production (Fail-closed):** `AUTO_ASSIGNMENT_WORKFLOW_ENABLED=False`, `AUTO_ASSIGNMENT_WORKER_ENABLED=False`, `ACCOUNTABILITY_ENABLED=False`.

---

## 1. Sao lưu trước Import & Snapshot sau Import (SHA-256)

### A. Bản sao lưu ngay trước khi import (`20261126-pre-prod-import-v1`)
Thư mục: `D:\đồ án\EduSuggest\backend\database\backups\official-dataset\20261126-pre-prod-import-v1\`  
Xác minh `pg_restore --list`: **PASS**

| Tập tin | Kích thước (bytes) | SHA-256 |
|---|---:|---|
| `EduSuggest.custom.dump` | 146,280 | `93db8f54d7e082b4ab82f90fefdb0aa94239ee2d0e0467b645bab1d16ee4b688` |
| `media.zip` | 1,137,264 | `f2169aff5c1868f0a827870112410153edab04d411082f47c8f745e5ef6aa60e` |
| `private-storage.zip` | 143,621 | `c32f506962f0666ef7a6bb91a73d087b6c133c46f62472f7096d64fe1f336653` |

### B. Snapshot chính thức sau khi import (`20261126-official-v1-snapshot`)
Thư mục: `D:\đồ án\EduSuggest\backend\database\backups\official-dataset\20261126-official-v1-snapshot\`  
Phục vụ thực nghiệm, bảo vệ đồ án và khôi phục nhanh về mốc `edusuggest-official-v1`:

| Tập tin | Kích thước (bytes) | SHA-256 |
|---|---:|---|
| `EduSuggest.custom.dump` | 175,216 | `be49843a11d65d8f2ff1a67af1d32f4008c904657030feb37982c9eda6bda7cd` |
| `media.zip` | 1,236,754 | `be922a599deba00ebe7bda64d5b8cdc8c1bc810fe62af066e92d33b1884a8b96` |
| `private-storage.zip` | 277,954 | `d8dd5672126c5598366e0f9cff09d5c20389118469bb08411eea9c65bc5a368d` |

---

## 2. Số lượng bản ghi Trước / Sau Import trên `EduSuggest`

Cơ chế bảo vệ: `--dry-run` trước khi ghi, xác nhận bắt buộc `--confirm-production-import`, kiểm tra `SELECT current_database() = 'EduSuggest'` trước và sau transaction, rollback tự động cả DB và file đã tạo nếu có lỗi.

| Bảng | Trước import | Sau import | Idempotency dry-run lại | Ghi chú |
|---|---:|---:|---:|---|
| `DanhMuc` | 8 | **24** | +0 | Chuẩn hóa 7 tên cũ + thêm 16 mới |
| `KhoaHoc` | 28 | **120** | +0 | Bảo toàn 28 cũ + thêm 92 mới |
| `BaiHoc` | 135 | **411** | +0 | Bảo toàn 135 cũ + thêm 276 mới |
| `TaiLieu` | 122 | **243** | +0 | Bảo toàn 122 cũ + thêm 121 mới |
| `ChuyenMon` | 15 | **30** | +0 | Thêm 15 mới + 60 liên kết danh mục |
| `ChuyenGia` | 7 | **20** | +0 | 7 hồ sơ cũ `#4..#10` giữ nguyên `DRAFT`, thêm 13 hồ sơ mới |
| `NhaCungCapKhoaHoc` | 6 | **8** | +0 | Bảo toàn 6 cũ + thêm 2 mới |
| `NguoiDung` | 29 | **78** | +0 | Bảo toàn toàn bộ tài khoản & mật khẩu cũ |
| `DangKyKhoaHoc` | 48 | **150** | +0 | Bảo toàn 48 cũ + thêm 102 mới |
| `LichSuHocTap` | 169 | **300** | +0 | Bảo toàn 169 cũ + thêm 131 mới |
| `DanhGiaChuyenGia` | 20 | **20** | +0 | Bảo toàn 100% lịch sử kiểm duyệt cũ |
| `ViPhamChuyenGia` | 0 | **0** | +0 | Không tạo vi phạm cho tài khoản thật |
| `ThongBao` | 0 | **12** | +0 | Thông báo mẫu cho bộ dữ liệu mới |

---

## 3. Đồng bộ Storage & Kết quả Kiểm chứng sau Import

| Hạng mục kiểm tra | Kết quả | Chi tiết bằng chứng |
|---|---|---|
| **Database & Schema** | **PASS** | `EduSuggest`, revision `c3d4e5f6a7b8`, đủ `24` bảng. |
| **Duplicates & Orphans** | **PASS** | `0` trùng lặp (`usernames/categories/courses/specialties`); `0` bản ghi mồ côi trên 6 quan hệ FK. |
| **120/120 Ảnh bìa (`D:\đồ án\EduSuggest\media\courses`)** | **PASS** | `missing_reference=[]`, `missing_local_file=[]`, `external_reference_count=0`, `0` đường dẫn rò rỉ `dataset-staging`. |
| **Private Storage (`backend\private_storage\EduSuggest\materials`)** | **PASS** | `missing_private_files=[]`; không đưa file riêng tư vào thư mục public `media/`. |
| **Private File Authorization Matrix** | **PASS** | Ẩn danh -> `401`; người học hợp lệ xem tài liệu độc lập -> `200`; học viên đã đăng ký khóa -> `200`; học viên chưa đăng ký khóa -> `403 Forbidden`. |
| **Recommendation 8 Persona (TF-IDF + Cosine)** | **PASS (8/8)** | `official_persona_ai`, `backend`, `data`, `devops`, `frontend`, `fullstack`, `mobile` (`content_based`, không rò rỉ khóa đã học, 100% có ảnh bìa) + `official_persona_new` (`latest` cold-start). |
| **Pre-import Backend Regression (`pytest tests/`)** | **216/217 PASS** | `216 passed`; duy nhất `test_abrupt_worker_kill_reclaims_stale_lease_without_duplicate` gặp tranh chấp vì worker GĐ3.8.3 đang chạy song song trên `EduSuggest_phase3_test` (đúng yêu cầu không dừng staging GĐ3.8.3). |
| **Frontend Production Build (`vite build`)** | **PASS** | `1,897 modules transformed`, built cleanly in `2.07s`. |
| **Fail-closed Runtime Flags** | **PASS** | `FLAGS: False False False`; `.env` không thay đổi. |

---

## 4. Hướng dẫn khởi động Website chính thức & Thông tin trình diễn

### Khởi động Backend chính thức (Database `EduSuggest`, port `8000`)
```powershell
Set-Location "D:\đồ án\EduSuggest\backend"
$env:DEBUG = "False"
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Khởi động Frontend chính thức (trỏ API `http://127.0.0.1:8000/api`, port `5173`)
```powershell
Set-Location "D:\đồ án\EduSuggest\frontend"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000/api"
npm run dev -- --host 127.0.0.1 --port 5173
```

### Thông tin tài khoản trình diễn (Demo Credentials)
- File mật khẩu cục bộ (không commit): `D:\đồ án\EduSuggest\backend\logs\official-dataset\demo-credentials.json` (`shared_password`).
- 8 tài khoản Persona Recommendation: `official_persona_ai`, `official_persona_backend`, `official_persona_data`, `official_persona_devops`, `official_persona_frontend`, `official_persona_fullstack`, `official_persona_mobile`, `official_persona_new`.

---

## 5. Rủi ro còn tồn đọng
- Bản ghi legacy `TaiLieu #132` (`PENDING`/`HIDDEN`, `maDanhMuc=NULL`) vẫn được giữ nguyên chưa sửa theo quy tắc bảo toàn dữ liệu cũ; cần bổ sung danh mục hợp lệ hoặc xử lý nghiệp vụ riêng khi phê duyệt kích hoạt workflow Production.
- Ba cờ `AUTO_ASSIGNMENT_WORKFLOW_ENABLED`, `AUTO_ASSIGNMENT_WORKER_ENABLED`, `ACCOUNTABILITY_ENABLED` vẫn đang ở trạng thái `False` (fail-closed) chờ phê duyệt rollout riêng.
