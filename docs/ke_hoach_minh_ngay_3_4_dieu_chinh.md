# Kế hoạch cuối Ngày 3–4 — Minh (DB / Supabase), theo backend UUID hiện tại

## Cơ sở thực tế đã kiểm tra

Backend mới đã có các thành phần sau và kế hoạch này phải dùng đúng chúng:

- Identity nghiệp vụ là `profiles.id UUID` từ Supabase JWT `sub`.
- Migration head: `20260830_uuid_cutover`; các bảng nghiệp vụ UUID gồm `locations`, `vehicles`, `route_jobs`, `routes`, `route_stops`, `tickets`, `bookings`, `incidents`, `idempotency_keys`; `profiles` do migration trước tạo.
- Ticket dùng lifecycle `reserved → assigned → used|cancelled|expired`; unique run là `uq_tickets_user_run`; routing dùng `ix_tickets_run_status`.
- Backend của Nhã đã có `POST /api/v1/tickets/reserve`, `POST /api/v1/tickets/{ticket_id}/cancel`, `POST /api/v1/routes/generate`, `GET /api/v1/routes` và `GET /api/v1/routes/{route_id}` — tất cả ID là UUID.
- `run_route_job_worker` và `route_jobs` đã có. Hiện endpoint generate gọi worker đồng bộ; chuyển sang worker service riêng là việc của Nhã/Duy, không thuộc Minh trong hai ngày này.
- Trigger `on_auth_user_created` tạo profile passenger đã có. RLS policy và seed UUID đúng Supabase chưa có.

> Rủi ro bắt buộc: `20260830_uuid_cutover` đang xóa các bảng nghiệp vụ bằng `DROP TABLE … CASCADE` trước khi tạo lại. Chỉ chạy trên staging rỗng hoặc sau phê duyệt reset/backup bằng văn bản của Leader; không dùng để nâng cấp database có dữ liệu cần giữ.

## Ngày 3 (T3) — Xác minh migration, trigger và RLS v1

### T3.1 — Fresh migration và Supabase Auth trigger

1. Tạo Supabase staging/preview sạch đã được Nhã phê duyệt. Không chạy `Base.metadata.create_all()` và không dùng script seed legacy.
2. Chạy `alembic upgrade head`, lưu revision head, log và schema inspection. Kiểm tra đủ **10** bảng: `profiles`, `locations`, `vehicles`, `route_jobs`, `routes`, `route_stops`, `tickets`, `bookings`, `incidents`, `idempotency_keys`.
3. Kiểm tra catalog PostgreSQL có enum/status và constraint/index backend đang cần: `uq_tickets_user_run`, `uq_idempotency_user_endpoint_key`, `ix_tickets_run_status`, `ix_vehicles_driver_id`, `ix_routes_run`, `ix_route_jobs_active_run`, `uq_route_stops_order`.
4. Tạo test user qua Supabase Dashboard hoặc Admin API; xác nhận trigger `on_auth_user_created` tạo `profiles.id = auth.users.id`, role `passenger`. Xác nhận việc xóa Auth user xóa profile theo cascade.
5. Phối hợp Nhã kiểm thử FastAPI nhận JWT Supabase, parse `sub` UUID và đọc đúng profile. Đây là smoke test backend mới, không dùng `users.id` legacy.

**Deliverable:** báo cáo migration/trigger có command, revision, screenshot hoặc query result; test UUID pass trên staging sạch.

### T3.2 — RLS v1: bổ sung migration do Minh sở hữu

Tạo **một Alembic migration mới** cho RLS (ví dụ `..._rls_policies_v1.py`), có `upgrade` và `downgrade`; không dùng file SQL rời không được deploy. Bật RLS cho 10 bảng public nhưng chỉ mở policy client ở nơi cần thiết.

| Bảng | Policy client `authenticated` | Lý do |
|---|---|---|
| `profiles` | Đọc profile mình; chỉ sửa `full_name`, `phone` của mình | Không được sửa `role`; profile do trigger/service tạo. |
| `tickets` | Chỉ đọc ticket có `user_id = auth.uid()` | Reserve/cancel phải qua backend transaction và idempotency, không cho direct write. |
| `routes`, `route_stops` | Chỉ đọc route/stop mà user có ticket `assigned`, hoặc route thuộc vehicle có `driver_id = auth.uid()` | Không dùng policy “mọi authenticated user đọc toàn bộ route”. |
| `locations` | Chỉ đọc | Flutter cần dữ liệu trạm; không sửa trực tiếp. |
| `vehicles` | Driver chỉ đọc xe được gán; admin theo rule riêng nếu cần | Không public dữ liệu vận hành không cần thiết. |
| `incidents` | Driver đọc/tạo incident của mình, `WITH CHECK driver_id = auth.uid()` | Không cho status update trực tiếp; backend/admin quản lý workflow. |
| `bookings`, `route_jobs`, `idempotency_keys` | Không cấp policy client | `bookings` là legacy ngoài MVP; job/idempotency chỉ backend/worker dùng. |

