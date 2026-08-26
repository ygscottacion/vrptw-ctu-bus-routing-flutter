# Kế hoạch MVP MyCTU BUS trong 10 ngày làm việc

## Kết luận rà soát

Hướng đi **Supabase Auth/PostgreSQL + FastAPI cho nghiệp vụ + Flutter** là phù hợp. Tuy nhiên bản kế hoạch 4 sprint không thể rút nguyên trạng xuống 1–2 tuần: ứng dụng hiện vẫn dùng tài khoản/JWT nội bộ, bảng `users` dùng số nguyên, API và UI còn có dữ liệu mô phỏng, trong khi Supabase Auth dùng `auth.users.id` dạng UUID. Cần làm một MVP tích hợp hoàn chỉnh, thay vì cố hoàn thiện tất cả các tính năng production.

Mục tiêu bàn giao sau 10 ngày là môi trường **staging** chạy end-to-end: sinh viên đăng nhập, đặt một lượt xe trước hạn, hệ thống sinh tuyến an toàn khi chạy tác vụ, tài xế xem tuyến được giao, bắt đầu/kết thúc chuyến và check-in QR. Production, thanh toán thật, background GPS và bản đồ realtime đầy đủ là giai đoạn sau.

## Các điều chỉnh kiến trúc bắt buộc

1. **Một định danh người dùng duy nhất:** thêm `profiles.id uuid primary key references auth.users(id)`. Không ánh xạ một cách chắp vá giữa `users.id integer` hiện tại và `auth.uid()`. Các bảng nghiệp vụ MVP (`tickets`, `bookings`, `routes`...) phải dùng `uuid` cho `user_id`/`driver_id`, hoặc có migration chuyển đổi được kiểm thử.
2. **Flutter chỉ dùng Supabase cho Auth:** access token hiện hành lấy từ `Supabase.instance.client.auth.currentSession`; không còn endpoint `/auth/login`, form username/password thử nghiệm, hay JWT ký bằng `SECRET_KEY` nội bộ. FastAPI xác minh Supabase JWT qua JWKS, kiểm tra `iss`, `aud`, `exp`, rồi tra `profiles` để nhận role.
3. **FastAPI là API nghiệp vụ duy nhất của Flutter trong MVP:** mọi read/write vé, ví, tuyến, GPS, QR đi qua FastAPI. Đây là cách ngắn nhất để không phải duy trì hai contract (Supabase SDK/RLS và REST) trong 10 ngày. RLS vẫn bật để khóa truy cập trực tiếp; chỉ mở direct read/Broadcast sau khi API contract ổn định.
4. **Tất cả write là transaction và idempotent:** mua/hủy vé, trừ/hoàn ví, check-in QR và tạo tuyến phải có khóa/unique key phù hợp. Job sinh tuyến có `service_date + session_id + trip_type` unique và trạng thái `queued/running/succeeded/failed`; chạy lại không sinh dữ liệu trùng.
5. **Mốc 22:00 phải theo `Asia/Ho_Chi_Minh`:** dùng timezone-aware datetime và `timestamptz`. Chỉ nhận booking trước 22:00 ngày liền trước service date. Không dùng `datetime.now()` naive như endpoint hiện tại.
6. **Bỏ `Base.metadata.create_all()` khi deploy:** schema chỉ được tạo bằng migration trong git. Supabase service role chỉ ở FastAPI/CI, không ở Flutter.
7. **Cron gọi API có chữ ký:** endpoint nội bộ yêu cầu `X-Cron-Secret`, giới hạn ngày/ca hợp lệ và log job. Trước khi có Supabase Cron/Edge Function ổn định, có thể test bằng scheduled job của Render/Railway nhưng chỉ một scheduler được phép chạy.

## Rà soát UI hiện tại và thay đổi cần làm

