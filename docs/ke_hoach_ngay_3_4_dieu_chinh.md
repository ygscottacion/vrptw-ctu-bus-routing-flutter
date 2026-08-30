# Kế hoạch cuối Ngày 3–4 — Leader / Backend (Nhã)

## Quyết định kiến trúc đã chốt

- **Identity duy nhất:** `profiles.id UUID`, khóa ngoại tới `auth.users.id`, là ID người dùng duy nhất trong toàn bộ nghiệp vụ. Không tạo mới hoặc tiếp tục dùng `users.id INTEGER`.
- **ID nghiệp vụ:** `tickets.id`, `routes.id`, `route_stops.id`, `locations.id`, `vehicles.id`, `route_jobs.id` và `idempotency_keys.id` đều là UUID. API, Pydantic schema, query parameter, foreign key, seed và Flutter đều truyền UUID; không có kiểu `Int`/`Integer` trong contract mới.
- **Nguồn sự thật lượt xe:** `tickets`, không dùng `bookings` trong MVP. Một ticket là một lượt đăng ký theo ngày, ca, chiều và trạm; `route_id` chỉ được gán khi routing thành công.
- **Luồng MVP:** `reserve ticket` → cutoff 22:00 (`Asia/Ho_Chi_Minh`) → tạo/chạy route job → gán `ticket.route_id` và `assigned` → xem tuyến.
- **Vòng đời ticket:** `reserved → assigned → used | cancelled | expired`. Chỉ `reserved` được hủy. Không dùng `active` làm trạng thái mơ hồ.
- **Run chuẩn:** `(service_date, session_id, trip_type)`, trong đó `session_id` là `MORNING_1|MORNING_2|NOON_1|NOON_2`, `trip_type` là `pickup|dropoff`. Không dùng `shift/direction`.
- Mọi timestamp là `timestamptz`/UTC; chỉ dùng `ZoneInfo("Asia/Ho_Chi_Minh")` để áp deadline và hiển thị.
- PostgreSQL là nguồn trạng thái bền vững cho idempotency và job. Không dùng Redis, `job_store` in-memory hoặc `FastAPI BackgroundTasks` làm queue production.

## Ngày 3 (T3) — Cutover UUID, schema và API giữ chỗ

### T3.1 — Migration UUID và cutover identity

Nhã viết migration Alembic, Minh review và chạy thử trên database staging rỗng trước.

1. Chuyển mọi FK người dùng sang UUID: `tickets.user_id`, `bookings.user_id` (nếu còn để lưu lịch sử), `vehicles.driver_id`, các bảng ledger/job/audit và bảng mới đều tham chiếu `profiles.id`.
2. Chuyển mọi ID và FK nghiệp vụ sang UUID, gồm ticket, route, route stop, location, vehicle và các foreign key liên quan. Không để endpoint nào nhận ID integer.
3. Loại `app.models.user.User` và auth nội bộ khỏi đường chạy mới; dependencies JWT đọc `sub` UUID từ Supabase, tải `Profile`, rồi áp role `admin|driver|passenger` từ `profiles.role`.
4. Đánh dấu endpoint/model `bookings` cũ là deprecated và gỡ chúng khỏi router MVP sau khi consumer đã chuyển. Không tiếp tục viết vào bảng này.
5. Nếu staging có dữ liệu cần giữ, viết migration mapping rõ `legacy users.id → auth.users/profiles.id`, kiểm đếm trước/sau và chỉ cutover khi mapping đầy đủ. Nếu không có mapping, dùng staging sạch + seed UUID; không ép cast integer thành UUID.

**Tiêu chí xong:** database sạch chạy `alembic upgrade head`; mọi FK kiểm tra được tới UUID; JWT `sub` khớp `profiles.id`; không còn `int` trong request/response identity hay khóa nghiệp vụ mới.

### T3.2 — Schema reservation, route và tính toàn vẹn

Migration tạo/chỉnh các cấu trúc sau:

