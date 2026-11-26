# EDUSUGGEST – GĐ6.3B: RECOMMENDATION CACHE CORRECTNESS & MATHEMATICAL EQUIVALENCE ACCEPTANCE REPORT

- **Ngày kiểm toán:** 2026-11-27
- **Phạm vi:** `backend/service/content_recommendation.py`, `backend/service/recommendation_service.py`
- **Artifacts kiểm chứng:** [`backend/tests/test_phase63_cache_and_metrics.py`](../../backend/tests/test_phase63_cache_and_metrics.py), [`media/phase63-staging/phase63b_verification.json`](../../media/phase63-staging/phase63b_verification.json)

## 1. Lỗ hổng phát hiện khi kiểm toán GĐ6.2 & Bản sửa GĐ6.3B

Trong quá trình kiểm toán chuyên sâu GĐ6.3B, phát hiện 4 điểm cần gia cố trên bản cache GĐ6.2 và **đã khắc phục triệt để trước khi triển khai Production**:

1. **Fingerprint dựa trên `count(*)` + `max(ngayCapNhat)` bỏ sót chỉnh sửa văn bản:** Nếu tiêu đề/mô tả khóa học, nội dung bài học (`BaiHoc` không có `ngayCapNhat`), tên danh mục (`DanhMuc`), hoặc mô tả tài liệu bị sửa bằng SQL trực tiếp (kể cả giữ nguyên độ dài chuỗi), fingerprint cũ không đổi.
   - **Khắc phục:** Nâng cấp `_course_corpus_fingerprint` và `_material_corpus_fingerprint` trên PostgreSQL sang **content-hash `md5(coalesce(string_agg(... ORDER BY id), ''))`** bao phủ **100% các cột** tham gia xây dựng `CourseFeatures`, `MaterialFeatures` và `image_by_course_id`. Đồng thời căn khớp điều kiện `WHERE` của `_material_corpus_fingerprint` với `list_standalone_recommendation_materials` (toàn bộ `APPROVED + VISIBLE`).
2. **Cách ly DB key đầy đủ:** `_current_db_key(db)` sử dụng đầy đủ `driver://host:port/database` để tránh mọi nguy cơ trùng tên DB giữa các môi trường.
3. **Khóa luồng & Bộ nhớ có giới hạn:** Chuyển sang `threading.RLock()`, giới hạn `_MAX_CACHED_DATABASES = 8`, và bổ sung `get_recommendation_cache_stats()` theo dõi hit/miss.
4. **Cách ly Transaction Rollback & Multi-process:** Session chưa commit có fingerprint `fp_dirty` khác với fingerprint `fp_clean` của các session đã commit; đồng thời mọi Backend process độc lập đều tính chung fingerprint từ PostgreSQL nên mọi cập nhật committed đều tự đồng bộ tức thời giữa các process.

## 2. Ma trận kiểm thử 16 kịch bản Cache Correctness

| # | Kịch bản kiểm thử | Cơ chế đảm bảo & Kết quả |
|---|---|---|
| 1–2 | Đổi tên / mô tả khóa học (kể cả SQL trực tiếp cùng độ dài) | **PASS** — `md5(string_agg(...))` đổi ngay (`test_phase63_cache_and_metrics.py`) |
| 3–4 | Đổi nội dung bài học / Thêm-xóa bài học | **PASS** — `md5` trên `BaiHoc.tieuDe` + `md5(noiDung)` đổi ngay |
| 5–6 | Đổi tên/mô tả danh mục / Đổi tài liệu | **PASS** — `DanhMuc` & `TaiLieu` hash đổi ngay |
| 7–8 | Đổi `APPROVED/PENDING` hoặc `VISIBLE/HIDDEN` | **PASS** — lọc `WHERE APPROVED AND VISIBLE` loại ngay khỏi corpus |
| 9–11 | Quyền truy cập / Sở thích / Lịch sử học tập thay đổi | **PASS** — hồ sơ người dùng & danh sách đã đăng ký luôn truy vấn trực tiếp theo user (không cache chung giữa user) |
| 12 | Transaction rollback | **PASS** — `test_cache_rollback_isolation_and_bounded_memory_across_invalidations` xác nhận `dirty_id` không rò rỉ sang session committed |
| 13–15 | Worker restart / Concurrent requests / Multi-process | **PASS** — 32 concurrent HTTP requests (8 threads) 0 lỗi; fingerprint nằm ở PostgreSQL nên multi-process luôn nhất quán |
| 16 | Chuyển đổi DB kiểm thử & Bộ nhớ sau 15 lần rebuild | **PASS** — `course_entries <= 8`, RAM sau 15 rebuild = **`5.70 MB`** (đỉnh `14.73 MB`) |

## 3. Nghiệm thu tương đương toán học (Mathematical Equivalence)

- **Sai số cho phép (`tolerance`):** `1e-12` (chuẩn sai số dấu phẩy động IEEE-754 double precision).
- **Kết quả đo trên 8 Official Personas (Top-20 Khóa học + Top-20 Tài liệu, READ-ONLY Production `EduSuggest`):**
  - `all_exact_match`: **`true`** (**8/8 personas**, 100% khớp Candidate IDs, Tokenization, TF/IDF vectors, Final Scores, Top-5, Top-10).
  - `max_score_abs_diff`: **`0.0`** (sai số tuyệt đối bằng **0**, hoàn toàn không đổi công thức hay trọng số).
  - **Edge cases:** Empty profile trả rỗng personalized (fallback `latest` hoạt động đúng); 2 khóa học điểm giống hệt nhau có tie-breaking tất định `[101, 102]`.
