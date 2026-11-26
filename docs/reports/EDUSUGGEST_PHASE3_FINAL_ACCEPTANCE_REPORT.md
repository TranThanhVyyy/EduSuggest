# EduSuggest – GĐ3.8 Final Acceptance & Production Readiness

**Ngày:** 2026-11-26  
**Kết luận:** **NO-GO cho Production activation**  
**Phạm vi:** Nghiệm thu luồng quản lý EXPERT, review assignment, accountability, bảo mật, concurrency và hồi quy. Không bật production flags, không chạy migration, không sửa `.env`, không dùng Git.

## 1. Tóm tắt nghiệm thu

| Hạng mục | Kết quả | Căn cứ |
|---|---|---|
| PostgreSQL staging | PASS có điều kiện | `EduSuggest_phase3_test` được xác nhận bằng `SELECT current_database()`; revision `c3d4e5f6a7b8`. |
| Production database | Chỉ đọc | Truy vấn chạy trong transaction `READ ONLY`, xác nhận `EduSuggest`, revision `c3d4e5f6a7b8`; không chạy mutation lên DB này. |
| Backend HTTP staging | PASS smoke | `127.0.0.1:8001`: `/`, `/api/health`, `/docs`, `/openapi.json` trả 200; `/api/auth/me` và gợi ý course không token trả 401. |
| Backend full suite | PASS | `209 passed`, 1 cảnh báo Starlette/httpx deprecation. Ba runtime flags tắt trong lượt này để giữ tương thích với các test legacy. |
| Backend workflow/accountability/worker tests với flags bật | PASS | Các file Phase 3.3–3.8: `28 passed`, 1 cảnh báo. Đây là integration/concurrency test với PostgreSQL test DB, không phải worker service chạy nền liên tục. |
| Frontend build | PASS | `npm.cmd run build`: Vite 8.3.8, 1,896 modules transformed. |
| Browser E2E / responsive / screenshot | NOT TESTED | Chrome headless thoát do GPU process fatal, kể cả với software rendering; không có browser automation khác sử dụng được. Frontend staging chỉ được xác nhận HTTP 200 tại `127.0.0.1:5174`. |
| Worker launcher | BLOCKED | Worker class có cơ chế xử lý job nhưng source không có CLI/service entrypoint; flag `AUTO_ASSIGNMENT_WORKER_ENABLED` không được tiêu thụ bởi app lifespan. Không chứng minh được worker được khởi động, giám sát và tự phục hồi như một tiến trình triển khai thực tế. |
| Kích hoạt Production | **NO-GO** | Browser acceptance chưa hoàn tất; worker deployment lifecycle chưa được xác minh; direct revocation của URL file ngoài hệ thống chưa được chứng minh. |

### Phạm vi kiểm thử thực tế

- **Integration trên PostgreSQL test:** test suite cài guard database `EduSuggest_phase3_test`; xác nhận revision không đổi và không chạy migration.
- **Unit/integration/security:** SEC-01/SEC-02, RBAC, ownership, token invalidation, notification ownership/idempotency, legacy open-pool route, workflow boundaries và material visibility được kiểm qua test hiện hữu.
- **Concurrency:** các kiểm thử Phase 3.3–3.8 chạy nhiều session PostgreSQL cho queue claim/fencing/recovery, tranh chấp manual-vs-auto assignment, accept-vs-expire, accountability và assignment lifecycle. Kết quả cuối: `28 passed` trên feature-flag test group.
- **HTTP trực tiếp:** chỉ smoke-check staging, không gửi request ghi nghiệp vụ qua HTTP vì không có browser/account E2E an toàn sẵn sàng. Các thao tác ghi được thực thi trong integration tests đã khóa vào DB test.
- **Không kiểm thử browser:** chưa xác nhận điều hướng, keyboard, console/network, viewport 375/768/1024/1440 hoặc chụp ảnh thật. Không đánh dấu UI/UX là PASS.

## 2. Runtime và bảo vệ dữ liệu