- `tickets`: `id UUID PK`, `user_id UUID FK profiles.id`, `route_id UUID FK routes.id NULL`, `service_date`, `session_id`, `trip_type`, `pickup_location_id UUID`, `status ticket_status`; các trường run/trạm bắt buộc với ticket mới.
  - Unique: `(user_id, service_date, session_id, trip_type)` để một sinh viên chỉ có một lượt trong mỗi ca/chiều.
  - Index phục vụ routing: `(service_date, session_id, trip_type, status)`.
- `routes`: `id UUID PK`, `route_job_id UUID FK route_jobs.id`, `service_date`, `session_id`, `trip_type`, `vehicle_id UUID`, `status`, `total_distance`; index theo run và vehicle. Đây là điều kiện để filter API theo ca/chiều không mơ hồ.
- `route_stops`: `id UUID PK`, `route_id UUID`, `location_id UUID`, `stop_order`, `arrival_time timestamptz`; unique `(route_id, stop_order)`.
- `route_jobs`: `id UUID PK`, run key, `depot_location_id UUID`, trạng thái `queued|running|succeeded|failed`, `error_message`, timestamps. Partial unique index chỉ cho một job `queued/running` trên mỗi run; job `succeeded` không được tạo route trùng.
- `idempotency_keys`: `id UUID PK`, `user_id UUID FK profiles.id`, `endpoint`, `key`, `request_hash`, `response_code`, `response_body JSONB`, `expires_at timestamptz`; unique `(user_id, endpoint, key)`.

Không tạo `wallet_ledger` trong phạm vi này vì MVP đã chốt “một reserve = một ticket”, không có số dư lượt/CTUPay thật.

### T3.3 — API reserve và cancel

**`POST /api/v1/tickets/reserve`**

- Header bắt buộc `X-Idempotency-Key`; body gồm `service_date`, `session_id`, `trip_type`, `pickup_location_id` — tất cả ID là UUID.
- Xác thực JWT Supabase, nhận `current_profile.id UUID`; validate enum, ngày tương lai và trạm hợp lệ.
- Áp deadline tại 22:00 của `service_date - 1` bằng timezone-aware clock. Quá hạn hoặc service date hôm nay/quá khứ trả 400.
- Một transaction kiểm tra/lưu idempotency, enforce unique run của user, tạo ticket `reserved` với `route_id = NULL`, lưu response rồi commit.
- Cùng key và cùng payload trả lại response đã lưu; cùng key nhưng payload khác trả 409. Unique violation được map thành lỗi nghiệp vụ, không trả 500.

**`POST /api/v1/tickets/{ticket_id}/cancel`**

- `ticket_id` là UUID; hỗ trợ `X-Idempotency-Key`.
- Một transaction kiểm tra owner `ticket.user_id == current_profile.id`, deadline, trạng thái `reserved`, rồi chuyển sang `cancelled`.
- Hủy lặp lại trả resource hiện tại (hoặc 409 theo OpenAPI đã công bố), tuyệt đối không tạo tác động thứ hai.

### T3.4 — Tests và bàn giao

- Test JWT `sub` UUID/profile role; reserve và cancel chỉ tác động ticket của owner.
- Test clock tại 21:59:59, 22:00:00 và 22:00:01 giờ Việt Nam.
- Test cùng idempotency key, key-body khác, hai request song song cùng run, unique constraint và rollback.
- Cập nhật OpenAPI với UUID examples; bàn giao contract reserve/cancel và lifecycle cho Khánh. Duy nhận input demand từ ticket `reserved`.

**Nghiệm thu T3:** một reserve/retry/cancel chỉ tạo đúng một ticket; tất cả các ID trả về là UUID; migration và test chạy trên staging sạch.

## Ngày 4 (T4) — Worker route job và API đọc tuyến

### T4.1 — Endpoint tạo và worker chạy job

**`POST /api/v1/routes/generate`** nhận `service_date`, `session_id`, `trip_type`, `depot_location_id UUID`.

