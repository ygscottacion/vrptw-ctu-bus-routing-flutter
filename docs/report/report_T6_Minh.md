# Báo cáo T6 (Ngày 6) — Minh, DB/Supabase

**Trạng thái: Hoàn tất, đã pass toàn bộ bước.**

## 1. Fresh-install / reset + seed repeatable

- Backup staging trước khi reset (`pg_dump`, lưu local).
- Reset sạch schema `public`, chạy lại toàn bộ chain migration từ đầu bằng `alembic upgrade head` — pass.
- Chạy seed (`seed_supabase.py`) 2 lần trên DB hoàn toàn mới — idempotent đúng: 5 passenger, 2 driver, 2 vehicle, 5 location, row count không đổi giữa 2 lần chạy.

## 2. Security review

- Kiểm tra RLS coverage toàn bộ bảng — pass, đúng thiết kế deny-all cho `bookings`/`route_jobs`/`idempotency_keys`/`alembic_version`/`gps_logs`.
- Kiểm tra policy list — khớp 100% với thiết kế T3.2, không thừa/thiếu.
- Chạy lại ma trận A/B bằng JWT thật (8 dòng, mở rộng thêm 1 dòng so với T3.2 để test bảng `users` legacy) — **8/8 pass**.

## 🔍 2 Finding quan trọng phát hiện qua fresh-install test

### Finding 1 — Thiếu UUID default trên 9 bảng
Migration nền tảng `20260830_uuid_cutover` tạo cột `id` kiểu UUID cho các bảng nghiệp vụ nhưng **không set `server_default gen_random_uuid()`**. Ghi qua FastAPI/SQLAlchemy vẫn hoạt động (model Python tự sinh UUID), nhưng ghi trực tiếp qua Supabase client (như seed script) bị lỗi `null value in column "id"`.

**Đã fix:** migration `20260903_fix_missing_uuid_defaults` — thêm default cho 9 bảng (`bookings, idempotency_keys, incidents, locations, route_jobs, route_stops, routes, tickets, vehicles`). Cố tình **không** thêm cho `profiles` vì `id` lấy từ `auth.users.id` qua trigger, không tự sinh.

**Cần Nhã/Duy rà lại:** nếu có bất kỳ chỗ nào trong code FastAPI insert thẳng qua raw SQL/Supabase client (bypass SQLAlchemy ORM) cho các bảng này, nên kiểm tra lại logic tương tự.

### Finding 2 — Bảng `users` legacy thiếu RLS sau fresh-install
Bảng `users` (trước UUID cutover) không nằm trong 10 bảng migration UUID quản lý, nên khi reset từ đầu, bảng được tạo lại bởi migration cũ hơn mà không có RLS — có thể bị đọc/ghi qua PostgREST nếu có GRANT rộng trên schema `public`.

**Đã fix tạm thời:** migration `20260903_rls_legacy_users` — bật RLS deny-all (không tạo policy), an toàn và không phá huỷ dữ liệu.

**Cần quyết định tiếp:** chờ kết quả rà soát code cũ từ Khánh/Lợi (mục A.6, đã giao ở T4.3) — nếu xác nhận không còn module nào dùng bảng `users`, sẽ có migration `DROP TABLE users` dứt điểm.

### Finding 3 — GRANT mặc định của Supabase cấp full CRUD cho anon/authenticated trên bảng deny-all
Khi kiểm tra `information_schema.role_table_grants` cho `bookings`, `idempotency_keys`, `route_jobs`, phát hiện cả `anon` và `authenticated` đều có sẵn đầy đủ quyền `SELECT/INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER`. Đây là hành vi **mặc định của Supabase** (`ALTER DEFAULT PRIVILEGES` tự động áp cho mọi bảng mới trong schema `public`), không phải do quá trình reset gây ra.

Về lý thuyết, RLS deny-all + `FORCE ROW LEVEL SECURITY` đã đủ chặn truy cập dù có GRANT, nhưng đây là rủi ro không cần thiết — nếu sau này ai vô tình thêm 1 policy permissive mà không rà kỹ, hậu quả sẽ nghiêm trọng hơn.

**Đã fix (defense in depth):** migration `20260903_revoke_excess_grants` — revoke toàn bộ quyền của `anon`/`authenticated` trên các bảng deny-all: `bookings, route_jobs, idempotency_keys, alembic_version, gps_logs, users`. `service_role` giữ nguyên quyền (backend/worker dùng, bypass RLS).

**Verify:** test request PostgREST tới `bookings` bằng JWT student — nhận `403 Forbidden` ngay ở tầng Postgres GRANT, không cần RLS phải xử lý. Đúng kỳ vọng.

**Lưu ý quy trình:** sau khi thay đổi grant/RLS trên bảng đã tồn tại, cần chạy `NOTIFY pgrst, 'reload schema';` để PostgREST nhận schema mới — bổ sung bước này vào checklist reset/migration cho các lần sau, tránh nhầm lẫn giữa "chưa reload cache" và "cấu hình sai".

## Migration đã thêm trong T6 (theo thứ tự chain)

1. `20260901_merge_heads` — gộp 2 head bị phân nhánh (Minh × Nhã tạo migration song song từ cùng gốc).
2. `20260902_gps_logs_v1` — bảng GPS log (đã có từ T5, xác nhận chạy đúng qua fresh-install).
3. `20260903_fix_missing_uuid_defaults` — fix Finding 1.
4. `20260903_rls_legacy_users` — fix Finding 2.
5. `20260903_revoke_excess_grants` — fix Finding 3.

**Head hiện tại:** `20260903_revoke_excess_grants`

## Việc tồn đọng / cần phối hợp tiếp

- Rotate 3 secret đã lộ (DB password, `SUPABASE_SERVICE_ROLE_KEY`, `CRON_SECRET`) — vẫn chưa thực hiện.
- Chờ Khánh/Lợi hoàn tất bảng rà soát code cũ (A.6) để quyết định drop hẳn bảng `users` hay không.
- Theo dõi `BUG-VRPTW-01` (route_stops thiếu khi generate route) — chưa có cập nhật fix từ Duy/Nhã.
- Trước khi tạo migration mới: luôn chạy `alembic heads` để tránh lặp lại tình huống 2-head như đầu T6.
