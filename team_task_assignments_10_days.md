# Phân công triển khai MVP staging — 10 ngày làm việc

**Quy ước thời gian:** Ngày 1 là ngày bắt đầu dự án. Mỗi việc phải được review/merge trước 17:00 ngày ghi trong cột “Hoàn thành”. `P0` là blocker; không bắt đầu việc phụ thuộc khi P0 chưa được nghiệm thu.

## Nguyên tắc tránh đụng độ

| Khu vực sở hữu | Chủ sở hữu duy nhất | Người chỉ được tích hợp qua API/PR |
|---|---|---|
| `backend/app/core`, `deps.py`, endpoint nghiệp vụ, Docker/CI | Thành viên 1 | 2, 3 cung cấp migration/contract; 4, 5 chỉ gọi API |
| `supabase/`, migration SQL, RLS, seed | Thành viên 2 | 1 chỉ chạy migration; không sửa SQL trực tiếp |
| `backend/app/services/student_routing/`, scheduler/job runner | Thành viên 3 | 1 chỉ đăng ký route/cron theo contract |
| `lib/main.dart`, auth/session, screens sinh viên, API client | Thành viên 4 | 5 không sửa các file này |
| `lib/features/driver/`, GPS/QR driver, test E2E | Thành viên 5 | 4 không sửa các file driver |

**Điểm bàn giao cố định:** 17:00 ngày 1 (OpenAPI + ERD), 17:00 ngày 3 (Auth/Profile), 17:00 ngày 5 (Booking → Route), 17:00 ngày 6 (GPS/QR), 17:00 ngày 8 (candidate staging). Mọi thay đổi contract sau ngày 3 phải được cả Thành viên 1, 3, 4 và 5 chấp thuận.

## Dependency tổng quát

```text
P0: ERD UUID + OpenAPI (Ngày 1)
 ├─> Migration/RLS/seed (TV2) ──> staging database
 ├─> JWT JWKS + profile/role API (TV1) ──> Flutter Auth (TV4, TV5)
 └─> Contract demand/job (TV3) ──> API booking/job (TV1)
                                      ├─> UI đặt vé/vé của tôi (TV4)
                                      └─> UI tuyến/start-end/QR (TV5)

Booking dữ liệu thật + seed ──> Job Sweep/Tabu (TV3) ──> route assignment
                                                        ├─> Student route/map (TV4)
                                                        └─> Driver route screen (TV5)

Driver start route ──> GPS foreground API (TV1) ──> GPS driver (TV5) ──> Map student (TV4)
```

## Thành viên 1 — Backend & Cloud lead

| ID | Công việc/đầu ra | File/khu vực sở hữu | Tiên quyết | Hoàn thành |
|---|---|---|---|---|
| B1-P0 | Viết OpenAPI v1, quy ước response/error, endpoint `/health` và `/ready`; tạo `.env.example`. | `backend/app/api`, `backend/app/core`, `backend/.env.example` | Không | Ngày 1 |
| B2-P0 | Docker deploy staging, cấu hình CORS allowlist, health check và log request an toàn. | `backend/Dockerfile`, cấu hình deploy | B1 | Ngày 2 |
| B3-P0 | Thay xác thực nội bộ bằng dependency xác minh Supabase JWT/JWKS; endpoint `/me` trả profile/role. | `backend/app/api/deps.py`, auth/profile endpoint | ERD TV2 ngày 1, B1 | Ngày 3 |
| B4-P0 | API mua/hủy vé và ví ledger trong transaction; deadline timezone-aware; idempotency key. | ticket/booking/wallet endpoints, tests | B3, migration TV2 ngày 3, contract TV3 ngày 2 | Ngày 4 |
| B5-P0 | Đăng ký endpoint tạo route-job bảo vệ `X-Cron-Secret`; gọi service TV3, trả trạng thái job. | route-job endpoint, cron config | B4, service interface TV3 ngày 4 | Ngày 5 |
| B6 | API start/end route, QR verify có ownership; API GPS POST + route position GET, rate limit cơ bản. | driver/ticket/GPS endpoints | B3, schema TV2 ngày 4 | Ngày 6 |
| B7 | Integration/regression tests, deploy candidate staging, fix P0/P1 backend. | `backend/tests`, deploy | B4–B6 | Ngày 8 |
| B8 | Runbook vận hành (env, migration, cron, rollback), release staging. | `backend/README.md` hoặc runbook | B7, QA pass | Ngày 10 |

