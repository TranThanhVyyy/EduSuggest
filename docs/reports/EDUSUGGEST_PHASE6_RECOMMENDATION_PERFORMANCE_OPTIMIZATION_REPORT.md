# EDUSUGGEST – GĐ6.2: RECOMMENDATION PERFORMANCE OPTIMIZATION REPORT (`ISSUE-009`)

- **Ngày thực hiện:** 2026-11-27
- **Môi trường benchmark:** Staging độc lập `edusuggest_phase62_staging` (clone từ `EduSuggest`, 35 bảng, revision `e5f6a7b8c9d0`)
- **Artifact benchmark:** [`media/phase62-staging/perf_benchmark.json`](../../media/phase62-staging/perf_benchmark.json)

## 1. Phân tích nguyên nhân gốc rễ (Root Cause Profiling)

Đo kiểm chi tiết `recommendation_service.recommend_courses(db, user_id=43, limit=10)` trên tập dữ liệu Official V2 (120 khóa học, 421 bài học, 243 tài liệu) cho kết quả trước tối ưu:

- **Tổng thời gian thực thi:** `17,655.8 ms` (GĐ6.1 API p50 = `15,232 ms`, max = `18,277 ms`).
- **Thời gian SQL (11 truy vấn):** `70.6 ms` (**0.4%**).
- **Thời gian xử lý Python TF-IDF:** `17,585.2 ms` (**99.6%**).

**Nguyên nhân cốt lõi** nằm ở `backend/service/content_recommendation.py`:
1. Trong `_profile_pair_score` (dòng 358): với mỗi khóa học ứng viên, hệ thống gọi lại `[_course_terms(c) for c in profile.corpus]` trên toàn bộ corpus (~100 khóa học × 421 bài học) → độ phức tạp **`O(N²)`** (~10.000 lần tách từ toàn bộ nội dung bài học trong một request).
2. Trong `_text_similarity`: bảng trọng số `_idf(corpus)` được tính lại từ đầu cho mỗi cặp so sánh ứng viên.
3. Trong `backend/service/recommendation_service.py`: corpus khóa học và tài liệu được nạp lại từ PostgreSQL trên mọi request dù danh mục không thay đổi.

## 2. Giải pháp tối ưu (Bảo toàn 100% công thức toán học)

**Không thay đổi bất kỳ công thức TF-IDF, Cosine Similarity, trọng số thành phần, cơ chế tie-breaking hay logic cold-start nào:**

1. **Precomputation trong `backend/service/content_recommendation.py`:**
   - Tính trước `terms_cache` (danh sách token cho từng khóa học/tài liệu), `idf_cache`, và `left_vec_cache` **một lần duy nhất** cho mỗi lệnh xếp hạng (`rank_similar_courses`, `rank_personalized_courses`, `build_preference_profile`, `_profile_pair_score`, `rank_standalone_materials`), hạ độ phức tạp từ `O(N²)` xuống `O(N)`.
2. **Thread-safe, DB-isolated, Fingerprint-validated Corpus Cache trong `backend/service/recommendation_service.py`:**
   - Dùng `_CACHE_LOCK = threading.RLock()` bảo vệ cache in-memory `_COURSE_CORPUS_CACHE` và `_MATERIAL_CORPUS_CACHE`.
   - Cách ly tuyệt đối theo database key (`_current_db_key(db)` = URL + `current_database()`) để không bao giờ lẫn dữ liệu giữa Production, Staging và Test DB.
   - Xác thực tức thời bằng lightweight fingerprint query (`<1 ms`: đếm số khóa/tài liệu `APPROVED + VISIBLE`, `max(ngayCapNhat/ngayTao)`, số bài học, số danh mục) — tự động làm mới ngay lập tức khi có thay đổi nội dung hoặc trạng thái hiển thị (ví dụ ẩn khóa học `#27`).
   - Cung cấp hàm `invalidate_recommendation_cache()` phục vụ kiểm thử và bảo trì.

## 3. Kết quả Benchmark (Before vs. After)

