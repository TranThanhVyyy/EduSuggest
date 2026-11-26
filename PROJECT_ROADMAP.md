# EduSuggest — kiểm kê và lộ trình triển khai

**Ngày kiểm kê:** 2026-11-24

**Phạm vi:** đọc source, tài liệu và PostgreSQL bằng truy vấn `READ ONLY`. Không sửa code, cấu hình, migration hoặc dữ liệu.
**Nguyên tắc trạng thái:** `COMPLETED` chỉ dùng cho phần có bằng chứng cụ thể; `PARTIAL` nghĩa là có một phần code/UI/API nhưng thiếu luồng hoàn chỉnh; `MISSING` nghĩa là chưa thấy triển khai; `UNVERIFIED` nghĩa là chưa có bằng chứng runtime phù hợp.

## 1. Kiến trúc hiện tại

```text
Vue 3 + Vite
  views / components / layouts / Vue Router
  axios services + authState (sessionStorage)
              │ HTTP JSON + Bearer JWT
              ▼
FastAPI
  api routes + dependencies
       → service
       → repository
       → SQLAlchemy models / Pydantic schemas
              │
              ▼
PostgreSQL + Alembic
```

- **Frontend:** `frontend/src/views/{admin,reviewer,provider,user}`, layouts, router, API services, shared UI components và design tokens. `reviewer` là tên thư mục/layout cho role EXPERT.
- **Backend:** `backend/api`, `service`, `repository`, `models`, `schemas`, `config`, `utils`; Uvicorn/FastAPI; SQLAlchemy đồng bộ với Alembic.
- **Dữ liệu/tệp:** PostgreSQL là nguồn dữ liệu nghiệp vụ. `media/data` hiện chỉ có `.gitkeep`; config có các biến MinIO nhưng chưa tìm thấy endpoint/service upload được nối vào luồng.
- **Tài liệu:** có ERD và Design System/UX guidelines. `frontend/README.md` còn là README scaffold Vite, chưa mô tả cách chạy/kiểm thử sản phẩm đầy đủ.
- **Kiểm thử:** Frontend chỉ có `dev`, `build`, `preview`; không có script test. Không tìm thấy suite test theo tên file/thư mục thông dụng. Backend có pytest trong requirements nhưng không tìm thấy test suite.

## 2. Bằng chứng và trạng thái tổng quan

| Hạng mục | Trạng thái | Bằng chứng / giới hạn |
|---|---|---|
| Sơ đồ SQLAlchemy ↔ PostgreSQL | **COMPLETED** | Transaction chỉ đọc xác nhận đủ 13/13 bảng; không lệch tên bảng/cột, nullability, PK hoặc FK. |
| Alembic chain và version DB | **COMPLETED** | 4 revision tuyến tính; DB `alembic_version` là `d8a41f6c2b90`, revision cuối hiện có. Không chạy migration. |
| Authentication và role routing | **PARTIAL / UNVERIFIED** | Source có register/login/me/logout, JWT và guard; chưa xác minh đăng nhập/token role thật trong đợt này. |
| Nghiệp vụ ADMIN/EXPERT/PROVIDER/USER | **PARTIAL** | Nhiều màn/API hiện có; các nhóm nghiệp vụ chưa hoàn tất được ghi theo role bên dưới. Không coi source mapping là kiểm thử thành công. |
| USER learning, materials và recommendation | **MISSING** ở API | Có model và màn hình/empty state nhưng chưa có API nghiệp vụ tương ứng. |
| PostgreSQL seed nội dung | **MISSING trong DB hiện tại** | 0 category/course/lesson/material/enrollment/history/review; không có dữ liệu để nghiệm thu các luồng nội dung. |
| Responsive và browser E2E | **UNVERIFIED** | DEVELOPMENT_STATUS ghi nhận chưa xác nhận trực quan ở các viewport. |
| Frontend build | **BUILD FAIL (không xác nhận được PASS)** | Lần chạy trực tiếp trong thư mục frontend thất bại exit code 1 do lỗi `EPERM, Permission denied` trên `dist/assets` (filesystem permission, không phải code). Các lần chạy sau bị chuyển sang log file tạm do hạn chế shell, không xác nhận exit code 0. |
| Uvicorn từ shell hiện tại | **UNVERIFIED / BLOCKED** | Biến tiến trình `DEBUG=release` ghi đè `backend/.env` (`DEBUG=True`); lệnh bình thường dừng ở `bool_parsing`. Không dùng override để né trong đợt này. |

## 3. Chức năng theo role

