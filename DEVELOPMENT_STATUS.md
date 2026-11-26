# DEVELOPMENT STATUS — EduSuggest QA

## GĐ6.3 — Controlled Production Deployment & Scientific Recommendation Evaluation — 2026-11-27

- **Trạng thái:** **HOÀN TẤT 100% GĐ6.3A–D: GIẢI QUYẾT REGRESSION BLOCKER (`274/274 PASS`), NÂNG CẤP CONTENT-HASH CACHE, TRIỂN KHAI CÓ KIỂM SOÁT LÊN PRODUCTION (`5173`/`8000`/`EduSuggest`) VÀ HOÀN THÀNH ĐÁNH GIÁ KHOA HỌC THUẬT TOÁN GỢI Ý. DỪNG LẠI CHỜ PHÊ DUYỆT GĐ6.4 — AUTOMATIC EXPERT ASSIGNMENT ACCEPTANCE.**
- **GĐ6.3A (Regression Blocker Resolution):** Xác định nguyên nhân gốc lỗi `test_phase383_abrupt_worker_recovery.py` là tiến trình worker mồ côi `stage-0056473c` (PID `23680`/`10460`) từ GĐ3 tranh chấp job trên `EduSuggest_phase3_test`; đã dừng tiến trình mồ côi và chạy `EDUSUGGEST_TEST_DB_NAME=EduSuggest_phase4_test` (giữ `EduSuggest_phase3_test` ở `c3d4e5f6a7b8` cho `test_h06`). Kết quả: `test_phase383` **3/3 PASS liên tiếp** + Full Backend Regression **`274/274 PASS` (`161.26s`, 0 FAIL, 0 SKIPPED)**.
- **GĐ6.3B (Cache Audit & Mathematical Equivalence):** Nâng cấp `_course_corpus_fingerprint` và `_material_corpus_fingerprint` sang PostgreSQL content-hash `md5(string_agg(...))` bao phủ 100% cột văn bản/trạng thái + `RLock` + giới hạn bộ nhớ (`5.70 MB` sau 15 rebuild) + kiểm thử `test_phase63_cache_and_metrics.py` (`3/3 PASS`). Tương đương toán học 8 Official Personas: **`max_score_abs_diff = 0.0`** (`tolerance = 1e-12`).
- **GĐ6.3C (Controlled Production Deployment `5173`/`8000`):** Backup đầy đủ `backups/phase63-pre-deploy-20261127/` (`EduSuggest.pre-phase63.dump` restore verify PASS trên DB tạm, `private-storage-pre-phase63.zip`, `deployed-source-phase63.zip`, `SHA256SUMS.txt`, rollback manifest). Ẩn khóa nháp `#27` trên `EduSuggest` (`0` enrollments/history/orders), restart Production Backend `8000` giữ nguyên toàn bộ Feature Flags. Kiểm chứng Production READ-ONLY: **Recommendation HTTP Warm p50 = `101.71 ms`, p95 = `144.50 ms`, Cold = `346.13 ms`** (**149.8× nhanh hơn** GĐ6.1); `/courses/6` đúng FPT & `5 bài giảng` (`0` rò rỉ); `120/120` WebP `image/webp`; `150/150 LEGACY ACTIVE` & `300` history nguyên vẹn; Playwright `5173` `0px` overflow & `0` page errors.
- **GĐ6.3D (Scientific Recommendation Evaluation):** Pipeline tái lập `backend/scripts/phase63_scientific_rec_eval.py` (READ-ONLY trên Official Dataset V2, nhãn liên quan độc lập 24 danh mục). Courses (7 Personalized Personas): TF-IDF + Cosine đạt `P@5=0.1429`, `HR@5=0.5714`, `NDCG@5=0.1671`, `MRR@5=0.3857`, **`Coverage@10=57.43%`** (vượt trội `Latest` `0.0000` / `10.89%` coverage; báo cáo trung thực `Popularity` cao hơn ở `P@5=0.3714` nhưng không cá nhân hóa `Coverage@10=10.89%`). Xuất đầy đủ JSON, CSV, 4 biểu đồ `matplotlib` và 8 Persona Case Studies.
- Hồ sơ bàn giao: [EDUSUGGEST_PHASE6_REGRESSION_BLOCKER_RESOLUTION_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_REGRESSION_BLOCKER_RESOLUTION_REPORT.md), [EDUSUGGEST_PHASE6_RECOMMENDATION_CACHE_ACCEPTANCE_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_RECOMMENDATION_CACHE_ACCEPTANCE_REPORT.md), [EDUSUGGEST_PHASE6_CONTROLLED_PRODUCTION_DEPLOYMENT_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_CONTROLLED_PRODUCTION_DEPLOYMENT_REPORT.md), [EDUSUGGEST_PHASE6_SCIENTIFIC_RECOMMENDATION_EVALUATION_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_SCIENTIFIC_RECOMMENDATION_EVALUATION_REPORT.md), [EDUSUGGEST_PHASE6_RECOMMENDATION_BASELINE_COMPARISON_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_RECOMMENDATION_BASELINE_COMPARISON_REPORT.md), [EDUSUGGEST_PHASE6_RECOMMENDATION_CASE_STUDIES.md](docs/reports/EDUSUGGEST_PHASE6_RECOMMENDATION_CASE_STUDIES.md), [EDUSUGGEST_PHASE6_FINAL_PERFORMANCE_BENCHMARK_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_FINAL_PERFORMANCE_BENCHMARK_REPORT.md), [production-phase63-rollback-manifest.json](docs/reports/production-phase63-rollback-manifest.json).

## GĐ6.2 — Core Performance Optimization, Functional Fixes & Comprehensive UI/UX Polish (Staging) — 2026-11-27

- **Trạng thái:** **HOÀN TẤT TOÀN BỘ TỐI ƯU HIỆU NĂNG, KHẮC PHỤC 2 LỖI P1, HOÀN THIỆN UI/UX & PLAYWRIGHT E2E TRÊN MÔI TRƯỜNG STAGING ĐỘC LẬP (`http://127.0.0.1:5177/` ↔ `http://127.0.0.1:8004/api`, DB `edusuggest_phase62_staging`). PRODUCTION `EduSuggest` GIỮ NGUYÊN 100% READ ONLY — DỪNG CHỜ PHÊ DUYỆT TRIỂN KHAI GĐ6.3.**
- **`ISSUE-009` (P1 – Recommendation Engine Performance):** Khử nút thắt cổ chai `O(N²)` re-tokenization trong `content_recommendation.py` + bổ sung thread-safe, DB-isolated, fingerprint-validated corpus cache trong `recommendation_service.py` (**bảo toàn 100% công thức TF-IDF & Cosine Similarity**).
  - `recommend_courses` Warm p50: **`15,232 ms → 113.31 ms`** (**134.4× nhanh hơn**, p95 `166.68 ms`, cold `584.02 ms`, 8-thread stampede `0` lỗi, RAM `6.83 MB`).
  - **Exact Equivalence 8 Official Personas (READ-ONLY trên Production `EduSuggest`):** **`16/16` (100%)** khớp tuyệt đối Top-5 Khóa học & Tài liệu.
- **`ISSUE-002` (P1 – Public Course Detail):** Bổ sung `tenNhaCungCap`, `soLuongBaiHoc`, `deCuongCongKhai` vào `CourseDetailResponse` & `CourseDetail.vue` (giữ `baiHocs = []`, 0 rò rỉ nội dung trả phí/video). `/courses/6` hiển thị `"Học viện Phần mềm FPT"`, `"5 bài giảng"` và 5 bài đề cương khóa.
- **UI/UX Polish (`emil-design-eng`, `impeccable`, `design-taste-frontend`) & Data Fixes:**
  - `ISSUE-001` (P2): Sửa tràn ngang mobile bằng `min-w-0`, `minmax(0,1fr)`, responsive typography → **`0px` overflow** trên toàn bộ 7 viewport (`320px–1920px`).
  - `ISSUE-003` (P2): Ảnh bìa `CourseCard.vue` chuẩn `aspect-video` 16:9 sạch, đưa badge Danh mục & Trình độ vào thân thẻ trắng.
  - `ISSUE-006` (P2): Khôi phục Header 2 tầng gọn nhẹ (`UserHeader.vue`) cho trang con, tự ẩn trên Homepage/Checkout/Auth.
  - `ISSUE-004` (P2): Ẩn khóa nháp `#27` trên `edusuggest_phase62_staging` ONLY; `ISSUE-005` đóng (`0.097 ms`, 84% selectivity); `ISSUE-007` giữ `#31`/`#132` ở `HIDDEN`/`PENDING`.
- **Kiểm chứng:** Playwright Interactive E2E (`ISSUE-008`) PASS đủ 4 vai trò (`USER`, `ADMIN`, `PROVIDER`, `EXPERT`) + YouTube embed `804×451` + `0` page errors + 11 ảnh chụp After; Backend `test_phase62_perf_and_public_course.py` **2/2 PASS** (tổng `270/271` PASS); Frontend Vite production build **PASS** (`1,912 modules`, `1.83s`).
- Hồ sơ bàn giao: [EDUSUGGEST_PHASE6_RECOMMENDATION_PERFORMANCE_OPTIMIZATION_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_RECOMMENDATION_PERFORMANCE_OPTIMIZATION_REPORT.md), [EDUSUGGEST_PHASE6_FUNCTIONAL_FIXES_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_FUNCTIONAL_FIXES_REPORT.md), [EDUSUGGEST_PHASE6_UI_UX_POLISH_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_UI_UX_POLISH_REPORT.md), [EDUSUGGEST_PHASE6_PLAYWRIGHT_E2E_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_PLAYWRIGHT_E2E_REPORT.md), [EDUSUGGEST_PHASE6_VISUAL_ACCEPTANCE_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_VISUAL_ACCEPTANCE_REPORT.md), [EDUSUGGEST_PHASE6_CONTROLLED_DEPLOYMENT_PLAN.md](docs/reports/EDUSUGGEST_PHASE6_CONTROLLED_DEPLOYMENT_PLAN.md), [phase62-visual-comparison-gallery.html](docs/reports/phase62-visual-comparison-gallery.html), [EDUSUGGEST_PHASE6_ISSUE_REGISTRY.json](docs/reports/EDUSUGGEST_PHASE6_ISSUE_REGISTRY.json).

## GĐ6.1 — Comprehensive System Audit & Functional Acceptance — 2026-11-27

- **Trạng thái:** **HOÀN TẤT KIỂM TOÁN TOÀN DIỆN HỆ THỐNG (PRODUCTION 100% READ ONLY, KHÔI PHỤC CHỤP ẢNH CHROME HEADLESS CÔ LẬP, ĐO HIỆU NĂNG/BẢO MẬT THỰC TẾ, 269/269 BACKEND PASS, VITE BUILD PASS). DỪNG CHỜ PHÊ DUYỆT GĐ6.2.**
- **Khôi phục Browser Automation:** Khôi phục chụp ảnh trình duyệt thật bằng Chrome `--headless=new` với profile cô lập (`media/phase6-audit/isolated-browser-profile`) → xuất và kiểm tra trực quan `7/7` ảnh PNG (`1440px`, `768px`, `375px`). *(Interactive click-flow & video playback cần Playwright ở GĐ6.2.)*
- **Phát hiện thực tế (`9` issues: `0 P0`, `2 P1`, `6 P2`, `1 P3`):**
  - **P1 (`ISSUE-009`):** Đo thực tế `recommend_courses` mất `p50 = 15,232 ms` (max `18,277 ms`) do tính lại TF-IDF không cache + N+1 trên 421 bài học V2; đề xuất cache RAM + eager-load ở GĐ6.6 (giữ nguyên công thức TF-IDF).
  - **P1 (`ISSUE-002`):** `CourseDetail.vue` hiển thị `0 bài giảng` và thiếu tên nhà cung cấp cho khách chưa đăng nhập do public API chưa trả `soLuongBaiHoc` và tên từ `NhaCungCapKhoaHoc → NguoiDung`.
  - **P2:** Tràn ngang mobile `375px` trên `UserHome.vue` (`ISSUE-001`), badge đè góc ảnh bìa WebP trên `CourseCard.vue` (`ISSUE-003`), tiêu đề `#27` còn `(Khóa học đang biên soạn)` (`ISSUE-004`), `Seq Scan` trên `KhoaHoc` (`ISSUE-005`), xác nhận Header 1/2 tầng (`ISSUE-006`), `#31`/`#132` giữ `HIDDEN`/`PENDING` (`ISSUE-007`).
- **Kiểm chứng:** Static security scan (`0` `v-html`, `0` raw f-string SQL, `0` hardcoded URL) + `10/10` live security probes PASS; **`269/269` Backend Regression PASS** (`106.04s`, `0 FAIL`, `0 SKIPPED`); Frontend Vite build **PASS** (`1,912 modules`, `2.06s`).
- Hồ sơ bàn giao: [EDUSUGGEST_PHASE6_COMPREHENSIVE_SYSTEM_AUDIT_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_COMPREHENSIVE_SYSTEM_AUDIT_REPORT.md), [EDUSUGGEST_PHASE6_FUNCTIONAL_COVERAGE_MATRIX.md](docs/reports/EDUSUGGEST_PHASE6_FUNCTIONAL_COVERAGE_MATRIX.md), [EDUSUGGEST_PHASE6_UI_UX_AUDIT_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_UI_UX_AUDIT_REPORT.md), [EDUSUGGEST_PHASE6_SECURITY_AUDIT_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_SECURITY_AUDIT_REPORT.md), [EDUSUGGEST_PHASE6_PERFORMANCE_AUDIT_REPORT.md](docs/reports/EDUSUGGEST_PHASE6_PERFORMANCE_AUDIT_REPORT.md), [EDUSUGGEST_PHASE6_RECOMMENDATION_EVALUATION_PLAN.md](docs/reports/EDUSUGGEST_PHASE6_RECOMMENDATION_EVALUATION_PLAN.md), [EDUSUGGEST_PHASE6_ISSUE_REGISTRY.json](docs/reports/EDUSUGGEST_PHASE6_ISSUE_REGISTRY.json), [EDUSUGGEST_PHASE6_IMPLEMENTATION_ROADMAP.md](docs/reports/EDUSUGGEST_PHASE6_IMPLEMENTATION_ROADMAP.md).

## GĐ5.5 — Final Dataset Acceptance, Official Content Deployment & Official Dataset V2 Release — 2026-11-27

- **Trạng thái:** **HOÀN TẤT NGHIỆM THU CUỐI CÙNG, TRIỂN KHAI CHÍNH THỨC 346 BÀI HỌC GĐ5.4 LÊN PRODUCTION `EduSuggest` (`http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api`) VÀ PHÁT HÀNH CHÍNH THỨC `edusuggest-official-v2`. DỪNG LẠI CHỜ PHÊ DUYỆT GĐ6.1.**
- **Backup & Official Production Deployment:** Sao lưu `EduSuggest.pre-phase55.dump` (`240,825 bytes`, restore verify PASS trên `edusuggest_phase55_backup_verify`), `media_courses_pre_phase55.zip` (`8.38 MB`), `private_storage_pre_phase55.zip` (`277 KB`). Áp dụng nguyên tử `346` bài học đã kiểm chứng (`0` xung đột, kèm `prod-phase54-rollback.json`): `421/421` bài học nội dung duy nhất (TB `1,414.7` ký tự), `65` bài video hợp lệ đúng chủ đề (`0` video chết, `0` video lệch chủ đề), bảo toàn `35` bảng (`e5f6a7b8c9d0`), `120/120` WebP `HTTP 200` & `image/webp`, `150/150 LEGACY ACTIVE`, `300` lịch sử học tập, giữ `#31` & `#132` ở `HIDDEN`/`PENDING`.
- **Official Dataset V2 (`20261127-official-v2-snapshot/`, giữ nguyên V1):** `EduSuggest-official-v2.custom.dump` (`254,958 bytes`, restore verify PASS trên `edusuggest_official_v2_verify`), `media-v2.zip` (`8.98 MB`), `private-storage-v2.zip` (`277 KB`), `SHA256SUMS.txt` và toàn bộ manifest provenance/attribution.
- **Kiểm chứng toàn hệ thống:** Recommendation 8 Official Personas trên Production (`Top-5`/`Top-10`) đạt **`0` rò rỉ `HIDDEN`/`PENDING`**; **`269/269` Backend Regression PASS** (`120.08s`, `0 FAIL`, `0 SKIPPED`, gồm 3 test mới GĐ5.5); Frontend Vite build **PASS** (`1,912 modules`, `3.36s`); Browser Automation **`NOT TESTED (BLOCKED)`** (`DevToolsActivePort ENOENT`).
- Hồ sơ bàn giao: [EDUSUGGEST_PHASE5_FINAL_DATASET_ACCEPTANCE_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_FINAL_DATASET_ACCEPTANCE_REPORT.md), [EDUSUGGEST_PHASE5_OFFICIAL_CONTENT_DEPLOYMENT_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_OFFICIAL_CONTENT_DEPLOYMENT_REPORT.md), [EDUSUGGEST_OFFICIAL_DATASET_V2_REPORT.md](docs/reports/EDUSUGGEST_OFFICIAL_DATASET_V2_REPORT.md), [EDUSUGGEST_OFFICIAL_DATASET_V2_RESTORE_GUIDE.md](docs/reports/EDUSUGGEST_OFFICIAL_DATASET_V2_RESTORE_GUIDE.md), [EDUSUGGEST_FINAL_RECOMMENDATION_EVALUATION_REPORT.md](docs/reports/EDUSUGGEST_FINAL_RECOMMENDATION_EVALUATION_REPORT.md).

