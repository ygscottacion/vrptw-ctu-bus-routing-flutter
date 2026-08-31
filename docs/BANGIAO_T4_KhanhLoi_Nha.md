# Bàn giao Ngày 4 (T4.3) — Minh (DB/Supabase) → Khánh/Lợi & Nhã

Ngày bàn giao: (điền ngày thực tế)
Người bàn giao: Minh
Trạng thái tổng quan: T3 hoàn tất; T4.1/T4.3 hoàn tất; **T4.2 blocked một phần bởi `BUG-VRPTW-01`** (xem file `BUG-VRPTW-01.md` đính kèm) — route_stops chưa đầy đủ, chờ Duy/Nhã fix.

---

## A. Bàn giao Khánh/Lợi

### A.1 API base URL staging

| Môi trường | URL |
|---|---|
| Staging | `<điền base URL staging thực tế>` |

### A.2 UUID contract

- Toàn bộ ID nghiệp vụ (`profiles.id`, `tickets.id`, `locations.id`, `vehicles.id`, `routes.id`, `route_stops.id`, `incidents.id`) là **UUID**, lấy từ Supabase Auth `sub` (đối với `profiles.id`) hoặc UUID sinh bởi Postgres (đối với các bảng còn lại).
- **Không còn** `users.id` kiểu integer từ backend cũ. Bất kỳ chỗ nào trong code Flutter/backend cũ đang parse ID dưới dạng `int` cho các entity này đều sẽ lỗi và cần sửa sang `String`/UUID.
- Header xác thực: `Authorization: Bearer <supabase_access_token>`. Backend parse `sub` trong JWT ra UUID để map sang `profiles.id` — không còn cơ chế session/token kiểu cũ.

### A.3 Account test

- 5 tài khoản student + 2 tài khoản driver đã tạo qua Supabase Admin API (script `seed_supabase.py`).
- Email/password gửi qua kênh bí mật nội bộ (1Password/Bitwarden share) — **không** gửi qua Slack/email thường. Sẽ gửi riêng ngay sau bản bàn giao này.

### A.4 Role mapping & dữ liệu seed hiện có

| Role | Số lượng | Ghi chú |
|---|---|---|
| `passenger` | 5 | Tạo tự động qua trigger `on_auth_user_created`, mặc định `passenger` |
| `driver` | 2 | Cập nhật role thủ công sau khi tạo user, bằng quyền admin |

| Loại dữ liệu | Natural key | Số lượng |
|---|---|---|
| `locations` | `code` (vd `LOC-01` → `LOC-05`) | 5 |
| `vehicles` | `license_plate` (vd `51F-000.01`, `51F-000.02`) | 2 |

Danh sách UUID cụ thể của các bản ghi trên: xem mục **B.4** (bàn giao cho Nhã) — Khánh/Lợi lấy qua API (`GET /api/v1/routes`, v.v.) bằng token test thay vì query DB trực tiếp.

### A.5 Những gì **không** được bàn giao

- Supabase service-role key.
- Cron secret dùng cho `POST /api/v1/routes/generate`.

Nếu module của Khánh/Lợi cần gọi các endpoint yêu cầu quyền này, báo lại để Nhã cấp quyền phù hợp (không dùng chung secret của backend/worker).

### A.6 Rà soát code cũ — cần Khánh/Lợi phản hồi

Đề nghị Khánh/Lợi kiểm tra và liệt kê lại các module hiện tại còn:

1. Gọi thẳng hoặc phụ thuộc vào `backend/seed_data.py` (seed legacy, bảng `users` integer, `Base.metadata.create_all()`).
2. Dùng `users.id` kiểu integer ở bất kỳ đâu (model, API call, local storage, cache key...).
3. Gọi endpoint cũ (không thuộc `/api/v1/...` mới) cho các nghiệp vụ: reserve/cancel ticket, generate route, đọc route.

**Bảng để điền (gửi lại cho Minh/Nhã):**

| Module/File | Đang dùng gì (cũ) | Cần chuyển sang | Người phụ trách | Trạng thái |
|---|---|---|---|---|
| (điền) | (điền) | (điền) | (điền) | (điền) |

Endpoint mới tương ứng cần chuyển sang:

| Nghiệp vụ | Endpoint mới |
|---|---|
| Đặt vé | `POST /api/v1/tickets/reserve` |
| Huỷ vé | `POST /api/v1/tickets/{ticket_id}/cancel` |
| Sinh tuyến | `POST /api/v1/routes/generate` |
| Danh sách tuyến | `GET /api/v1/routes` |
| Chi tiết tuyến | `GET /api/v1/routes/{route_id}` |