| Role | Chức năng | Trạng thái | Ghi chú |
|---|---|---|---|
| ADMIN | Danh sách tài khoản, lọc theo role | **PARTIAL** | UI/API đọc `GET /api/admin/users`; không có CRUD tài khoản tổng quát. |
| ADMIN | Cấp role EXPERT | **PARTIAL** | Backend có `POST /api/admin/users/{user_id}/expert-role`; chưa thấy UI/service gọi endpoint này. |
| ADMIN | Quản lý danh mục | **PARTIAL** | UI và API list/create/update/delete có; DB hiện 0 danh mục, chưa kiểm thử CRUD. |
| ADMIN | Danh sách khóa học và trạng thái hiển thị | **PARTIAL** | Có list và API visibility; DB hiện 0 khóa học. Quy tắc chỉ đổi visibility sau APPROVED có trong workflow source. |
| ADMIN | Hồ sơ nhà cung cấp | **PARTIAL** | API duyệt/từ chối application và UI hiện có; DB hiện không có application. |
| ADMIN | Dashboard thống kê, analytics, gán reviewer, giám sát kiểm duyệt | **MISSING** ở API | Có một số màn hình điều hướng/placeholder; chưa có API thống kê, assignment hoặc review-monitor tương ứng. |
| EXPERT | Hồ sơ chuyên môn | **PARTIAL** | GET/PUT API và UI có; DB hiện không có hồ sơ chuyên gia. |
| EXPERT | Hàng đợi, chi tiết, quyết định và lịch sử duyệt khóa học | **PARTIAL** | API/UI có; chưa có course/review data để kiểm thử. |
| EXPERT | Duyệt tài liệu | **MISSING** ở API | Có route/view cho pending materials, nhưng Backend hiện không khai báo endpoint xử lý. |
| PROVIDER | Nộp hồ sơ và theo dõi application | **PARTIAL** | API/UI có; DB hiện không có application hoặc provider profile. |
| PROVIDER | Hồ sơ, khóa học, bài học, metadata tài liệu, gửi duyệt, lịch sử | **PARTIAL** | API/UI CRUD có; chưa có dữ liệu, chưa kiểm thử quyền sở hữu runtime. |
| PROVIDER | Upload file thật | **MISSING** | API lưu URL/metadata; chưa thấy multipart upload hoặc storage service được sử dụng. |
| USER | Register/login/profile và danh mục/khóa học | **PARTIAL** | Source gọi API; API có role guard. Giai đoạn 2 xác nhận snapshot mới có 3 tài khoản (ADMIN 1, USER 2), nhưng chưa chạy luồng bằng token thật; 0 danh mục/course. |
| USER | Enrollment, tiến độ, lịch sử học | **MISSING** ở API | Model tồn tại; không có endpoint cho ghi/đọc nghiệp vụ. `userService.js` trả empty/unavailable, không giả lập kết quả. |
| USER | Xem tài liệu công khai, đánh giá người học, gợi ý cá nhân hóa | **MISSING** ở API | Có model/UI một phần nhưng chưa có API/service tương ứng. |

**Không có chức năng nghiệp vụ nào được đánh dấu COMPLETED end-to-end** trong kiểm kê này: chưa có dữ liệu nội dung và chưa chạy kiểm thử theo role. Các status PARTIAL phản ánh code/UI/API hiện diện, không phải cam kết chức năng chạy ổn định.

## 4. API Backend hiện có

Các đường dẫn dưới đây được trích từ route source, mọi route có prefix `/api`. **Có route không đồng nghĩa đã được gọi thành công.** `FE: Có` nghĩa là service/view hiện tại có tham chiếu; `FE: Chưa thấy` nghĩa là route chưa thấy UI/service kết nối.