## GĐ5.4 — Official GĐ5.3 Deployment & Staging Learning Content Enhancement — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRIỂN KHAI CHÍNH THỨC GĐ5.3 LÊN PRODUCTION `EduSuggest` (`421` BÀI HỌC, `120/120` WEBP `HTTP 200` & `image/webp`) VÀ HOÀN TẤT NÂNG CẤP 346 BÀI HỌC GĐ5.4 TRÊN STAGING ĐỘC LẬP `edusuggest_phase54_staging`. DỪNG CHỜ PHÊ DUYỆT GĐ5.5 — KHÔNG GHI NỘI DUNG GĐ5.4 LÊN PRODUCTION.**
- **Official GĐ5.3 Production Deployment:** Backup đầy đủ (`EduSuggest.pre-phase54.dump`, `media_v5_pre_phase54.zip`, `private_materials_pre_phase54.zip`, restore verify PASS trên `edusuggest_phase54_backup_verify`), áp dụng nguyên tử 16 thay đổi: khôi phục khóa `#31` (*"Kiểm thử API thực chiến với Postman"*, `+10` bài học, ảnh bìa WebP mới, giữ nguyên `HIDDEN`/`PENDING`), sửa `#29` (`180 → 300 phút`), sửa `#110`/`#98`, chuẩn hóa Provider `#5`. Bảo toàn 100% `150/150 LEGACY ACTIVE`, `300` lịch sử học tập, `0` dữ liệu GĐ5.4 chạm Production.
- **GĐ5.4 Staging Learning Content Enhancement (`edusuggest_phase54_staging`):**
  - Kiểm toán trực tiếp `135` bài video qua YouTube oEmbed: giữ **`65`** bài video hợp lệ đúng chủ đề (`oEmbed 200 OK`), gỡ **`20`** video chết `404` và **`50`** video SQL gán lệch chủ đề, chuyển sang bài đọc/thực hành hoàn chỉnh.
  - Cải thiện **`346 / 421`** bài học với nội dung chuẩn hóa theo đúng công nghệ khóa học & nguồn tham khảo chính thức; xác minh **`121 / 121`** tệp `private://` tồn tại & không rỗng (ghi nhận `TaiLieu #132` rác `"hi"/"gsdfsd"` cho GĐ5.5).
  - Gia cố `LearningView.vue` (allowlist iframe `youtube-nocookie.com` & chống XSS).
- **Kiểm chứng:** Recommendation 8 Official Personas trên Staging giữ nguyên 100% chiến lược (`7` `content_based`, `1` `latest`); Frontend Vite build **PASS** (`1,912 modules`, `3.93s`); Full Backend Regression (`EduSuggest_phase4_test`) **`266/266 PASS`** (`129.84s`); Production `5173`/`8000` và Staging `5176`/`8003` đều `200 OK`.
- Hồ sơ bàn giao: [EDUSUGGEST_PHASE5_OFFICIAL_STANDARDIZATION_DEPLOYMENT_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_OFFICIAL_STANDARDIZATION_DEPLOYMENT_REPORT.md), [EDUSUGGEST_PHASE5_LEARNING_CONTENT_ENHANCEMENT_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_LEARNING_CONTENT_ENHANCEMENT_REPORT.md), [EDUSUGGEST_PHASE5_VIDEO_SOURCE_VERIFICATION_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_VIDEO_SOURCE_VERIFICATION_REPORT.md), [EDUSUGGEST_PHASE5_MATERIAL_QUALITY_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_MATERIAL_QUALITY_REPORT.md), [learning-content-comparison-gallery.html](docs/reports/learning-content-comparison-gallery.html), [learning-content-provenance.json](docs/reports/learning-content-provenance.json), [learning-content-diff.json](docs/reports/learning-content-diff.json), [learning-content-rollback-manifest.json](docs/reports/learning-content-rollback-manifest.json).

## GĐ5.3 — Realistic Dataset Standardization & Content Quality (Staging) — 2026-11-26

- **Trạng thái:** **HOÀN TẤT CHUẨN HÓA DATASET TRÊN STAGING ĐỘC LẬP `edusuggest_phase53_staging` (`16` THAY ĐỔI CÓ DIFF & ROLLBACK MANIFEST, 8/8 PERSONA RECOMMENDATION ỔN ĐỊNH 100%, VITE BUILD PASS, 266/266 BACKEND PASS). PRODUCTION `EduSuggest` GIỮ NGUYÊN 100% READ ONLY — DỪNG CHỜ PHÊ DUYỆT TRIỂN KHAI.**
- **Chuẩn hóa trên `edusuggest_phase53_staging` (`backend/scripts/phase53_standardize_staging.py`):**
  - Khôi phục khóa `#31` (xác nhận `0` tham chiếu trên 10 bảng) → *"Kiểm thử API thực chiến với Postman"* (`399,000 ₫`, `320 phút`, `+10` bài học thực chiến Postman/Newman, ảnh bìa WebP QA mới), giữ nguyên **`HIDDEN` + `PENDING`** chờ kiểm duyệt hợp lệ.
  - Sửa khóa `#29` (`thoiLuong`: `180 → 300 phút` khớp tổng 5 bài học); sửa 2 URL tài liệu chết (`#110` Atlassian Jira `200 OK`, `#98` OWASP WSTG `200 OK` kèm cập nhật metadata); cập nhật hồ sơ mô phỏng nhà cung cấp `#5` (`"h"` → mô tả chuẩn khớp 12 khóa).
  - Giải trình đối chiếu Chuyên gia `20 vs 21`: `20` tài khoản role `EXPERT` (`13 VERIFIED`, `7 DRAFT`) + `1` bản ghi `ChuyenGia #4` (`linhphuong123`, role `USER`, trạng thái `DRAFT`).
- **Frontend hiển thị dữ liệu (`courseDisplay.js`, `CourseCard.vue`, `CourseDetail.vue`):** Chuẩn hóa nhãn cấp độ tiếng Việt thống nhất (`Cơ bản`, `Trung cấp`, `Nâng cao`, `Mọi cấp độ`) không làm ảnh hưởng TF-IDF; hiển thị tách bạch **"Thời lượng học ước tính"** và **"Tổng bài giảng"**.
- **Kiểm chứng:** 8/8 Official Personas Recommendation (khóa học & tài liệu) trước/sau ổn định 100%; Frontend Vite build **PASS** (`1,912 modules`, `2.17s`); Full Backend Regression (`EduSuggest_phase4_test`) **`266/266 PASS`** (`91.20s`); Production `EduSuggest` giữ nguyên 100% READ ONLY.
- Hồ sơ bàn giao: [EDUSUGGEST_PHASE5_DATASET_STANDARDIZATION_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_DATASET_STANDARDIZATION_REPORT.md), [EDUSUGGEST_PHASE5_COURSE_CONTENT_AUDIT_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_COURSE_CONTENT_AUDIT_REPORT.md), [EDUSUGGEST_PHASE5_LEARNING_CONTENT_ENHANCEMENT_PLAN.md](docs/reports/EDUSUGGEST_PHASE5_LEARNING_CONTENT_ENHANCEMENT_PLAN.md), [dataset-refinement-diff.json](docs/reports/dataset-refinement-diff.json), [dataset-refinement-rollback-manifest.json](docs/reports/dataset-refinement-rollback-manifest.json).

## GĐ5.2 — Official Course Cover Deployment & Dataset Refinement Plan — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRIỂN KHAI CHÍNH THỨC 120/120 ẢNH BÌA WEBP `1280×720` LÊN PRODUCTION `EduSuggest` (`http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api`). DỪNG LẠI CHỜ PHÊ DUYỆT GĐ5.3 CHO KẾ HOẠCH CẢI THIỆN DỮ LIỆU NỘI DUNG.**
- **Hoàn thiện 6 ảnh bìa cuối & Final Visual Audit (`120/120 PASS`):** Thay thế sạch `#29, #136, #142, #176, #177, #179` bằng ảnh chụp thực tế đúng chủ đề; xác minh `24/24` trang nguồn gốc `Public Domain Mark 1.0`, `CC BY 2.0`, `CC BY-SA 2.0` trả `HTTP 200 OK`; tổng `7.92 MB` (TB `69.2 KB`/ảnh, `stocksnap`: 69, `rawpixel`: 26, `flickr`: 25).
- **Backup & Versioned Deployment:** Sao lưu `EduSuggest.pre-phase52.dump` (`239,865 bytes`, SHA-256 `B049EE81...`, restore kiểm chứng trên `edusuggest_phase52_backup_verify` **PASS** 35 bảng / 120 khóa / 150 LEGACY ACTIVE / 300 lịch sử) + `media_courses_pre_phase52.zip` (`595,071 bytes`). Triển khai nguyên tử vào thư mục versioned `media/courses/v5-realistic/` (giữ nguyên 100% `119` `.svg` + `1` `.jpg` cũ), bổ sung `mimetypes.add_type("image/webp", ".webp")` trong `backend/main.py`.
- **Kiểm chứng thực tế:** Production `8000` trả **`120/120 HTTP 200`** và **`120/120 MIME image/webp`**, `0` orphan files, bảo toàn `150/150 LEGACY ACTIVE` & `300` lịch sử học tập; Frontend Vite build **PASS** (`1,911 modules`, `6.76s`); Full Backend Regression (`EduSuggest_phase4_test`) **`266/266 PASS`** (`109.61s`); Staging `5176`/`8003` hoạt động `200 OK`.
- **Kế hoạch cải thiện dữ liệu GĐ5.3 (READ ONLY, chờ phê duyệt):** Đã hoàn tất kiểm toán chi tiết khóa rác `#31` (`0` tham chiếu trên 10 bảng), 86 khóa lệch thời lượng, phân loại 411 bài học, xác minh 2 URL tài liệu thay thế (`200 OK`) & 5 URL MySQL chống bot (`403`), nhà cung cấp `#5` (`h`/`h`), và phương án chuẩn hóa hiển thị `trinhDo` không ảnh hưởng TF-IDF.
- Hồ sơ bàn giao: [EDUSUGGEST_PHASE5_OFFICIAL_COVER_DEPLOYMENT_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_OFFICIAL_COVER_DEPLOYMENT_REPORT.md), [EDUSUGGEST_PHASE5_DATASET_REFINEMENT_PLAN.md](docs/reports/EDUSUGGEST_PHASE5_DATASET_REFINEMENT_PLAN.md), [COURSE_COVER_SOURCE_ATTRIBUTION.md](docs/reports/COURSE_COVER_SOURCE_ATTRIBUTION.md), [course-cover-manifest.json](docs/reports/course-cover-manifest.json), [course-cover-comparison-gallery.html](docs/reports/course-cover-comparison-gallery.html).

## GĐ5.1 — Realistic Course Cover Dataset & Data Quality Audit — 2026-11-26

- **Trạng thái:** **HOÀN TẤT PIPELINE TỰ ĐỘNG 120 ẢNH BÌA, STAGING DB ĐỘC LẬP, GALLERY SO SÁNH & KIỂM TOÁN CHẤT LƯỢNG DỮ LIỆU. DỪNG CHỜ PHÊ DUYỆT BỘ ẢNH MỚI TRƯỚC KHI CẬP NHẬT PRODUCTION `EduSuggest`.**
- **Pipeline tự động (`backend/scripts/phase5_cover_pipeline.py`):** Truy xuất 120 ảnh thực tế duy nhất từ **Openverse API** (`license_type=modification`, ưu tiên `stocksnap`/`rawpixel`/`wordpress`, dự phòng Wikimedia Commons), xác minh giấy phép mở (`CC0 1.0`: 94, `CC BY 2.0`: 19, `PDM 1.0`: 4, `CC BY-SA 2.0`: 3), chống trùng lặp 3 lớp (`120/120` URL & SHA-256 duy nhất, `min dHash HD = 13`), tạo `1280×720` (16:9) WebP (tổng `8.00 MB`, TB `68.2 KB`/ảnh) trên 6 bố cục Editorial EdTech Modernism.
- **Visual Audit (2 vòng trên 4 Contact Sheets):** Vòng 1 thay thế sạch 59 ảnh lệch chủ đề; vòng 2 đạt **`114/120` ảnh đạt chuẩn ngay lập tức**, ghi nhận trung thực **`6/120`** ảnh nền còn lệch nhẹ (`#29, #136, #142, #176, #177, #179`) có thể thay nhanh bằng 1 lệnh trước khi áp dụng Production.
- **Staging & An toàn Production:** Tạo Staging DB độc lập `EduSuggest_phase5_cover_staging` (`120/120` → `.webp`), `apply_phase5_covers.py --dry-run` **PASS** (kèm `rollback-manifest.json`). Production `EduSuggest` giữ nguyên **100% READ ONLY** (`119` `.svg` + `1` `.jpg`, `150/150 LEGACY ACTIVE`, `300` lịch sử).
- **Data Quality Audit (READ ONLY):** `114/121` URL tài liệu ngoài `200 OK` (2 URL chết, 5 URL MySQL trả 403 bot-filter), `0` lỗi thứ tự bài học / lịch sử học tập / đánh giá; ghi nhận khóa rác `#31`, nhà cung cấp placeholder `#5`, lệch `trinhDo` Anh/Việt, lệch thời lượng trên `86/120` khóa để đề xuất xử lý riêng.
- Hồ sơ bàn giao: [EDUSUGGEST_PHASE5_REALISTIC_COVER_DATASET_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_REALISTIC_COVER_DATASET_REPORT.md), [EDUSUGGEST_PHASE5_DATA_QUALITY_AUDIT_REPORT.md](docs/reports/EDUSUGGEST_PHASE5_DATA_QUALITY_AUDIT_REPORT.md), [COURSE_COVER_SOURCE_ATTRIBUTION.md](docs/reports/COURSE_COVER_SOURCE_ATTRIBUTION.md), [course-cover-manifest.json](docs/reports/course-cover-manifest.json), [course-cover-comparison-gallery.html](docs/reports/course-cover-comparison-gallery.html).

## GĐ4.7C — Official Marketplace Activation on Production (Gateways OFF) — 2026-11-26

- **Trạng thái:** **HOÀN TẤT KÍCH HOẠT MARKETPLACE CHÍNH THỨC TRÊN `http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api` (`COMMERCE_ENROLLMENT_GATE_ENABLED=True`, ĐÓNG COM-01, TOÀN BỘ CỔNG THANH TOÁN & WORKER TÀI CHÍNH VẪN TẮT).**
- **Tách bạch & Gia cố UI:** Xác nhận `GET /api/commerce/capabilities` tách độc lập `marketplaceEnabled`/`enrollmentGateEnabled` khỏi `mockPaymentEnabled`/`vnpaySandboxEnabled`; gia cố `CheckoutView.vue` chặn tạo đơn mồ côi khi chưa có cổng thanh toán và hiển thị thông báo rõ ràng trạng thái chưa mở cổng thanh toán trực tuyến.
- **Tính năng đã kích hoạt trên Production `5173`/`8000`:** Icon Yêu thích (Header + `CourseCard`), Icon Giỏ hàng + badge, `/wishlist`, `/cart`, Mua ngay, `/checkout`, `/orders`, `/orders/:id` + Báo cáo sự cố thanh toán, `/admin/commerce` (ADMIN), `/provider/sales` (PROVIDER) và **Commerce Enrollment Gate** chặn đăng ký trực tiếp khóa trả phí (**COM-01**).
- **Kiểm chứng thực tế:**
  - `GET http://127.0.0.1:8000/api/commerce/capabilities` → `marketplaceEnabled: true`, `enrollmentGateEnabled: true`, `mockPaymentEnabled: false`, `vnpaySandboxEnabled: false`, `orderTtlMinutes: 15`.
  - Production `EduSuggest` (`e5f6a7b8c9d0`, `35` bảng): bảo toàn 100% `24` danh mục, `120` khóa học (`97` có phí, `23` miễn phí), `411` bài học, `243` tài liệu, `78` tài khoản, **`150/150 LEGACY ACTIVE`**, `300` lịch sử học tập, **`120/120` ảnh bìa `HTTP 200`**, `0` đơn/giao dịch giả.
  - Frontend Vite build **PASS** (`1,911 modules`, `3.58s`); Full Backend Regression (`EduSuggest_phase4_test`) **266/266 PASS** (`92.04s`); Staging Marketplace `5176`/`8003` (`mockPaymentEnabled: true`) và Dataset Staging `5175`/`8002` hoạt động ổn định (`200 OK`).
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_OFFICIAL_ACTIVATION_REPORT.md](docs/reports/EDUSUGGEST_PHASE4_OFFICIAL_ACTIVATION_REPORT.md).