Người dùng kiểm thử chính: `#43 (learner_data_ai)` — 22 bản ghi lịch sử học tập (`content_based`).

| Chỉ số | GĐ6.1 Before | GĐ6.2 After (Staging) | Mục tiêu GĐ6.2 | Kết luận |
|---|---:|---:|---:|---|
| `recommend_courses` Warm p50 (`n=35`) | `15,232.00 ms` | **`113.31 ms`** (**134.4× nhanh hơn**) | `<= 150 ms` | **PASS** |
| `recommend_courses` Warm p95 (`n=35`) | `18,277.00 ms` | **`166.68 ms`** | `<= 300 ms` | **PASS** |
| `recommend_courses` Warm max (`n=35`) | `18,277.00 ms` | **`193.36 ms`** | `<= 300 ms` | **PASS** |
| `recommend_courses` Cold p50 (`n=5`) | `17,655.80 ms` | **`584.02 ms`** (**30.2× nhanh hơn**) | `<= 1,500 ms` | **PASS** |
| `recommend_courses` Cold max (`n=5`) | `18,277.00 ms` | **`751.80 ms`** | `<= 1,500 ms` | **PASS** |
| 8-thread Cold Cache Stampede p50 / max | N/A | **`1,306.04 ms` / `1,354.05 ms`** | 0 lỗi | **PASS** |
| `recommend_standalone_materials` Warm p50 | `~15,000 ms` | **`395.21 ms`** (Cold `1,138.12 ms`) | Ổn định | **PASS** |
| SQL queries median (Warm) | `11–14` | **`9` (courses) / `10` (materials)** (`17–19 ms`) | Giảm tải DB | **PASS** |
| Bộ nhớ cache (tracemalloc) | N/A | **`6.83 MB` hiện tại / `15.49 MB` đỉnh** | Nhẹ, an toàn | **PASS** |

## 4. Chứng minh tương đương toán học 100% (8 Official Personas)

Chạy kiểm chứng **READ-ONLY** trực tiếp trên Production `EduSuggest` (0 ghi) và so sánh từng phần tử Top-5 với baseline Official V2 (`media/phase54-staging/final_prod_rec_eval.json`):

| Persona | Chiến lược | Top-5 Khóa học | Top-5 Tài liệu | Khớp chính xác |
|---|---|---|---|---|
| `official_persona_ai` (#111) | `content_based` | `[158, 22, 204, 157, 126]` | `[290, 373, 331, 288, 103]` | **EXACT MATCH (100%)** |
| `official_persona_backend` (#109) | `content_based` | `[182, 131, 137, 136, 14]` | `[264, 312, 309, 53, 57]` | **EXACT MATCH (100%)** |
| `official_persona_data` (#112) | `content_based` | `[125, 156, 167, 127, 176]` | `[300, 256, 341, 346, 255]` | **EXACT MATCH (100%)** |
| `official_persona_devops` (#113) | `content_based` | `[179, 139, 138, 126, 197]` | `[270, 312, 259, 309, 311]` | **EXACT MATCH (100%)** |
| `official_persona_frontend` (#108) | `content_based` | `[24, 155, 6, 130, 132]` | `[330, 337, 297, 28, 29]` | **EXACT MATCH (100%)** |
| `official_persona_fullstack` (#110) | `content_based` | `[155, 151, 15, 145, 144]` | `[286, 276, 66, 320, 285]` | **EXACT MATCH (100%)** |
| `official_persona_mobile` (#114) | `content_based` | `[190, 150, 149, 10, 151]` | `[323, 282, 278, 320, 280]` | **EXACT MATCH (100%)** |
| `official_persona_new` (#107) | `latest` | `[124, 125, 126, 127, 129]` | `[374, 373, 372, 371, 370]` | **EXACT MATCH (100%)** |

**Kết luận:** **`ISSUE-009` (P1) ĐÃ KHẮC PHỤC HOÀN TOÀN** trên staging với độ tương đương 16/16 (100%) và tốc độ warm nhanh hơn **134.4×**.
