# EDUSUGGEST – GĐ6.3A: REGRESSION BLOCKER RESOLUTION REPORT

- **Ngày thực hiện:** 2026-11-27
- **Mục tiêu:** Giải quyết dứt điểm lỗi `test_phase383_abrupt_worker_recovery.py` và làm rõ sự tương thích schema `EduSuggest_phase3_test` vs `EduSuggest_phase4_test`, đạt **100% PASS (0 FAIL, 0 SKIPPED)** toàn bộ Backend regression trước khi triển khai Production.

## 1. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)

### A. Lỗi `test_phase383_abrupt_worker_recovery.py`
Kiểm tra trực tiếp tiến trình hệ điều hành Windows (`Get-CimInstance Win32_Process`) và traceback thực tế phát hiện **worker contention do tiến trình worker mồ côi**:
- Tiến trình cũ `run_assignment_worker.py --expected-database EduSuggest_phase3_test --worker-id stage-0056473c` (PID `23680` / `10460`) từ đợt kiểm thử GĐ3 vẫn đang chạy nền và poll `EduSuggest_phase3_test` mỗi 1 giây.
- Khi `test_phase383_abrupt_worker_recovery.py` chèn job `PENDING` và khởi chạy `killed_worker`, tiến trình mồ côi `stage-0056473c` **cướp quyền claim job trước khi `killed_worker` kịp khởi động**, khiến `_wait_until(claimed_by_first_worker)` timeout sau 15 giây.
- Khi khối `finally:` thực hiện `lock_session.rollback()`, tiến trình mồ côi ngay lập tức chèn bản ghi `PhanCongKiemDuyet` xen giữa `DELETE FROM PhanCongKiemDuyet` và `DELETE FROM KhoaHoc`, gây `ForeignKeyViolation`.

### B. Tương thích Schema (`EduSuggest_phase3_test` `c3d4e5f6a7b8` vs `EduSuggest_phase4_test` `e5f6a7b8c9d0`)
- `test_phase47a_hardening_stress_fault_injection.py::test_h06_startup_schema_guard_blocks_24_table_db_and_passes_30_table_db` sử dụng `EduSuggest_phase3_test` ở revision `c3d4e5f6a7b8` (24 bảng, chưa có `DangKyKhoaHoc.maDonHang`) làm **negative fixture** để kiểm chứng Startup Schema Guard fail-closed.
- Các test tích hợp (`test_recommendation_integration.py`, `test_private_file_security.py`, `test_phase383_abrupt_worker_recovery.py`) đều hỗ trợ biến môi trường chính thức `EDUSUGGEST_TEST_DB_NAME`. Khi chạy full suite với `EDUSUGGEST_TEST_DB_NAME=EduSuggest_phase4_test` (35 bảng, `e5f6a7b8c9d0`), toàn bộ test tích hợp chạy trên schema mới nhất mà vẫn giữ nguyên `EduSuggest_phase3_test` (`c3d4e5f6a7b8`) cho `test_h06`.

## 2. Xử lý & Kiểm chứng không flaky (Zero Code Hacks)

- **Không** xóa test, **không** skip/xfail, **không** giảm assertion, **không** tăng timeout tùy tiện, **không** tắt schema guard.
- Đã dừng tiến trình worker mồ côi `stage-0056473c` (PID `23680`/`10460`) và xác nhận `0` tiến trình `run_assignment_worker.py` chạy nền.
- **Chạy lặp 3 lần liên tiếp `test_phase383_abrupt_worker_recovery.py`** trên `EDUSUGGEST_TEST_DB_NAME=EduSuggest_phase4_test`:
  - Lần 1: **PASS** (`14.08s`)
  - Lần 2: **PASS** (`13.89s`)
  - Lần 3: **PASS** (`15.72s`)
- **Chạy Full Backend Regression Suite (`pytest -q`, 274 tests):**
  - Tổng số test thu thập (`--collect-only`): **`274 tests`** (269 GĐ6.1 + 2 GĐ6.2 + 3 GĐ6.3).
  - Kết quả cuối cùng: **`274 passed, 0 failed, 0 skipped in 161.26s (100.0% PASS)`**.
