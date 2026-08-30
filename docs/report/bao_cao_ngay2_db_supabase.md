# Báo cáo Ngày 2 — DB/Supabase (Minh)

**Dự án:** MyCTU BUS MVP — 10 ngày
**Thành viên:** Thành viên 2 – DB/Supabase
**Ngày:** 2/10
**Trạng thái:** ✅ Hoàn thành, tất cả kiểm thử pass

---

## 1. Việc đã thực hiện

### 1.1. Auth trigger tự động sinh `profiles`
- Tạo function `handle_new_user()` (SECURITY DEFINER) + trigger `on_auth_user_created` trên `auth.users`.
- Khi có tài khoản mới đăng ký qua Supabase Auth, hệ thống tự động insert 1 row `profiles` tương ứng với `role = 'passenger'` mặc định.
- File migration: `backend/alembic/versions/20260829_auth_trigger_default_role.py`

### 1.2. Index cho các FK còn thiếu
- Thêm 10 index phục vụ các truy vấn thường xuyên (danh sách vé/tuyến theo user, tuyến theo tài xế...):
  `ix_bookings_user_id`, `ix_bookings_route_id`, `ix_tickets_user_id`, `ix_tickets_route_id`, `ix_vehicles_driver_id`, `ix_incidents_driver_id`, `ix_incidents_vehicle_id`, `ix_route_stops_route_id`, `ix_route_stops_location_id`, `ix_routes_vehicle_id`.
- File migration: `backend/alembic/versions/20260829_add_missing_fk_indexes.py`

### 1.3. Enum — rà soát, không cần thay đổi
- Xác nhận `UserRole` (bảng `users` cũ, Postgres type `userrole`) và `ProfileRole` (bảng `profiles`, Postgres type `profile_role`) không đụng tên, không xung đột.

### 1.4. Seed dữ liệu test
- Tạo 3 tài khoản test qua Supabase Dashboard, gán đúng 3 role: `passenger`, `driver`, `admin`.
- Đã gửi thông tin đăng nhập cho Thành viên 4 & 5 phục vụ tích hợp Flutter trong ngày.

---

## 2. Kiểm thử — tất cả PASS

| # | Kịch bản test | Kết quả |
|---|---|---|
| 1 | Trigger `on_auth_user_created` tồn tại và đang bật (`pg_trigger`) | ✅ PASS |
| 2 | Tạo user thật qua Dashboard → `profiles` tự sinh với `role = 'passenger'` | ✅ PASS |
| 3 | Xóa user ở `auth.users` → `profiles` tương ứng tự xóa theo (`ON DELETE CASCADE`) | ✅ PASS |
| 4 | Seed 3 tài khoản, cập nhật đúng 3 role khác nhau | ✅ PASS |
| 5 | Xác nhận đủ 10 index đã tạo (`pg_indexes`) | ✅ PASS |
| 6 | Insert trùng (mô phỏng trigger chạy 2 lần) không gây lỗi, không ghi đè role đã set | ✅ PASS |

---

## 3. Hạ tầng / môi trường — đã xác nhận

- Migration chạy qua `docker compose exec web alembic upgrade head`, container không mount volume nên **cần `docker compose build web` sau mỗi lần thêm file migration mới** để container nhận code cập nhật.
- Đã xác minh `assemble_db_connection()` trả về đúng host Supabase Session Pooler (`aws-0-ap-southeast-1.pooler.supabase.com:5432`), không rơi vào Postgres local (`db` service trong `docker-compose.yml`) dù service đó vẫn chạy song song.
- Chuỗi migration đủ 4 bước, không có nhánh (multiple heads):
  `<base> → 20260825_daily_tickets → 20260828_profiles_baseline → 20260829_auth_trigger → 20260829_fk_indexes (head)`

## 4. Git

- Nhánh làm việc: `feat/db-profiles-uuid-baseline`
- File thêm mới trong Ngày 2:
  - `backend/alembic/versions/20260829_auth_trigger_default_role.py`
  - `backend/alembic/versions/20260829_add_missing_fk_indexes.py`
- Đã commit và push, PR đang chờ Nhã review.

---

## 5. Việc cần cho Ngày 3

- Phối hợp với Nhã (leader) triển khai JWKS + role guard + endpoint `/me` ở FastAPI — dựa trên `profiles` và trigger đã có sẵn từ Ngày 2.
- Theo `auth_supabase_contract.md`: cần chuẩn bị RLS deny-by-default, kiểm thử user A/B (đã lên lịch cho Ngày 3 theo phân công gốc).

## 6. Rủi ro / điểm cần theo dõi (chưa xử lý, không thuộc phạm vi Ngày 2)

- `routes` hiện chưa có `service_date`/`session_id`/`trip_type` + unique constraint như plan mô tả cho job sinh tuyến idempotent — dự kiến bổ sung Ngày 4–5.
- `TicketStatus` hiện chỉ có `active/used/expired`, chưa khớp vòng đời `reserved → assigned → checked_in/expired/cancelled` mô tả trong UI "Vé của tôi" — cần leader/Thành viên 4 xác nhận hướng xử lý trước Ngày 4.