- Staging API phản hồi trên `127.0.0.1:8001`; frontend Vite phản hồi trên `127.0.0.1:5174`, cấu hình tiến trình Vite trỏ API tới `http://127.0.0.1:8001/api`.
- Staging database được xác nhận độc lập. Cả hai database hiện ở Alembic revision `c3d4e5f6a7b8`; không có migration chạy trong GĐ3.8.
- Production DB được truy vấn chỉ đọc. Không gọi endpoint ghi trên cổng production `8000`, không thay `.env`, không xóa/chỉnh dữ liệu production.
- Một account ADMIN staging tạm được tạo để dự phòng browser acceptance nhưng automation không khởi động được. Account ID 2600 và các phụ thuộc được kiểm tra rồi xóa trong `EduSuggest_phase3_test`; truy vấn sau dọn xác nhận còn 0 account theo marker fixture đó.
- Backend lifespan có job dọn token hết hạn. Trong lần khởi động staging trước đó, job đã xóa 5 token blacklist hết hạn **trên test DB**; đây là thay đổi staging được ghi nhận. Không có tác động lên production.
- Không thể đọc environment của tiến trình production đang chạy để xác nhận trực tiếp ba runtime flags. Source mặc định cả ba cờ là false; trạng thái process production vẫn cần xác nhận trong rollout window trước khi cho phép thay đổi.

## 3. Kết quả nghiệp vụ và bảo mật

### Luồng EXPERT / assignment

Test suite bao phủ tạo expert bằng API, mật khẩu đổi lần đầu, hồ sơ/chuyên môn/xác minh, eligibility gate, tạo review round và durable queue, assignment scoring, nhận/từ chối/hết hạn/thu hồi/tái phân công, draft/decision, thông báo và accountability. Kết quả tự động trên test DB đạt PASS. **Chưa có browser E2E chạy trọn quy trình qua UI**, nên nghiệm thu thao tác thực tế ADMIN/EXPERT vẫn PARTIAL.

### Security audit

| Kiểm soát | Kết quả từ source/test | Hạn chế nghiệm thu |
|---|---|---|
| SEC-01: chỉ EXPERT ACTIVE, không còn buộc đổi mật khẩu, hồ sơ VERIFIED mới được review | PASS trong guard trung tâm và test HTTP/service. | Không chạy thao tác qua trình duyệt. |
| SEC-02: open-pool bypass và assignment ownership | PASS trong test matrix legacy/new route; kiểm tra assignment theo chuyên gia hiện tại. | Chưa chạy browser role switching. |
| USER/PROVIDER/ADMIN/EXPERT boundaries, IDOR và mass assignment | Có test backend; không thấy bằng chứng thất bại ở lượt cuối. | Test không thay thế kiểm tra UI và cấu hình deployment. |
| ACC-09..12/15: token cũ sau unlock, chu kỳ lịch sử, policy snapshot, recovery và khóa đồng bộ | Nhóm test Phase 3.4–3.8 PASS; feature-flag run gồm 28 test. | Chưa diễn tập crash tiến trình production hoặc kiểm chứng telemetry/alerting. |
| File access sau revoke/lock | Chưa được xác minh bằng HTTP trực tiếp. `main.py` mount công khai `/media/courses`; source này là course media path. Tài liệu lưu `duongDanTep` dạng URL/string, không có protected file streaming endpoint/FileResponse trong Backend. | Nếu tài liệu trỏ URL công khai bên ngoài, backend không thể thu hồi URL sau revoke/lock. Cần xác định chính sách lưu trữ/ủy quyền file và kiểm thử URL thật trước rollout. Đây là security readiness blocker, không tự thay contract trong GĐ3.8. |

### Concurrency và recovery

- Test group chạy với `AUTO_ASSIGNMENT_WORKFLOW_ENABLED=True`, `AUTO_ASSIGNMENT_WORKER_ENABLED=True`, `ACCOUNTABILITY_ENABLED=True` đạt `28 passed`.
- Test coverage bao gồm SKIP LOCKED, worker claim token/lease generation, fencing, stale reclaim/crash recovery, assignment tranh chấp và accountability recovery.
- Một lượt đầu của test concurrency được sửa ở test harness trong phần chuẩn bị GĐ3.8: hai futures phải được submit đồng thời trước barrier; assertion/production behavior không bị nới. Full suite sau đó đạt 209/209.
- Chưa chạy worker tiến trình riêng liên tục. `AUTO_ASSIGNMENT_WORKER_ENABLED` hiện chỉ được khai báo trong Settings; `main.py` không khởi động worker và `assignment_worker.py` nêu rõ không tự chạy trong lifespan. Trước deployment cần có launcher được giám sát và health/heartbeat rõ ràng.

## 4. Production legacy review (READ ONLY)

Truy vấn ngày 2026-11-26 xác nhận `current_database() = EduSuggest` và revision `c3d4e5f6a7b8`:

