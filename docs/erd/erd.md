# ERD — MyCTU BUS (cập nhật sau migration `20260828_profiles_baseline`)

> **Trạng thái Ngày 1:** `profiles` đã tạo, FK → `auth.users.id` (UUID), migration đã chạy thành công. Toàn bộ 6 model nghiệp vụ (`users`, `tickets`, `bookings`, `routes`, `route_stops`, `locations`, `vehicles`, `incidents`) đã đối chiếu trực tiếp với code thật — ERD dưới đây phản ánh đúng schema hiện tại trong repo.
>
> **Chưa đổi ở Ngày 1 (theo đúng phân công):** tất cả FK người dùng (`user_id`, `driver_id`) trong `tickets`, `bookings`, `routes`, `vehicles`, `incidents` **vẫn là `Integer` trỏ về `users.id`**, chưa chuyển sang `uuid` trỏ về `profiles.id`. Việc này thuộc Ngày 4 (Thành viên 1, phối hợp Minh).
>
> ⚠️ **Cảnh báo kỹ thuật cần xử lý trước Ngày 4:** `alembic/env.py` hiện chỉ import `User, Location, Vehicle, Route, RouteStop` — **chưa import `Ticket`, `Booking`, `Incident`**. Nếu chạy `alembic revision --autogenerate` ở trạng thái này, Alembic sẽ không thấy 3 bảng này thuộc `target_metadata` và có thể sinh migration `DROP TABLE` nhầm. Cần thêm import trước khi bất kỳ ai autogenerate migration tiếp theo.

---

## Sơ đồ quan hệ (Mermaid)

```mermaid
erDiagram
    AUTH_USERS ||--|| PROFILES : "id = id (FK, CASCADE)"

    USERS {
        int id PK
        string username UK
        string password_hash
        enum role "admin/driver/passenger"
        string full_name
        string phone
    }

    PROFILES {
        uuid id PK "FK -> auth.users.id, ON DELETE CASCADE"
        enum role "admin/driver/passenger"
        string full_name
        string phone
    }

    LOCATIONS {
        int id PK
        string name
        float latitude
        float longitude
        datetime time_window_start
        datetime time_window_end
        int demand "default 1"
    }

    VEHICLES {
        int id PK
        string license_plate UK
        int capacity "default 30"
        int driver_id FK "-> users.id, nullable"
    }

    ROUTES {
        int id PK
        int vehicle_id FK "-> vehicles.id, nullable"
        date date
        enum status "pending/in_progress/completed"
        float total_distance "default 0.0"
    }

    ROUTE_STOPS {
        int id PK
        int route_id FK "-> routes.id"
        int location_id FK "-> locations.id"
        datetime arrival_time
        int stop_order
    }

    TICKETS {
        int id PK
        int user_id FK "-> users.id"
        int route_id FK "-> routes.id, nullable"
        date service_date "nullable, index"
        string session_id "nullable, index"
        string trip_type "nullable"
        int pickup_location_id FK "-> locations.id, nullable"
        string qr_code UK
        enum status "active/used/expired"
        datetime created_at
    }

    BOOKINGS {
        int id PK
        int user_id FK "-> users.id"
        int route_id FK "-> routes.id"
        int ticket_id FK "-> tickets.id, UNIQUE"
        int pickup_location_id FK "-> locations.id"
        string schedule_time "nullable"
        string note "nullable"
        enum status "confirmed/cancelled/completed"
        datetime created_at
    }

    INCIDENTS {
        int id PK
        int driver_id FK "-> users.id"
        int vehicle_id FK "-> vehicles.id, nullable"
        string title
        text description "nullable"
        enum status "pending/processing/resolved"
        datetime reported_at
    }

    USERS ||--o{ VEHICLES : "driver_id"
    USERS ||--o{ TICKETS : "user_id"
    USERS ||--o{ BOOKINGS : "user_id"
    USERS ||--o{ INCIDENTS : "driver_id"

    VEHICLES ||--o{ ROUTES : "vehicle_id"
    VEHICLES ||--o{ INCIDENTS : "vehicle_id"

    ROUTES ||--o{ ROUTE_STOPS : "route_id"
    ROUTES ||--o{ TICKETS : "route_id"
    ROUTES ||--o{ BOOKINGS : "route_id"

    LOCATIONS ||--o{ ROUTE_STOPS : "location_id"
    LOCATIONS ||--o{ TICKETS : "pickup_location_id"
    LOCATIONS ||--o{ BOOKINGS : "pickup_location_id"

    TICKETS ||--|| BOOKINGS : "ticket_id (1-1, unique)"
```

---

## Chi tiết từng bảng

### `auth.users` — do Supabase quản lý, không migrate bằng Alembic
Bảng hệ thống của Supabase Auth. `profiles.id` tham chiếu trực tiếp `id` của bảng này.

### `profiles` — ✅ mới, tạo ở migration `20260828_profiles_baseline`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | `uuid` (PK) | FK → `auth.users.id`, `ON DELETE CASCADE`. Định danh chuẩn duy nhất từ nay. |
| `role` | enum `profile_role` (`admin`/`driver`/`passenger`) | default `passenger` |
| `full_name` | `varchar(100)` | nullable |
| `phone` | `varchar(20)` | nullable |