## GĐ4.7B — Controlled Production Deployment (35 Tables, Gateways OFF) — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRIỂN KHAI CÓ KIỂM SOÁT LÊN PRODUCTION `EduSuggest` (`http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api`) VỚI TOÀN BỘ CỔNG THANH TOÁN & WORKER TÀI CHÍNH TẮT. DỪNG SAU GĐ4.7B.**
- **Backup & Restore Verification:** `EduSuggest.pre-phase47b.dump` (`174,109 bytes`, SHA-256 `C6C0B731...`, restore kiểm chứng trên `EduSuggest_phase47b_backup_verify` PASS), `media_courses.zip` (`595,071 bytes`, SHA-256 `4742BA22...`), `private_materials.zip` (`116,317 bytes`, SHA-256 `67531C96...`).
- **Production Migration:** Dừng đúng PID `22268`/`24856` (Production `8000`/`5173`), chạy nối chuỗi `c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0` trên `EduSuggest` → **35 bảng**, `Startup Schema Guard = True`, trigger `trg_sukienthanhtoan_append_only` hoạt động.
- **Bảo toàn dữ liệu 100% (`edusuggest-official-v1`):** `24` danh mục, `120` khóa học, `411` bài học, `243` tài liệu, `78` tài khoản, `150` đăng ký (`150/150 LEGACY ACTIVE`), `300` lịch sử học tập, `0` đơn hàng/giao dịch giả.
- **Runtime & Validation:** Production `8000`/`5173` chạy với `APP_ENV=production`, toàn bộ cờ thanh toán/tài chính/auto-assignment đều `False`; `/api/health` & `/api/commerce/capabilities` (`marketplaceEnabled=false`, `mockPaymentEnabled=false`, `vnpaySandboxEnabled=false`) & `100/100` ảnh bìa trả `200 OK`; Vite build **PASS** (`1,911 modules`, `1.43s`); Backend regression **266/266 PASS** trên `EduSuggest_phase4_test`. Staging Marketplace `5176`/`8003` và Dataset Staging `5175`/`8002` tiếp tục hoạt động bình thường (`200 OK`).
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_CONTROLLED_PRODUCTION_DEPLOYMENT_REPORT.md](docs/reports/EDUSUGGEST_PHASE4_CONTROLLED_PRODUCTION_DEPLOYMENT_REPORT.md).

## GĐ4.7A.3 — Final Financial Acceptance & Deployment Readiness — 2026-11-26

- **Trạng thái:** **HOÀN TẤT NGHIỆM THU TÀI CHÍNH CUỐI CÙNG (`266/266 BACKEND PASS`, `0 FAIL`, REAL OS WORKER PASS, `EduSuggest_phase47a3_rehearsal` 35 BẢNG PASS). DỪNG CHỜ PHÊ DUYỆT GĐ4.7B — CHƯA TRIỂN KHAI PRODUCTION.**
- **Lỗi nghiêm trọng đã phát hiện & sửa:** Sửa lỗi tràn số nguyên 32-bit `int4` trong `commerce_service._lock_user_course` (`(user_id * 1_000_000) + course_id` tràn ở `user_id >= 2148`) bằng khóa gốc `(int4, int4)` `pg_advisory_xact_lock(CAST(:u AS integer), CAST(:c AS integer))`; cô lập `test_phase33` và `test_phase38` qua `EDUSUGGEST_TEST_DB_NAME` (không sửa assertion/timeout, không chạm `EduSuggest_phase3_test`).
- **Kiểm chứng toàn diện:**
  - **Full Backend Regression (`EDUSUGGEST_TEST_DB_NAME=EduSuggest_phase4_test`):** **`266 collected / 266 PASSED / 0 FAILED / 0 SKIPPED / 0 XFAILED`** (`94.73s`) — 49/49 Marketplace & Financial Integrity PASS, 217/217 GĐ3/Core PASS.
  - **Real OS Worker Acceptance (`test_phase47a3_real_worker_process_acceptance.py`):** 2 tiến trình OS thực tế của `run_payment_reconciliation_worker.py` chạy song song (`SKIP LOCKED`), abrupt `kill()` + stale lease recovery (`leaseGeneration >= 2`), graceful `terminate()`, và xác minh 0 sử dụng `session_replication_role` trong mã runtime — **PASS**.
  - **Final Migration Rehearsal (`EduSuggest_phase47a3_rehearsal`):** Backup mới từ Production `EduSuggest` (`174,043 bytes`, SHA-256 `A8C47895...`), upgrade nối chuỗi `c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0` (`35` bảng, `schema_guard=True`, bảo toàn `24` danh mục, `120` khóa học, `411` bài học, `243` tài liệu, `78` tài khoản, `150` LEGACY ACTIVE, `300` lịch sử, `0` đơn giả) + diễn tập rollback trên bản sao sạch — **PASS**.
- **Quyết định GO/NO-GO:** (A) Staging Mock Marketplace: **CONDITIONAL GO** (chờ Browser thủ công do Chrome DevTools MCP `BLOCKED`); (B) Production 35 bảng với các gateway thanh toán TẮT: **CONDITIONAL GO** (chờ phê duyệt GĐ4.7B); (C) VNPay Sandbox trực tuyến: **BLOCKED/NO-GO**; (D) Giao dịch tiền thật: **NO-GO**.
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_FINAL_FINANCIAL_ACCEPTANCE_REPORT.md](EDUSUGGEST_PHASE4_FINAL_FINANCIAL_ACCEPTANCE_REPORT.md), [EDUSUGGEST_PHASE4_CONTROLLED_DEPLOYMENT_PLAN.md](EDUSUGGEST_PHASE4_CONTROLLED_DEPLOYMENT_PLAN.md), [EDUSUGGEST_PHASE4_PRODUCTION_READINESS_REPORT.md](EDUSUGGEST_PHASE4_PRODUCTION_READINESS_REPORT.md).

## GĐ4.7A.2 — Financial Integrity Schema & Durable Payment Recovery Implementation — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRIỂN KHAI TRÊN `EduSuggest_phase4_test` (`e5f6a7b8c9d0`, 35 BẢNG). DỪNG CHỜ PHÊ DUYỆT NGHIỆM THU CUỐI CÙNG — CHƯA TRIỂN KHAI PRODUCTION HOẶC GĐ4.7B.**
- **Migration mới (`e5f6a7b8c9d0`, single head nối tiếp `d4e5f6a7b8c9`, 30 → 35 bảng):**
  - Mở rộng `ThanhToan` (`daThuTien`, `soTienDaThuThucTe`, `CAPTURED_UNAPPLIED`, `PARTIALLY_REFUNDED` — không dùng `FAILED` cho giao dịch đã thu tiền).
  - Tạo 5 bảng tài chính chuẩn hóa: `HoanTienNgoaiLe`, `LanThuHoanTien`, `BaoCaoSuCoThanhToan`, `SuKienThanhToan` (có PostgreSQL trigger `trg_SuKienThanhToan_append_only` chặn `UPDATE`/`DELETE` ở tầng DB), `TacVuDoiSoatThanhToan`.
  - Backfill idempotent từ `ThanhToan.duLieuPhanHoiAnToan` (bảo toàn 100% JSONB gốc). Backup trước migration: `205,076 bytes` (SHA-256 `7E539870...`); diễn tập `upgrade → downgrade → re-upgrade` trên `EduSuggest_phase47a2_rehearsal` **PASS**.
- **Durable Payment Reconciliation Worker & VNPay Response Verification:**
  - Triển khai `service/payment_reconciliation_worker.py` + CLI độc lập `scripts/run_payment_reconciliation_worker.py` (3 pha `SKIP LOCKED` + lease + fencing token `claimToken`/`leaseGeneration` + exponential backoff + sweeper, zero DB lock khi gọi mạng, zero blind refund retry, 4 cờ mới mặc định `False`).
  - Bổ sung `verify_vnpay_querydr_response`, `verify_vnpay_refund_response`, `PARTIAL_OVERCHARGE`, `GET /api/orders/{id}/incidents` (owner-scoped), và cập nhật `schema_guard.py` fail-closed cho revision `e5f6a7b8c9d0`.
- **Kiểm chứng:** `test_phase47a2_financial_integrity_durable_recovery.py` **5/5 PASS** (`10.75s`); Full Backend Regression **`263/264 PASS`** (`89.54s` — **100% Marketplace & Financial Integrity 47/47 PASS**, `test_phase383` PASS; 1 FAIL ở `test_phase33` trên `EduSuggest_phase3_test` do tranh chấp với tiến trình staging worker GĐ3.8.3 nền); Frontend Vite build **PASS** (`1,911 modules`, `2.45s`).
- **Môi trường:** Staging `http://127.0.0.1:5176/` ↔ `http://127.0.0.1:8003/api` hoạt động trên 35 bảng (`e5f6a7b8c9d0`); Production `EduSuggest` (`c3d4e5f6a7b8`, `24` bảng) và `EduSuggest_phase3_test` (`c3d4e5f6a7b8`, `24` bảng) giữ nguyên 100%. VNPay Live Sandbox & Browser Automation vẫn `BLOCKED`.
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_FINANCIAL_INTEGRITY_IMPLEMENTATION_REPORT.md](EDUSUGGEST_PHASE4_FINANCIAL_INTEGRITY_IMPLEMENTATION_REPORT.md) và [EDUSUGGEST_PHASE4_DURABLE_PAYMENT_RECOVERY_IMPLEMENTATION_REPORT.md](EDUSUGGEST_PHASE4_DURABLE_PAYMENT_RECOVERY_IMPLEMENTATION_REPORT.md).

## GĐ4.7A.1 — Financial Integrity, Durable Payment Recovery & Regression Blocker Resolution — 2026-11-26

- **Trạng thái:** **HOÀN TẤT XỬ LÝ 8/8 LỖI HỒI QUY (259/259 BACKEND PASS) & HOÀN THÀNH HỒ SƠ THIẾT KẾ TÀI CHÍNH + DURABLE RECOVERY. DỪNG CHỜ PHÊ DUYỆT KIẾN TRÚC TÀI CHÍNH (CHƯA TẠO MIGRATION MỚI, CHƯA TRIỂN KHAI PRODUCTION).**
- **Xử lý 8/8 lỗi hồi quy Backend (không xóa test, không sửa assertion, không tăng timeout, không migrate `EduSuggest_phase3_test`):**
  - **7 tests** (`test_recommendation_integration.py` x6 + `test_private_file_security.py` x1): chạy sạch trên DB cô lập đã migrate `EduSuggest_phase4_test` (`d4e5f6a7b8c9`, 30 bảng) qua `EDUSUGGEST_TEST_DB_NAME` → **7/7 PASS** (0 hồi quy GĐ3).
  - **1 test** (`test_phase383_abrupt_worker_recovery.py`): xác định nguyên nhân gốc do tranh chấp với staging worker GĐ3.8.3 trên `EduSuggest_phase3_test` (worker nền hoàn tất job trong 299ms); mở allowlist kiểm thử cô lập `EduSuggest_phase4_test` trong `run_assignment_worker.py` (vẫn chặn cứng Production `EduSuggest`) → **PASS (`14.02s`)**.
  - **Full Backend Regression:** **`259 collected / 259 PASSED / 0 FAILED / 0 SKIPPED / 0 XFAILED` (`76.60s`)**.
- **Fail-Closed Startup Schema Guard (`backend/config/schema_guard.py` + `main.py`):** Chặn cứng Backend GĐ4 không thể âm thầm khởi động trên DB 24 bảng thiếu cột `DangKyKhoaHoc.maDonHang`/`trangThaiQuyenHoc` (`test_h06` PASS).
- **Cổng phê duyệt kiến trúc tài chính & phục hồi bền vững (chưa tạo migration):**
  - Thiết kế chuẩn hóa 4 bảng tài chính (`HoanTienNgoaiLe`, `LanThuHoanTien`, `BaoCaoSuCoThanhToan`, `SuKienThanhToan`), trạng thái `CAPTURED_UNAPPLIED` & `PARTIALLY_REFUNDED` (hỗ trợ hoàn một phần `PARTIAL_OVERCHARGE`), backfill JSONB không mất bằng chứng: [EDUSUGGEST_PHASE4_FINANCIAL_INTEGRITY_DESIGN_REPORT.md](EDUSUGGEST_PHASE4_FINANCIAL_INTEGRITY_DESIGN_REPORT.md).
  - Thiết kế Durable Payment Reconciliation Worker (`TacVuDoiSoatThanhToan`, lease + fencing token, backoff, QueryDR tự động, cấm retry hoàn tiền mù khi `UNKNOWN`, cờ mặc định `False`): [EDUSUGGEST_PHASE4_DURABLE_PAYMENT_RECOVERY_DESIGN_REPORT.md](EDUSUGGEST_PHASE4_DURABLE_PAYMENT_RECOVERY_DESIGN_REPORT.md).
  - Báo cáo xử lý 8 lỗi hồi quy: [EDUSUGGEST_PHASE4_REGRESSION_BLOCKER_RESOLUTION_REPORT.md](EDUSUGGEST_PHASE4_REGRESSION_BLOCKER_RESOLUTION_REPORT.md).
- **Trạng thái Production & Staging:** Production `EduSuggest` giữ nguyên **100% READ ONLY** (`c3d4e5f6a7b8`, `24` bảng, `120` khóa học, `150` đăng ký, `300` lịch sử); `EduSuggest_phase3_test` giữ nguyên `c3d4e5f6a7b8` (`24` bảng); Staging `5176`/`8003` đang hoạt động (`200 OK`). **NO-GO cho giao dịch tiền thật** đến khi triển khai xong kiến trúc tài chính + Durable Recovery Worker + nghiệm thu VNPay Sandbox & Browser E2E.

## GĐ4.7A — Final Marketplace Acceptance & Payment Safety Hardening — 2026-11-26

- **Trạng thái:** **HOÀN TẤT KIỂM TOÁN, GIA CỐ & DIỄN TẬP TRIỂN KHAI TRÊN MÔI TRƯỜNG KIỂM THỬ. DỪNG CHỜ PHÊ DUYỆT GĐ4.7B.**
- **Gia cố an toàn thanh toán (5 Hardening Fixes, 0 migration mới):**
  - `HARDEN-01`: Bắt buộc cả `vnp_ResponseCode == "00"` và `vnp_TransactionStatus == "00"` trong `VNPaySandboxPaymentProvider.verify_callback`.
  - `HARDEN-02`: Xác minh request fingerprint (`nguonTao` + `courseIds` cho `create_order`; `congThanhToan` cho `initiate_payment`) trên `Idempotency-Key` → trả `409 Conflict` nếu tái sử dụng key cho yêu cầu khác.
  - `HARDEN-03`: Chặn callback `FAILED`/non-PAID đến muộn ghi đè `fundsCaptured`/`auditTrail` trong `ThanhToan.duLieuPhanHoiAnToan`.
  - `HARDEN-04`: Fail-closed `HTTP 503` cho API Marketplace khi bảng chưa tồn tại trên DB 24 bảng (giữ `/api/commerce/capabilities` trả `200 OK`).
  - `HARDEN-05`: Sửa nhãn `isSimulated` trong thông báo `ORDER_PAID`.