## Thành viên 2 — Database & Supabase lead

| ID | Công việc/đầu ra | File/khu vực sở hữu | Tiên quyết | Hoàn thành |
|---|---|---|---|---|
| D1-P0 | Chốt ERD và data dictionary: `profiles.id UUID`, role, ticket/booking/route/wallet/job/GPS; quyết định enum & state machine. | ERD/document + `supabase/migrations` skeleton | Không | Ngày 1 |
| D2-P0 | Tạo Supabase staging, Supabase CLI, migration baseline và trigger `auth.users → profiles`. | `supabase/migrations/00001_*` | D1 | Ngày 2 |
| D3-P0 | Migration domain: wallet ledger, ticket/booking, route/job; FK/unique/index; UTC `timestamptz`. | `supabase/migrations/00002_*` | D1 | Ngày 3 |
| D4-P0 | RLS deny-by-default, policy role phù hợp, test A không thấy B. | `supabase/migrations/00003_*` | D2, D3 | Ngày 4 |
| D5 | Seed idempotent: 5 sinh viên, 2 tài xế, 2 xe, 5 trạm; tài liệu test credentials không commit secret. | `supabase/seed_staging.sql` | D3 | Ngày 5 |
| D6 | Bảng GPS/retention/index, reset staging từ đầu; hỗ trợ query plan/index. | migration bổ sung + test reset | D4 | Ngày 6 |
| D7 | Security review: RLS, service-role exposure, migration fresh-install; freeze schema. | checklist DB | D5, D6 | Ngày 8 |
| D8 | Xác minh migration/seed trên candidate staging và bàn giao database release. | pipeline/runbook | D7 | Ngày 10 |

## Thành viên 3 — Routing & Scheduler lead

| ID | Công việc/đầu ra | File/khu vực sở hữu | Tiên quyết | Hoàn thành |
|---|---|---|---|---|
| R1-P0 | Chốt contract `DemandInput`, `RouteOutput`, job status và các tham số thuật toán với TV1/TV2. | `backend/app/services/student_routing/schemas.py`, tài liệu contract | D1, B1 | Ngày 2 |
| R2 | Adapter đọc booking thật theo service date/session/trip; validation năng lực xe/trạm. | `backend/app/services/student_routing/` | R1, schema D3 | Ngày 3 |
| R3-P0 | Job runner idempotent: lock, `queued/running/succeeded/failed`, chạy Sweep → Tabu → persist route/stops/assignment. | routing service/job runner và unit tests | R2, B4, D3 | Ngày 5 |
| R4 | Timezone cutoff + retry/failure policy; không chạy lặp route đã thành công. | scheduler/job tests | R3 | Ngày 6 |
| R5 | Benchmark với seed, giới hạn dữ liệu MVP, log metric và hướng dẫn gọi cron. | benchmark/runbook | R3, D5 | Ngày 7 |
| R6 | Hỗ trợ E2E booking → route; sửa P0/P1 thuật toán, freeze interface. | service/tests | B5, R4 | Ngày 8 |
| R7 | Chạy job nghiệm thu và bàn giao kết quả/mức giới hạn đã đo. | evidence QA/runbook | R6 | Ngày 10 |

## Thành viên 4 — Flutter sinh viên & app shell lead

| ID | Công việc/đầu ra | File/khu vực sở hữu | Tiên quyết | Hoàn thành |
|---|---|---|---|---|
| F1-P0 | Tạo layer config từ `--dart-define`, repository/API client, auth/session state; xóa định tuyến URL localhost trên đường release. | `lib/config`, `lib/services`, `lib/main.dart` | B1 | Ngày 2 |
| F2-P0 | Supabase Auth UI: email/password, lỗi/loading, logout, restore session; lấy role qua `/me`. | auth/app shell/settings | B3, package/config F1 | Ngày 3 |
| F3-P0 | Đổi luồng đặt vé: ngày chạy, ca, chiều, trạm; deadline/error; không chọn route trước chốt sổ. | `lib/screens/ticket_screen.dart` | B4, contract B1 | Ngày 5 |
| F4 | Vé của tôi theo `reserved/assigned/checked_in/expired/cancelled`; QR chỉ với vé hợp lệ. | ticket UI | B4, B5 | Ngày 6 |
| F5 | Trang chủ dùng số dư/lịch sử API hoặc ẩn thao tác nạp demo; CTA đặt vé/trạng thái deadline. | `lib/screens/home_screen.dart` | B4 | Ngày 6 |
| F6 | Map sinh viên lấy route/vị trí thật, loading/empty/error, polling 15s; xóa xe/tuyến fallback giả. | `lib/screens/map_screen.dart` | B6, route assignment R3 | Ngày 7 |
| F7 | Android device test, UI polish/accessibility, xử lý offline/retry và P0/P1. | student feature tests | F3–F6 | Ngày 9 |
| F8 | Build APK staging, checklist UI sinh viên, hỗ trợ nghiệm thu. | build/release evidence | F7 | Ngày 10 |

