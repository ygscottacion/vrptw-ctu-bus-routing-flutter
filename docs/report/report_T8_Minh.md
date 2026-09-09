# Bàn giao cuối cùng (T8) — Migration & Seed, Minh (DB/Supabase)

**Ngày bàn giao:** (điền ngày thực tế chạy xong bước 1)
**Trạng thái:** Migration/schema đã freeze từ T7, chỉ nhận sửa P0/P1.

---

## 1. Migration chain — đầy đủ, theo thứ tự

| Revision | Nội dung | Ngày |
|---|---|---|
| `20260825_daily_tickets` | Baseline ban đầu | Trước dự án hiện tại |
| `20260828_profiles_baseline` | Baseline `profiles` | Trước dự án hiện tại |
| `20260829_add_missing_fk_indexes` | Thêm index FK còn thiếu | Trước dự án hiện tại |
| `20260829_auth_trigger_default_role` | Trigger `on_auth_user_created` | Trước dự án hiện tại |
| `20260830_uuid_cutover` | Cutover toàn bộ sang UUID (DROP + tạo lại 10 bảng nghiệp vụ) | T0 |
| `20260831_rls_policies_v1` | RLS v1 cho 10 bảng UUID | T3 |
| `20260901_add_locations_code` | Thêm cột `code` unique cho `locations` (phục vụ seed idempotent) | T4 |
| `20260901_rls_alembic_version` | Bật RLS bảng `alembic_version` | T4 (song song, Nhã) |
| `20260901_merge_heads` | Gộp 2 head phân nhánh (`add_locations_code` × `rls_alembic_version`) | T5 |
| `20260902_gps_logs_v1` | Bảng `gps_logs` + index + RLS deny-all + retention `pg_cron` 48h | T5 |
| `20260903_fix_missing_uuid_defaults` | Fix thiếu `gen_random_uuid()` default trên 9 bảng | T6 |
| `20260903_rls_legacy_users` | RLS deny-all cho bảng `users` legacy | T6 |
| `20260903_revoke_excess_grants` | Revoke GRANT mặc định quá rộng (`anon`/`authenticated`) trên bảng deny-all | T6 |
| `20260904_fix_profiles_role_escalation` | **Fix critical:** chặn leo thang quyền qua `profiles.role` (REVOKE ALL + trigger) | T7 |

**Head cuối cùng:** `20260904_fix_profiles_role_escalation`

Chạy từ đầu (fresh-install, đã verify nhiều lần ở T6/T7/T8):
```bash
alembic upgrade head
```

## 2. Schema tổng quan — 12 bảng

| Bảng | RLS | Ghi chú |
|---|---|---|
| `profiles` | Có policy (select/update own, chặn đổi `role` bằng trigger) | `id` = `auth.users.id` qua trigger, không tự sinh |
| `tickets` | Có policy (select own) | Write qua backend transaction |
| `routes` | Có policy (select nếu có ticket assigned hoặc là driver xe đó) | |
| `route_stops` | Có policy (theo route) | |
| `locations` | Có policy (select all) | Cột `code` unique, dùng cho seed |
| `vehicles` | Có policy (select own driver + admin) | |
| `incidents` | Có policy (select/insert own driver) | |
| `bookings` | Deny-all (RLS bật, 0 policy, GRANT đã revoke) | Legacy ngoài MVP |
| `route_jobs` | Deny-all | Chỉ backend/worker dùng |
| `idempotency_keys` | Deny-all | Chỉ backend/worker dùng |
| `gps_logs` | Deny-all | Ghi qua API, retention 48h qua `pg_cron` |
| `users` (legacy) | Deny-all | Chờ xác nhận từ Khánh/Lợi để `DROP TABLE` dứt điểm |

## 3. Seed script — bản cuối cùng

File: `backend/scripts/seed_supabase.py`

```bash
export SUPABASE_URL=...
export SUPABASE_SERVICE_ROLE_KEY=...
export SEED_TEST_PASSWORD=...
python -m scripts.seed_supabase
```

Idempotent — chạy nhiều lần không tạo trùng dữ liệu. Kết quả chuẩn khi seed script tự chạy:
- 5 passenger (`student1-5@test.example.com`)
- 2 driver (`driver1-2@test.example.com`)
- 2 vehicle (upsert theo `license_plate`)
- 5 location (upsert theo `code`)

> **Lưu ý khi verify trên staging thực tế:** Query đếm role trên staging cho ra 9 passenger / 3 driver thay vì 5/2. Đối chiếu qua `JOIN auth.users` phát hiện các tài khoản dư này có **`email = NULL`** — không khớp pattern `studentN@test.example.com`/`driverN@test.example.com` mà seed script tạo ra. Xác nhận: **không phải do seed script** (chạy 2 lần vẫn ra đúng log 5+2, không insert thêm). Nhiều khả năng là tài khoản test được tạo bằng cách khác (ví dụ qua anonymous sign-in của Supabase Auth, hoặc insert thẳng vào `auth.users` không qua flow email/password chuẩn) bởi thành viên khác trong team phục vụ test tính năng riêng. Chưa xoá các tài khoản này vì chưa xác nhận có đang được dùng test dở hay không — cần team xác nhận nguồn gốc trước khi dọn dẹp.

## 4. Finding & fix quan trọng trong quá trình (T3-T7)

| # | Finding | Mức độ | Trạng thái |
|---|---|---|---|
| 1 | 9 bảng thiếu `gen_random_uuid()` default, lỗi khi ghi trực tiếp qua Supabase client | Medium | Đã fix (T6) |
| 2 | Bảng `users` legacy thiếu RLS sau fresh-install | Medium | Đã fix tạm (RLS deny-all), chờ quyết định drop hẳn |
| 3 | GRANT mặc định của Supabase cấp full CRUD cho `anon`/`authenticated` trên bảng deny-all | Medium | Đã fix (T6) |
| 4 | **Leo thang đặc quyền:** student tự đổi `profiles.role` thành `admin` qua PostgREST trực tiếp | **Critical** | Đã fix, 2 lớp phòng thủ (T7) |

## 5. Việc còn tồn đọng, bàn giao lại cho team

- Quyết định `DROP TABLE users` hay giữ RLS deny-all vĩnh viễn — chờ kết quả rà soát code cũ từ Khánh/Lợi.
- `BUG-VRPTW-01` (route_stops thiếu khi generate route) — theo dõi trạng thái fix từ Duy/Nhã, cần verify lại E2E routing sau khi fix xong.
- 3 secret từng bị lộ trong quá trình debug (DB password, `service_role` key, `CRON_SECRET`) — team đã quyết định không rotate vì đây là dự án nộp trường, không phải production.
- **Mới:** staging hiện có thêm 4 passenger + 1 driver có `email = NULL` không thuộc seed script — cần team xác nhận nguồn gốc (ai tạo, còn cần giữ không) trước khi dọn dẹp dứt điểm.

## 6. Đánh giá đối chiếu tiêu chí nghiệm thu (phần liên quan DB)

| Tiêu chí | Trạng thái |
|---|---|
| Migration chạy từ đầu không lỗi (`alembic upgrade head` trên DB trống) | ✅ Đạt |
| Sinh viên A không đọc/ghi dữ liệu B (RLS) | ✅ Đạt, verify 3 lần (T3.2, T6, T7) |
| Không secret trong repository | ✅ Đạt (`.env` không bị track) |
| Seed idempotent, seed lại không tạo trùng | ✅ Đạt |
| Chạy job cùng ngày/ca hai lần không tạo route/booking trùng | ⚠️ Phụ thuộc `BUG-VRPTW-01` — cần Duy/Nhã xác nhận riêng |
