# Hợp đồng Xác thực Supabase Auth & Phân quyền (Auth & Identity Contract)

**Cập nhật:** Ngày 2 (T2) — Nhã (Leader / Backend & Cloud)  
**Đối tượng áp dụng:** Backend (FastAPI), Database (Supabase/PostgreSQL), Mobile (Flutter Sinh viên & Tài xế).

---

## 1. Nguyên tắc Định danh Duy nhất (Single Identity Source)
- **Chuẩn định danh:** `auth.users.id` (Supabase Auth UUID) = `public.profiles.id` (UUID).
- **Phân quyền (`profiles.role`):** Chỉ chấp nhận 3 giá trị chuẩn enum:
  - `admin`
  - `driver`
  - `passenger` *(tương ứng với sinh viên / hành khách; không dùng từ `student` trong DB enum)*.
- **Access Token:** Sử dụng JWT do Supabase cấp chứa claim `sub` chính là UUID của user. Backend FastAPI **không** dùng `username` làm định danh duy nhất.
- **Cơ chế gọi API:** Flutter SDK đăng nhập trực tiếp qua Supabase Client (`Supabase.instance.client.auth.signInWithPassword`), sau đó truyền `access_token` vào Header của mọi request gửi tới FastAPI:
  ```http
  Authorization: Bearer <supabase_access_token>
  ```
- **Xác thực tại FastAPI:** FastAPI giải mã JWT qua JWKS / Supabase JWT Secret, kiểm tra `iss`, `aud == "authenticated"`, `exp`, và tra cứu `public.profiles` theo `id = sub`.
- **API nhận diện cá nhân:** `GET /api/v1/auth/me` trả về `ProfileResponse` (chứa `id` UUID, `role`, `full_name`, `phone`, `email`).

---

## 2. Lộ trình Chuyển đổi Foreign Key các Bảng Nghiệp vụ (Ngày 3)
Các bảng nghiệp vụ sẽ lần lượt được migration sang `profile_id` UUID thay vì tham chiếu tới `users.id` (integer) cũ:
1. `tickets` & `bookings`: chuyển `user_id` (int) → `profile_id` (UUID references `profiles.id`).
2. `incidents` & `vehicles`: chuyển `driver_id` (int) → `driver_profile_id` (UUID references `profiles.id`).
3. `routes` & `route_stops`: nâng cấp truy vấn ownership & phân công tài xế theo `driver_profile_id` UUID.

---

## 3. Danh mục Dependency cần Minh (DB Specialist) xác nhận cho Staging
1. ✅ Migration `profiles` baseline đã được áp dụng trên Supabase Staging.
2. ✅ Trigger tự động khởi tạo `profile` mặc định với role `passenger` khi có tài khoản mới đăng ký qua Supabase Auth.
3. 🔄 Chuẩn bị tài khoản test trên Staging cho 3 role: `passenger`, `driver`, `admin`.
4. 🔄 Kế hoạch migration cột `user_id` / `driver_id` legacy cho mốc Ngày 3.