## Thành viên 5 — Flutter tài xế & QA lead

| ID | Công việc/đầu ra | File/khu vực sở hữu | Tiên quyết | Hoàn thành |
|---|---|---|---|---|
| Q1-P0 | Viết test matrix E2E: role/RLS, deadline, booking, generate, assigned, start/end, QR, GPS. | `docs/qa` hoặc tài liệu QA | B1, D1 | Ngày 1 |
| Q2 | Refactor driver shell/menu/empty-loading-error; thống nhất nhãn tiếng Việt, chỉ route được gán. | `lib/features/driver`, `driver_shell.dart` | B3, contract B1 | Ngày 3 |
| Q3-P0 | UI danh sách/chi tiết tuyến; start/end route và phản hồi lỗi server. | `driver_home_tab.dart`, `driver_map_tab.dart` | B6 | Ngày 6 |
| Q4-P0 | Tích hợp camera QR, permissions, duplicate scan guard; input mã chỉ debug. | `driver_qr_tab.dart`, Android permissions | B6 | Ngày 6 |
| Q5 | GPS foreground: permission, start/stop theo trạng thái chuyến, gửi 15–20 giây/lần, lỗi mạng. | `driver_gps_service.dart`, driver map/home UI | B6 | Ngày 7 |
| Q6 | Test E2E vòng 1 bằng seed và thiết bị thật; tạo defect P0/P1/P2 có bước tái hiện. | test matrix/evidence | B5, R3, F3–F5, Q3–Q5 | Ngày 8 |
| Q7 | Retest candidate staging, test A/B RLS và deadline 21:59/22:01; sign-off QA. | QA report | B7, D7, F6 | Ngày 9 |
| Q8 | Smoke test APK cuối, lưu ảnh/video evidence và known limitations. | QA report | F8, B8 | Ngày 10 |

## Thứ tự thực hiện bắt buộc theo ngày

| Ngày | Việc phải hoàn thành trước 17:00 | Việc chỉ được bắt đầu sau khi mốc đạt |
|---|---|---|
| 1 | B1, D1, Q1; chốt OpenAPI/ERD | D2, R1, F1, Q2 |
| 2 | B2, D2, R1, F1 | B3, D3, R2, F2 |
| 3 | B3, D3, R2, F2, Q2 | D4, B4, F3 |
| 4 | D4, B4 | D5, R3, B5, F4/F5 |
| 5 | D5, R3, B5, F3 | B6, Q3/Q4, F4/F5 |
| 6 | B6, R4, F4/F5, Q3/Q4 | D6, F6, Q5 |
| 7 | D6, R5, F6, Q5 | B7, Q6 |
| 8 | B7, D7, R6, Q6 | F7, Q7, B8 |
| 9 | F7, Q7; mọi P0/P1 đóng | F8, Q8 |
| 10 | B8, D8, R7, F8, Q8 | Nghiệm thu staging |

## Quy tắc báo cáo và xử lý blocker

- Mỗi thành viên báo cáo trước 17:00: ID công việc, PR/commit, test đã chạy, blocker và dependency ngày sau.
- P0 được báo ngay trong ngày cho TV1 (API), TV2 (DB), TV3 (routing), TV4/TV5 (client) theo khu vực chủ sở hữu; không tự sửa file của người khác để “chữa cháy”.
- PR chạm OpenAPI, migration hoặc state của ticket phải có người chủ sở hữu và ít nhất một consumer review: TV4 hoặc TV5 cho API; TV1 cho migration; TV1 và TV3 cho route-job.
- Sau 17:00 ngày 8: đóng băng schema và API; chỉ nhận sửa lỗi P0/P1, không nhận thêm tính năng.