| Đối tượng | Giá trị chỉ đọc hiện tại | Hành động |
|---|---|---|
| `KhoaHoc #28` | `PENDING`, `HIDDEN`, review round `0` | Giữ nguyên. Nếu đưa vào workflow mới, cần kế hoạch tạo round/job idempotent trên test rehearsal trước. |
| `TaiLieu #132` | danh mục `NULL`, `PENDING`, `HIDDEN`, review round `0` | Không gán danh mục giả; nghiệp vụ cần bổ sung danh mục hợp lệ trước khi submit. |
| `ChuyenGia #4` | liên kết tài khoản role `USER`, hồ sơ `DRAFT` | Không đổi role/hồ sơ; yêu cầu xử lý nghiệp vụ và xác minh thủ công. |
| Nội dung PENDING với round 0 | 1 khóa học | Chỉ lập kế hoạch backfill/review round trên test DB. |
| Hồ sơ chuyên gia khác VERIFIED | 7 hồ sơ | Đây là số hồ sơ chưa VERIFIED, không đồng nghĩa 7 tài khoản đủ/không đủ điều kiện; cần đánh giá onboarding thực tế. |
| `DanhGiaChuyenGia` | 20 dòng | Không sửa; cần đối chiếu ngữ nghĩa/lịch sử qua báo cáo migration riêng trước rollout. |

Không có thao tác UPDATE/INSERT/DELETE trên production trong lượt này.

## 5. Lỗi và thay đổi trong lượt nghiệm thu

1. Frontend `Recommendations.vue` hiển thị bộ lọc danh mục trên danh sách tài liệu, trong khi recommendation response không có thuộc tính danh mục. Đã giới hạn bộ lọc đó cho màn gợi ý khóa học để tránh lọc rỗng sai.
2. Test concurrency chờ future đầu tiên trước khi submit future thứ hai, khiến barrier test harness không đồng thời. Đã sửa thứ tự submit; test xác nhận PASS.
3. Fixture SEC-04 thiếu trường `soVongKiemDuyetHienTai`; bổ sung trường còn thiếu trong test fixture, không đổi nghiệp vụ/API.
4. Cleanup fixture durable queue/accountability trước đây bỏ sót violation/audit history, gây sót fixture test. Cleanup kiểm thử đã được bổ sung để dọn phụ thuộc và kiểm tra marker.
5. Không sửa backend runtime, schema, migration, API contract hoặc `.env` trong GĐ3.8.

### UI review – Before / After / Why

| Before | After | Why |
|---|---|---|
| Bộ lọc danh mục xuất hiện cả trong màn tài liệu đề xuất. | Bộ lọc chỉ hiện cho recommendations khóa học. | Schema tài liệu đề xuất không cung cấp category; filter đó không thể lọc dữ liệu thực đúng cách. |
| Responsive Admin/Expert và Recommendation UI chưa được render kiểm tra trong browser. | Không chỉnh bố cục; ghi `NOT TESTED`, không tạo screenshot giả. | Chrome automation fatal trước khi tạo tab/DOM. Cần chạy lại trên máy/runner có browser hoạt động. |

## 6. Rollout và rollback (kế hoạch, chưa thực hiện)

### Điều kiện trước rollout

- Có browser E2E thực tế cho ADMIN/EXPERT, regression USER/PROVIDER và bốn viewport; lưu screenshot có URL/viewport/timestamp.
- Có worker runner độc lập có supervisor, readiness/heartbeat, graceful shutdown, retry/backoff, alert khi lease backlog tăng; xác minh flag worker thực sự điều khiển runner.
- Bảo vệ private file bằng storage/authorization flow có thể revoke; chứng minh direct URL không truy cập được sau assignment revoke/account lock. Không coi obscurity của URL là authorization.
- Xác nhận production runtime flags trực tiếp; rà soát đủ chuyên gia đã VERIFIED/ACTIVE, đổi mật khẩu xong, chuyên môn active và không tạm ngưng.
- Rehearsal legacy `#28`, `#132`, `#4` trên test clone; kiểm tra counts/history/constraints trước và sau, đảm bảo idempotency.
- Backup PostgreSQL custom format bằng `pg_dump`, xác minh SHA-256, restore rehearsal trên PostgreSQL cô lập; xác nhận revision `c3d4e5f6a7b8`, row counts và FK.
- Phê duyệt maintenance window, người chịu trách nhiệm, ngưỡng dừng khẩn cấp, metrics/alerts và support path.

### Trình tự đề xuất

