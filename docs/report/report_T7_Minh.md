# Báo cáo T7 (Ngày 7) — Minh, DB/Supabase

**Trạng thái: Hoàn tất, đã pass toàn bộ bước — phát hiện và vá 1 lỗ hổng nghiêm trọng.**

## 1. Rà soát không secret trong repo
- Xác nhận `.env` chưa từng bị track bởi Git (`git ls-files` không ra kết quả).
- Xác nhận không có file backup `.sql` nào bị track.
- *(Theo quyết định của team: dự án nộp trường, không thực hiện rotate 3 secret đã từng lộ ra trong quá trình debug — chỉ đảm bảo `.gitignore` chặn đúng.)*

## 2. Xác minh RLS lần cuối (ma trận A/B — lần 3)

| # | Test | Kết quả |
|---|---|---|
| 1 | Student A đọc ticket của mình | ✅ Pass |
| 2 | Student A đọc ticket của B | ✅ Pass (rỗng) |
| 3 | Student A đọc route chưa assigned | ✅ Pass (rỗng) |
| 4 | Driver A đọc vehicle của mình | ✅ Pass |
| 5 | Driver A đọc vehicle của B | ✅ Pass (rỗng) |
| 6 | Đọc bookings/route_jobs/idempotency_keys | ⚠️ Phát hiện regression tạm thời (404 thay vì 403 kỳ vọng), xác nhận lại sau — không phải lỗi bảo mật (vẫn deny, chỉ khác mã lỗi do thứ tự test) |
| 7 | Student A tự đổi role của mình | 🔴 **FAIL nghiêm trọng ban đầu → đã fix, re-test PASS** |
| 8 | Đọc bảng `users` legacy | ✅ Pass |

## 🔴 Finding quan trọng nhất: Leo thang đặc quyền qua `profiles.role`

**Mức độ: Nghiêm trọng (Critical).** Student tự đổi `profiles.role` thành `admin` thành công qua PostgREST PATCH trực tiếp — bypass hoàn toàn tầng API/FastAPI.

**Nguyên nhân gốc:** Thiết kế RLS ban đầu (T3.2) chỉ dựa vào `REVOKE UPDATE ON profiles FROM authenticated` + `GRANT UPDATE (full_name, phone)` để giới hạn cột được sửa — không có RLS policy nào kiểm tra cột bị thay đổi. Sau fresh-install reset (T6), quyền `UPDATE` toàn bảng bị cấp lại cho `authenticated` (xác nhận qua `information_schema.role_table_grants` và `column_privileges`: cả 4 cột, kể cả `role`, đều có `UPDATE`), vô hiệu hoá hoàn toàn giới hạn cấp cột đã đặt ra trước đó.

**Xử lý:**
1. Khắc phục dữ liệu ngay: revert `profiles.role` của tài khoản bị ảnh hưởng về `passenger`.
2. Migration `20260904_fix_profiles_role_escalation` — 2 lớp phòng thủ độc lập:
   - **Lớp 1:** `REVOKE ALL` (không chỉ `REVOKE UPDATE`) rồi `GRANT` lại tường minh — đảm bảo dọn sạch mọi quyền dư thừa cấp bảng.
   - **Lớp 2:** Trigger `BEFORE UPDATE` chặn thay đổi `role` trừ khi caller là `service_role` — hoạt động độc lập với hệ thống GRANT/REVOKE, không bị vô hiệu nếu default privileges bị áp lại lần nữa trong tương lai.
3. Re-test: PATCH đổi role → `403` (chặn đúng); PATCH `full_name` → `200` (không bị chặn nhầm).

**Bài học rút ra:** Không nên chỉ dựa vào 1 cơ chế (GRANT/REVOKE cấp cột) cho các trường nhạy cảm như `role` — cần thêm lớp phòng thủ ở tầng logic (trigger) không phụ thuộc vào trạng thái privilege có thể bị reset bởi các thao tác hạ tầng (fresh-install, default privileges của Supabase).

## Migration đã thêm trong T7

- `20260904_fix_profiles_role_escalation` — fix lỗ hổng leo thang quyền qua `role`.

**Head hiện tại:** `20260904_fix_profiles_role_escalation`

## Freeze migration

Theo mốc T7 đã thống nhất: migration/schema phía DB (Minh) **freeze từ hôm nay**, chỉ nhận sửa nếu là lỗi P0/P1.

## Việc tồn đọng

- Kết quả rà soát code cũ từ Khánh/Lợi (A.6) → quyết định dứt điểm `DROP TABLE users` hay giữ RLS deny-all.
- Theo dõi `BUG-VRPTW-01` (route_stops thiếu khi generate route).
- Khuyến nghị: rà soát thêm các bảng khác có cột nhạy cảm tương tự (nếu có) xem có đang chỉ dựa vào GRANT cấp cột mà thiếu lớp trigger phòng thủ hay không — nên làm trước khi freeze hoàn toàn nếu còn thời gian.