⚠️ **Lưu ý tạm thời:** dữ liệu trả về từ `GET /api/v1/routes/{route_id}` hiện đang thiếu điểm dừng (`route_stops`) do `BUG-VRPTW-01` — nếu đang test phần hiển thị lộ trình trên Flutter, đây là lỗi đã biết, không phải do phía Khánh/Lợi. Sẽ báo lại khi Duy/Nhã fix xong.

---

## B. Bàn giao Nhã

### B.1 Revision migration RLS

- File: `alembic/versions/20260831_rls_v1.py` (đổi tên theo revision thực tế đã commit).
- `down_revision` trỏ về `20260830_uuid_cutover`.
- Có đủ `upgrade`/`downgrade`, đã test cả 2 chiều trên staging.
- Kèm theo: migration bổ sung `20260901_add_locations_code.py` (thêm cột `code` unique cho `locations`, cần cho seed idempotent) — `down_revision` trỏ về `20260831_rls_v1`.

### B.2 Ma trận A/B (kết quả thật từ T3.2)

| Actor | Resource | Kỳ vọng | Kết quả thực tế |
|---|---|---|---|
| Student A | ticket của A | Đọc được | (điền pass/fail) |
| Student A | ticket của B | Không đọc được | (điền) |
| Student A | route/stop không có ticket assigned | Không đọc được | (điền) |
| Driver A | route/vehicle của A | Đọc được | (điền) |
| Driver A | route/vehicle của B | Không đọc được | (điền) |
| Bất kỳ authenticated | `bookings`, `route_jobs`, `idempotency_keys` | Không đọc/ghi được | (điền) |
| Student A | tự đổi `profiles.role` của mình | Bị từ chối | (điền) |

Smoke test backend/worker sau khi bật RLS: (điền kết quả — reserve/cancel/generate/route worker/read route có bị RLS chặn nhầm không, dùng role/connection nào để verify).

### B.3 Script seed

- File: `backend/scripts/seed_supabase.py`.
- Cách chạy:
  ```bash
  export SUPABASE_URL=...
  export SUPABASE_SERVICE_ROLE_KEY=...
  export SEED_TEST_PASSWORD=...
  python -m scripts.seed_supabase
  ```
- Idempotent: chạy 2 lần cho cùng row count (5 passenger, 2 driver, 2 vehicle, 5 location) — evidence 2 lần chạy đính kèm riêng.
- Yêu cầu migration `20260901_add_locations_code.py` đã chạy trước (thêm cột `code` unique) — nếu chưa, script sẽ lỗi khi upsert `locations`.

### B.4 UUID của depot/vehicle/stop test đã seed

| Entity | Natural key | UUID |
|---|---|---|
| Location (depot/stop) | `LOC-01` | (điền UUID) |
| Location | `LOC-02` | (điền UUID) |
| Location | `LOC-03` | (điền UUID) |
| Location | `LOC-04` | (điền UUID) |
| Location | `LOC-05` | (điền UUID) |
| Vehicle | `51F-000.01` | (điền UUID) |
| Vehicle | `51F-000.02` | (điền UUID) |

### B.5 Report E2E route-job (T4.2)

**Trạng thái: một phần blocked bởi `BUG-VRPTW-01`.**

- 5 ticket đã reserve thành công qua `POST /api/v1/tickets/reserve` (danh sách `ticket_id`: điền).
- `POST /api/v1/routes/generate` chạy, job chuyển `queued → running → SUCCEEDED` (run_key: điền).
- Ticket chuyển `RESERVED → ASSIGNED` đúng cho cả 5 vé.
- **Route_stops KHÔNG đầy đủ:** chỉ có 1 row (depot), thiếu 5 điểm đón — xem chi tiết root cause và đề xuất fix trong `BUG-VRPTW-01.md`.
- `EXPLAIN (ANALYZE, BUFFERS)` cho 3 truy vấn (demand/driver routes/active job) đã chạy trên dữ liệu hiện có — kết quả đính kèm riêng, không phụ thuộc vào bug này (bug chỉ ảnh hưởng `route_stops`, không ảnh hưởng các bảng khác).
- **Cần làm lại sau khi Duy/Nhã fix bug:** verify lại `count(route_stops)` khớp số điểm đón kỳ vọng, và chạy lại API `GET /api/v1/routes/{route_id}` để xác nhận Flutter nhận đủ dữ liệu.

---

## Việc tiếp theo

1. Nhã/Duy xác nhận người phụ trách fix `BUG-VRPTW-01` và thời gian dự kiến.
2. Khánh/Lợi điền bảng rà soát code cũ (mục A.6) và gửi lại.
3. Minh chạy lại phần verify T4.2 (route_stops + API read) sau khi bug được fix, cập nhật report.
