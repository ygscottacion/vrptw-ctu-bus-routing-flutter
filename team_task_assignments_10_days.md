# Kế hoạch MVP staging sau khi đã tạo Supabase và deploy Render

**Cập nhật:** 27/08/2026 (GMT+7)  
**Thời lượng còn lại:** 8 ngày làm việc, tính từ ngày nhóm bắt đầu mốc T1.  
**Mục tiêu:** một bản staging chạy end-to-end: đăng nhập Supabase, đặt vé đúng hạn, sinh/gán tuyến, tài xế quét QR và gửi GPS foreground.

## Mốc đã hoàn thành (T0)

| Hạng mục | Trạng thái | Bằng chứng/việc còn phải nghiệm thu |
|---|---|---|
| Khởi tạo project Supabase | Hoàn thành | Minh kiểm tra URL, database connection và quyền của các key; **không** đưa service-role key vào Flutter hoặc Git. Schema, RLS và seed chưa được coi là hoàn thành chỉ vì project đã được tạo. |
| Deploy Web API FastAPI lên Render | Hoàn thành | Service Render đang Live, endpoint `/` trả `200`. Nhã cần xác minh `/health` trả database `connected`, `/ready` trả `200`, và lưu URL staging trong cấu hình dự án. |

> Log `HEAD / 405` trên Render không phải lỗi deploy: FastAPI chỉ khai báo `GET /`. Health check của Render nên gọi `GET /health` hoặc cấu hình endpoint health phù hợp.

## Phân công cố định và ranh giới sở hữu

| Thành viên | Vai trò | Chịu trách nhiệm chính | Không tự sửa |
|---|---|---|---|
| **Nhã (leader)** | Tích hợp Backend/Cloud | API FastAPI, Render, OpenAPI, auth JWT, biến môi trường, merge/release và xử lý blocker liên nhóm | migration/RLS của Minh; UI Flutter của Khánh/Lợi; thuật toán của Duy |
| **Minh** | Database/Supabase | ERD UUID, SQL migration, RLS, seed, indexes, kiểm thử quyền A/B | endpoint/backend Python của Nhã |
| **Duy** | Routing/Scheduler | contract demand/route/job, Sweep/Tabu, job idempotent, scheduler/cron và benchmark | schema migration và Flutter UI |
| **Khánh** | Flutter sinh viên | cấu hình API/Auth, phiên đăng nhập, booking/ticket, map sinh viên và APK sinh viên | các file `lib/features/driver/` |
| **Lợi** | Flutter tài xế & QA | UI tài xế, QR camera, GPS foreground, test matrix, E2E và evidence QA | `lib/main.dart`, auth/app shell và màn hình sinh viên của Khánh |

## Các việc ưu tiên ngay tại T1

| Người | Việc phải làm trước khi nhận tính năng mới | Đầu ra nghiệm thu |
|---|---|---|
| Nhã | Kiểm tra Render ↔ Supabase bằng `GET /health`; chuyển toàn bộ secret sang Render Environment; bỏ secret mặc định khỏi mã; giới hạn CORS theo URL web staging. Dừng dùng `Base.metadata.create_all()` khi deploy và thống nhất migration là nguồn schema. | `/health` báo `connected`; không có service-role/DB password/cron secret trong Git hoặc APK; pull request cấu hình được Minh review. |
| Minh | Chốt ERD Supabase dùng `profiles.id uuid → auth.users.id`; tạo baseline migration và trigger tạo profile. | Migration chạy được trên database trống; tài khoản tạo trong Supabase Auth có profile đúng role. |
| Duy | Chốt với Nhã/Minh hợp đồng `DemandInput`, `RouteOutput`, `job status` và khóa duy nhất theo ngày/ca/chiều. | Tài liệu contract được cả ba xác nhận; test dữ liệu nhỏ chạy được độc lập. |
| Khánh | Tạo `--dart-define` cho base API/Supabase URL/anon key, thay localhost; chuẩn bị Auth/session repository. | Web/APK staging không chứa `localhost`, `10.0.2.2` hay key nhạy cảm. |
| Lợi | Lập test matrix E2E và rà soát quyền camera/location Android; dọn UI driver placeholder theo trạng thái. | Checklist có bước, dữ liệu test, expected result và nơi lưu ảnh/video evidence. |

## Lộ trình 8 ngày còn lại