1. Triển khai release code đã được phê duyệt, giữ cả ba flags tắt.
2. Chạy smoke checks, DB read-only revision/count checks, auth/RBAC và worker connectivity; xác nhận không có queue backlog bất thường.
3. Onboard/xác minh chuyên gia thật trước khi bật workflow; chạy rehearsal dữ liệu legacy riêng.
4. Bật `AUTO_ASSIGNMENT_WORKFLOW_ENABLED` trước để các lần submit tạo round/job mới; xác nhận queue được tạo idempotent.
5. Bật `ACCOUNTABILITY_ENABLED` sau khi xác nhận policy/configuration và lịch sử legacy; giám sát token revocation, audit/recovery.
6. Bật runner `AUTO_ASSIGNMENT_WORKER_ENABLED` sau khi ownership guards, worker health và retry alert đã được chứng minh. Chỉ thực hiện từng bước theo change approval.
7. Theo dõi assignment/queue state, duplicate keys, stuck leases, expert load/fairness, notification delivery, 401/403/5xx và audit events.

### Rollback an toàn

- Dừng nhận workflow mới bằng cờ workflow; không xóa queue hoặc assignment đã phát sinh.
- Dừng worker có kiểm soát; để lease hết hạn/reclaim theo thiết kế, xác nhận không còn worker cũ ghi kết quả và không xóa job PROCESSING thủ công.
- Giữ accountability evidence/audit; không rollback bằng cách xóa vi phạm hoặc assignment.
- Rollback application version chỉ sau khi xác nhận tương thích schema (không có migration trong GĐ3.8); giữ nguyên dữ liệu đã sinh và dùng forward-fix nếu cần.
- Không mở lại open-pool API cho nội dung đã có assignment. Mọi khôi phục dữ liệu cần restore rehearsal, approval riêng, backup hiện hành và đối chiếu row-level trước/sau.

## 7. Checklist readiness và quyết định

| Điều kiện | Trạng thái |
|---|---|
| Backend regression tests | PASS: 209/209, flags off |
| Workflow/accountability concurrency tests | PASS: 28/28, flags on |
| Frontend production build | PASS |
| Schema/revision unchanged | PASS: `c3d4e5f6a7b8` trên cả DB |
| Production DB read-only | PASS trong lượt audit |
| Browser E2E, responsive, screenshot | BLOCKED / NOT RUN – Chrome/Edge không tạo được browser session; hướng dẫn manual tại `docs/EDUSUGGEST_GD381_MANUAL_BROWSER_TEST_GUIDE.md` |
| Independent worker process | PASS trên `EduSuggest_phase3_test`: process integration, 2 workers, stop/restart; chưa phải runtime supervision/Production sign-off |
| Private direct-file authorization/revocation | BLOCKED – chưa có managed private file storage; URL ngoài không thể revoke; cần duyệt kiến trúc |
| Production eligible expert capacity and process flags | NOT VERIFIED |
| Legacy migration rehearsal | NOT TESTED in this acceptance run |

**Quyết định: NO-GO.** Không bật runtime flags và không triển khai Production dựa trên kết quả hiện tại. Cần xử lý các readiness blocker nêu trên và chạy lại nghiệm thu browser + worker + file authorization. GĐ3.8 dừng tại đây, chờ phê duyệt nhiệm vụ tiếp theo.


---

# GĐ3.8.1 – Final Blocker Resolution Addendum (2026-11-26)

Tài liệu nghiệm thu chi tiết: `EDUSUGGEST_PHASE3_FINAL_BLOCKER_RESOLUTION_REPORT.md`.

| Điều kiện | Trạng thái mới |
|---|---|
| Independent Worker Launcher | PASS trong test/staging scope; real process, hai worker, graceful stop/restart và test DB guard đã kiểm tra. Chưa phải phê duyệt Production. |
| Private managed documents | BLOCKED; source hiện lưu URL ngoài/metadata, chưa có private binary proxy. Cần duyệt kiến trúc storage và per-request authorization; không thay schema/API trong lượt này. |
| Browser E2E / responsive screenshots | BLOCKED / NOT RUN; Chrome/Edge không tạo được browser session. Dùng hướng dẫn kiểm thử thủ công trong `docs/EDUSUGGEST_GD381_MANUAL_BROWSER_TEST_GUIDE.md`. |
| Backend full suite | PASS: 213 tests. |
| Workflow suite, three flags enabled | PASS: 32 tests. |
| Frontend production build | PASS: 1,896 modules. |
| Production DB writes / migrations | None; revision baseline `c3d4e5f6a7b8` retained. |

**Quyết định:** NO-GO. Không kích hoạt Production. GĐ3.8 vẫn chờ xử lý private-file architecture và Browser E2E; manual-vs-worker race test cũng cần bổ sung để đóng phần PARTIAL.

