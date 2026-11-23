# DEVELOPMENT STATUS — EduSuggest QA

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

**Build result:** BUILD FAIL (không thể xác nhận PASS). Lần chạy trực tiếp trong thư mục frontend thất bại với exit code 1 do lỗi `EPERM, Permission denied: 'D:\\đồ án\\EduSuggest\\frontend\\dist\\assets'` — Vite không thể xóa thư mục `dist/assets` cũ trước khi build (lỗi filesystem permission, không phải lỗi source code). Các lần chạy sau bị chuyển sang file log tạm do hạn chế shell môi trường, không trả kết quả trực tiếp nên không thể xác nhận exit code 0. Không đánh dấu BUILD PASS vì chưa có bằng chứng build hoàn tất thành công.

**Test result:** Không có script `test` trong `frontend/package.json`; không chạy được browser test. PostgreSQL integration test NOT TESTED (DB chính, không có DB test độc lập, không gửi request ghi).

**Các lỗi còn tồn tại:** Không có lỗi import/code đã xác định từ source review. Build chưa xác nhận được do hạn chế môi trường shell.

**NOT TESTED:** `npm.cmd run build`, browser render, responsive layout, PostgreSQL integration, authenticated API request với token thật, course/material recommendation với dữ liệu thật.