- Policy admin dùng profile role được kiểm soát; tránh dựa vào metadata client tự ghi.
- Trước khi deploy RLS, Nhã cung cấp **database role/connection thực tế** của FastAPI và worker. Minh kiểm tra RLS không chặn luồng backend mới: reserve, cancel, generate, route worker, read route. Không mặc định rằng `SUPABASE_SERVICE_ROLE_KEY` giống database connection hoặc tự động bypass RLS.
- Vì Flutter hiện dùng Supabase cho Auth và gọi API backend cho nghiệp vụ, RLS là lớp phòng thủ cho direct Supabase access; RBAC trong FastAPI vẫn là bắt buộc.
- Chạy A/B bằng JWT thực: student A không đọc/sửa ticket/route của B; driver A không xem route/vehicle B; client không đọc route job/idempotency và không đổi role.

**Deliverable:** migration RLS đã commit, matrix A/B allow/deny, và smoke test API/worker sau RLS cùng Nhã. Đây là đầu việc của Minh; Nhã review tác động backend.

## Ngày 4 (T4) — Seed UUID tương thích backend và E2E routing

### T4.1 — Thay seed legacy bằng Supabase seed idempotent

`backend/seed_data.py` hiện seed bảng `users` integer và gọi `Base.metadata.create_all()`, nên không tương thích backend UUID. Minh thay bằng script seed riêng theo các quy tắc sau:

1. Dùng Supabase Admin API/Dashboard để tìm hoặc tạo 5 student và 2 driver theo email. Không SQL insert trực tiếp vào `auth.users`; không commit service-role key hay password vào repository.
2. Lấy UUID từ Auth response; trigger tạo profile passenger. Dùng quyền quản trị để cập nhật đúng 2 profile thành `driver`.
3. Upsert 2 vehicle theo `license_plate`, gán `driver_id` UUID. Upsert 5 location theo natural key ổn định đã chốt; thêm column `code` unique nếu tên không đủ ổn định. Không dùng UUID ngẫu nhiên mới mỗi lần chạy để nhận diện dữ liệu cũ.
4. Chạy seed hai lần, báo cáo row count không đổi: 5 passenger, 2 driver, 2 vehicle, 5 location. Chỉ bàn giao tài khoản test qua kênh bí mật nội bộ.

**Deliverable:** script seed UUID idempotent, hướng dẫn chạy bằng environment variables, evidence hai lần chạy và seed trên staging.

### T4.2 — Data routing và xác nhận index

1. Tạo 5 ticket `reserved` bằng chính `POST /api/v1/tickets/reserve` của backend mới hoặc service transaction tương đương, với `service_date`, `session_id`, `trip_type`, `pickup_location_id` UUID hợp lệ. Không insert ticket tay để bỏ qua deadline/idempotency/unique constraint.
2. Cùng Duy/Nhã gọi `POST /api/v1/routes/generate` bằng cron secret từ môi trường kín. Với backend hiện tại, endpoint gọi `run_route_job_worker` đồng bộ; chấp nhận đây là smoke E2E hiện tại, không giao Minh sửa worker.
3. Xác minh một job chuyển `queued → running → succeeded`, route/route_stops có UUID và run key đúng, ticket chuyển `reserved → assigned`; student/driver đọc đúng bằng API route mới.
4. Chạy `EXPLAIN (ANALYZE, BUFFERS)` trên dữ liệu đại diện:
   - Demand: run key + `status = 'reserved'` được hỗ trợ bởi `ix_tickets_run_status`.
   - Driver routes: join `routes.vehicle_id → vehicles.driver_id` được hỗ trợ bởi `ix_routes_vehicle_id` và `ix_vehicles_driver_id`.
   - Active job: run key + `status IN ('queued','running')` khớp predicate `ix_route_jobs_active_run`.
5. Không yêu cầu “100% Index Scan/không Sequential Scan”: với seed nhỏ PostgreSQL chọn sequential scan là bình thường. Chỉ thêm index nếu `EXPLAIN` dữ liệu đại diện chỉ ra bottleneck; report có SQL, số row và buffers.

**Deliverable:** 5 ticket reserve mẫu, report E2E route-job và report query plan; Duy xác nhận worker xử lý đúng dữ liệu seed.

### T4.3 — Handoff và checklist staging

- Bàn giao Khánh/Lợi: API base URL staging, UUID contract, account test qua secret channel, role và dữ liệu seed. Không bàn giao Supabase service-role key hay cron secret.
- Bàn giao Nhã: revision/migration RLS, kết quả A/B, script seed, UUID của depot/vehicles/stops test, report E2E.
- Runbook staging: phê duyệt reset/backup → `alembic upgrade head` → Auth/profile seed → vehicle/location seed → RLS A/B smoke → reserve → generate → route read.

## Tóm tắt giao việc

| Ngày | Minh thực hiện | Bên review/phối hợp |
|---|---|---|
| T3 | Fresh migration, trigger profile UUID, catalog verification | Nhã |
| T3 | Migration RLS v1, A/B test, API/worker smoke sau RLS | Nhã |
| T4 | Thay seed legacy bằng seed Supabase UUID idempotent | Khánh, Lợi |
| T4 | Seed ticket qua backend mới, E2E generate và EXPLAIN report | Duy, Nhã |
