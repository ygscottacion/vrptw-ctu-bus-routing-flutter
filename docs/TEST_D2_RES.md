# BÁO CÁO KIỂM THỬ HỆ THỐNG DATABASE & TÀI KHOẢN TÍCH HỢP
**Dự án:** CTU Bus Routing System  
**Người thực hiện:** Thành viên 2 - Minh (Database, Ví Điện Tử & Supabase)  
**Trạng thái kiểm thử:** **100% PASSED (6/6 Technical Specifications)**

---

## 1. Kết Quả Kiểm Thử Kỹ Thuật (TS-DB-01 ➔ TS-DB-06)

| Mã TS | Tên Kịch Bản | Trạng Thái | Kết Quả Thực Nghiệm & Chi Tiết Đối Soát |
|---|---|---|---|
| **TS-DB-01** | Khởi tạo Dữ liệu Seed & Reset Môi trường | **PASSED** | Seed thành công 5 Sinh viên, 2 Tài xế, 1 Admin, 3 Xe buýt, 20 Trạm dừng. Migration DB ở trạng thái sạch (`3eed03f3ffda`). |
| **TS-DB-02** | Đặt vé & Trừ tiền Ví (Transaction Atomic) | **PASSED** | Đặt vé thành công, trừ đúng 7,000 VNĐ trong ví (200,000 ➔ 193,000 VNĐ), ghi nhận 1 bản ghi giao dịch `purchase` đồng bộ trong cùng transaction. |
| **TS-DB-03** | Hủy vé & Hoàn tiền Ví trước Deadline | **PASSED** | Trạng thái vé chuyển thành `cancelled`, hoàn trả chính xác 7,000 VNĐ (193,000 ➔ 200,000 VNĐ) và ghi nhận giao dịch `refund`. |
| **TS-DB-04** | Kiểm tra RLS & Cô lập Dữ liệu (Data Isolation) | **PASSED** | Row Level Security (RLS) ngăn chặn hoàn toàn Sinh viên 1 truy vấn ví và vé của Sinh viên 2 (Query trả về 0 bản ghi dưới JWT authenticated). |
| **TS-DB-05** | Ràng buộc Trùng vé (Duplicate Ticket Guard) | **PASSED** | Database chặn thành công khi chèn vé thứ 2 cho cùng một người dùng trong cùng ca chạy/ngày (`uq_tickets_user_run`). |
| **TS-DB-06** | Đối soát Toàn vẹn Dữ liệu Solver (Referential Integrity) | **PASSED** | Khóa ngoại và unique constraint (`uq_route_stops_order`) hoạt động chuẩn xác: chặn trùng thứ tự trạm dừng và đảm bảo liên kết giữa `tickets` ➔ `routes` ➔ `route_stops` ➔ `vehicles`. |

---

## 2. Thông Tin Tài Khoản & Dữ Liệu Seed (Bàn giao Team FE / BE / QA)

Tất cả tài khoản thử nghiệm dưới đây đã được khởi tạo sẵn trên môi trường Staging/Supabase với mật khẩu chung: **`TestPassword123!`**

### Danh sách Tài khoản Kiểm thử (Users & Wallets)

| Vai trò (Role) | Email Login | Mật khẩu | Số dư Ví khởi tạo | Mục đích sử dụng / Test Case |
|---|---|---|---|---|
| **Admin** | `admin1@test.example.com` | `TestPassword123!` | N/A | Quản trị hệ thống, giám sát tuyến đường |
| **Driver** | `driver1@test.example.com` | `TestPassword123!` | N/A | Tài xế lái xe `51F-000.01` |
| **Driver** | `driver2@test.example.com` | `TestPassword123!` | N/A | Tài xế lái xe `51F-000.02` |
| **Passenger** | `student1@test.example.com` | `TestPassword123!` | **200,000 VNĐ** | Sinh viên U1 (Dùng cho luồng Happy Path: Đặt/Hủy vé) |
| **Passenger** | `student2@test.example.com` | `TestPassword123!` | **5,000 VNĐ** | Sinh viên U2 (Test lỗi số dư không đủ mua vé 7k - USR-04) |
| **Passenger** | `student3@test.example.com` | `TestPassword123!` | **200,000 VNĐ** | Sinh viên U3 (Test luồng VRPTW Solver gom chuyến) |
| **Passenger** | `student4@test.example.com` | `TestPassword123!` | **200,000 VNĐ** | Sinh viên U4 (Test luồng VRPTW Solver gom chuyến) |
| **Passenger** | `student5@test.example.com` | `TestPassword123!` | **200,000 VNĐ** | Sinh viên U5 (Test luồng VRPTW Solver gom chuyến) |

### Danh sách Phương tiện (Vehicles)

| Biển số xe | Sức chứa | Tài xế gán mặc định | Trạng thái |
|---|---|---|---|
| `51F-000.01` | 16 chỗ | `driver1@test.example.com` | Đã gán tài xế D1 |
| `51F-000.02` | 16 chỗ | `driver2@test.example.com` | Đã gán tài xế D2 |
| `51F-000.03` | 29 chỗ | `NULL` | Xe dự phòng (Chờ gán tài xế qua Admin) |

---

## 3. Các Điểm Kỹ Thuật Cần Lưu Ý Khi Tích Hợp Backend & API

Dưới đây là các lưu ý quan trọng phát hiện được qua quá trình tự động hóa kiểm thử DB, team Backend cần chú ý khi viết API/ORM:

1. **Khấu trừ & Hoàn tiền Ví (`wallet_transactions.id`)**:
   * Cột `id` của bảng `wallet_transactions` là Primary Key nhưng chưa cài giá trị tự động `DEFAULT gen_random_uuid()`. Team Backend cần cập nhật file migration Alembic/SQL hoặc truyền `uuid4()` khi tạo record giao dịch ví trong code Python/NodeJS.
2. **Quản lý Thông tin Email người dùng**:
   * Cột `email` nằm ở bảng `auth.users` của Supabase, không nằm trực tiếp trong `public.profiles`. Để lấy thông tin người dùng kèm email, Backend cần thực hiện `JOIN public.profiles p ON p.id = auth.users.id`.
3. **Các trường bắt buộc (`NOT NULL`) khi tạo Vé (`tickets`)**:
   * Mọi câu lệnh tạo vé bắt buộc phải chứa `pickup_location_id` và mã `qr_code` (chuỗi ngẫu nhiên/hash). Thiếu 1 trong 2 trường này Database sẽ chặn giao dịch.
4. **Cấu trúc Lộ trình (`routes`)**:
   * Cột `driver_id` không nằm ở bảng `routes` mà nằm ở bảng `vehicles`. Thông tin tài xế được xác định gián tiếp qua `routes.vehicle_id ➔ vehicles.driver_id`.
   * Bảng `routes` có các trường bắt buộc (`NOT NULL`): `trip_type` (`pickup` hoặc `dropoff`) và `status` thuộc Enum `route_status`.