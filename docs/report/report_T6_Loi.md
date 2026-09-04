# Báo cáo T6 (Ngày 6) — Lợi, Flutter Tài xế & QA

**Trạng thái: Hoàn tất 100% nhiệm vụ E2E Vòng 1.**

---

## 1. Kết quả Kiểm thử E2E Vòng 1 trên Thiết bị thật / Emulator

Đã thực hiện kiểm thử toàn diện quy trình nghiệp vụ thực tế với dữ liệu seed Supabase UUID từ Minh và Backend Candidate từ Nhã & Duy:

| STT | Luồng kiểm thử (Flow) | Test Cases | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| 1 | **Xác thực Supabase Auth** | `TC_AUTH_01`, `TC_AUTH_02` | Đăng nhập tài khoản thật `driver1@ctu.edu.vn` và `passenger`, nhận JWT hợp lệ, điều hướng đúng `DriverShell` & `StudentShell`. | **PASS** |
| 2 | **Nhận tuyến & Điều phối** | `TC_DRV_01`, `TC_DRV_02` | Hiển thị Empty State khi chưa có tuyến; hiển thị đầy đủ thông tin trạm và hành khách khi có tuyến được phân công. | **PASS** |
| 3 | **Bắt đầu & Kết thúc chuyến** | `TC_DRV_03` | Hộp thoại cảnh báo `AlertDialog` xác nhận trước khi bấm; chuyển trạng thái `pending` → `in_progress` → `completed` mượt mà; hiển thị SnackBar Teal/Red. | **PASS** |
| 4 | **Quét vé QR & Chống quét lặp** | `TC_QR_01`, `TC_QR_02`, `TC_QR_03` | Quét chuỗi UUID vé thật thành công; modal xanh cho vé hợp lệ; modal đỏ cho vé sai; modal cam cảnh báo vé đã sử dụng khi quét lại lần 2. | **PASS** |
| 5 | **GPS Foreground Tracking** | `TC_GPS_01` | Khi tài xế bật ca làm việc, `GpsService` tự động lấy tọa độ thực tế từ `geolocator` và gọi API `POST /api/v1/gps/` đều đặn 15 giây/lần. | **PASS** |
| 6 | **Bảo mật & Phân quyền RLS** | `TC_SEC_01` | Dữ liệu được cô lập hoàn toàn giữa các role theo chính sách RLS deny-all của Minh. | **PASS** |

---

## 2. Ghi nhận Defect / Quan sát kiểm thử (Defect Log)

- **`DEFECT-DRV-01` (Mức độ: P2 - Normal - Đã xử lý phòng ngừa):**
  - *Hiện tượng:* Khi tài xế đi vào khu vực mất sóng 4G/GPS (hầm, vùng sâu), API POST GPS có thể timeout.
  - *Xử lý:* `GpsService` đã có cơ chế swallow error an toàn, không làm crash hoặc đơ giao diện điều hướng của tài xế. Sẽ bổ sung retry buffer ở T7 nếu cần.
- **Theo dõi `BUG-VRPTW-01`:** Phía Mobile đã sẵn sàng nhận mảng `route_stops` sau khi Duy/Nhã hoàn tất fix trên engine sinh tuyến.

---

## 3. Phản hồi Rà soát Code cũ (Mục A.6 theo yêu cầu của Minh)

Xác nhận với Minh & Nhã: **Mã nguồn phía Tài xế (Driver) và Flutter Client đã sạch 100%**:

| Module/File | Đang dùng gì (cũ) | Đã chuyển sang | Người phụ trách | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| `lib/features/driver/*` | Parse `int` ID giả lập | Toàn bộ dùng `String` (UUID Supabase) | Lợi | ✅ **Đã sạch 100%** |
| `lib/services/api_service.dart` | `int driverId, routeId` | `String (UUID)` cho toàn bộ endpoint v1 | Lợi / Khánh | ✅ **Đã sạch 100%** |
| `backend/seed_data.py` | Bảng `users` legacy | Đã chuyển sang `seed_supabase.py` | Toàn team | ✅ **Đồng ý DROP TABLE users** |

---

## 4. Kết luận nghiệm thu T6

Mã nguồn phía Flutter Tài xế và bộ Test Matrix E2E đạt chuẩn **Candidate Staging**, sẵn sàng bước vào giai đoạn **UAT & Retest Vòng 2 (T7)**.
