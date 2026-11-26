# EDUSUGGEST — GĐ6.1: BÁO CÁO KIỂM TOÁN BẢO MẬT (SECURITY AUDIT)

**Ngày kiểm toán:** 2026-11-27  
**Phạm vi:** Static code analysis toàn dự án (`67` Vue views + `168` FastAPI endpoints) + `10` live non-destructive probes trên Production `8000` + `269/269` Backend security/RBAC/payment tests trên `EduSuggest_phase4_test`.

---

## 1. Kết quả kiểm tra thực tế

| Hạng mục bảo mật | Phương pháp kiểm tra | Kết quả | Mức độ rủi ro |
| :--- | :--- | :--- | :--- |
| **Authentication & JWT Revocation** | Live probe `invalid_jwt_me` → `401`; Argon2id + blacklist cleanup | **PASS** | An toàn |
| **RBAC & Unauthenticated Access** | Live probes `/api/admin/commerce/overview`, `/api/provider/sales/summary`, `/api/wishlist`, `/api/cart` → **`401`** | **PASS** | An toàn |
| **IDOR (Cross-user / Cross-provider / Cross-expert)** | Kiểm chứng qua `test_phase42`, `test_phase46`, `test_phase47a` (`269/269` PASS) | **PASS** | An toàn |
| **SQL Injection** | Static scan toàn bộ `backend/` → **`0` file dùng `text(f"...")`**; 100% SQLAlchemy parameterized queries | **PASS** | An toàn |
| **XSS & Video Iframe Injection** | Static scan `frontend/src/` → **`0` file dùng `v-html`**; `LearningView.vue` dùng allowlist `youtube-nocookie.com/embed/{11-char-id}` + chặn `javascript:`/`data:` (`test_phase55` PASS) | **PASS** | An toàn |
| **Path Traversal & Private File Auth** | Live probe `/media/courses/../../.env` → **`404`**; `private://materials/<id>` chặn ẩn danh (`401`/`404`) và chỉ phục vụ qua API kiểm tra quyền học | **PASS** | An toàn |
| **Hidden / Pending Leakage** | Live probe `/api/courses/31` → **`404`**; Recommendation `0` rò rỉ khóa `#31` & tài liệu `#132` | **PASS** | An toàn |
| **CORS Policy** | Live probe `Origin: https://evil.example.com` → `Access-Control-Allow-Origin: None` | **PASS** | An toàn |
| **Payment Safety, Signatures, Idempotency & Append-Only Logs** | HMAC-SHA256/512, `Idempotency-Key` fingerprint `409`, `trg_SuKienThanhToan_append_only`, Production chặn cứng `MOCK_PAYMENT` & `VNPAY_SANDBOX` | **PASS** | An toàn |
| **Rate Limiting (Auth & Public Search)** | Source audit: có rate limit trên các nhánh nhạy cảm, đề xuất bổ sung middleware rate-limit thống nhất theo IP ở GĐ6.6 | **LOW (P3)** | Thấp |

**Kết luận:** **`0` lỗ hổng CRITICAL/HIGH (P0)** được phát hiện.