### `users` — ⚠️ legacy, giữ tạm tới Ngày 3–4
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | `Integer` (PK) | Toàn bộ FK nghiệp vụ hiện tại (`tickets.user_id`, `bookings.user_id`, `routes` gián tiếp qua `vehicles.driver_id`, `incidents.driver_id`) đều đang trỏ vào đây |
| `username` | `varchar(50)` unique | thuộc auth nội bộ cũ, dự kiến bỏ ở Ngày 3 |
| `password_hash` | `varchar(255)` | thuộc auth nội bộ cũ, dự kiến bỏ ở Ngày 3 |
| `role` | enum `UserRole` | trùng ý nghĩa với `profiles.role`, sẽ hợp nhất |
| `full_name`, `phone` | | trùng cấu trúc `profiles` |

### `locations`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | Integer PK | |
| `name` | `varchar(100)` | required |
| `latitude`, `longitude` | Float | required — tọa độ trạm |
| `time_window_start`, `time_window_end` | DateTime | nullable — dùng cho bài toán routing (Sweep/Tabu) |
| `demand` | Integer | default 1 — số lượng khách dự kiến tại trạm, input cho thuật toán sinh tuyến |

### `vehicles`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | Integer PK | |
| `license_plate` | `varchar(20)` unique | |
| `capacity` | Integer | default 30 |
| `driver_id` | Integer FK → `users.id` | nullable — **ứng viên đổi UUID → `profiles.id` ở Ngày 4** |

### `routes`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | Integer PK | |
| `vehicle_id` | Integer FK → `vehicles.id` | nullable |
| `date` | Date | required |
| `status` | enum `RouteStatus` (`pending`/`in_progress`/`completed`) | |
| `total_distance` | Float | default 0.0 |

⚠️ Lưu ý: `routes` **chưa có** `service_date`/`session_id`/`trip_type` như plan mô tả (*"Job sinh tuyến có `service_date + session_id + trip_type` unique"*) — hiện chỉ có cột `date` đơn thuần, chưa có unique constraint chống trùng job. Đây là việc cần bổ sung, dự kiến thuộc Ngày 4–5 (Minh + Thành viên 3 phối hợp) khi làm idempotent cho route generation job.

### `route_stops`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | Integer PK | |
| `route_id` | Integer FK → `routes.id` | required |
| `location_id` | Integer FK → `locations.id` | required |
| `arrival_time` | DateTime | nullable |
| `stop_order` | Integer | required — thứ tự trạm trong tuyến |

### `tickets`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → `users.id` | required — **ứng viên đổi UUID Ngày 4** |
| `route_id` | Integer FK → `routes.id` | nullable — vé chưa gán tuyến (trước 22:00) sẽ null |
| `service_date` | Date | nullable, index |
| `session_id` | String | nullable, index |
| `trip_type` | String | nullable |
| `pickup_location_id` | Integer FK → `locations.id` | nullable |
| `qr_code` | String unique | required, index — dùng cho check-in |
| `status` | enum `TicketStatus` (`active`/`used`/`expired`) | |
| `created_at` | DateTime | default `utcnow` |

⚠️ Chưa thấy state `reserved/assigned/checked_in/cancelled` như mô tả trong plan (mục "Vé của tôi") — hiện enum chỉ có `active/used/expired`, có thể cần mở rộng ở Ngày 4 tùy cách Thành viên 4 (Flutter) map UI.

### `bookings`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → `users.id` | required — **ứng viên đổi UUID Ngày 4** |
| `route_id` | Integer FK → `routes.id` | required |
| `ticket_id` | Integer FK → `tickets.id`, **unique** | required — quan hệ 1-1 với `tickets` |
| `pickup_location_id` | Integer FK → `locations.id` | required |
| `schedule_time` | String | nullable — lưu ý: đang là String tự do, không phải DateTime chuẩn |
| `note` | String | nullable |
| `status` | enum `BookingStatus` (`confirmed`/`cancelled`/`completed`) | |
| `created_at` | DateTime | default `utcnow` |

### `incidents`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | Integer PK | |
| `driver_id` | Integer FK → `users.id` | required — **ứng viên đổi UUID Ngày 4** |
| `vehicle_id` | Integer FK → `vehicles.id` | nullable |
| `title` | String | required |
| `description` | Text | nullable |
| `status` | enum `IncidentStatus` (`pending`/`processing`/`resolved`) | |
| `reported_at` | DateTime | default `utcnow` |

---

## Việc còn lại liên quan ERD (không làm ở Ngày 1, ghi chú để không quên)

1. **Sửa `alembic/env.py`**: thêm import `Ticket`, `Booking`, `Incident` — bắt buộc trước khi ai đó chạy autogenerate lần tới.
2. **Ngày 4** — đổi toàn bộ `user_id`/`driver_id` (Integer → uuid, trỏ `profiles.id`) tại: `tickets`, `bookings`, `vehicles.driver_id`, `incidents.driver_id`.
3. **Ngày 4–5** — thêm unique constraint `(service_date, session_id, trip_type)` cho `routes` để job sinh tuyến idempotent như plan yêu cầu.
4. **Cần Product Owner/leader xác nhận** — enum `TicketStatus` có cần mở rộng thành `reserved/assigned/checked_in/expired/cancelled` để khớp UI "Vé của tôi" hay giữ nguyên `active/used/expired` và map ở tầng API.