- **Full Backend Regression (không bỏ sót test):** Tổng `258` tests (`250 PASS / 8 FAIL / 0 SKIPPED`):
  - **100% Marketplace GĐ4.1–GĐ4.7A PASS (`41/41`)**, gồm `5/5` GĐ4.7A stress/hardening (100x concurrent VNPay IPN callback replay, multi-order race, DB rollback, repurchase sau `FULL_ORDER` refund, fail-closed `503`).
  - **7 FAIL** (`test_recommendation_integration.py` x6 + `test_private_file_security.py` x1) trên `EduSuggest_phase3_test` (`c3d4e5f6a7b8`, 24 bảng) chứng minh thực nghiệm: **bắt buộc chạy migration `d4e5f6a7b8c9` trước khi deploy Backend GĐ4** (do ORM `DangKyKhoaHoc` truy vấn `maDonHang`/`trangThaiQuyenHoc`). **1 FAIL** (`test_phase383_abrupt_worker_recovery.py`) timeout worker 15s trên `EduSuggest_phase3_test`.
- **Backup & Migration Rehearsal (`EduSuggest_phase47a_rehearsal`):** Dump `EduSuggest.custom.dump` (`174,043 bytes`, SHA-256 `1232C6C0...`), single head `d4e5f6a7b8c9`, upgrade `c3d4e5f6a7b8 → d4e5f6a7b8c9` **PASS**, bảo toàn 100% (`24` danh mục, `120` khóa học, `411` bài học, `243` tài liệu, `78` tài khoản, `150` LEGACY ACTIVE, `300` lịch sử, `0` đơn giả). Production `EduSuggest` giữ nguyên **100% READ ONLY**.
- **Browser E2E & VNPay Live Sandbox:** Browser Automation `BLOCKED` (Chrome DevTools MCP `DevToolsActivePort ENOENT` — đã cung cấp manual checklist và giữ staging `5176`/`8003` chạy); VNPay Live Sandbox `BLOCKED` (thiếu credentials & public HTTPS IPN).
- **Quyết định GO/NO-GO:** (A) Staging Marketplace: **CONDITIONAL GO**; (B) Schema + UI lên Production (thanh toán TẮT, chạy migration trước Backend): **CONDITIONAL GO**; (C) VNPay Sandbox Live: **BLOCKED/NO-GO**; (D) Giao dịch tiền thật: **NO-GO** (còn Financial Schema Gaps & thiếu Durable Reconciliation Worker).
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_FINAL_ACCEPTANCE_REPORT.md](EDUSUGGEST_PHASE4_FINAL_ACCEPTANCE_REPORT.md), [EDUSUGGEST_PHASE4_PRODUCTION_READINESS_REPORT.md](EDUSUGGEST_PHASE4_PRODUCTION_READINESS_REPORT.md), [docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md](docs/EDUSUGGEST_PHASE4_MANUAL_BROWSER_ACCEPTANCE.md).

## GĐ4.6 — Commerce Management, Payment Safety & Exception Refund — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRÊN STAGING `EduSuggest_phase4_test` (137/137 Backend PASS, 30/30 kịch bản Payment Stress PASS, Vite Build PASS `1,911 modules`, Staging `5176`/`8003` đang hoạt động). DỪNG CHỜ PHÊ DUYỆT GĐ4.7.**
- **Chính sách & An toàn thanh toán:** Áp dụng mua một lần – sở hữu lâu dài (không có hoàn tiền đổi ý), nhưng hỗ trợ đầy đủ **Hoàn tiền ngoại lệ đã xác minh** (`PENDING_REVIEW → VERIFIED → REFUND_PENDING → REFUNDED | REFUND_FAILED | UNKNOWN`) chỉ do ADMIN khởi tạo. Gia cố `_record_reconciliation` lưu `fundsCaptured`, `capturedAmountVnd`, `reconciliationStatus`, `auditTrail` trong `ThanhToan.duLieuPhanHoiAnToan` để không bao giờ mất bằng chứng giao dịch thu trùng/IPN trễ; tách bạch `EXCESS_PAYMENT` (giữ nguyên đơn `PAID` + quyền học `ACTIVE` + không trừ nhầm doanh thu hợp lệ) với `FULL_ORDER` (thu hồi đúng `maDonHang` sang `REVOKED`, bảo toàn `DangKyKhoaHoc`, `LichSuHocTap` và `LEGACY`). Bổ sung bộ tạo payload chuẩn **VNPay API v2.1.0 QueryDR & Refund** (HMAC-SHA512 nối `|`) cùng lớp chặn không giả lập thành công (`409`). Không tạo migration mới; đã ghi nhận đề xuất schema cho thu tiền thật.
- **Backend & Frontend mới:** 14 endpoints mới (`api/commerce_admin.py`, `service/commerce_admin_service.py`, `schemas/commerce_admin.py`) cho USER Incident Report, ADMIN Commerce Workspace (Overview, Revenue, Orders, Transactions, Reconciliation Priority #1 Activate, Exception Refunds, Incidents) và PROVIDER Sales (owner-scoped, loại trừ `LEGACY`). Frontend bổ sung `AdminCommerceView.vue` (`/admin/commerce`), `ProviderSalesView.vue` (`/provider/sales`), cập nhật `PaymentResultView.vue`, `OrderDetailView.vue`, `AdminSidebar.vue`, `ProviderSidebar.vue`.
- **Kiểm chứng:** Backend **137/137 PASS** (`28.66s`, gồm `10/10` GĐ4.6 stress/fault-injection 30 kịch bản); Vite build **PASS** (`1,911 modules`, `2.03s`). Production `EduSuggest` giữ nguyên **100% READ ONLY** (`c3d4e5f6a7b8`, `24` bảng, `120` khóa học, `150` đăng ký, `300` lịch sử học tập).
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_PAYMENT_SAFETY_AUDIT_REPORT.md](EDUSUGGEST_PHASE4_PAYMENT_SAFETY_AUDIT_REPORT.md) và [EDUSUGGEST_PHASE4_ADMIN_PROVIDER_COMMERCE_REPORT.md](EDUSUGGEST_PHASE4_ADMIN_PROVIDER_COMMERCE_REPORT.md).

## GĐ4.5 — VNPay Sandbox Payment Integration (API v2.1.0) — 2026-11-26

- **Trạng thái:** **HOÀN TẤT MÃ NGUỒN & KIỂM THỬ NỘI BỘ TRÊN `EduSuggest_phase4_test` (127/127 PASS, Vite Build PASS); GIAO DỊCH SANDBOX THỰC TẾ QUA INTERNET: BLOCKED (chưa có `VNPAY_TMN_CODE`/`VNPAY_HASH_SECRET` và HTTPS IPN URL cho localhost). DỪNG CHỜ PHÊ DUYỆT GĐ4.6.**
- **Backend:** Bổ sung cấu hình VNPay Sandbox mặc định OFF (`config/config.py`, `VNPAY_HASH_SECRET` dùng `SecretStr`), triển khai `VNPaySandboxPaymentProvider` trong `service/payment_providers.py` (API v2.1.0, HMAC-SHA512, `quote_plus`, VND×100, UTC+7 `Asia/Ho_Chi_Minh`), dùng chung 10 bước cấp quyền học nguyên tử `_apply_verified_callback` với Mock Sandbox, bổ sung `GET /api/payments/vnpay/ipn` (trả `RspCode` `00`/`01`/`02`/`04`/`97`/`99`) và `GET /api/payments/vnpay/return` (chỉ đọc, chống Return URL tampering).
- **Frontend:** Cập nhật `CheckoutView.vue` (chọn động Mock Sandbox / VNPay Sandbox từ `/api/commerce/capabilities`), `PaymentResultView.vue` (xác minh chữ ký Return URL rồi luôn lấy trạng thái thật từ Backend), `commerceState.js`, `commerceApiService.js`.
- **Kiểm chứng:** Backend **127/127 PASS** (`23.22s`, gồm `4/4` GĐ4.5 VNPay test vectors/security/concurrency + `7/7` GĐ4.3 + `8/8` GĐ4.2 + `7/7` GĐ4.1 + `9/9` Recommendation + `69/69` Public API + `23/23` Critical/High Fixes); Vite build (`--outDir dist-phase45-check`) **PASS** (`1,909 modules`, `2.37s`). Production `EduSuggest` giữ nguyên READ ONLY (`c3d4e5f6a7b8`, `24` bảng).
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_VNPAY_SANDBOX_INTEGRATION_REPORT.md](EDUSUGGEST_PHASE4_VNPAY_SANDBOX_INTEGRATION_REPORT.md).

## GĐ4.4 — Premium Learner Marketplace UI & Staging — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRÊN STAGING `EduSuggest_phase4_test` (`http://127.0.0.1:5176/` ↔ `http://127.0.0.1:8003/api`), CHỜ KIỂM TRA TRÊN CHROME & PHÊ DUYỆT GĐ4.5.**
- **Frontend UI (áp dụng Emil Design Engineering, Impeccable, Design Taste Frontend):** Nâng cấp `UserHeader.vue` (icon Heart + Cart có badge đồng bộ API + `Lịch sử mua hàng`), `CourseCard.vue` (nút Heart góc ảnh bìa + trạng thái `Đã sở hữu`), `CourseDetail.vue` (CTA phân nhánh Miễn phí / Mua ngay + Giỏ hàng / Đã sở hữu / Chưa khả dụng), cùng 7 màn hình mới (`WishlistView`, `CartView`, `CheckoutView`, `MockPaymentView`, `PaymentResultView`, `OrderHistoryView`, `OrderDetailView`) và service/state tập trung (`commerceApiService.js`, `commerceState.js`).
- **Backend hỗ trợ & tương thích Production:** Bổ sung `GET /api/commerce/capabilities` (zero-DB-query giúp Production `EduSuggest` 24 bảng không gọi Marketplace API), endpoint `GET/POST /api/payments/mock/{txn_ref}(/simulate)` ký HMAC hoàn toàn trên server và chỉ cho phép trên `EduSuggest_phase4_test`, bổ sung `Idempotency-Key` vào CORS và sửa stale identity-map (`populate_existing=True` trên `FOR UPDATE`).
- **Kiểm chứng:** Backend regression **123/123 PASS**; Vite production build (`--outDir dist-phase44-check`) **PASS** (`1909 modules`, `3.30s`); HTTP smoke staging `8003`/`5176` **200 OK**. Browser E2E tự động: **chưa chạy** (giữ staging mở cho người dùng kiểm tra trên Chrome). Production `EduSuggest` giữ nguyên READ ONLY (`c3d4e5f6a7b8`, `24` bảng).
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_LEARNER_MARKETPLACE_UI_REPORT.md](EDUSUGGEST_PHASE4_LEARNER_MARKETPLACE_UI_REPORT.md).

## GĐ4.3 — Order, Checkout & Mock Payment Sandbox APIs — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRÊN `EduSuggest_phase4_test` (123/123 PASS), DỪNG CHỜ PHÊ DUYỆT GĐ4.4.**
- **Phạm vi triển khai:** Bổ sung `service/payment_providers.py` (Protocol `PaymentProvider` + `MockSandboxPaymentProvider` ký HMAC-SHA256 sẵn sàng mở rộng sang VNPay GĐ4.5), `service/order_payment_service.py` (Preview, Create Order idempotent + price snapshot + price-change guard, Order History/Detail/Status/Cancel/Auto-Expire TTL 15p, Payment Initiation, 10-step Atomic Callback & Enrollment Activation, Late/Conflict Reconciliation evidence), mở rộng `schemas/commerce.py`, `repository/commerce_repository.py`, `api/commerce.py` (+8 endpoints) và thêm cờ `MOCK_PAYMENT_ENABLED=False` (chặn cứng trên `APP_ENV=production` và database `EduSuggest`).
- **Kiểm thử PostgreSQL & multi-connection concurrency (`EduSuggest_phase4_test`):** **123/123 PASS** (`19.08s`) gồm `7/7` GĐ4.3 (18 kịch bản security, rollback atomicity, late callback reconciliation, REVOKED repurchase, COM-01 HTTP 402, concurrency 6 luồng) + `8/8` GĐ4.2 + `7/7` GĐ4.1 + `9/9` Recommendation + `69/69` Public Readonly API + `23/23` Critical/High Fixes.
- **An toàn dữ liệu:** Production `EduSuggest` giữ nguyên READ ONLY (`c3d4e5f6a7b8`, `24` bảng, `150` đăng ký, `300` lịch sử học tập). Không tạo migration mới, không sửa `.env`, không ảnh hưởng Recommendation Engine hay staging GĐ3.
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_ORDER_CHECKOUT_PAYMENT_REPORT.md](EDUSUGGEST_PHASE4_ORDER_CHECKOUT_PAYMENT_REPORT.md).

## GĐ4.2 — Wishlist, Shopping Cart & Buy Now APIs — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRÊN `EduSuggest_phase4_test` (116/116 PASS), DỪNG CHỜ PHÊ DUYỆT GĐ4.3.**
- **Phạm vi triển khai:** 4 module mới (`schemas/commerce.py`, `repository/commerce_repository.py`, `service/commerce_service.py`, `api/commerce.py` đăng ký vào `main.py`) cung cấp 12 API endpoints cho Wishlist (phân trang, đếm, trạng thái, thêm/xóa idempotent, chuyển sang giỏ nguyên tử), Shopping Cart (giỏ riêng mỗi USER, tính giá live bằng `Decimal` VND, phát hiện thay đổi giá & loại trừ mục không hợp lệ khỏi tổng tiền, xóa mục/xóa toàn bộ) và Buy Now validation (`prepare_buy_now` tái sử dụng cho GĐ4.3).
- **Kiểm thử PostgreSQL & hồi quy (`EduSuggest_phase4_test`):** **116/116 PASS** (`8/8` GĐ4.2 API/Security/RBAC/IDOR/Mass Assignment/Concurrency/Recommendation isolation + `7/7` GĐ4.1 + `9/9` Recommendation + `69/69` Public Readonly API + `23/23` Critical/High Fixes).
- **An toàn dữ liệu:** Production `EduSuggest` giữ nguyên READ ONLY (`c3d4e5f6a7b8`, `24` bảng, `150` đăng ký, `300` lịch sử học tập). Không tạo migration mới, không sửa `.env`, không ảnh hưởng Recommendation Engine hay staging GĐ3.
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_WISHLIST_CART_API_REPORT.md](EDUSUGGEST_PHASE4_WISHLIST_CART_API_REPORT.md).

## GĐ4.1 — Marketplace Database, ORM & Commerce Security Rehearsal — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRÊN `EduSuggest_phase4_test`, CHỜ PHÊ DUYỆT (CHƯA CHẠY MIGRATION LÊN DATABASE CHÍNH `EduSuggest`).**
- **Backup & Rehearsal DB:** Backup `EduSuggest` (`pg_dump -Fc`, `174,107 bytes`, SHA-256 `3c84ce35...`) tại `backend/database/backups/phase4-rehearsal/20261126-pre-phase4-rehearsal/EduSuggest.custom.dump`, restore sạch vào `EduSuggest_phase4_test`.
- **Migration mới (`d4e5f6a7b8c9`, single head nối tiếp `c3d4e5f6a7b8`):** Tạo 6 bảng (`YeuThich`, `GioHang`, `ChiTietGioHang`, `DonHang`, `ChiTietDonHang`, `ThanhToan`), bổ sung `ck_KhoaHoc_gia_non_negative` (COM-03), `uq_DangKyKhoaHoc_user_course` (COM-02) và 5 cột vòng đời quyền học (`maDonHang`, `nguonCapQuyen='LEGACY'`, `trangThaiQuyenHoc='ACTIVE'`, `ngayThuHoi`, `lyDoThuHoi`).
- **Diễn tập Upgrade → Downgrade → Re-upgrade trên `EduSuggest_phase4_test`:** **PASS** (24 → 30 → 24 → 30 bảng; bảo toàn 100% 150 `DangKyKhoaHoc` dạng `ACTIVE/LEGACY` và 300 `LichSuHocTap`). Production `EduSuggest` giữ nguyên READ ONLY (`c3d4e5f6a7b8`, 24 bảng).
- **Commerce Security & Regression Tests:** Bổ sung cờ rollout an toàn `COMMERCE_ENROLLMENT_GATE_ENABLED=False` (COM-01) và kiểm tra quyền học `ACTIVE` trên `workflow_repository`/`workflow_service`/`private_material_service`. Kết quả pytest: **108/108 PASS** (`7/7` GĐ4.1 security/concurrency/grandfathering/revocation + `9/9` Recommendation + `69/69` Public Readonly API + `23/23` Critical/High Fixes).
- Báo cáo chi tiết: [EDUSUGGEST_PHASE4_DATABASE_ORM_REPORT.md](EDUSUGGEST_PHASE4_DATABASE_ORM_REPORT.md).

## Official Dataset Controlled Import into `EduSuggest` (`edusuggest-official-v1`) — 2026-11-26

