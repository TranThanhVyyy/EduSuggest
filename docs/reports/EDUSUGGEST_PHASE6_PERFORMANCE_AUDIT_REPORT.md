# EDUSUGGEST — GĐ6.1: BÁO CÁO KIỂM TOÁN HIỆU NĂNG (PERFORMANCE AUDIT)

**Ngày đo:** 2026-11-27  
**Môi trường đo:** Local Windows 11 · Production `127.0.0.1:8000` (FastAPI + Uvicorn, `APP_ENV=production`) · `127.0.0.1:5173` (Vite) · PostgreSQL 16 Docker (`EduSuggest`, `111` indexes, `edusuggest-official-v2`).

---

## 1. Số liệu đo độ trễ thực tế (Real Measurements)

| Endpoint / Tác vụ | Số lần đo | Min (ms) | p50 (ms) | p95 / Max (ms) | Đánh giá |
| :--- |---:|---:|---:|---:|---|
| `GET /api/health` | 8 | `5.9` | **`6.8`** | `17.0 / 25.8` | Rất tốt |
| `GET /api/commerce/capabilities` | 8 | `3.6` | **`15.6`** | `26.8 / 28.2` | Rất tốt (zero DB query) |
| `GET /api/categories` | 8 | `9.9` | **`12.4`** | `22.1 / 29.1` | Rất tốt |
| `GET /api/courses?page=1&page_size=24` | 8 | `10.9` | **`12.5`** | `15.1 / 27.0` | Rất tốt |
| `GET /api/courses?q=python` | 8 | `10.9` | **`12.1`** | `13.0 / 14.3` | Rất tốt |
| `GET /api/courses/3` | 8 | `9.7` | **`11.1`** | `15.3 / 19.8` | Rất tốt |
| `GET /api/materials?page=1&page_size=24` | 8 | `16.3` | **`19.8`** | `25.9 / 39.2` | Tốt |
| `GET /media/courses/v5-realistic/course-003.webp` | 8 | `5.6` | **`6.2`** | `19.0 / 23.8` | Rất tốt |
| `GET http://127.0.0.1:5173/` | 8 | `2.6` | **`3.5`** | `4.5 / 4.7` | Rất tốt |
| `recommend_standalone_materials` (4 personas) | 4 | — | **`1,162.3`** | `max 1,379.0` | **Cần tối ưu (P2)** |
| **`recommend_courses` (4 personas)** | 4 | — | **`15,232.3`** | **`max 18,277.1`** | **NGHẼN CỔ CHAI (P1 — `ISSUE-009`)** |

---

## 2. Phân tích PostgreSQL `EXPLAIN ANALYZE` & Frontend Bundle Size
- **PostgreSQL `BaiHoc` by `maKhoaHoc`:** Dùng `Index Scan using uq_BaiHoc_maKhoaHoc_maBaiHoc` → **`0.038 ms`** (tối ưu).
- **PostgreSQL `KhoaHoc` catalog query:** Dùng `Seq Scan on "KhoaHoc"` (`0.209 ms` với 120 khóa) → đề xuất bổ sung composite index `(trangThaiDuyet, trangThaiHienThi, ngayTao DESC)` ở GĐ6.6 khi dữ liệu tăng trưởng (`ISSUE-005`).
- **Nguyên nhân gốc của `recommend_courses` (`15.23s` — `ISSUE-009`):** Sau khi nâng cấp nội dung 421 bài học lên TB `1,414.7` ký tự ở `edusuggest-official-v2`, hàm `recommend_courses` dựng lại toàn bộ đặc trưng khóa học + N+1 truy vấn bài học/tài liệu và ma trận TF-IDF từ đầu cho từng request mà chưa có in-memory TTL/versioned corpus cache!
- **Frontend Vite Bundle (`1,912 modules`, `2.06s`):** `index.js` = `130.44 kB` (`46.25 kB` gzip), `index.css` = `105.97 kB` (`17.05 kB` gzip), lazy-loaded route chunks `7–39 kB` (`2–10 kB` gzip) — gọn nhẹ, tải ảnh dùng `loading="lazy"`.

## 3. Kế hoạch tối ưu cho GĐ6.6
1. **P1 (`ISSUE-009`):** Eager-load `BaiHoc`/`DanhMuc` trong 1 query + cache corpus TF-IDF theo phiên bản dữ liệu (TTL 60–300s, invalidate khi xuất bản/sửa khóa học) → mục tiêu giảm `15,232 ms` xuống **`< 100 ms`** mà **không đổi công thức TF-IDF + Cosine Similarity**.
2. **P2 (`ISSUE-005`):** Bổ sung composite index cho `KhoaHoc(trangThaiDuyet, trangThaiHienThi, ngayTao DESC)`.
