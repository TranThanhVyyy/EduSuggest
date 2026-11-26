# EDUSUGGEST — GĐ5.5: BÁO CÁO NGHIỆM THU CUỐI CÙNG DATASET (`edusuggest-official-v2`)

**Ngày nghiệm thu:** 2026-11-27  
**Trạng thái:** **ĐẠT NGHIỆM THU & ĐÃ TRIỂN KHAI CHÍNH THỨC LÊN PRODUCTION `EduSuggest` (`http://127.0.0.1:5173/` ↔ `http://127.0.0.1:8000/api`). PHÁT HÀNH CHÍNH THỨC `edusuggest-official-v2`. DỪNG CHỜ PHÊ DUYỆT GĐ6.1.**

---

## 1. Bảng tổng hợp Nghiệm thu chất lượng toàn bộ Dataset

| Hạng mục | Tổng số | Đạt chuẩn | Chưa đạt / Hạn chế ghi nhận trung thực |
| :--- |---:|---:|---|
| **Danh mục (`DanhMuc`)** | `24` | **`24 / 24`** | `0` |
| **Khóa học (`KhoaHoc`)** | `120` | **`119` công khai + `1` (`#31`) đã khôi phục** | Khóa `#31` (*Kiểm thử API thực chiến với Postman*, 10 bài học, `320 phút`, `399,000 ₫`) giữ nguyên **`HIDDEN` / `PENDING`** chờ kiểm duyệt nghiệp vụ hợp lệ (không duyệt bằng SQL) |
| **Ảnh bìa thực tế (`1280×720` WebP)** | `120` | **`120 / 120`** | `120/120` `HTTP 200` & `MIME image/webp`, `0` trùng lặp (`dHash`), giữ nguyên `119` `.svg` + `1` `.jpg` cũ để rollback |
| **Bài học (`BaiHoc`)** | `421` | **`421 / 421`** | `421/421` nội dung duy nhất (`min 185`, TB `1,414.7` ký tự), `0` video chết, `0` video lệch chủ đề; `0` thay đổi `maBaiHoc` |
| **Bài học Video (`duongDanVideo`)** | `65` | **`65 / 65` oEmbed `200 OK`** | Kiểm tra phát video trên trình duyệt thực tế: **`NOT TESTED`** (Chrome DevTools MCP `BLOCKED`) — giữ allowlist `youtube-nocookie.com` & nút mở tại nguồn |
| **Tài liệu học tập (`TaiLieu`)** | `243` | **`237 / 243`** (`116` ngoài `200 OK` + `121` private `.bin`/`.json`) | `5` URL `dev.mysql.com` trả `403` bot-filter (mở bằng trình duyệt bình thường); **`1` tài liệu rác `#132`** (`"hi"`/`"gsdfsd"`, `0` tham chiếu) giữ nguyên **`HIDDEN` / `PENDING`** (không xóa, không tự duyệt) |
| **Học phí & Thời lượng** | `120` | **`120 / 120`** | `23` miễn phí, `97` trả phí (`199,000 – 899,000 ₫`, TB `493,845 ₫`), `0` giảm giá giả, `0` khóa có `thoiLuong < SUM(BaiHoc.thoiLuong)`; UI tách bạch **"Thời lượng học ước tính"** vs **"Tổng bài giảng"** |
| **Chuyên gia & Nhà cung cấp** | `8` NCC · `21` CG | **`8 / 8` NCC · `21 / 21` CG** | NCC `#5` đã chuẩn hóa hồ sơ mô phỏng; `20` role `EXPERT` (`13 VERIFIED`, `7 DRAFT`) + `1` `ChuyenGia #4` (`USER`/`DRAFT`); không tự động `VERIFIED` |
| **Quyền học & Lịch sử học tập** | `150` ĐK · `300` LS | **`100% nguyên vẹn`** | `150/150 LEGACY ACTIVE`, `300` lịch sử học tập, `0` lỗi FK / orphan records |

---

## 2. Nghiệm thu Hệ thống, Kiểm thử & Trình duyệt
- **Backend Regression (`EduSuggest_phase4_test`):** `pytest --collect-only` = `269 tests` → **`269 passed, 0 failed, 0 skipped` (`120.08s`)** (gồm Auth, RBAC, Recommendation, Course Management, Learning Progress, Private File Authorization, Expert Workflow, Marketplace, Enrollment Gate, Payment Safety, Exception Refund, Financial Integrity, Durable Workers và 3 test mới GĐ5.5 cho allowlist video/anti-XSS/visibility).
- **Frontend Vite Production Build:** **PASS** (`1,912 modules`, `3.36s`).
- **Browser Automation Acceptance:** **`NOT TESTED (BLOCKED)`** do Chrome DevTools MCP báo `DevToolsActivePort ENOENT` trên môi trường host. Đã kiểm chứng toàn bộ HTTP endpoints (`5173`/`8000`, `120/120` WebP, `5176`/`8003`), cung cấp HTML Gallery so sánh ảnh bìa & nội dung bài học để kiểm tra trực quan trực tiếp tại `http://127.0.0.1:5173/`.