- **Trạng thái:** **HOÀN TẤT IMPORT CÓ KIỂM SOÁT VÀO DATABASE CHÍNH `EduSuggest` (Revision `c3d4e5f6a7b8`, 24 bảng).**
- **Backup & Snapshot (SHA-256 verified):**
  - Pre-import backup: `backend/database/backups/official-dataset/20261126-pre-prod-import-v1/` (`EduSuggest.custom.dump` SHA-256 `93db8f54...`).
  - Post-import official snapshot: `backend/database/backups/official-dataset/20261126-official-v1-snapshot/` (`EduSuggest.custom.dump` SHA-256 `be49843a...`).
- **Kết quả import & idempotency:** `24` danh mục, `120` khóa học (`120/120` ảnh bìa trong `media/courses`, `0` đường dẫn `dataset-staging`), `411` bài học, `243` tài liệu (`0` file private thiếu trong `private_storage/EduSuggest/materials`), `30` chuyên môn, `20` chuyên gia (`#4..#10` giữ nguyên `DRAFT`), `8` nhà cung cấp, `78` người dùng, `150` đăng ký, `300` lịch sử học tập, `20` đánh giá cũ bảo toàn, `0` vi phạm, `12` thông báo. Chạy lại `--dry-run` tạo mới `+0` bản ghi.
- **Kiểm chứng:** `0` duplicates, `0` orphans, **8/8 Recommendation personas PASS**, Private File Auth (`401`/`200`/`403`) PASS, `vite build` PASS (`1,897 modules`), `FLAGS: False False False`.
- Báo cáo chi tiết: [EDUSUGGEST_OFFICIAL_DATASET_IMPORT_REPORT.md](EDUSUGGEST_OFFICIAL_DATASET_IMPORT_REPORT.md).

## Official Dataset Staging (`edusuggest-official-v1`) — 2026-11-26

- **Trạng thái:** **HOÀN TẤT TRÊN STAGING (`EduSuggest_dataset_staging`), CHỜ PHÊ DUYỆT IMPORT VÀO PRODUCTION.**
- Restore rehearsal từ backup `20261126-official-v1` (SHA-256 verified) vào `EduSuggest_dataset_staging` (`c3d4e5f6a7b8`, 24 bảng): **PASS** (đã sửa tương thích dòng `SET transaction_timeout = 0;` giữa dump PG17 và server PG16).
- Dry-run & Import chính thức trên `EduSuggest_dataset_staging`: **24 danh mục, 120 khóa học (120/120 ảnh bìa nội bộ hợp lệ), 411 bài học, 243 tài liệu, 30 chuyên môn, 20 chuyên gia, 8 nhà cung cấp, 78 người dùng, 150 đăng ký, 300 lịch sử học tập, 12 thông báo**.
- Kiểm chứng toàn vẹn: `0` trùng lặp, `0` bản ghi mồ côi FK, `120/120` ảnh bìa HTTP 200, private file ẩn danh trả `401`, **8/8 persona Recommendation PASS** (7 `content_based` + 1 `latest` cold-start; `test_content_recommendation.py` 9/9 PASS; `vite build` PASS 1,897 modules). Duy nhất bản ghi legacy `#132` (`PENDING`/`HIDDEN`, `maDanhMuc=NULL`) được giữ nguyên.
- Website staging đang chạy sẵn tại **`http://127.0.0.1:5175/`** (API `http://127.0.0.1:8002/api`, credentials tại `backend/logs/official-dataset/demo-credentials.json`).
- Production `EduSuggest` giữ nguyên **100% READ ONLY** (`28` khóa học, `8` danh mục, `135` bài học, `122` tài liệu); staging GĐ3.8.3 (8001/5174) không bị gián đoạn.
- Báo cáo chi tiết: [EDUSUGGEST_OFFICIAL_DATASET_REPORT.md](EDUSUGGEST_OFFICIAL_DATASET_REPORT.md) và [docs/EDUSUGGEST_DATASET_DOCUMENTATION.md](docs/EDUSUGGEST_DATASET_DOCUMENTATION.md).

## GĐ3.8 Final Acceptance (2026-11-26)

- Kết luận: **NO-GO cho Production activation**. Backend unit/integration/concurrency tests đạt nhưng browser E2E chưa chạy được, worker chưa có launcher độc lập được xác minh và private-file revocation chưa được chứng minh.
- `EduSuggest_phase3_test` và Production `EduSuggest` đều ở Alembic revision `c3d4e5f6a7b8`; production được kiểm tra bằng READ ONLY transaction. Không chạy migration hoặc thay `.env`.
- Backend full suite: **209 passed**, 1 cảnh báo Starlette/httpx; feature-flag group Phase 3.3–3.8: **28 passed**, 1 cảnh báo.
- `npm.cmd run build`: **PASS**, 1,896 modules. Staging HTTP smoke trên 8001/5174 PASS; không xem đây là browser E2E.
- Chrome headless thoát do GPU fatal; responsive 375/768/1024/1440, screenshot và console UI: **NOT TESTED**.
- Worker implementation không được FastAPI lifespan khởi động; `AUTO_ASSIGNMENT_WORKER_ENABLED` hiện chưa gắn với launcher runtime. Chưa nghiệm thu worker service.
- Production READ ONLY snapshot: course #28 `PENDING/HIDDEN`, round 0; material #132 category NULL, `PENDING/HIDDEN`, round 0; expert #4 linked account role USER, profile DRAFT; 1 pending course round 0; 7 unverified expert profiles; 20 review rows. Không chỉnh legacy data.
- Test ADMIN fixture `maNguoiDung=2600` chỉ được tạo trên test DB và đã xóa; không còn fixture theo marker đó.
- Chỉnh Frontend recommendation filter (category filter chỉ cho course recommendations) và test harness fixture/concurrency cleanup. Không sửa Backend behavior, database schema/migration, API contract hoặc Recommendation Engine.
- Chi tiết nghiệm thu, rollout/rollback: [EDUSUGGEST_PHASE3_FINAL_ACCEPTANCE_REPORT.md](EDUSUGGEST_PHASE3_FINAL_ACCEPTANCE_REPORT.md). Tài liệu kỹ thuật: [EDUSUGGEST_EXPERT_MANAGEMENT_TECHNICAL_DOCUMENTATION.md](EDUSUGGEST_EXPERT_MANAGEMENT_TECHNICAL_DOCUMENTATION.md).

**Ngày kiểm tra:** 2026-11-24

**Phạm vi:** Frontend, ánh xạ API và kiểm tra khả năng chạy cục bộ. Không sửa Backend, database, migration hoặc `.env`.

## Tóm tắt

- Frontend Vite khởi động được; HTTP `GET /login` trả `200`.
- Ở lần kiểm tra ban đầu Backend không phản hồi. Lần xác minh sau khởi động được khi override DEBUG tạm thời (các GET root/health/docs/OpenAPI trả 200); kiểm tra hiện tại cho thấy lệnh Uvicorn thông thường lại dừng trước khi mở cổng do biến `DEBUG=release` trong môi trường tiến trình.
- Lần khởi động trước đã xác nhận PostgreSQL hoạt động qua `SELECT 1` và `/api/health` trả 200; lần chạy Uvicorn thông thường mới nhất dừng ở bước đọc cấu hình nên không kiểm tra DB lại.
- Có 29 nhóm tình huống nghiệp vụ trong checklist: **0 đã pass runtime, 0 fail runtime, 29 chưa thể kiểm thử runtime** do Backend không chạy.
- Responsive: **0/4 viewport** được xác nhận trực quan. Chrome headless không tạo DOM/screenshot; công cụ browser điều khiển trang không có trong phiên.
- `npm.cmd run build`: **PASS**, Vite build hoàn tất (1876 modules transformed).
- Frontend không khai báo script `test` và không tìm thấy bộ test frontend theo tên file/thư mục thông dụng; không có kết quả unit/integration test.

## Mức độ xác minh

| Phần | Source code | API thực tế | Trình duyệt |
|---|---|---|---|
| Request path/method/body/params | Đã đối chiếu với route/schema Backend trong mã | Chưa kiểm tra | Chưa kiểm tra |
| Response mapping | Đã đối chiếu tên trường ở các response/schema hiện có | Chưa kiểm tra | Chưa kiểm tra |
| Token và role | Đã rà `Authorization: Bearer`, xử lý 401 và route guard dùng `/auth/me` | Chưa kiểm tra token/role thật | Chưa kiểm tra |
| Loading/error/empty state | Có rà mã màn hình chính | Chưa kích hoạt bằng API runtime | Chưa kiểm tra |
| HTTP Frontend | Không áp dụng | `GET /login` trả 200 từ Vite | Đây là HTTP smoke check, không phải browser render |

## Kiểm thử theo role

Các nhóm trong bảng dưới đây đều **chưa thể xác nhận runtime**. “Có ánh xạ” nghĩa là mã Frontend gọi route tương ứng đã tìm thấy trong Backend; không chứng minh request/response hoặc nghiệp vụ chạy thành công.

| Role | Nhóm tình huống | Source/API mapping | Runtime |
|---|---|---|---|
| ADMIN | Tài khoản; danh mục; danh sách khóa học; trạng thái hiển thị; CRUD danh mục; route role | Có mapping cho GET users/categories/courses, category CRUD và visibility. Admin users hiện là danh sách; chưa có UI gán chuyên gia. | Chưa kiểm thử |
| EXPERT | Dashboard; hàng đợi; chi tiết; phê duyệt; từ chối; lịch sử; modal/thông báo | Có mapping cho profile, pending courses, detail, decision và review history. Backend hiện chưa có luồng duyệt tài liệu. | Chưa kiểm thử |
| PROVIDER | Hồ sơ; khóa học; tạo/sửa; bài học; metadata tài liệu; gửi duyệt; review history; phân quyền sở hữu; upload | Các endpoint tương ứng được gọi trong `providerApiService`. Backend không có upload file multipart; hiện chỉ lưu metadata/URL. | Chưa kiểm thử |
| USER | Đăng ký; đăng nhập; categories/catalog/detail; tìm kiếm; role guard; học tập/gợi ý | Có mapping cho auth và GET `/categories`, `/courses`, `/courses/{id}`; user routes yêu cầu USER. | Chưa kiểm thử |

Không chạy POST/PATCH/PUT/DELETE trên dữ liệu thật trong lần kiểm tra này. Những thao tác tạo/sửa/xóa danh mục, quyết định kiểm duyệt, cập nhật hiển thị, Provider CRUD và cập nhật hồ sơ cần tài khoản/môi trường test riêng; không tạo hoặc xóa dữ liệu nghiệp vụ để thử.

## Responsive và giao diện

Các viewport yêu cầu đều chưa được kiểm tra render thực tế:

| Viewport | Trạng thái |
|---|---|
| Desktop 1440px | Chưa kiểm tra trực quan |
| Laptop 1366px | Chưa kiểm tra trực quan |
| Tablet 768px | Chưa kiểm tra trực quan |
| Mobile 375px | Chưa kiểm tra trực quan |

Vite phản hồi HTML, nhưng Chrome headless không xuất DOM hoặc screenshot trong môi trường này. Vì vậy không kết luận về tràn ngang, bảng, menu, modal, cuộn trang, Console hoặc Network của browser.

## Fixture, service demo và component không được route

Rà tham chiếu toàn repository (loại `node_modules`, `dist`, `.git`):

- **Fixture không được màn nghiệp vụ đang route import trực tiếp:** `adminData.js`, `providerData.js`, `reviewerCourses.js`, `reviewerDashboardData.js`, `reviewerHistory.js`, `reviewerLectures.js`, `reviewerMaterials.js`, `userData.js`.
- **Service cũ không còn được component/layout route import:** `adminService.js`, `reviewerService.js`, `providerService.js`. `adminService` còn liên kết nội bộ tới `reviewerService`; các service này vẫn giữ fixture trong dependency graph nếu bị import lại.
- `userData.js` hiện không có tham chiếu. `ExperiencePreview.vue` cũng không được Router tham chiếu.
- Chưa xóa file nào; chúng đủ điều kiện để cân nhắc dọn sau khi xác nhận không có quy trình demo/test bên ngoài source hiện tại.
- Không phát hiện fixture đang được các màn nghiệp vụ chính sử dụng sau các thay đổi hiện có. Nội dung hardcode còn lại chủ yếu là nhãn/trạng thái và empty state, không phải số liệu nghiệp vụ.

## API chưa có hoặc chưa đủ hỗ trợ

- ADMIN: thống kê tổng hợp, số liệu gợi ý, phân công chuyên gia và màn theo dõi kiểm duyệt. API danh sách user có, nhưng UI chỉ đọc; chưa có API CRUD tài khoản/role tổng quát.
- EXPERT: duyệt tài liệu.
- PROVIDER: upload tệp thực; endpoint hiện lưu URL/metadata tài liệu.
- USER: đăng ký khóa học, tiến độ/bài học, lịch sử học, danh mục tài liệu, gợi ý cá nhân hóa và đánh giá chuyên gia.

## Lỗi và sửa đổi

Lần kiểm tra Frontend ban đầu không ghi nhận response API do Backend chưa chạy. Các kết quả Backend sau đó được ghi tại mục xác minh bên dưới. Không chỉnh sửa source code.

## Kiểm tra lệnh

- `npm.cmd run build`: **PASS**.
- `git diff --check`: **PASS** (exit code 0); Git in cảnh báo chuyển line ending LF → CRLF ở một số file đã sửa.
- Unit/integration test: không có script `test` trong `frontend/package.json`.
- Git: giữ nguyên các thay đổi đang có; không reset, clean, commit hoặc push.

## Xác minh Backend (2026-11-24)

