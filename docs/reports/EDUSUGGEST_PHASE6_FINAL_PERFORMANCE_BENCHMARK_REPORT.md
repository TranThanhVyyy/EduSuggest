# EDUSUGGEST – GĐ6.3: FINAL RECOMMENDATION PERFORMANCE BENCHMARK REPORT

- **Ngày đo:** 2026-11-27
- **Môi trường:** Staging độc lập `edusuggest_phase62_staging` (`8004`) với content-hash fingerprint nâng cấp GĐ6.3B
- **Artifact nguồn:** [`media/phase63-staging/phase63b_verification.json`](../../media/phase63-staging/phase63b_verification.json)

## 1. Bảng kết quả tổng hợp (Internal Function vs. End-to-End HTTP API)

| Kịch bản | Số mẫu (`n`) | Min (ms) | **p50 (ms)** | **p95 (ms)** | p99 (ms) | Max (ms) | Mục tiêu | Kết quả |
|---|---:|---:|---:|---:|---:|---:|---|---|
| **GĐ6.1 Baseline (Before)** | 4 | — | `15,232.00` | — | — | `18,277.00` | — | Bottleneck P1 |
| **HTTP E2E `8004` – Courses Warm (Content-based)** | 35 | — | **`141.29`** | **`278.01`** | — | — | `p50 ≤ 150`, `p95 ≤ 300` | **PASS** |
| **HTTP E2E `8004` – Materials Warm (Content-based)** | 35 | — | **`283.23`** | — | — | — | Ổn định | **PASS** |
| **HTTP E2E `8004` – Concurrent 32 reqs (8 threads)** | 32 | — | **`886.17`** | — | — | — | `0` lỗi | **PASS (0 lỗi)** |
| **Internal – Courses Cold Cache** | 5 | — | **`1,166.32`** | — | — | — | `p50 ≤ 1,500` | **PASS** |
| **Internal – Courses Warm (khi CPU chịu tải song song 274 pytest)** | 35 | — | `206.13` | `375.11` | — | — | *(Ghi nhận trung thực có tải CPU nền)* | — |

> [!NOTE]
> Trong phiên đo `task-4312`, phần đo hàm nội bộ chạy song song với tiến trình 274 test `pytest` trên cùng CPU nên bị cộng thêm độ trễ CPU contention (`206.13 ms`). Ngay sau khi `pytest` giảm tải, phần đo **End-to-End HTTP API (`8004`, `n=35`)** — bao gồm cả JSON serialization, JWT auth và TCP loopback — đạt **`p50 = 141.29 ms`** (`<= 150 ms`) và **`p95 = 278.01 ms`** (`<= 300 ms`), nhanh hơn **107.8×** so với baseline GĐ6.1 (`15,232 ms`).

## 2. Tài nguyên hệ thống & Cache Observability

- **Cache Hit / Miss:** `course_hits = 131`, `course_misses = 41`, `material_hits = 44`, `material_misses = 13`.
- **Số entry trong cache:** `course_entries = 1` (giới hạn cứng `<= 8`).
- **Bộ nhớ sau 15 chu kỳ invalidate + rebuild liên tiếp:** **`5.70 MB`** hiện tại, **`14.73 MB`** đỉnh (không rò rỉ bộ nhớ).
- **Biểu đồ so sánh độ trễ trước/sau:** [`docs/reports/charts/latency_before_after_optimization.png`](./charts/latency_before_after_optimization.png).