| Ngày | Nhã — leader/Backend/Cloud | Minh — DB/Supabase | Duy — Routing/Scheduler | Khánh — Flutter sinh viên | Lợi — Flutter tài xế/QA | Mốc tích hợp |
|---|---|---|---|---|---|---|
| **T1** | Nghiệm thu health, Render env, CORS/secret/migration policy; công bố OpenAPI v1. | ERD UUID, migration baseline + `auth.users → profiles`. | Chốt contract demand/route/job. | App config + Supabase client/session state. | Test matrix, quyền QR/GPS, trạng thái driver. | URL API, OpenAPI và ERD được chốt. |
| **T2** | JWT/JWKS dependency, `/me`, role guard; bỏ luồng JWT nội bộ trên đường release. | Migration ticket/booking/wallet/job; ràng buộc/index UTC. | Adapter booking → demand; validation xe/trạm. | Login/logout/restore session, gọi `/me`. | Driver chỉ xem route được gán; empty/loading/error. | Sinh viên/tài xế login Supabase và nhận đúng role. |
| **T3** | API đặt/hủy vé + wallet ledger trong transaction, idempotency key, deadline `Asia/Ho_Chi_Minh`. | RLS deny-by-default, policy và test user A/B. | Job skeleton có lock và trạng thái `queued/running/succeeded/failed`. | Màn đặt vé: ngày, ca, chiều, trạm; xử lý deadline/lỗi. | Chuẩn bị API start/end route và UX trạng thái chuyến. | Một booking và ledger được tạo đúng một lần. |
| **T4** | Endpoint route-job bảo vệ `X-Cron-Secret`; endpoint danh sách/chi tiết route. | Seed idempotent: 5 SV, 2 tài xế, 2 xe, 5 trạm. | Chạy Sweep → Tabu, persist route/stops/assignment; chống chạy trùng. | Vé của tôi: `reserved/assigned/checked_in/cancelled`; bỏ route giả. | UI start/end route; QR camera scanner + duplicate-scan guard. | Demo booking → generate → assigned. |
| **T5** | API QR verify ownership/idempotency; API GPS POST + route-position GET, rate limit cơ bản. | GPS table/index/retention, kiểm tra query plan. | Cutoff timezone, retry/failure policy, benchmark seed. | Hiển thị route/vị trí thật, polling 15 giây, không timer xe giả. | GPS foreground: permission, start/stop, gửi 15–20 giây/lần. | Tài xế gửi vị trí; sinh viên thấy vị trí thật. |
| **T6** | Integration/regression tests; fix P0/P1; deploy candidate Render. | Fresh-install/reset + seed repeatable; security review. | E2E booking → route; freeze service interface. | Test Android, offline/retry/accessibility. | E2E vòng 1 trên thiết bị thật, ghi defect tái hiện được. | Candidate staging. |
| **T7** | Freeze API/schema, chỉ sửa P0/P1; runbook Render/rollback/cron. | Xác minh RLS và không secret trong repo; freeze migration. | Chạy job nghiệm thu, ghi giới hạn dữ liệu/hiệu năng. | UAT sinh viên, sửa blocker. | UAT tài xế QR/GPS, retest A/B RLS và deadline 21:59/22:01. | E2E vòng 2 đạt. |
| **T8** | Release/tag staging, công bố known limitations. | Bàn giao migration/seed phiên bản cuối. | Bàn giao scheduler/runbook. | Build APK staging + checklist sinh viên. | Smoke test cuối, evidence QA và sign-off. | Nghiệm thu MVP staging. |

## Quy tắc phối hợp

- Nhã là người quyết định ưu tiên, chủ trì stand-up 15 phút mỗi ngày và chỉ merge khi có owner review. Mỗi người báo trước 17:00: mã việc, PR/commit, test đã chạy, blocker và dependency ngày kế tiếp.
- Minh gửi cho Nhã **tên biến môi trường và cách đặt giá trị**, không gửi secret vào chat/commit. Nhã đặt giá trị thật trên Render; Khánh chỉ dùng URL + anon key qua `--dart-define`.
- Thay đổi OpenAPI, migration hoặc ticket state phải có review của owner và ít nhất một consumer: Khánh hoặc Lợi review API; Nhã review migration; Nhã và Duy review route-job.
- Sau T7, API/schema đóng băng; chỉ nhận sửa P0/P1. Không thêm thanh toán thật, background GPS, push notification hoặc admin web vào đợt này.

## Tiêu chí nghiệm thu T8

- `/health` trên Render kết nối Supabase thành công và `/ready` trả `200`; secrets không xuất hiện trong repository, log hay Flutter build.
- Sinh viên và tài xế đăng nhập Supabase trên thiết bị thật; FastAPI xác minh JWT và trả role đúng.
- Sinh viên A không đọc/ghi dữ liệu B; booking trước 22:00 thành công và sau 22:00 bị chặn theo giờ Việt Nam.
- Chạy job cùng ngày/ca/chiều hai lần không tạo dữ liệu trùng; vé được gán tuyến khi job thành công.
- QR hợp lệ chỉ check-in một lần; GPS foreground của tài xế hiển thị trên app sinh viên.
- APK staging không chứa endpoint localhost, thông tin demo nhạy cảm, service-role key hoặc dữ liệu xe/vị trí giả.