- Lần khởi động trước dùng override trong tiến trình PowerShell (`DEBUG=false`), kết nối PostgreSQL thành công bằng `SELECT 1`; các GET `/` **200**, `/api/health` **200**, `/docs` **200**, `/openapi.json` **200**, `/api/auth/me` không token **401**. Đây không phải lần chạy cấu hình thông thường.
- Rà soát hiện tại: `backend/.env` có `DEBUG=True`, trùng kiểu Boolean của `Settings.debug` và trùng `backend/.env.example`. Không tìm thấy chỗ nào khác đọc `settings.debug`; các `DEBUG` còn lại là `LOG_LEVEL=DEBUG` trong mẫu cấu hình.
- Nguyên nhân lần khởi động thông thường thất bại hiện tại là môi trường tiến trình chứa `DEBUG=release`, ghi đè giá trị từ `.env` theo ưu tiên của Pydantic Settings. User/Machine environment scope không đặt `DEBUG`; giá trị được kế thừa từ tiến trình cha/terminal. `release` không phải giá trị Boolean hợp lệ và repo dùng `APP_ENV` (`development`) riêng để chỉ môi trường chạy.
- Đã chạy lệnh thông thường `.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000`; Uvicorn dừng ở lỗi `bool_parsing` trước lifespan. HTTP kiểm tra sau đó: `/`, `/api/health`, `/docs`, `/openapi.json` đều không kết nối được (curl mã `000`). Lần thất bại này không mở kết nối DB và không chạy cleanup.
- Cleanup lifespan gọi `DELETE` các token blacklist hết hạn ngay khi ứng dụng khởi động, sau đó lặp mỗi 24 giờ. Trong lần khởi động có override trước đó log ghi nhận một bản ghi hết hạn bị xóa tự động. Không hoàn nguyên dữ liệu. Vì ràng buộc không thay đổi dữ liệu, chưa khởi động lại ứng dụng trong lần kiểm tra này.
- **Phương án tối thiểu:** giữ `Settings.debug: bool` và `.env` như hiện tại; loại bỏ/sửa biến môi trường `DEBUG=release` tại nơi khởi chạy (terminal/tiến trình cha), không dùng `release` làm `DEBUG`. Sau khi tiến trình khởi chạy không còn kế thừa giá trị sai, chạy lệnh Uvicorn bình thường từ `backend`. Chưa thay đổi cấu hình vì biến sai không nằm trong `.env` hay User/Machine scope và không xác định được nguồn bên ngoài repo.
- API auth trong OpenAPI: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`. Chỉ GET được gọi; chưa thử request tạo/đổi dữ liệu hoặc token. Các route nghiệp vụ theo role được liệt kê trong source section trước; runtime cần xác minh lại sau khi sửa môi trường tiến trình.
- Không sửa source, `.env`, schema, API contract hoặc thông tin PostgreSQL. Báo cáo này là file duy nhất cập nhật trong đợt chẩn đoán hiện tại; các thay đổi Git có trước được giữ nguyên.

## Giai đoạn 0 — kiểm kê hiện trạng (2026-11-24)

Đây là kiểm kê source và PostgreSQL chỉ đọc; không chạy migration, seed, API ghi dữ liệu hay test nghiệp vụ. Kết quả trong mục này là bằng chứng mới nhất.

- Kiến trúc đọc được trong repository: Vue 3/Vite theo role; FastAPI routes → services → repositories → SQLAlchemy models/schemas; PostgreSQL và Alembic. Có design-system tokens và component dùng chung. Tài liệu README Frontend còn là nội dung scaffold Vite.
- PostgreSQL `EduSuggest.public` được kiểm tra bằng transaction `READ ONLY`: 13/13 bảng model hiện diện; không lệch tên bảng/cột, nullability, primary key hoặc foreign key so với SQLAlchemy models. Alembic version trong DB là `d8a41f6c2b90`, khớp revision cuối của chuỗi 4 migration tuyến tính.
- Dữ liệu tổng hợp: 4 role `ADMIN`, `USER`, `PROVIDER`, `EXPERT`; 5 tài khoản; 0 danh mục, khóa học, nhà cung cấp, hồ sơ chuyên gia, bài học, tài liệu, đăng ký, lịch sử học và đánh giá chuyên gia; 6 token blacklist. Không đọc thông tin định danh cá nhân.
- Do môi trường hiện tại, Uvicorn thông thường kế thừa `DEBUG=release` từ tiến trình cha; `.env` và `.env.example` đều là `DEBUG=True`. Lệnh Uvicorn thường dừng ở `bool_parsing` trước lifespan. `DEBUG=release` không phải Boolean; `.env` không cần sửa. Các HTTP 200 đã nêu ở mục Backend trước là lần chạy có override tạm, không phải xác minh cấu hình thường.
- API/runtime nghiệp vụ với token role thật: **chưa kiểm thử**. Các màn hình responsive cũng chưa được xác nhận trực quan. Trong phạm vi này chỉ kiểm tra DB bằng SELECT transaction read-only; không chạy suite vì repository không có test suite được tìm thấy.
- Rà fixture: `userData.js` không có tham chiếu; `adminData.js`, `providerData.js`, reviewer fixtures chỉ được import trong legacy services (`adminService.js`, `providerService.js`, `reviewerService.js`) hiện không được route/component đang dùng. `userService.js` được dùng nhưng trả empty/unavailable, không trả fixture. `demoOnly` xuất hiện trong route metadata nhưng router guard không đọc metadata này. Chưa xóa fixture/service.
- API bổ sung cần kiểm tra việc nối UI: `PUT /api/users/change-password` và `POST /api/admin/users/{user_id}/expert-role` tồn tại ở Backend nhưng chưa thấy UI/service gọi. Nhiều màn admin analytics/assignment/review-monitor và learner learning/recommendation có UI nhưng chưa có API hỗ trợ.
- Không thay đổi source, cấu hình, schema hay dữ liệu. Bộ hồ sơ giai đoạn 0: `PROJECT_ROADMAP.md`.

## Giai đoạn 2 — Authentication & Authorization (2026-11-24)

- **Test DB:** chưa xác nhận được DB kiểm thử độc lập. `.env` hiện trỏ tới `EduSuggest`; danh sách DB không có DB EduSuggest test riêng. Vì vậy không đăng ký tài khoản, đổi mật khẩu, logout bằng token thật hoặc gửi request ghi nghiệp vụ.
- Backend đang phản hồi trong phiên này: `GET /`, `/api/health`, `/docs`, `/openapi.json` đều **200**. `GET /api/auth/me` không token và token sai đều **401**.
- Không token: GET `/api/admin/users`, `/api/admin/categories`, `/api/expert/courses/pending`, `/api/provider/courses`, `/api/categories` đều **401**. Đây xác nhận chặn anonymous; chưa xác minh **403** với token role không đủ quyền.
- Input âm: login với username không tồn tại trả **401**; register payload cố chèn `maVaiTro` trả **422**. Không tạo tài khoản. Không thử trùng username/email vì chưa có môi trường/tài khoản test được duyệt.
- DB đọc bằng transaction `READ ONLY`: 3 tài khoản hiện tại (ADMIN 1, USER 2); aggregate cho thấy cả 3 mật khẩu lưu dạng Argon2. Snapshot Giai đoạn 0 từng ghi 5 tài khoản; chênh lệch này không do request ghi ở lượt này và cần xác minh thay đổi dữ liệu giữa hai lần kiểm tra. Không đọc username/email/password hash.
- **Source review:** đăng ký gán role USER ở Backend và schema `extra='forbid'`; response schemas không trả password/hash; login dùng username, Argon2 và JWT có hạn; `/auth/me` lấy role từ user DB; revoke/blacklist được kiểm tra trong dependency; role guards và provider ownership có ở Backend. Frontend gọi `/auth/me`, dùng role Backend để điều hướng, lưu token trong `sessionStorage`, kiểm tra guard khi reload; interceptor 401 xóa session và `main.js` điều hướng về login. Không phát hiện lỗi source cần sửa trong phạm vi đã kiểm tra.
- **Chưa test:** valid login/register/duplicate/logout/token revoked hoặc expiry; role 403 với tài khoản thật; thay đổi role/profile; provider truy cập chéo owner; response `/auth/me` với token thật; browser route/navigation. Không có browser automation tool khả dụng.
- `python -m pytest`: **NOT TESTED — 0 tests collected**, pytest exit 1. Frontend `npm.cmd run build`: **PASS** (Vite 1876 modules). `git diff --check`: không có lỗi whitespace; vẫn có cảnh báo LF→CRLF ở file Git đã sửa trước đó.
- Không phát hiện lỗi cần sửa chắc chắn; không thay source/API/database. Authentication & Authorization còn **PARTIAL / UNVERIFIED** đến khi có DB test riêng và bộ test/credentials cho 4 role.


## Provider phase review (2026-11-24)

- Source review confirms routes for Provider profile, courses, lessons, material metadata, submission, and per-course review history. Backend checks ownership against the Provider profile; EXPERT controls review status.
- Frontend fixes: removed two UI statuses unsupported by Backend (`PendingAssignment`, `DangKiemDuyet`); preserved zero values for duration; wired course price to the existing `gia` API field; constrained expertise to 255 characters per schema.
- Frontend build: PASS (`npm.cmd run build`). `git diff --check`: PASS; Git reports existing LF/CRLF conversion warnings.
- Unauthenticated GETs to `/api/provider/profile`, `/api/provider/courses`, and `/api/provider/categories` returned HTTP 401. This confirms authentication guards only; no valid Provider credential was available for real payload checks.
- Backend tests could not run because the current Python environment has no `pytest` module.
- CRUD, submission, and ownership behavior remain untested against data: configured database is the primary DB and no isolated test DB was confirmed. No write requests were sent. File upload API, chapter entity, and aggregate Provider review-history API are absent.
- Provider phase remains PARTIAL / UNVERIFIED; no direct browser or responsive check was performed.


## Expert moderation phase review (2026-11-24)

- Backend source confirms EXPERT-only routes for profile GET/PUT, pending-course list, pending-course detail, decision, and expert review history. Decision schema accepts APPROVED, REJECTED, NEEDS_REVISION; non-approval requires a note. Service rechecks PENDING under a row lock, records a review, sets visibility HIDDEN, and commits. Provider history is owner-scoped.
- Frontend fixes: removed unsupported `IN_REVIEW` state from mapping/reviewable statuses; Dashboard queue and history now report independent API errors; failed decisions keep the modal and entered note available for retry; successful decision updates preserve detail fields because the decision response is summary-only.
- Runtime unauthenticated GETs to `/api/expert/profile`, `/api/expert/courses/pending`, `/api/expert/reviews/history`, and `/api/provider/courses/1/reviews` returned HTTP 401. This confirms the anonymous access guard only. No valid Expert/Provider credentials or isolated test DB were available, so role matrix and business writes are NOT TESTED.
- `npm.cmd run build`: PASS (Vite transformed 1876 modules). Backend `venv` pytest: 0 tests collected (exit 1). `git diff --check`: PASS; existing LF/CRLF conversion warnings remain.
- API response limitation: review-history response contains foreign-key IDs but no reviewer display name or course title; course/detail response lacks category/provider display names and learning objectives/audience fields. UI uses IDs or explicit unavailable states rather than invented values. Document this before considering API contract changes. Material moderation API is absent.
- Browser interaction, responsive layouts, decision outcomes, provider resubmission and cross-role 403 behavior remain NOT TESTED. Expert phase remains PARTIAL / UNVERIFIED.


## Admin phase review (2026-11-24)

- Source checked: Admin dashboard, users/roles, categories, provider applications, course visibility, routes, Backend schemas/services/repositories and role dependencies.
- Existing API integrations: GET users/categories/courses/provider applications; POST/PATCH/DELETE categories; approve/reject provider applications; PATCH visibility; POST assign EXPERT. Admin role guards exist in Backend. Visibility service independently rejects non-APPROVED courses. User response schema exposes account name/email/phone/role only, not password/hash.
- Frontend change: the users table now offers the supported one-way USER-to-EXPERT operation with confirmation and waits for the Backend response before updating the displayed role. Category create/edit/delete success messages now survive the subsequent list reload. No other roles can be assigned through this control.
- Runtime unauthenticated GETs to `/api/admin/users`, `/api/admin/categories`, `/api/admin/courses`, and `/api/admin/provider-applications` returned HTTP 401. No valid ADMIN credentials/test DB; no write requests were sent. Therefore successful CRUD, role assignment, provider-application decisions, visibility transitions, and cross-role 403 checks are NOT TESTED.
- `npm.cmd run build`: PASS (Vite transformed 1876 modules). Backend `venv` pytest collected 0 tests (exit 1). `git diff --check`: PASS with existing LF/CRLF conversion warnings. No browser/responsive check performed.
- API gaps: no aggregate dashboard/statistics API, generic user detail/update/lock API, provider-profile management list/detail API, admin review-history monitor API, or reviewer assignment API. Existing provider applications are manageable; `/admin/users` only provides account fields. Generic arbitrary role changes are not supported.
- Admin phase: PARTIAL / UNVERIFIED.


## User phase review (2026-11-24)

- Source checked: USER routes/views/services, auth/profile schemas, course/category APIs and visibility filtering in repository/service. Backend catalog and detail queries restrict results to APPROVED + VISIBLE. `PUT /users/me` supports `hoTen` and `soDienThoai`; `/auth/me` supplies the authenticated account.
- Frontend fixes: category-list failures no longer suppress successful course results/details; course detail ignores stale route responses; search label now matches Backend title-only search; courses with unknown prices sort after known prices; phone input is limited to the schema's 20 characters.
- Runtime unauthenticated GETs: `/api/categories`, `/api/courses`, `/api/courses/1`, `/api/auth/me` returned 401. GET `/api/users/me` returned 405 because this route only defines PUT. No authenticated requests or writes were sent.
- `npm.cmd run build`: PASS (Vite transformed 1876 modules). Backend `venv` pytest: 0 tests collected (exit 1). `git diff --check`: PASS with LF/CRLF conversion warnings. No browser/responsive test was performed.
- User account profile display comes from `/auth/me`; profile edits use the existing `PUT /users/me` contract. This mutation was not runtime-tested. Backend also has `PUT /users/change-password`, currently no USER UI integration.
- API gaps: no enrollment create/list, duplicate enrollment policy endpoint, learner progress/history/activity, learner material catalog/detail/access, recommendation, or expert-rating API. Dashboard, learning progress/history/content, material screens and recommendations therefore remain unavailable/empty and must not be described as complete.
- Catalog API only supports title query, category ID and `limit` (maximum 100); no offset/page contract exists. Existing pagination is client-side over the received result set. Course/category responses omit display image, category/provider names and some richer course metadata.
- User phase remains PARTIAL / UNVERIFIED: no valid USER credentials or isolated test DB; enrollment/profile mutation and visible-course data were not exercised with authenticated requests.

## Phase 7 - enrollment and learning progress (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Implemented USER-only endpoints using the existing `DangKyKhoaHoc` and `LichSuHocTap` tables; no schema or migration changes were made. New routes: `POST /api/courses/{course_id}/enrollments`, `GET /api/enrollments`, `GET /api/learning/courses/{course_id}`, `GET /api/learning/courses/{course_id}/progress`, `POST /api/learning/courses/{course_id}/lessons/{lesson_id}/complete`, and `GET /api/learning/history`. The API derives user ownership from JWT, filters learning/enrollment/history reads to APPROVED + VISIBLE courses, checks enrollment before serving lessons or recording completion, and uses a PostgreSQL transaction advisory lock to serialize duplicate enrollment attempts because the existing schema has no unique user/course constraint.

Frontend now connects course registration, enrolled-course dashboard/progress, enrolled lesson content, lesson completion, and learning history through the centralized USER API service. Registration and completion UI updates only after successful API responses and exposes loading/error/success states. Unenrolled course detail returns no lesson payload; lesson details/materials are available through the enrollment-protected learning route.

**Validation:** `npm.cmd run build` PASS (Vite transformed 1876 modules); Python `compileall` PASS; Backend app import + OpenAPI generation PASS and all six routes are present; `git diff --check` PASS (pre-existing LF-to-CRLF warnings). These are source/build checks only. No write request, migration, database mutation, browser test, or backend integration test was run because the configured database is the primary EduSuggest database and no isolated test database is confirmed. Enrollment/duplicate, access-control, progress, and history workflows remain NOT TESTED against a database.

**Known limits:** The existing tables have no database unique constraint for enrollment or user/course/lesson history. Advisory locking serializes calls through this PostgreSQL service but does not enforce uniqueness for external writers. Existing columns do not represent a start event or time spent reliably; this phase records explicit lesson completion and does not invent those values. Cancellation/un-enrollment has no defined lifecycle rule and is not implemented. Existing learning history is returned as completion records only.
## Phase 7.1 - learning-flow verification (2026-11-24)

**Conclusion: PARTIAL.** Source audit covered the six Phase 7 routes, JWT role dependency, services/repositories/models/schemas, and the five USER views. `user.maNguoiDung` is passed from the authenticated USER dependency; request payloads and route params contain no user ID. Enrollment and history queries are scoped by that ID. Enrollment, lesson, progress, and history paths check APPROVED + VISIBLE course status; lesson content/completion also requires an enrollment; completion verifies the lesson belongs to the requested course. Empty reads return empty collections/zero progress. Registration uses one transaction and PostgreSQL transaction advisory locking; lesson completion serializes on the enrollment row and commits history plus aggregate progress together.

Source defects found and fixed in this verification: re-marking an already completed lesson no longer rewrites its history timestamp; lesson-completion responses from a previous course route no longer overwrite the newly opened course state; enrollment responses are similarly guarded after route changes; course status is row-locked while enrollment/completion writes proceed, and enrollment completed counts are bounded to lessons belonging to that course. No API shape, schema, migration, or business workflow was changed.

**Database safety:** Backend configuration resolves to PostgreSQL `localhost:5432/EduSuggest`; a read-only `SELECT` confirmed the live server address `172.17.0.2:5432` and current database `EduSuggest`. The connected role has `CREATEDB`; there are zero matching EduSuggest test databases. No credentials were printed. No database write, test DB creation, migration, or application startup was performed. A separate database can be provisioned on this PostgreSQL server, then its exact `current_database()` verified before applying schema/test setup; that setup was not performed in this audit.

**Automated checks:** Frontend production build PASS (1876 modules); Python compileall PASS; Backend import/OpenAPI generation PASS with all six routes present; pytest collection reports `no tests collected`; `git diff --check` PASS with existing LF/CRLF warnings. No automated integration cases exist to execute. Browser automation is unavailable in this session.

**NOT TESTED:** All write and authenticated integration cases: anonymous 401, valid/duplicate/hidden/unapproved enrollment, enrolled/unenrolled/cross-course lesson access, cross-user reads, concurrent enrollment/completion, persisted progress/history, empty responses against PostgreSQL, UI interaction and responsive layout. The configured connection points at the primary `EduSuggest` DB; no test requests were sent.

**Concurrency/data risk:** Advisory locking protects duplicate enrollment requests only when all writers use this service and the same lock key. There is no database unique constraint on `(maNguoiDung, maKhoaHoc)`, so another writer that omits the lock can create duplicates; repair requires a uniqueness constraint after auditing/deduplicating existing rows, therefore no schema change was made. Same-service lesson-completion calls serialize on the enrollment row and update the latest matching history record without adding another row. A writer bypassing that row lock can still create duplicate `(user, course, lesson)` history rows because the schema has no such unique constraint. Aggregate enrollment percentage and completion date are denormalized from history; this service updates them transactionally, but external writes/legacy duplicates can make them diverge. No direct SQL writers for these records were found in the repository source reviewed.
## Giai đoạn 8.1 - Recommendation System design (2026-11-24)

**Kết luận: MISSING / UNVERIFIED; chỉ hoàn thành phân tích/thiết kế.** Đã đối chiếu Backend FastAPI routes/services/repositories/schemas, Frontend USER screens/services, SQLAlchemy models, migration/ERD và PostgreSQL bằng truy vấn READ ONLY. Tạo `docs/RECOMMENDATION_DESIGN.md`; không thay đổi source, API, model, schema, migration, `.env` hoặc dữ liệu.

PostgreSQL được xác nhận là `EduSuggest`; snapshot aggregate hiện tại: 0 category, course, lesson, material, enrollment, learning-history row và expert review; có 3 user accounts. Không có corpus để xếp hạng hoặc đánh giá. Model đã có metadata course/category/lesson/material và enrollment/history implicit signals; nhưng không có explicit user preferences hoặc learner course rating với semantics đã được xác minh, impression/click/skip events, keyword/tags cho content hoặc recommender service/API. `DanhGiaChuyenGia` là đánh giá EXPERT, không phải rating của learner. Frontend Recommendation pages vẫn dùng empty helpers/empty states; `demoRecommendations` không được tham chiếu trong source tìm kiếm. Admin có legacy demo metric fixture nhưng màn hiện tại không tiêu thụ.

Thiết kế đề xuất Content-Based baseline trước; CF/Hybrid giữ gated đến khi interactions thật đủ để tạo holdout và vượt baseline. Material candidates phải bám quan hệ Tài liệu→Bài học→Khóa học, trạng thái APPROVED + VISIBLE và enrollment/access policy; không coi `duongDanTep` là chứng minh file public/an toàn. Không đề xuất bảng `GoiY` hoặc `DuLieuTuongTac`.

**Evidence:** PostgreSQL counts came from aggregate SELECTs in a READ ONLY transaction; no personal identifiers read. No recommendation request, write, migration, frontend build, or browser test was part of this analysis-only task. Earlier roadmap wording that recommendation has no interaction tables/API is superseded: Giai đoạn 7 added enrollment/history models and routes, but current tables contain zero records. Recommendation route/service and quality evidence remain absent.
## Phase 8.2 implementation update (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Added a dependency-free Content-Based ranking module and three USER-only recommendation endpoints: personalized/discovery courses, similar public courses, and materials restricted to an enrolled public course. User identity is derived from JWT; public course filters and enrollment scope are applied in repository/service code. No database schema, migrations, dependencies, `.env`, Frontend, CF, or Hybrid changes were made.

**Checks:** 9 algorithm unit tests PASS; Python compilation, Backend import, OpenAPI generation (all three routes present), and `pip check` PASS. PostgreSQL integration and browser tests are NOT TESTED: the configured database is the primary project database, no isolated test database is configured, and its verified catalog/interaction tables are empty. No database reads/writes or migration were performed in this implementation turn. `git diff --check` reports trailing whitespace in pre-existing changed Frontend files, including `ProviderSidebar.vue`, `AdminLayout.vue`, `AdminDashboard.vue`, and `AuthView.vue`, plus LF-to-CRLF notices. These unrelated working-tree changes were left untouched. Frontend integration and data-backed ranking quality remain outstanding.

## Giai đoạn 8.3 - Frontend Recommendation integration (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Tích hợp ba API Recommendation Backend vào Frontend USER. Không tạo Backend API mới, không thay đổi database/migration/.env, không triển khai CF/Hybrid.

**API đã tích hợp (dùng `userApiService.js`, axios hiện có, JWT interceptor):**
- `GET /api/recommendations/courses?limit=10` → `fetchRecommendedCourses({ limit })` — gợi ý cá nhân hóa/khám phá, trả về `{ items, strategy, personalized }`.
- `GET /api/courses/{course_id}/similar?limit=10` → `fetchSimilarCourses(courseId, { limit })` — khóa học tương tự.
- `GET /api/recommendations/materials?course_id=...&lesson_id=...&limit=10` → `fetchRecommendedMaterials(courseId, { lessonId, limit })` — tài liệu đề xuất (yêu cầu đăng ký).

**Màn hình đã tích hợp:**
- `UserDashboard.vue`: "Khóa học dành cho bạn" đã dùng `fetchRecommendedCourses({ limit: 6 })` với loading/error/empty/CourseCard. Không tạo dữ liệu giả.
- `UserHome.vue`: "Khóa học dành cho bạn" đã dùng `fetchRecommendedCourses({ limit: 3 })` thay placeholder trống. Loading/error/empty/CourseCard.
- `CourseDetail.vue`: Thêm section "Khóa học tương tự" dưới chi tiết khóa học, dùng `fetchSimilarCourses(course.id, { limit: 6 })`. Sequence guard tránh response cũ ghi đè dữ liệu mới khi chuyển nhanh. Không hiển thị lại khóa học nguồn (Backend đã loại). Loading/error/empty.
- `Recommendations.vue`: Đã nối `fetchRecommendedCourses` và `fetchRecommendedMaterials` thay legacy `userService` (trả `[]`). Query `course_id`/`lesson_id` từ route. Loading/error/retry/empty/CourseCard/MaterialCard.
- `MaterialCatalog.vue`: Đơn giản hóa — không còn gọi legacy `getPublicMaterials`/`getPublicCourses` (trả `[]`). Hiển thị EmptyState giải rõ Backend chưa có endpoint thư viện tài liệu công khai; tài liệu được gợi ý qua trang Gợi ý tài liệu (yêu cầu đăng ký).

**Bảo toàn nguyên tắc:**
- Không gửi `maNguoiDung` từ Frontend; user identity từ JWT qua Backend dependency.
- Không tự tính TF-IDF/Cosine tại Frontend; không tạo API Backend mới.
- Không tạo dữ liệu demo khi API thất bại; chỉ hiển thị lỗi thật từ API.
- Chỉ USER role được truy cập (Backend `require_roles("USER")`).
- Lỗi Recommendation không làm hỏng Dashboard hoặc CourseDetail (mỗi vùng xử lý độc lập).

**File thay đổi:**
- `frontend/src/views/user/Recommendations.vue`
- `frontend/src/views/user/CourseDetail.vue`
- `frontend/src/views/user/UserHome.vue`
- `frontend/src/views/user/MaterialCatalog.vue`
- `frontend/src/views/user/UserDashboard.vue` (không thay đổi code — đã tích hợp trước đó)

**Build result:** BUILD PASS. Đã xử lý phân quyền NTFS bằng cách đổi tên `frontend/dist` thành `dist_old`, sau đó thực thi `npm.cmd run build` thành công hai lần liên tiếp (exit code 0, 1876 modules transformed).

**Test result:** Backend 9/9 unit tests Recommendation PASS. Smoke test GĐ8.3.2: FastAPI (127.0.0.1:8000) và Vite (127.0.0.1:5173) hoạt động đồng thời, CORS preflight 200, Protected API 401 khi không token. PostgreSQL integration test dữ liệu nghiệp vụ: NOT TESTED (database hiện tại là database chính EduSuggest, chưa có database test riêng biệt).

## Giai đoạn 8.4 - Thiết kế và Chuẩn bị bộ dữ liệu kiểm thử (2026-11-24)

**Trạng thái: COMPLETED (Đặc tả dữ liệu & Script bảo vệ hoàn thành).**

- **Kiểm tra Database:** Xác nhận kết nối PostgreSQL tới `EduSuggest`. Đếm bảng read-only: `DanhMuc`: 0, `KhoaHoc`: 0, `BaiHoc`: 0, `TaiLieu`: 0, `DangKyKhoaHoc`: 0, `LichSuHocTap`: 0. Chưa có database kiểm thử riêng biệt (như `EduSuggest_test`). Tuân thủ quy tắc an toàn: Dừng mọi thao tác ghi dữ liệu, không tự tạo database, không seed vào database `EduSuggest`.
- **Đặc tả Bộ dữ liệu mẫu (Dataset Specification):**
  * 6 Danh mục đầy đủ miền kiến thức: Web Frontend, Web Backend, Cơ sở dữ liệu & SQL, Mobile Dev, Data Science & AI, DevOps & Cloud.
  * 13 Khóa học mẫu đa dạng trạng thái kiểm duyệt và hiển thị: 10 khóa APPROVED+VISIBLE (ứng viên hợp lệ), 1 khóa APPROVED+HIDDEN (kiểm tra ẩn), 1 khóa PENDING+VISIBLE (kiểm tra chờ duyệt), 1 khóa REJECTED+HIDDEN (kiểm tra từ chối). Đa dạng trình độ (Beginner/Intermediate/Advanced), thời lượng và học phí.
  * Cấu trúc bài học và tài liệu học tập chi tiết cho các khóa học tiêu biểu (tiêu đề, nội dung, phân loại tài liệu: PDF, SLIDE, CHEATSHEET, CODE, DATASET).
  * 5 Tài khoản mẫu đại diện cho các User Personas: Cold-start user, Vue specialist user (đã học 100% Vue, đánh giá tương tự Pinia/SPA), Full-stack hybrid user (kết hợp Frontend và Backend), Provider demo và Expert demo.
- **Kịch bản kiểm thử (Test Scenarios):**
  * Scenario 1: Lọc trạng thái khóa học (loại bỏ HIDDEN, PENDING, REJECTED).
  * Scenario 2: Gợi ý khóa học tương tự theo Cosine Similarity văn bản.
  * Scenario 3: Loại trừ khóa học người dùng đã đăng ký (Enrolled Exclusion).
  * Scenario 4: Gợi ý tài liệu học tập theo ngữ cảnh bài học / khóa học.
  * Scenario 5: Fallback người dùng mới (Cold-Start fallback sang 'latest' discovery).
  * Scenario 6: Người dùng đa sở thích (Multi-interest personalized ranking).
  * Scenario 7: Kiểm tra Enrollment Gate bảo vệ truy cập tài liệu học tập (403 Forbidden).
- **Chuẩn bị Script Seed an toàn (`backend/scripts/seed_recommendation_demo.py`):**
  * Guardrail 1: Từ chối chạy nếu database là `EduSuggest`, `production`, `postgres`, `defaultdb`.
  * Guardrail 2: Yêu cầu xác nhận cờ dòng lệnh `--confirm-seed-test-data` hoặc `--dry-run`.
  * Guardrail 3: Idempotent - kiểm tra tồn tại theo unique key trước khi chèn bản ghi.
  * Guardrail 4: Atomic transaction - rollback toàn bộ nếu có bất kỳ lỗi nào.
  * Kiểm tra cú pháp: `python -m py_compile` PASS. Kiểm tra guardrail: Từ chối thực thi khi không có flag hoặc khi trỏ vào `EduSuggest`. Script KHÔNG được chạy ghi vào DB trong giai đoạn này.

## Giai đoạn 8.5 - Triển khai Database kiểm thử và Nghiệm thu Recommendation (2026-11-24)

**Trạng thái: COMPLETED.**

- **Database kiểm thử (`EduSuggest_test`):**
  * Khởi tạo thành công database độc lập `EduSuggest_test` trên PostgreSQL 16.
  * Database chính `EduSuggest` được xác minh READ ONLY và bảo toàn tuyệt đối 100% (0 bản ghi thay đổi).
  * Chạy thành công chuỗi 4 Alembic migrations trên `EduSuggest_test`: đạt revision `d8a41f6c2b90`, đồng bộ 14 bảng (13 bảng nghiệp vụ + `alembic_version`) với đầy đủ PK, FK, Unique và Check constraints.
- **Thực thi Seed dữ liệu an toàn:**
  * Dry-run `--dry-run` hoàn tất thành công với rollback 100%, không để lại dữ liệu rác.
  * Seed thật với cờ `--confirm-seed-test-data --target-db EduSuggest_test`:
    - `VaiTro`: 4 bản ghi.
    - `DanhMuc`: 6 danh mục.
    - `NguoiDung`: 5 tài khoản demo theo persona.
    - `NhaCungCapKhoaHoc`: 1 bản ghi.
    - `ChuyenGia`: 1 bản ghi.
    - `KhoaHoc`: 13 khóa học (10 APPROVED+VISIBLE, 1 APPROVED+HIDDEN, 1 PENDING+VISIBLE, 1 REJECTED+HIDDEN).
    - `BaiHoc`: 16 bài học.
    - `TaiLieu`: 21 tài liệu (PDF, SLIDE, CODE, CHEATSHEET, DATASET).
    - `DangKyKhoaHoc`: 3 lượt đăng ký.
    - `LichSuHocTap`: 5 lượt bài học hoàn thành.
- **Kết quả Nghiệm thu 7 Kịch bản Recommendation (`tests/integration/test_recommendation_integration.py`):**
  * **Kịch bản 1 (Lọc trạng thái):** PASS. Chỉ các khóa APPROVED+VISIBLE được trả về; các khóa C11 (HIDDEN), C12 (PENDING), C13 (REJECTED) bị loại trừ 100%.
  * **Kịch bản 2 (Similar Courses):** PASS. Gợi ý khóa tương tự C1 (Vue 3 cơ bản) loại trừ chính C1. Cả C2 (Vue 3 Pinia, score=0.4134) và C3 (React UI/UX, score=0.5563) đều nằm trong Top 2, điểm vượt trội so với Mobile C7 (0.2427) và Data Science C8 (0.1893).
  * **Kịch bản 3 (Loại trừ khóa đã đăng ký):** PASS. User `learner_vue_specialist` đã học C1 thì C1 hoàn toàn không xuất hiện trong gợi ý; trả về `personalized=True`, `strategy="content_based"`.
  * **Kịch bản 4 (Gợi ý tài liệu ngữ cảnh):** PASS. User đăng ký C1 gọi tài liệu theo lesson 1.1 nhận về danh sách tài liệu hợp lệ, tài liệu bài 1.1 xếp đầu tiên.
  * **Kịch bản 5 (Cold-start):** PASS. User `learner_frontend_newbie` (0 enrollment) kích hoạt fallback `strategy="latest"`, `personalized=False`, reasonCodes `RECENT_COURSE`.
  * **Kịch bản 6 (User đa sở thích):** PASS. User `learner_fullstack_hybrid` (đã học C1 và C4) được gợi ý kết hợp đa dạng các chủ đề Frontend và Backend/Database.
  * **Kịch bản 7 (Enrollment Gate):** PASS. User chưa đăng ký C4 gọi gợi ý tài liệu C4 bị chặn ngay với HTTP 403 Forbidden; user đã đăng ký C1 gọi tài liệu C1 trả về HTTP 200 OK.
- **Tổng hợp Kiểm thử và Build:**
  * 9/9 Unit tests Recommendation: PASS.
  * 7/7 Integration tests Recommendation: PASS (Tổng cộng 16/16 tests PASS).
  * Python `compileall` và `pip check`: PASS (No broken requirements).
  * Ruff linter & formatter: PASS (0 errors, formatted cleanly).
  * Frontend Vite build (`npm.cmd run build`): PASS (1876 modules transformed, built in 1.43s).

## Giai đoạn 8.6 - Kiểm thử E2E Frontend và Trực quan hóa Khuyến nghị (2026-11-24)

**Trạng thái: COMPLETED.**

- **Môi trường thực thi E2E:**
  * Backend FastAPI (Uvicorn) chạy cổng `127.0.0.1:8000`, kết nối trực tiếp database kiểm thử `EduSuggest_test`.
  * Frontend Vue 3 + Vite dev server chạy cổng `127.0.0.1:5173`.
  * Chrome Headless chạy qua Chrome DevTools Protocol (CDP) cổng remote debugging `9222`.
  * Cơ chế Auth & Session: Lấy JWT access token thật từ Backend (`POST /api/auth/login`), inject an toàn vào `sessionStorage("edusuggest.accessToken")` và điều hướng Vue Router.
- **Khắc phục lỗi Frontend:**
  * `frontend/src/views/user/Recommendations.vue`: Khắc phục lỗi `isMaterialView.value` và `strategy.value` được unwrap thủ công trong template khiến biểu thức điều kiện trả về `undefined` khi hiển thị banner Cold-start.
  * `frontend/src/views/user/CourseDetail.vue`: Khắc phục thiếu import `CourseCard` (`import CourseCard from '@/components/user/CourseCard.vue'`), giúp phần "Khóa học tương tự" render đầy đủ danh sách card thay vì cảnh báo unhandled custom element.
- **Nghiệm thu 4 Luồng & 7 Kịch bản E2E Frontend:**
  * **Flow 1 (Cold-start User - learner_frontend_newbie):**
    - Dashboard: Hiển thị banner trạng thái *"Chưa có đủ lịch sử học tập để cá nhân hóa. Các khóa học dưới đây là gợi ý khám phá mới cập nhật."*, rỗng phần khóa học đang học, render 6 khóa học mới nhất.
    - Trang Gợi ý khóa học (`/recommendations/courses`): Hiển thị đầy đủ banner cold-start và 10 khóa học khám phá mới nhất.
    - An toàn hiển thị: 0 khóa học HIDDEN/PENDING/REJECTED xuất hiện trong DOM.
    - Ảnh chụp màn hình: `flow1_newbie_dashboard.png`, `flow1_newbie_recommendations.png`.
  * **Flow 2 (Vue Specialist - learner_vue_specialist):**
    - Dashboard: Khóa học đã học C1 (Vue 3 cơ bản) hiển thị tại mục "Khóa học đang học". Trong mục gợi ý, C1 được loại trừ hoàn toàn; các khóa học liên quan mật thiết gồm C2 (Vue 3 Pinia) và C3 (React UI/UX) được xếp hạng đầu.
    - Trang Gợi ý khóa học (`/recommendations/courses`): Render 9 khóa học gợi ý cá nhân hóa không chứa C1.
    - Chi tiết khóa học (`/courses/14`): Render chi tiết C1 cùng danh sách "Khóa học tương tự" (C3 React, C2 Vue 3 Pinia, C7 Flutter...).
    - Gợi ý tài liệu đã đăng ký (`/recommendations/materials?course_id=14&lesson_id=17`): Render thành công 5 tài liệu học tập theo ngữ cảnh bài 1.1.
    - Gợi ý tài liệu chưa đăng ký (`/recommendations/materials?course_id=17`): Hiển thị cảnh báo lỗi HTTP 403 Forbidden (*"Enroll in this course before requesting its materials."*), không làm crash trang.
    - Ảnh chụp màn hình: `flow2_vue_dashboard.png`, `flow2_vue_recommendations.png`, `flow2_vue_course_detail.png`, `flow2_materials_enrolled.png`, `flow2_materials_forbidden_403.png`.
  * **Flow 3 (Multi-Interest User - learner_fullstack_hybrid):**
    - Dashboard: Hiển thị 2 khóa học đã đăng ký gồm C1 (Vue 3) và C4 (FastAPI).
    - Danh sách gợi ý cá nhân hóa: Loại trừ hoàn toàn cả C1 và C4; xếp hạng ưu tiên các khóa học nâng cao tương ứng gồm C5 (FastAPI Microservices), C3 (React UI/UX), C2 (Vue 3 Pinia), C7 (Flutter), C8 (Pandas), C10 (Docker).
    - Ảnh chụp màn hình: `flow3_hybrid_dashboard.png`, `flow3_hybrid_recommendations.png`.
  * **Flow 4 (Responsive & Visual Layout - Mobile 375x667):**
    - Màn hình Home và Dashboard trên viewport 375x667: `scrollWidth === clientWidth` (375px), không có hiện tượng vỡ layout hay thanh cuộn ngang ngoài ý muốn (`hasHorizontalScroll = false`).
    - Tất cả 8 card khóa học trên Dashboard co giãn linh hoạt theo grid responsive.
    - Ảnh chụp màn hình: `flow4_mobile_home.png`, `flow4_mobile_dashboard.png`.
- **Giám sát Console & Network Browser:**
  * Console Warnings / Errors: 0 lỗi, 0 cảnh báo sau khi sửa import `CourseCard`.
  * Network Requests: 100% API nghiệp vụ phản hồi HTTP 200 OK; ngoại lệ duy nhất là HTTP 403 Forbidden có chủ đích tại kịch bản kiểm tra Enrollment Gate và được UI xử lý hiển thị banner an toàn.
  * Lọc hiển thị bảo mật: Toàn bộ 3 khóa học không hợp lệ (C11 - HIDDEN, C12 - PENDING, C13 - REJECTED) không xuất hiện ở bất kỳ màn hình nào.
- **Hồi quy kiểm thử & Build:**
  * Frontend Vite build (`npm.cmd run build`): PASS (1876 modules transformed, hoàn tất trong 1.18s).
  * Backend Pytest: 16/16 tests PASS (9 unit tests + 7 integration tests với `EduSuggest_test`).
  * Database chính `EduSuggest`: Bảo toàn nguyên trạng 100% (0 bản ghi thay đổi).

---

## Giai đoạn 9.2: Hoàn thiện chức năng phụ và tinh chỉnh giao diện (2026-11-24)

- **Mục tiêu:** Khắc phục các tồn đọng kỹ thuật và bổ sung các chức năng phụ trợ đã xác định trong báo cáo audit GĐ9.1.
- **Các hạng mục đã hoàn thành:**
  1. **Đổi mật khẩu người dùng (`UserProfile.vue`):**
     * Tích hợp form đổi mật khẩu với đầy đủ kiểm tra phía client: mật khẩu hiện tại, mật khẩu mới (8-128 ký tự, khác mật khẩu cũ), xác nhận mật khẩu khớp.
     * Thêm tính năng ẩn/hiện mật khẩu (Lucide `Eye`/`EyeOff`), trạng thái loading (`Submitting...`), thông báo lỗi inline và Toast thông báo thành công.
     * Bổ sung hàm `changePassword(currentPassword, newPassword)` trong `frontend/src/service/authService.js` gọi `PUT /api/users/change-password`.
     * Giữ nguyên form cập nhật thông tin cá nhân hiện có.
  2. **Thống kê Admin Analytics (`AdminAnalytics.vue` & API):**
     * Backend: Thêm Pydantic schema `AdminAnalyticsSummaryResponse` tại `backend/schemas/workflow.py`.
     * Backend: Triển khai hàm truy vấn tổng hợp `get_admin_analytics_summary(db)` tại `workflow_repository.py` và `workflow_service.py` (tính `total_users`, `total_courses`, `total_lessons`, `total_enrollments`, `completed_enrollments`, `completion_rate`).
     * Backend: Khai báo endpoint `GET /api/admin/analytics/summary` tại `backend/api/workflows.py` được bảo vệ bằng quyền `require_roles("ADMIN")`.
     * Frontend: Tái thiết kế màn hình `AdminAnalytics.vue` kết nối API thật, hiển thị 4 stat cards chính, bảng chi tiết tiến độ đào tạo, thanh progress bar, trạng thái loading skeleton, banner lỗi có nút "Thử lại", và empty state.
  3. **Thông báo hoạt động học tập (`UserHeader.vue`):**
     * Kết nối danh sách thông báo chuông với API lịch sử học tập thực tế qua `fetchLearningHistory()` từ `userApiService.js`.
     * Hiển thị tối đa 5 hoạt động gần nhất kèm tên khóa học, tên bài học và mốc thời gian định dạng tiếng Việt.
     * Điều hướng trực tiếp đến khóa học tương ứng hoặc link "Xem tất cả" tới `/learning-history`.
     * Trạng thái chưa đăng nhập hiển thị lời nhắc kèm link đăng nhập; trạng thái không có hoạt động hiển thị thông báo rõ ràng; xử lý lỗi nhẹ nhàng không làm crash header.
  4. **Khắc phục cảnh báo Ruff Linter:**
     * Sắp xếp lại thứ tự imports bảng chữ cái trong `backend/api/workflows.py`, khắc phục dứt điểm cảnh báo Ruff `I001`.
     * Toàn bộ backend đạt trạng thái kiểm tra clean: 0 lỗi lint trên toàn bộ codebase (`ruff check .` -> All checks passed!).
  5. **Bổ sung Unit & Integration Test:**
     * Thêm file `backend/tests/test_admin_analytics.py` kiểm thử tính toán tỷ lệ hoàn thành, trường hợp 0 lượt đăng ký, xác thực phân quyền ADMIN (200 OK) và từ chối truy cập không có token (401 Unauthorized).
- **Kết quả kiểm thử & xác minh:**
  * **Backend Pytest:** 20/20 tests PASS (9 content recommendation + 7 recommendation integration + 4 admin analytics).
  * **Frontend Build:** `npm.cmd run build` PASS (1876 modules transformed, 1.22s, 0 errors).
  * **Bảo vệ Database:** Cả 2 database `EduSuggest` và `EduSuggest_test` được bảo toàn nguyên vẹn cấu trúc và dữ liệu. Không chạy bất kỳ migration hay seed mới nào.


## GĐ3.8.1 – Final Blocker Resolution (2026-11-26)

- **Kết luận nghiệm thu: NO-GO / chờ phê duyệt.** Không bật Production.
- **BLOCKER-01 Worker Launcher: PASS trên test/staging scope.** Đã thêm standalone launcher + PowerShell start/stop/watch; xác minh DB đích `EduSuggest_phase3_test`, flags, logging và graceful shutdown. Real worker process kiểm tra submit → durable queue → assignment → notification, chạy đồng thời hai worker, stop/restart; fixture đã cleanup.
- **BLOCKER-02 Tài liệu riêng tư: BLOCKED.** Hiện chưa có private binary storage trong EduSuggest; `TaiLieu.duongDanTep` là URL và URL ngoài không thể thu hồi bởi backend. Cần duyệt kiến trúc lưu trữ riêng tư và authorization từng request trước khi triển khai.
- **BLOCKER-03 Browser E2E: BLOCKED / NOT RUN.** Chrome/Edge automation không tạo được browser session; không có screenshot, console E2E hoặc xác minh responsive. Hướng dẫn manual: `docs/EDUSUGGEST_GD381_MANUAL_BROWSER_TEST_GUIDE.md`.
- **Kiểm thử:** backend full suite `213 passed`; workflow suite khi ba flags bật `32 passed`; `py_compile` PASS; `npm.cmd run build` PASS (1,896 modules). Staging API smoke trả `/`, `/api/health`, `/docs`, `/openapi.json` 200; protected `/api/auth/me` và recommendation API không token trả 401. Cổng 8001/5174 đã dừng.
- **Dữ liệu:** mọi ghi thử nghiệm có guard `current_database() == EduSuggest_phase3_test`; xác nhận fixture users/courses/categories/specialties còn lại đều 0. Không migration, không sửa `.env`, không ghi Production; giữ revision baseline `c3d4e5f6a7b8`.
- **Audit:** ACC-11, JWT revocation, SEC-02 và recommendation regression PASS theo test suite. ACC-15 PASS theo source/workflow coverage nhưng không có test riêng mang mã ACC-15. Manual assignment khi queue đang PROCESSING còn PARTIAL do thiếu race test trực tiếp. Chi tiết tại `EDUSUGGEST_PHASE3_FINAL_BLOCKER_RESOLUTION_REPORT.md`.
- **Rủi ro:** launcher chính đã sửa unwrap `SecretStr`; có hai entrypoint worker cần hợp nhất trước vận hành lâu dài. Abrupt process kill chưa được thực hiện trực tiếp; stale lease/fencing recovery được test trong workflow suite.

## GĐ3.8.2 – Private File Security & Final Acceptance (2026-11-26)

- **Kết luận: NO-GO / chờ phê duyệt.** Không bật Production; Browser E2E vẫn BLOCKED.
- **Private Local Storage: IMPLEMENTED / PASS trong integration scope.** File managed nằm ngoài static tại `backend/private_storage/<current_database>/materials`; reference server-generated `private://materials/<uuid>` được lưu trong `TaiLieu.duongDanTep` nhưng API chỉ trả endpoint bảo vệ. Chưa cần migration; URL HTTP(S) legacy được giữ nguyên và không được tuyên bố có thể thu hồi.
- **API bảo vệ:** thêm `POST /api/provider/materials/{material_id}/file` và `GET /api/materials/{material_id}/file`. Mỗi request kiểm JWT/account state, provider ownership, expert assignment + vòng + trạng thái + hạn + current eligibility, hoặc USER visibility/enrollment. Response dùng private/no-store, nosniff và không lộ filesystem path.
- **Validation/lifecycle:** allowlist file, 25 MB, filename/path traversal, MIME, magic/OOXML, executable/spoof/empty; atomic local write. Object mới được cleanup khi validation/DB transaction lỗi; object managed cũ xóa sau commit. Abrupt kill giữa file-write/commit vẫn là rủi ro reconciliation.
- **Frontend:** PROVIDER upload/view/download; EXPERT review document; USER material/learning/course document đều dùng Axios/JWT blob flow, không token query string và object URL được revoke. Có loading/error/access-denied; không redesign.
- **Concurrency/ACC-15:** race PostgreSQL nhiều connection giữa manual assignment và queue `PROCESSING` PASS, không duplicate/lost job/deadlock; fencing giữ nguyên. Advisory lock/recheck được bổ sung cho eligibility write paths và expert protected writes.
- **Worker:** chuẩn hóa `backend/scripts/run_assignment_worker.py` làm entrypoint chính; wrapper `backend/run_assignment_worker.py` giữ tương thích. Staging start/stop scripts có DB/port/PID/start-time guard và fixture cleanup.
- **Kiểm thử:** full Backend cuối cùng **216 passed**; workflow + file-security flags bật cuối cùng **34 passed**; recommendation **9 passed**; target private/concurrency/worker **9 passed**; course/material assignment file-security **2 passed**; compileall PASS; target Ruff private modules PASS; Frontend build PASS (**1,897 modules**). PostgreSQL mất listener tạm thời rồi tự phục hồi; không có thao tác khởi động/chỉnh dịch vụ.
- **Staging smoke:** Backend `/`, `/api/health`, `/docs` 200; Frontend 200; worker graceful stop; fixture/process manifests bị xóa, ports 8001/5174 free, `g382_browser_%` còn 0. Production chỉ query trong transaction READ ONLY; cả Production/test revision `c3d4e5f6a7b8`; ba runtime flags trở về False.
- **Browser:** không lặp Chrome/Edge vì không có điều kiện mới. Hướng dẫn và scripts tại `docs/EDUSUGGEST_GD382_MANUAL_BROWSER_ACCEPTANCE.md`; chưa có screenshot/Console/responsive evidence nên **BLOCKED / NOT RUN**.
- Báo cáo chi tiết: `EDUSUGGEST_PHASE3_PRIVATE_FILE_SECURITY_ACCEPTANCE_REPORT.md`.