| Khu vực | Hiện trạng | Sửa trong MVP |
|---|---|---|
| Đăng nhập/cài đặt | Dialog dùng username/password mẫu và backend JWT nội bộ. | Đổi thành màn hình Supabase email/password; có loading, lỗi xác thực, logout và restore session. Role lấy từ `/me` FastAPI. |
| Trang chủ sinh viên | Số dư CTUPay là biến `_balance`, cho nạp/trừ mô phỏng. | Hiển thị số dư/lịch sử thật từ API hoặc ẩn thao tác nạp tiền. Thêm CTA “Đặt lượt xe” và trạng thái deadline. |
| Đặt vé | UI chọn `route` trước, trong khi tuyến phải được sinh sau hạn 22:00; có fallback/mô phỏng. | Chọn **ngày chạy, ca, chiều, trạm đón**. Trước chốt sổ hiển thị “đang chờ phân tuyến”; sau khi job xong hiển thị tuyến/trạm/giờ. |
| Vé của tôi | Có thể hiển thị QR nhưng trạng thái và route chưa phản ánh vòng đời phân tuyến. | Một state rõ ràng: `reserved → assigned → checked_in/expired/cancelled`; QR chỉ bật với vé hợp lệ. |
| Bản đồ sinh viên | Trạm fallback cứng và xe chạy bằng `Timer.periodic`. | Không được hiển thị xe giả. Hiển thị empty/loading state; ở MVP dùng vị trí API polling 15 giây khi có chuyến đang chạy. |
| App tài xế | Có UI tuyến khá tốt nhưng dựa nhiều dữ liệu placeholder, nhãn Anh/Việt lẫn lộn. | Chỉ cho xem tuyến của tài xế đăng nhập, thống nhất tiếng Việt, có trạng thái “chưa có tuyến / sắp chạy / đang chạy / hoàn tất”. |
| Quét QR | Có ô nhập giả lập; chưa thấy camera/permission thực. | Tích hợp camera scanner, đồng thời giữ nhập mã chỉ trong debug. Sau quét phải hiện kết quả API rõ ràng và chống quét lặp. |
| GPS | Mới là trạng thái/hiển thị UI, chưa có service và quyền vị trí. | Xin quyền, start/stop GPS khi bắt đầu/kết thúc chuyến; gửi API mỗi 15–20 giây khi app foreground. Background tracking để sprint sau. |

## Phạm vi khóa lại để kịp 2 tuần

**Có trong MVP:** Supabase Auth; profile/role; ví điểm nội bộ với ledger; đặt/hủy một vé lượt; deadline; sinh tuyến Sweep/Tabu theo một ca; gán xe/tài xế; QR check-in; GPS foreground; staging deploy; kiểm thử E2E.

**Không nhận trong 10 ngày:** MoMo/VNPay, nạp tiền thật, background GPS, push notification, Broadcast/Realtime trực tiếp từ Flutter, map xe chạy mượt mọi trường hợp, admin web hoàn chỉnh, production release/backup/branching. Các mục này chỉ được đưa vào sau khi MVP staging đạt tiêu chí nghiệm thu bên dưới.

## Phân công 5 thành viên và lộ trình 10 ngày