| Nhóm | Method và endpoint | Frontend |
|---|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` | Có |
| Tài khoản | `PUT /users/me`, `PUT /users/change-password` | Profile có; change-password đã kết nối UI tại UserProfile.vue (GĐ9.2) |
| Provider application | `POST /provider/applications`, `GET /provider/applications/me` | Có |
| Admin application | `GET /admin/provider-applications`, `POST /admin/provider-applications/{application_id}/approve`, `POST /admin/provider-applications/{application_id}/reject` | Có |
| Admin users/roles | `GET /admin/users`, `POST /admin/users/{user_id}/expert-role` | User list có; cấp EXPERT chưa thấy UI/service |
| Admin analytics | `GET /admin/analytics/summary` | Đã triển khai và kết nối UI tại AdminAnalytics.vue (GĐ9.2) |
| Categories | `GET /admin/categories`, `GET /provider/categories`, `POST /admin/categories`, `PATCH /admin/categories/{category_id}`, `DELETE /admin/categories/{category_id}` | Có |
| Admin courses | `GET /admin/courses`, `PATCH /admin/courses/{course_id}/visibility` | Có |
| Expert | `GET/PUT /expert/profile`, `GET /expert/courses/pending`, `GET /expert/courses/{course_id}`, `POST /expert/courses/{course_id}/decision`, `GET /expert/reviews/history` | Có |
| Provider review history | `GET /provider/courses/{course_id}/reviews` | Có |
| Provider profile/courses | `GET/PUT /provider/profile`, `GET /provider/courses`, `POST /provider/courses`, `GET/PUT/DELETE /provider/courses/{course_id}`, `POST /provider/courses/{course_id}/submit` | Có |
| Provider lessons | `POST /provider/courses/{course_id}/lessons`, `PUT/DELETE /provider/courses/{course_id}/lessons/{lesson_id}` | Có |
| Provider materials | `POST /provider/courses/{course_id}/lessons/{lesson_id}/materials`, `PUT/DELETE /provider/courses/{course_id}/lessons/{lesson_id}/materials/{material_id}` | Có, metadata/URL |
| USER catalog | `GET /categories`, `GET /courses` (query, category_id, limit), `GET /courses/{course_id}` | Có |

## 5. API còn thiếu

- USER: đăng ký/hủy đăng ký khóa học; đọc ghi progress và completion; lịch sử/learning activity; danh sách/chi tiết tài liệu truy cập được; ratings/reviews khóa học từ người học; API recommendation cho courses/materials.
- EXPERT: hàng đợi/chi tiết/quyết định/lịch sử kiểm duyệt tài liệu.
- ADMIN: thống kê tổng hợp; review-monitor; phân công reviewer; quản trị role tổng quát/thu hồi role; thống kê recommendation.
- PROVIDER: upload/stream/download file và quản lý lifecycle storage (xóa file, quyền truy cập, kích thước/loại MIME); API course activity nếu dashboard cần lịch sử.
- Chưa có endpoint cho reporting/analytics hoặc recommendation model metrics.

## 6. Database hiện trạng và điểm cần xác nhận

### Đối chiếu runtime

- Database trả lời truy vấn chỉ đọc; tên DB/schema: `EduSuggest.public`.
- 13 bảng domain: `VaiTro`, `NguoiDung`, `NhaCungCapKhoaHoc`, `DonXinNhaCungCap`, `DanhMuc`, `KhoaHoc`, `BaiHoc`, `TaiLieu`, `ChuyenGia`, `DanhGiaChuyenGia`, `LichSuHocTap`, `DangKyKhoaHoc`, `TokenBiThuHoi`; cộng bảng quản lý `alembic_version`.
- Snapshot Giai đoạn 0 ghi 4 role, 5 tài khoản, 6 token revoked; snapshot chỉ đọc Giai đoạn 2 hiện có 3 tài khoản (ADMIN 1, USER 2). Không có request ghi từ đợt kiểm thử này; cần xác minh thay đổi giữa hai snapshot trước khi dùng làm baseline. Các bảng category/course/provider profile/expert profile/lesson/material/enrollment/learning history/review/application hiện rỗng.
- Các bảng/cột/nullability/PK/FK khớp metadata ORM trong lần introspection này. Không chạy migration và không suy ra rằng mọi ràng buộc nghiệp vụ đã đầy đủ.

### Điểm cần đưa vào thiết kế trước khi triển khai

- Nhiều FK nghiệp vụ đang nullable (`NguoiDung.maVaiTro`, owner/category/reviewer của course, quan hệ lesson/material, enrollment/history). Xác nhận quy tắc nullability trước khi thiết kế data validation; không tự thay schema.
- Database hiện có unique cho username và `TokenBiThuHoi.jti`, nhưng chưa thấy unique constraint cho email, một provider/expert profile trên mỗi user, hoặc một enrollment trên cặp user-course. Service có kiểm tra một số điều kiện; nên quyết định tính duy nhất có cần được bảo vệ cả ở DB hay không.
- Status được lưu bằng string; chưa thấy check constraint cho các tập giá trị course review/visibility, provider application hoặc review. Cần thống nhất enum và chuyển đổi an toàn nếu sau này có migration.
- `LichSuHocTap.tienDo` là string trong khi `DangKyKhoaHoc.tienDo` là numeric; cần định nghĩa semantics, đơn vị và nguồn sự thật cho progress.
- ERD mô tả các quan hệ nhưng bảng interaction/rating chưa có dữ liệu. Chưa thể đánh giá truy vấn, index hoặc chất lượng dữ liệu ở quy mô thật.
- Backend lifespan chạy cleanup xóa token hết hạn ngay khi startup và lặp mỗi 24 giờ; đã có lần startup trước ghi nhận xóa 1 token hết hạn. Tính chất ghi dữ liệu này cần được đưa vào vận hành/test strategy. README cũng liệt kê `utils.seed_roles`, là lệnh ghi role/đồng bộ sequence; không tự chạy trong kiểm kê.

## 7. Recommendation System

### Dữ liệu sẵn có

- Content: `KhoaHoc.tieuDe`, `moTa`, `trinhDo`, `thoiLuong`, `gia`, `maDanhMuc`; bài học và metadata tài liệu có thể bổ trợ nếu được chuẩn hóa.
- Taxonomy: `DanhMuc`; hiện **0 danh mục và 0 khóa học**.
- Interactions: `DangKyKhoaHoc`, `LichSuHocTap`, trường `danhGia`; hiện các bảng này rỗng và chưa có API ghi/đọc tương tác.
- User preferences/profile: hiện chưa thấy trường sở thích học tập có cấu trúc/API riêng.

### Đánh giá phương pháp

- **Content-Based Filtering:** phù hợp làm baseline đầu tiên sau khi có metadata thật. Chuẩn hóa category/level/keywords; có thể dùng title/description/features, rồi loại khóa học không APPROVED + VISIBLE. Chất lượng phụ thuộc metadata và cần giải thích lý do gợi ý.
- **Collaborative Filtering:** chưa khả thi để đánh giá trong DB hiện tại; thiếu interactions và endpoint ghi enrollment/progress/ratings. Cold-start user/item sẽ nặng khi số lượng nhỏ.
- **Hybrid:** chỉ nên thử sau khi content baseline và interaction pipeline có dữ liệu đủ. Có thể kết hợp ranking có trọng số hoặc fallback theo mức độ confidence; không tạo bảng `GoiY`/`DuLieuTuongTac` nếu quyết định vẫn là tính toán ở Backend.
- **Cold-start:** user mới có thể chọn category/level hoặc dùng content profile từ hành vi ban đầu; course mới dựa metadata. Popularity fallback chỉ dùng số liệu thật, có lọc trạng thái hiển thị.
- **Đánh giá:** temporal holdout; Precision@K, Recall@K, NDCG@K, catalog coverage, diversity, novelty và phân tích riêng cold-start. So sánh với baseline phổ biến có thật; online A/B chỉ sau khi có traffic và logging đồng ý.

**Trạng thái Recommendation: MISSING / UNVERIFIED.** Có màn hình nhưng empty state nói rõ chưa nối dịch vụ; chưa có route, recommender service, interaction data hoặc chỉ số đánh giá.

## 8. Mock, chất lượng và rủi ro

- Fixture còn trong repo: `adminData.js`, `providerData.js`, `reviewerCourses.js`, `reviewerDashboardData.js`, `reviewerHistory.js`, `reviewerLectures.js`, `reviewerMaterials.js`, `userData.js`. Legacy `adminService.js`, `providerService.js`, `reviewerService.js` tạo dependency tới fixture; không thấy component/router hiện tại gọi các service legacy. `userData.js` không có reference. **Không xóa** vì ngoài phạm vi và chưa kiểm tra quy trình demo ngoài source.
- `userService.js` vẫn được gọi từ các màn learning/material/recommendation nhưng trả `[]`/`null` hoặc báo API chưa có; đây là empty/unavailable placeholder, không phải dữ liệu nghiệp vụ thật.
- `demoOnly` metadata còn trên nhiều route, nhưng `router.beforeEach` không kiểm tra cờ đó. Tên metadata có thể làm người bảo trì hiểu nhầm chức năng đang bị chặn demo.
- Rủi ro xác thực/vận hành: token nằm trong `sessionStorage` (JS-accessible); chưa có kiểm thử XSS/CSP. Có JWT validation, Argon2 hashing, revocation, backend role dependencies theo source; chưa kiểm thử bảo mật runtime, rate limiting hoặc brute-force controls.
- Rủi ro config: tiến trình làm việc hiện kế thừa `DEBUG=release`, làm lệnh bình thường lỗi dù `.env` có `DEBUG=True`. Nguồn biến không xác định được trong repo/User/Machine scope.
- Rủi ro khởi động: token cleanup gây delete tự động; cần phân biệt môi trường dev/test và production, đồng thời không chạy startup trên DB thật khi chưa chấp thuận side effect.
- Rủi ro hiệu năng: không có dữ liệu để benchmark; xem lại index cho filter/status/FK/query catalog sau khi có workload và query plan thật. Không thêm index theo suy đoán.
- **Chưa xác minh:** các luồng role bằng token thật, API response/error, browser console/network, responsive 1440/1366/768/375, accessibility thực tế, upload, database performance và recommendation quality.

## 9. Lộ trình 11 giai đoạn

Đánh số 0–10 để bao gồm giai đoạn kiểm kê hiện tại và 10 giai đoạn triển khai tiếp theo. Chỉ bắt đầu giai đoạn mới sau khi tiêu chí nghiệm thu của dependency trước đạt.

| Giai đoạn | Trạng thái hiện tại | Phạm vi và tiêu chí nghiệm thu |
|---|---|---|
| **0 — Kiểm kê và baseline** | **COMPLETED** (tài liệu/source/DB read-only) | Bàn giao roadmap/status; có danh sách chức năng/API, DB baseline, giới hạn bằng chứng và rủi ro; không thay dữ liệu. |
| **1 — Môi trường và kiểm thử nền** | **PARTIAL** | Khắc phục nguồn `DEBUG=release`; thống nhất lệnh setup/start; cô lập DB test; tránh cleanup/seed tự chạy trên DB thật; thêm smoke/unit/integration checks. Nghiệm thu: start bình thường, readiness trả trạng thái DB thật, test dùng dữ liệu cô lập, không ghi vào DB dev/prod. |
| **2 — Auth, hồ sơ và role access** | **PARTIAL** | Register/login/me/logout, đổi mật khẩu, refresh/expiry policy nếu cần, frontend redirect và role matrix. Nghiệm thu: happy path và sai mật khẩu/email-as-username, token revoked/expired, role mismatch, password/session behavior có API tests. |
| **3 — Taxonomy và onboarding Provider/Expert** | **PARTIAL** | Quy trình provider application, quyết định admin, tạo profile/role; cấp expert và profile; xác thực uniqueness/transaction. Nghiệm thu: state transitions, chống quyết định lặp, role/profile đồng bộ và ownership tests; dùng DB test. |
| **4 — Provider authoring** | **PARTIAL** | CRUD course/lesson/material metadata, categories, validate required fields, ownership, editability và submit. Nghiệm thu: provider chỉ thao tác nội dung của mình; trạng thái draft/revision; roundtrip response↔UI. |
| **5 — Expert moderation** | **PARTIAL** | Pending/detail/approve/reject/needs-revision/history; bổ sung material review API/UI nếu được duyệt. Nghiệm thu: EXPERT duy nhất đổi review status, audit trail/feedback bền vững, duplicate/concurrent decisions an toàn. |
| **6 — User discovery** | **PARTIAL** | Category/course search/filter/detail; đảm bảo chỉ APPROVED + VISIBLE lọt catalog/detail. Nghiệm thu: query, pagination/limits, empty/error states và visibility boundary có integration tests. |
| **7 — Enrollment và learning progress** | **MISSING** | Enrollment, progress, lesson completion, history/activity endpoints và UI; định nghĩa nguồn truth/đơn vị progress trước. Nghiệm thu: idempotent enrollment, user chỉ đọc/ghi dữ liệu của mình, tiến độ tổng hợp nhất quán. |
| **8 — Materials, ratings và feedback** | **PARTIAL/MISSING** | Chọn storage thật cho upload; quyền truy cập/metadata/lifecycle; learner rating/review và material access; material moderation. Nghiệm thu: kiểm tra MIME/size/authorization, file không public ngoài ý muốn, rating chỉ từ user đủ điều kiện, moderation theo role. |
| **9 — Recommendation** | **MISSING** | Content baseline → logging interactions → offline CF/hybrid; không cần bảng gợi ý/tương tác mới nếu giữ compute-at-request. Nghiệm thu: không trả nội dung bị ẩn/chưa duyệt, đo ranking metrics trên tập holdout, cold-start/coverage/diversity và giải thích kết quả. |
| **10 — Admin analytics và production readiness** | **MISSING/PARTIAL** | API dashboard/reporting, review assignment/monitoring, audit, observability, index/query tuning và release/security checklist. Nghiệm thu: số liệu đối chiếu truy vấn nguồn, role authorization, pagination/performance budget, backup/restore và vận hành đã diễn tập. |

## 10. Phụ thuộc chức năng

```text
G1 môi trường/test isolation
  └─ G2 auth/role
       └─ G3 onboarding + profiles + taxonomy
            └─ G4 provider content
                 └─ G5 expert review
                      └─ G6 approved/visible catalog
                           ├─ G7 enrollment/progress/events ─┐
                           └─ G8 materials/ratings/storage ─┴─ G9 recommendation