---

# GĐ3.8.2 – Private File Security & Final Acceptance Addendum (2026-11-26)

Tài liệu chi tiết: `EDUSUGGEST_PHASE3_PRIVATE_FILE_SECURITY_ACCEPTANCE_REPORT.md`.

| Điều kiện | Trạng thái mới |
|---|---|
| Private Local Storage | **PASS trong source/integration scope**; file nằm ngoài StaticFiles, namespace theo `current_database()`, server-generated reference, validation và transaction cleanup. |
| Protected file API | **PASS**; upload PROVIDER owner và read/preview per-request cho ADMIN/PROVIDER/EXPERT/USER với assignment/enrollment/current-state checks. External URL không được coi là private/revocable. |
| Frontend private file integration | **PASS build/source**; JWT blob flow, không token query string, transient object URL, loading/error/denied states. Chưa Browser E2E. |
| Manual assignment vs PROCESSING | **PASS** bằng PostgreSQL multi-connection race test; không duplicate assignment, lost queue job hoặc deadlock; fencing giữ nguyên. |
| ACC-15 | **PASS source/suite**; advisory transaction lock + current eligibility recheck trên các write path liên quan. |
| Worker entrypoint | **PASS staging**; một implementation chính và wrapper tương thích. Abrupt process kill vẫn NOT RUN. |
| Backend full suite | **PASS: 216 tests**, 1 deprecation warning. |
| Workflow + private security | **PASS: 34 tests**, 1 warning. |
| Recommendation regression | **PASS: 9 tests**; không đổi TF-IDF/Cosine Similarity. |
| Frontend production build | **PASS: 1,897 modules**. |
| Safe staging lifecycle | **PASS smoke**; API/docs/frontend 200, worker graceful stop, fixtures và listeners được cleanup. |
| Browser E2E/responsive/screenshots | **BLOCKED / NOT RUN**; không có browser condition mới. Manual guide: `docs/EDUSUGGEST_GD382_MANUAL_BROWSER_ACCEPTANCE.md`. |
| Regression cuối sau chỉnh sửa course-category | **PASS**; file-security `2 passed`, full Backend `216 passed`, workflow + file-security `34 passed`. |

Production và test DB cùng giữ revision `c3d4e5f6a7b8`; Production chỉ được query READ ONLY, không migration, không sửa `.env`, không thao tác Git. Ba runtime flags được xác minh `False` sau kiểm thử.

**Quyết định: NO-GO.** Private-file blocker đã được xử lý ở integration scope và race PROCESSING đã đóng, nhưng Browser Acceptance chưa có bằng chứng thật. Không kích hoạt Production; dừng chờ phê duyệt.

---

# GĐ3.8.3 – Final Browser Acceptance Preparation Addendum (2026-11-26)

Báo cáo đang cập nhật: `EDUSUGGEST_PHASE3_BROWSER_ACCEPTANCE_REPORT.md`.

| Điều kiện | Trạng thái |
|---|---|
| Staging isolated environment | **PASS** – Frontend 5174, Backend 8001, `EduSuggest_phase3_test`, independent worker; API base và DB target xác minh thực tế |
| Browser fixtures | **PASS** – 5 accounts, verified/unverified EXPERT, provider/user, category/specialty, courses/materials, 2 assignments, notifications và managed private files |
| Fixture account login | **PASS 5/5** sau khi sửa test-only email domain từ reserved `.local` sang `.example.com` |
| Abrupt worker kill + recovery | **PASS** – OS kill sau claim, stale lease reclaim, đúng 1 assignment/notification, stale claim fenced |
| Full Backend | **PASS: 217 tests** |
| Workflow + file security + crash recovery | **PASS: 35 tests** |
| Recommendation | **PASS: 9 tests** |
| Frontend build | **PASS: 1,897 modules** |
| Private file staging smoke | **PASS** – no token/role/enrollment/pre-accept cases đúng 401/403/200 |
| Browser automation | **BLOCKED** – không có runtime mới; không lặp Chrome/Edge cùng điều kiện đã thất bại |
| Manual Chrome acceptance | **IN PROGRESS / NOT RUN** – staging đang giữ hoạt động để người dùng kiểm thử từng batch |

**Quyết định hiện tại: NO-GO.** Không cleanup/dừng staging cho tới khi người dùng xác nhận xong. Không kích hoạt Production; chờ Browser Acceptance evidence tại 375/768/1024/1440 và Console/Network review.