- Đây là endpoint nội bộ cron: yêu cầu `X-Cron-Secret`; so sánh constant-time; secret bắt buộc có trong environment, không có giá trị default trong source. Sai/thiếu trả 401.
- Nếu cần admin chạy tay, mở endpoint admin riêng và xác thực thêm JWT role `admin`; Flutter không bao giờ giữ cron secret.
- Validate run/depot/vehicle/demand và chỉ nhận job sau cutoff. Trong transaction, tạo hoặc lấy job theo partial unique key: queued/running trả job hiện có (202); succeeded không rerun; failed chỉ retry theo policy có audit.
- Worker chạy ở **một process riêng duy nhất** (ví dụ service Render Worker) polling `route_jobs` PostgreSQL. Worker claim job bằng `SELECT … FOR UPDATE SKIP LOCKED`, đổi `queued → running`, gọi interface Duy, sau đó ghi routes/stops/assignment trong một transaction.
- Transaction kết quả tạo routes có run key, route stops, gán những ticket `reserved` đúng run sang `route_id` và `assigned`, rồi chuyển job `succeeded`. Bất kỳ lỗi nào rollback dữ liệu route/assignment và job thành `failed` kèm error an toàn để debug.
- Viết runbook: số worker phải là 1, cách deploy/restart, retry failed job và cách theo dõi queued/running quá lâu.

**Interface Duy:** `trigger_routing_job(service_date, session_id, trip_type, depot_location_id)`; Backend đưa aggregate demand của ticket `reserved`, Routing trả `vehicle_id UUID` và mỗi stop gồm `location_id UUID`, `stop_order`, `arrival_time`.

### T4.2 — API route có RBAC

**`GET /api/v1/routes?service_date=&session_id=&trip_type=&status=`**

- Sinh viên chỉ nhận routes join từ ticket của `current_profile.id` đã `assigned`.
- Tài xế chỉ nhận routes có `vehicle.driver_id == current_profile.id`.
- Admin được filter toàn bộ. Không nhận `driver_id` tùy ý từ client để thay đổi quyền.
- Eager-load vehicle, stops và location; phân trang khi cần.

**`GET /api/v1/routes/{route_id}`**

- `route_id` UUID; dùng cùng rule authorisation.
- Trả stops theo `stop_order`, tên/toạ độ trạm, `arrival_time` ISO-8601 UTC, vehicle, route status và `passenger_count` tính aggregate từ ticket `assigned` theo `pickup_location_id`/run. Không trả danh tính sinh viên.

### T4.3 — Verification, staging và bàn giao

- Test secret thiếu/sai (401), request sai (422), duplicate run, worker crash/failure rollback, claim song song và job succeeded không tạo data trùng.
- Test RBAC A/B: student A không xem ticket/route B; driver A không xem/sửa route driver B.
- Test route detail có UUID, stops đúng thứ tự, UTC timestamps và passenger count đúng.
- Deploy staging theo thứ tự: migration → worker → API. Smoke test `/health`, `/docs`, worker và luồng `reserve → generate → assigned`.
- Khánh và Lợi review OpenAPI mới trước merge; không tích hợp endpoint booking/route detail cũ dùng integer.

**Nghiệm thu T4:** một run có tối đa một worker job đang chạy; job thành công tạo/gán chính xác một lần; sinh viên và tài xế chỉ thấy dữ liệu trong phạm vi UUID profile của mình.

## Phối hợp và điểm chặn

| Bên phối hợp | Việc phải chốt |
|---|---|
| Minh / DB | UUID cutover, migration mapping hoặc seed sạch, RLS `auth.uid() = profiles.id`, review constraint/index |
| Duy / Routing | Contract UUID cho job/input/output, worker retry/rerun policy |
| Khánh / Flutter sinh viên | Đổi model/API sang UUID; reserve/cancel/lifecycle ticket mới |
| Lợi / Flutter tài xế | Đổi model/API sang UUID; route list/detail theo scope driver |

Standup trước 17:00 kiểm tra migration, OpenAPI consumer review, worker/job, staging và các test 21:59/22:00/22:01. Không merge endpoint write trước khi migration UUID được Minh review.
