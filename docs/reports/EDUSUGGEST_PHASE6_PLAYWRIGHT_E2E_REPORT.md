# EDUSUGGEST – GĐ6.2: PLAYWRIGHT INTERACTIVE E2E REPORT (`ISSUE-008`)

- **Ngày thực hiện:** 2026-11-27
- **Môi trường kiểm thử độc lập:**
  - Staging UI: `http://127.0.0.1:5177` (Vite, `VITE_API_BASE_URL=http://127.0.0.1:8004/api`)
  - Staging API: `http://127.0.0.1:8004/api`
  - Staging DB: `edusuggest_phase62_staging` (clone sạch từ Production `EduSuggest`, 35 bảng, revision `e5f6a7b8c9d0`)
  - Trình duyệt: Playwright Python + Google Chrome (`C:\Program Files\Google\Chrome\Application\chrome.exe`, headless, isolated context)
- **Script & Artifact:** [`media/phase62-staging/run_playwright_e2e.py`](../../media/phase62-staging/run_playwright_e2e.py), [`media/phase62-staging/playwright_e2e_results.json`](../../media/phase62-staging/playwright_e2e_results.json)

## 1. Tổng hợp kết quả Multi-Viewport Responsive (`320px – 1920px`)

Kiểm tra tự động `document.documentElement.scrollWidth <= window.innerWidth` trên **7 độ rộng × 3 tuyến chính = 21 kịch bản**:

| Viewport | `/` (Home) | `/courses` (Catalog) | `/courses/6` (Detail) | Tràn ngang (`overflowPx`) |
|---|---|---|---|---:|
| `320 × 700` | `320 / 320` | `320 / 320` | `320 / 320` | **`0 px` (PASS)** |
| `375 × 812` | `375 / 375` | `375 / 375` | `375 / 375` | **`0 px` (PASS)** |
| `390 × 844` | `390 / 390` | `390 / 390` | `390 / 390` | **`0 px` (PASS)** |
| `768 × 1024` | `768 / 768` | `768 / 768` | `768 / 768` | **`0 px` (PASS)** |
| `1024 × 768` | `1024 / 1024` | `1024 / 1024` | `1024 / 1024` | **`0 px` (PASS)** |
| `1440 × 900` | `1440 / 1440` | `1440 / 1440` | `1440 / 1440` | **`0 px` (PASS)** |
| `1920 × 1080` | `1920 / 1920` | `1920 / 1920` | `1920 / 1920` | **`0 px` (PASS)** |

## 2. Kiểm thử tương tác đa vai trò & tính năng trọng yếu

| Hạng mục | Vai trò | Kết quả | Chi tiết xác minh |
|---|---|---|---|
| Public CourseDetail `/courses/6` | Guest | **PASS** | `has_zero_lessons_bug: false`, `has_provider_fallback_bug: false`, hiển thị `"Học viện Phần mềm FPT"`, `"5 bài giảng"`, đề cương khóa 5 bài |
| Header 2 tầng (`ISSUE-006`) | Guest / USER | **PASS** | Ẩn trên Homepage (tránh trùng Hero search), hiện trên `/courses` & `/courses/6`, submit `"Python"` điều hướng đúng `/courses?q=Python` |
| CourseCard 16:9 WebP (`ISSUE-003`) | Guest | **PASS** | `6/6` ảnh bìa tải hoàn tất (`naturalWidth > 0`), không có badge đè lên ảnh |
| Khóa học nháp `#27` ẩn (`ISSUE-004`) | Guest | **PASS** | `/courses/27` trả trạng thái không tìm thấy trên staging (`blocked_or_not_found: true`) |
| Learner Dashboard `/dashboard` | `USER` | **PASS** | Wishlist icon + Cart icon hiển thị, `0px` overflow |
| Wishlist `/wishlist` & Cart `/cart` | `USER` | **PASS** | Tải đầy đủ, `0px` overflow |
| LearningView YouTube Embed `/learning/6` | `USER` | **PASS** | Iframe `https://www.youtube-nocookie.com/embed/0sOvCWFmrtA?rel=0` (`804 × 451`), `0px` overflow |
| Admin Dashboard `/admin/dashboard` | `ADMIN` | **PASS** | Tải đầy đủ 79 tài khoản, 120 khóa học, 150 lượt ghi danh, `0px` overflow |
| Provider Dashboard `/provider/dashboard` | `PROVIDER` | **PASS** | Tải đầy đủ 12 khóa học cùng ảnh bìa WebP, `0px` overflow |
| Expert Dashboard `/reviewer/dashboard` | `EXPERT` | **PASS** | Tải đầy đủ không gian kiểm duyệt, `0px` overflow |
| Runtime Page Errors (`pageerror`) | All | **PASS** | **`0` page errors** |

**Kết luận:** **`ISSUE-008` (P3) ĐÃ HOÀN TẤT** — bộ Playwright E2E đã hoạt động ổn định, thay thế hoàn toàn khoảng trống kiểm thử tương tác của Chrome DevTools MCP bị chặn.