G3–G9 dữ liệu nghiệp vụ + audit ─────────────────────────────── G10 analytics/release
```

- User discovery cần category/course thật và quy tắc moderation/visibility đã ổn định.
- Enrollment/progress cần catalog và identity/ownership; interaction data mới là đầu vào CF.
- Recommendation cần item metadata trước, interactions sau; không thể nghiệm thu với DB rỗng.
- Admin analytics phụ thuộc dữ liệu có định nghĩa và audit source-of-truth.
- Upload và kiểm duyệt tài liệu phụ thuộc quyết định storage/quyền truy cập; không thay bằng URL giả.

## 11. Đề xuất bước tiếp theo

Ưu tiên **Giai đoạn 1**: xác định ai/đâu đặt `DEBUG=release`, chạy từ môi trường đã chuẩn hóa, tách test database và xử lý side effect cleanup/seed trước khi bắt đầu test tích hợp. Sau đó làm Giai đoạn 2 với ma trận role và token; tiếp tục theo dependencies trong roadmap. Trước mọi CRUD cần tài khoản/môi trường test riêng và phê duyệt rõ phạm vi dữ liệu.

## 12. Kiểm tra Authentication & Authorization — cập nhật Giai đoạn 2

- Runtime GET: `/`, `/api/health`, `/docs`, `/openapi.json` trả **200**; `/api/auth/me` không token/token sai, cùng GET admin users/categories, expert pending, provider courses và USER categories không token đều trả **401**.
- Runtime input âm: login username không tồn tại trả **401**; đăng ký payload có `maVaiTro` trả **422**. Các request không tạo tài khoản. Không gửi request CRUD, đăng ký hợp lệ, logout bằng token thật hoặc thay đổi dữ liệu.
- Runtime roles: chưa có credentials/token test đủ 4 role; chưa xác nhận 403, quyền chéo role, quyền sở hữu provider, valid `/auth/me`, logout/revocation hoặc browser navigation. DB config đang trỏ `EduSuggest`; chưa xác minh DB test độc lập.
- Source review xác nhận register gán USER, login username tạo JWT, `/auth/me` đọc role Backend, response schema không có password/hash, Backend dependency áp role và Frontend guard gọi `/auth/me`. Frontend build **PASS**; Backend pytest thu thập **0 tests** (exit 1). Không phát hiện source defect đủ căn cứ để sửa.
- Giai đoạn 2 tiếp tục **PARTIAL / UNVERIFIED**. Điều kiện nghiệm thu còn lại: DB test độc lập; credentials đủ 4 role; kiểm thử 401/403, expiry/revocation và browser routing; xác minh không phát sinh ghi vào DB chính.


## Provider phase update (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Backend source provides Provider profile/course/lesson/material-metadata/submission routes and per-course review history, with ownership checks and review-state restrictions. Frontend status mapping now matches Backend states, numeric zero is preserved, and course price uses the existing `gia` API field. Production build passed.

**Acceptance work remaining:** isolated test DB; approved Provider credentials and test data; integration coverage for CRUD, cross-owner access, validation, submit/resubmit, and API responses; install test dependencies and run Backend suite; browser/responsive checks. No writes were sent to the primary DB. Upload and chapters are unsupported by current API/schema; review history is available per course only.


## Expert moderation phase update (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Source confirms EXPERT role guards; pending-only review detail/decision; supported transitions APPROVED, REJECTED, NEEDS_REVISION; required feedback for rejection/revision; review audit record creation; and a history endpoint scoped to the current Expert. Frontend decision payload fields match the existing schema. Small UI state-handling defects were fixed.

Runtime evidence is limited to unauthenticated GETs returning 401. No decision was submitted. Acceptance still requires an isolated test DB, valid Expert and Provider accounts, integration checks for all decisions and access-control cases, and browser/responsive validation. Review history lacks display names (only IDs), course detail lacks category/provider names and objectives/audience, and material moderation has no API. Keep these as API capability gaps; do not infer them or change the contract in this phase.


## Admin phase update (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Existing Backend supports protected account listing, category CRUD, provider-application review, course listing, approved-course visibility changes, and a constrained USER-to-EXPERT role assignment. Frontend now integrates the constrained role assignment with confirmation; category operation success feedback is retained after refresh. Backend separately enforces that only APPROVED courses may change visibility.

Runtime checks were unauthenticated GETs only (401); there were no ADMIN credentials or isolated test DB, and no writes were sent. Admin CRUD/decisions/visibility, role assignment, role matrix, and browser/responsive behavior remain untested. Current APIs do not provide aggregate statistics, generic user detail/edit/lock, provider-profile admin listing/detail, review monitoring, or reviewer assignment. Proceed to acceptance only after isolated test data and ADMIN/non-ADMIN credentials are available.


## User phase update (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Backend provides authenticated public course/category reads, course detail restricted to APPROVED + VISIBLE, `/auth/me`, and `PUT /users/me`. Frontend uses these routes; category lookup failure no longer masks the course response, search now reflects title-only Backend behavior, unknown-price sorting is preserved, and phone length matches schema.

Anonymous GETs to catalog/category/course detail/auth-me returned 401; `GET /users/me` returned 405 because the supported method is PUT. No valid USER credential or isolated test DB was available, and no writes were sent. Enrollment, enrollment listing, learning progress/history/content, public materials, recommendations and expert ratings lack USER APIs. Catalog has no offset pagination and is capped at 100 results. Browser/responsive behavior remains unverified.

## Phase 7 implementation update (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Added USER enrollment, enrollment list, enrollment-protected lesson access, progress, explicit lesson completion, and learning history endpoints; integrated the existing USER course detail, dashboard, progress, learning, and history screens. Implementation reuses the two existing tables, makes no migration/schema change, and filters learner views to currently APPROVED + VISIBLE courses. Completion is recorded per lesson using the existing `LichSuHocTap.tienDo` field and aggregate percentage/date in `DangKyKhoaHoc`.

Acceptance remains blocked on a confirmed isolated PostgreSQL test database and test USER/course data. Build, Python compilation, app/OpenAPI import, and diff whitespace checks passed; no DB writes or browser checks were performed. Schema-level uniqueness for enrollment/history and explicit start/time-spent tracking remain open design gaps; no cancellation behavior was added.
## Phase 7.1 verification update (2026-11-24)

**Phase 7 remains PARTIAL / UNVERIFIED.** Source review passed for identity scoping, role checks, course visibility, enrollment gates, course/lesson ownership, empty responses, and transaction boundaries. Two source defects were fixed: repeated completion no longer refreshes the history timestamp, and delayed requests no longer overwrite state after route changes. Enrollment and completion now hold a row lock on the course against concurrent visibility changes; counts are constrained to the course's own lesson IDs.

The configured/live PostgreSQL target is the primary `EduSuggest` database (`localhost:5432`, server `172.17.0.2:5432`). No EduSuggest test database exists. A read-only catalog/privilege check found the current role can create a separate database (`CREATEDB`); no database was created, migrated, or written in this phase. Same-service advisory/row locks do not protect against external writers that bypass those locks; schema uniqueness is still absent for enrollment and per-lesson history. Fixing that safely requires a separate data audit and schema decision.

Build, Python compile/import/OpenAPI, and `git diff --check` passed. Pytest found no tests; no browser tool or safe test DB/data was available. All PostgreSQL integration and browser/responsive scenarios remain NOT TESTED. G7.1 conclusion: PARTIAL, not COMPLETED.
## Giai đoạn 8.1 - Recommendation design update (2026-11-24)

The requested analysis/design is documented in `docs/RECOMMENDATION_DESIGN.md`; no code/API/database change was made. This request's “Giai đoạn 8.1” is a design milestone for Recommendation; the existing 0–10 roadmap labels Recommendation as Giai đoạn 9 after Giai đoạn 8 materials/ratings. Keep that roadmap sequence unless the project owner renumbers it.

**Recommendation remains MISSING / UNVERIFIED for runtime.** Source contains course/item features and Giai đoạn 7 enrollment/progress history routes, but no recommendation route/service/schema; current DB snapshot has 0 categories/courses/lessons/materials/enrollments/learning histories/expert reviews (3 users). User profile has no preference attributes; expert ratings are not learner ratings. Current USER Recommendation view uses empty placeholder service methods. Admin recommendation metrics fixture is not used by the current AdminRecommendations screen.

The earlier §7 wording that no interaction tables/APIs exist is superseded by Giai đoạn 7: those models/routes now exist, but have no rows in the verified current DB. Proposed order: data readiness → Content-Based baseline → protected APIs → existing USER screens integration → time-split offline evaluation → CF only after evidence → tuned Hybrid. No Recommendation tables are proposed.
## Phase 8.2 - Backend Content-Based baseline (2026-11-24)

**Status: PARTIAL / UNVERIFIED.** Implemented the pure Python ranking service and three USER-only API routes without schema/migration/dependency changes. Unit tests (9), compilation, import/OpenAPI (3 routes present), and dependency consistency pass. PostgreSQL integration and browser checks are NOT TESTED because no isolated test DB is configured and the verified primary database has no recommendation catalog or interaction rows. The new-user fallback is labeled as discovery and is not claimed to be personalized.

**Remaining sequence:** (1) provision and verify a separate test database, then test role gates, visibility, enrollment scope, route validation, empty results, and actual response schemas; (2) integrate existing USER recommendation/course/material screens with these APIs, with loading/error/empty states; (3) seed only the isolated test DB through an approved test fixture for deterministic integration/quality checks; (4) when real interaction history has sufficient coverage, establish time-based Precision/Recall/NDCG and coverage baselines; (5) consider CF, then Hybrid, only after measured evidence. No production DB writes or recommendation tables are part of this implementation.

## Giai đoạn 8.3 - Frontend Recommendation integration update (2026-11-24)

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

**Trạng thái: COMPLETED.**

- **Kiểm tra Database:** Xác nhận kết nối PostgreSQL tới `EduSuggest`. Đếm bảng read-only: `DanhMuc`: 0, `KhoaHoc`: 0, `BaiHoc`: 0, `TaiLieu`: 0, `DangKyKhoaHoc`: 0, `LichSuHocTap`: 0. Xác nhận chưa có database kiểm thử riêng biệt (`EduSuggest_test`). Tuân thủ quy tắc an toàn: Không tự ý tạo DB, không chạy seed vào DB `EduSuggest`.
- **Bộ dữ liệu kiểm thử (Dataset Specification):**
  * 6 Danh mục bao phủ toàn diện: Web Frontend, Web Backend, Cơ sở dữ liệu & SQL, Mobile Dev, Data Science & AI, DevOps & Cloud.
  * 13 Khóa học mẫu đa dạng trạng thái (APPROVED+VISIBLE, APPROVED+HIDDEN, PENDING+VISIBLE, REJECTED+HIDDEN), trình độ (Beginner/Intermediate/Advanced), thời lượng và học phí.
  * Cấu trúc bài học và tài liệu học tập chi tiết (tiêu đề, nội dung, phân loại: PDF, SLIDE, CHEATSHEET, CODE, DATASET).
  * 5 Tài khoản người dùng mẫu đại diện cho các User Personas: Cold-start user, Vue specialist user, Full-stack hybrid user, Provider demo, Expert demo.
- **Kịch bản kiểm thử (Test Scenarios):**
  * Scenario 1: Lọc trạng thái khóa học (APPROVED+VISIBLE candidate filtering).
  * Scenario 2: Gợi ý khóa học tương tự theo Cosine Similarity văn bản.
  * Scenario 3: Loại trừ khóa học đã đăng ký (Enrolled Exclusion).
  * Scenario 4: Gợi ý tài liệu học tập theo ngữ cảnh bài học / khóa học.
  * Scenario 5: Fallback người dùng mới (Cold-Start fallback sang 'latest' discovery).
  * Scenario 6: Người dùng đa sở thích (Multi-interest personalized ranking).
  * Scenario 7: Kiểm tra Enrollment Gate bảo vệ truy cập tài liệu học tập (403 Forbidden).
- **Chuẩn bị Script Seed an toàn (`backend/scripts/seed_recommendation_demo.py`):**
  * Tích hợp 4 lớp bảo vệ an toàn: Chặn database chính (`EduSuggest`), yêu cầu cờ xác nhận `--confirm-seed-test-data` hoặc `--dry-run`, cơ chế Idempotent tránh trùng lặp, cơ chế Atomic transaction rollback.
  * Cú pháp `py_compile` PASS. Kiểm tra guardrail: Từ chối thực thi khi không có flag hoặc khi kết nối vào `EduSuggest`. Script KHÔNG được chạy ghi vào DB trong giai đoạn này.

**Kế hoạch tiếp theo (GĐ8.5):**
1. Nhận chỉ thị/phê duyệt từ User để thiết lập database test an toàn (ví dụ: `EduSuggest_test`).
2. Chạy Alembic migration trên database test để đồng bộ schema 13 bảng.
3. Chạy script seed an toàn `seed_recommendation_demo.py` vào database test.
4. Chạy bộ test kiểm chứng thuật toán Recommendation (GĐ8.5 Recommendation Verification Suite).

## Giai đoạn 8.5 - Triển khai Database kiểm thử và Nghiệm thu Recommendation (2026-11-24)

**Trạng thái: COMPLETED.**

- Đã tạo database độc lập `EduSuggest_test` trên PostgreSQL 16; database chính `EduSuggest` được bảo toàn tuyệt đối 100% (READ ONLY, không thay đổi bản ghi nào).
- Chạy Alembic migration đạt revision `d8a41f6c2b90` (14 bảng, đầy đủ constraints).
- Chạy dry-run và seed thực tế thành công qua `seed_recommendation_demo.py` với các cơ chế guardrail nghiêm ngặt.
- Nghiệm thu thành công 7/7 kịch bản Recommendation qua test suite `backend/tests/integration/test_recommendation_integration.py` (tổng 16/16 unit + integration tests PASS).
- Frontend Vite build hoàn tất thành công (1876 modules transformed, exit code 0).
- Hệ thống Recommendation Content-Based và Authorization Enrollment Gate đã được kiểm chứng hoạt động chính xác trên cơ sở dữ liệu thật.

## Giai đoạn 8.6 - Kiểm thử E2E Frontend và Trực quan hóa Khuyến nghị (2026-11-24)

**Trạng thái: COMPLETED.**

- **Triển khai môi trường kiểm thử E2E tự động:**
  * Backend FastAPI (port 8000) kết nối database kiểm thử `EduSuggest_test`.
  * Frontend Vite dev server (port 5173).
  * Chrome Headless qua giao thức Chrome DevTools Protocol (CDP) port 9222.
- **Khắc phục lỗi Frontend:**
  * Sửa lỗi unwrap reactivity template trong `Recommendations.vue` (`!isMaterialView && strategy === 'latest'`).
  * Bổ sung import `CourseCard` bị thiếu trong `CourseDetail.vue`.
- **Nghiệm thu toàn diện 4 luồng người dùng E2E:**
  * Flow 1 (Cold-start - `learner_frontend_newbie`): Hiển thị đúng banner khám phá mới cập nhật, 6 thẻ Dashboard, 10 thẻ trang gợi ý.
  * Flow 2 (Vue Specialist - `learner_vue_specialist`): Loại trừ khóa C1 đã học; đề xuất C2 (Vue 3 Pinia) và C3 (React); hiển thị Similar Courses trên Course Detail; tải 5 tài liệu hợp lệ; chặn 403 Forbidden khi truy cập tài liệu khóa chưa đăng ký.
  * Flow 3 (Multi-interest - `learner_fullstack_hybrid`): Loại trừ đồng thời C1 và C4; đề xuất phân bổ cân bằng cả Backend nâng cao (C5 Microservices) và Frontend (C3, C2).
  * Flow 4 (Responsive Mobile 375x667): Xác nhận không tràn ngang, layout co giãn chuẩn mực trên thiết bị di động.
- **Giám sát chất lượng:** 0 lỗi console, 0 cảnh báo; 100% request API hợp lệ; 0 khóa học HIDDEN/PENDING/REJECTED rò rỉ vào giao diện người dùng.
- **Hồi quy kiểm thử & Build:**
  * `npm.cmd run build`: PASS (1876 modules transformed, built in 1.18s).
  * Backend Pytest: 16/16 tests PASS (9 unit tests + 7 integration tests).
  * Database chính `EduSuggest`: Bảo toàn tuyệt đối 100%.

**Đề xuất Giai đoạn tiếp theo (GĐ9):**
1. Đánh giá hiệu năng và mở rộng thuật toán Recommendation (Collaborative Filtering / Hybrid Recommendation / Matrix Factorization khi có dữ liệu tương tác người dùng lớn).
2. Chuẩn bị hồ sơ nghiệm thu kỹ thuật, biểu đồ kiến trúc, tài liệu hướng dẫn vận hành và báo cáo tốt nghiệp.

## Giai đoạn 9.1 - Kiểm toán Kỹ thuật Toàn diện và Đánh giá Hoàn thiện (2026-11-24)

**Trạng thái: COMPLETED.**

- Đã thực hiện kiểm toán toàn diện 100% cấu trúc dự án EduSuggest: Backend, Frontend, Cơ sở dữ liệu, Mô hình Recommendation, Bộ test và Tài liệu.
- Báo cáo chi tiết 12 phần được lưu tại `docs/GD9_1_COMPREHENSIVE_AUDIT_REPORT.md`.
- Đánh giá mức độ sẵn sàng tốt nghiệp: 8.5/10 điểm (Sẵn sàng bảo vệ sau khi tinh chỉnh các tính năng phụ).
- Xác định 4 hạng mục hành động ưu tiên cao cho Giai đoạn 9.2: Đổi mật khẩu, Thống kê Admin, Hoạt động học tập trên Header và chuẩn hóa Ruff Linter.

## Giai đoạn 9.2 - Hoàn thiện Chức năng Phụ và Tinh chỉnh Giao diện (2026-11-24)

**Trạng thái: COMPLETED.**

- **Hạng mục 1 (Đổi mật khẩu):** Tích hợp hoàn chỉnh form đổi mật khẩu vào `UserProfile.vue`, kết nối API `PUT /api/users/change-password`, kiểm tra client-side độ dài 8-128 ký tự, mật khẩu mới khác mật khẩu cũ, khớp xác nhận, ẩn/hiện mật khẩu, trạng thái submitting và toast thông báo.
- **Hạng mục 2 (Admin Analytics):** Xây dựng schema `AdminAnalyticsSummaryResponse`, service và repo `get_admin_analytics_summary`, endpoint `GET /api/admin/analytics/summary` bảo vệ bằng role `ADMIN`. Thiết kế lại `AdminAnalytics.vue` với 4 stat cards, chi tiết lượt học, loading skeleton, banner lỗi có retry và empty state.
- **Hạng mục 3 (Thông báo Header):** Kết nối chuông thông báo trên `UserHeader.vue` với API `GET /api/learning/history` qua `fetchLearningHistory()`. Hiển thị 5 hoạt động gần nhất kèm tên khóa học, bài học, thời gian hoàn thành và liên kết điều hướng.
- **Hạng mục 4 (Sửa Ruff I001):** Sắp xếp imports trong `backend/api/workflows.py`. Toàn bộ backend đạt 0 cảnh báo lint (`ruff check .` -> All checks passed!).
- **Hồi quy & Kiểm thử:**
  * Backend Pytest: 20/20 tests PASS (9 unit tests + 7 integration tests + 4 admin analytics tests).
  * Frontend Vite build: PASS (1876 modules transformed, 1.22s, 0 errors).
  * Cơ sở dữ liệu: Cả 2 DB `EduSuggest` và `EduSuggest_test` được bảo toàn nguyên vẹn 100%.