| Ngày | Thành viên 1 – Backend/Cloud | Thành viên 2 – DB/Supabase | Thành viên 3 – Routing/Scheduler | Thành viên 4 – Flutter sinh viên | Thành viên 5 – Flutter tài xế/QA | Mốc tích hợp |
|---|---|---|---|---|---|---|
| 1 | Chốt OpenAPI/error format, `.env.example`, health/readiness. | Chốt ERD UUID và migration baseline. | Chốt input/output route-job với backend. | Audit màn hình, tạo auth/app-state/data repository. | Audit driver flows, lập test matrix E2E. | Contract API v1 được tất cả xác nhận. |
| 2 | Docker + deploy staging + CORS allowlist. | Auth trigger `profiles`, enum/constraint/index; seed test. | Map booking → demand, test dữ liệu nhỏ. | Khởi tạo Supabase qua `--dart-define`; login/logout/restore session. | Chỉnh navigation/trạng thái empty/loading, chuẩn bị quyền camera/location. | Flutter đăng nhập Supabase, gọi `/me` staging. |
| 3 | JWKS dependency, role guard, `/me`; bỏ auth nội bộ trên client path. | RLS deny-by-default, kiểm thử user A/B; migrations reset được. | Thiết kế job idempotent và timezone 22:00. | Đổi UI đặt vé: ngày/ca/chiều/trạm, deadline và lỗi server. | API “tuyến của tôi”, UI danh sách tuyến được giao. | Auth + profile role hoạt động E2E. |
| 4 | API purchase/cancel + ví/ledger transaction. | Migration tickets/bookings/wallet/jobs, unique keys. | Tích hợp đọc demand DB, persist job skeleton. | Vé của tôi theo trạng thái reserved/assigned; bỏ route giả. | Start/end route API, trạng thái chuyến thực. | Một vé được ghi và ledger đúng một lần. |
| 5 | Route/job endpoint bảo vệ cron secret; integration tests. | Seed 5 SV, 2 tài xế, 2 xe, 5 trạm. | Sweep/Tabu chạy từ booking và lưu routes/stops/gán tài xế. | Hiện thông tin tuyến sau assigned, empty/error states. | QR scanner thật + gọi verify API; debug input chỉ debug. | Demo: booking → generate → assigned. |
| 6 | API GPS POST và route position GET, rate limit/ownership. | Bảng/index GPS retention đơn giản; policy/service access. | Test chạy lại job không trùng; đo thời gian mẫu. | Bản đồ lấy tuyến/vị trí thật; polling 15 giây; xóa timer giả. | GPS foreground start/stop, permission/error UX. | Một tài xế phát vị trí, sinh viên xem được. |
| 7 | Fix integration, logs, health/readiness monitoring. | RLS/security review, migration fresh install. | Xử lý failure/retry job; test deadline 21:59/22:01. | Polish auth/booking/ticket UI và accessibility cơ bản. | Polish driver/QR/GPS UI, tiếng Việt nhất quán. | Test E2E vòng 1. |
| 8 | Backend test/regression, deploy candidate. | Reset staging + seed repeatable. | Benchmark, giới hạn dữ liệu MVP và fallback lỗi. | Test thiết bị Android thật, xử lý network/retry. | Test 2 thiết bị tài xế + 5 sinh viên, ghi defect. | Candidate staging. |
| 9 | Sửa blocker P0/P1, freeze API. | Kiểm tra không secret trong repo/app. | Chạy job thực nghiệm, xác nhận dữ liệu gán tuyến. | UAT sinh viên, sửa lỗi blocker. | UAT tài xế, QR/GPS test thực địa ngắn. | E2E vòng 2 đạt. |
| 10 | Tag/release staging, tài liệu vận hành ngắn. | Xuất migration/seed đã xác minh. | Hướng dẫn cron/runbook và known limits. | Build APK staging, checklist UI. | Tổng hợp evidence QA, smoke test cuối. | Nghiệm thu MVP staging. |

## Definition of Done ngày 10

- `supabase db reset` (hoặc pipeline migration staging tương đương) chạy thành công từ repository; không có schema tạo tự động khi FastAPI khởi động.
- Sinh viên và tài xế đăng nhập Supabase trên Android thật; token được FastAPI JWKS xác minh và role đúng.
- Sinh viên A không thể đọc/ghi dữ liệu của sinh viên B trực tiếp hay qua API.
- Vé mua lúc 21:59 thành công và lúc 22:01 bị chặn theo giờ Việt Nam; ledger và vé chỉ được tạo một lần dù retry request.
- Job của một ca chạy hai lần không tạo route/booking trùng; vé chuyển sang `assigned` khi thành công.
- Tài xế chỉ thấy tuyến được gán, check-in QR hợp lệ đúng một lần, và GPS foreground cập nhật vị trí trên app sinh viên.
- APK staging không chứa `localhost`, `10.0.2.2`, service-role key, tài khoản demo hoặc vị trí/xe giả.

## Điều kiện quyết định trước ngày 1

1. Chỉ chọn **một** nhà cung cấp staging (Render *hoặc* Railway) và một project Supabase staging; production chưa là mốc bàn giao 10 ngày.
2. Chủ sản phẩm xác nhận luồng ví điểm là dữ liệu test/seed trong MVP, không có nạp tiền thật.
3. Chốt ca chạy, năng lực xe, danh sách trạm và tài khoản test trong ngày 1; thay đổi các quy tắc này sau ngày 3 sẽ ảnh hưởng trực tiếp thuật toán và UI đặt vé.