## GĐ3.8.3 – Final Browser Acceptance Preparation (2026-11-26)

- **Trạng thái: IN PROGRESS / Production NO-GO.** Staging được giữ hoạt động tại Frontend `127.0.0.1:5174`, Backend `127.0.0.1:8001`, DB `EduSuggest_phase3_test` và independent worker. Browser manual acceptance chưa có kết quả.
- **Môi trường:** trước start không có listener 8000/8001/5173/5174, Node/Python/worker task process hoặc manifest cũ. Vite cache tồn tại nhưng không bị lock; start không có EPERM. Runtime module xác nhận API base `http://127.0.0.1:8001/api`; DB/revision xác nhận `EduSuggest_phase3_test` / `c3d4e5f6a7b8`.
- **Fixtures:** 5 accounts (ADMIN, PROVIDER, verified EXPERT, unverified EXPERT, USER), 2 expert profiles, category/specialty, 3 courses, 4 materials, 2 assignments, notifications và 2 managed private PDFs. USER đã enroll learner course; verified EXPERT có 2 task riêng cho accept/decision và decline.
- **Fixture fix:** email `@test.local` làm login serialize trả 500 do `EmailStr`; đổi riêng fixture sang `@test.example.com`. Sau restart/cleanup an toàn, login + `/auth/me` PASS thực tế cho 5/5 account.
- **Abrupt kill:** bổ sung OS-process test. Worker đầu bị kill sau khi claim; recovery worker reclaim stale lease, hoàn tất đúng 1 assignment/notification; lease generation tăng và stale context bị `FENCED_OUT`. Test PASS.
- **Regression cuối:** full Backend **217 passed**; workflow + file security + crash recovery **35 passed**; recommendation **9 passed**; Frontend build PASS (**1,897 modules**).
- **Private HTTP smoke:** no-token 401; ADMIN/owner PROVIDER 200; EXPERT trước accept 403; enrolled USER đọc public managed file 200 và pending review file 403. Revoke/account-lock matrix tiếp tục PASS trong automated suite.
- **Browser:** automation BLOCKED vì không có Playwright/browser runtime/Firefox và không có điều kiện mới cho Chrome/Edge. Manual acceptance chia 5 batch; ADMIN/EXPERT/PROVIDER/USER/responsive hiện **NOT RUN**. Báo cáo: `EDUSUGGEST_PHASE3_BROWSER_ACCEPTANCE_REPORT.md`.
- **Giữ staging:** không chạy stop/cleanup cho tới khi người dùng xác nhận hoàn tất. Không sửa `.env`, migration/schema, Recommendation algorithm, Production data hoặc Git; không bật Production flags.
