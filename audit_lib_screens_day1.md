# Audit UI — Ngày 1 (Thành viên 4 – Flutter sinh viên)

> Mục đích: ghi lại hiện trạng từng màn hình so với yêu cầu kiến trúc MVP, làm căn cứ sửa ở các ngày tiếp theo. Đây là audit — chưa sửa code.

---

## 1. `screens/settings_screen.dart` (Đăng nhập/Cài đặt)

- Dialog dùng username/password mẫu (`admin/admin123`, `driver1/driver123`), gọi `ApiService.login()` cũ.
- **Vi phạm yêu cầu bắt buộc #2**: cần thay bằng Supabase email/password, bỏ hoàn toàn JWT nội bộ.
- Chưa có loading/error state rõ ràng trong bản gốc (đã bổ sung ở bản sửa Ngày 2, chưa merge).
- Nút Đăng nhập/Đăng xuất gắn trực tiếp trong trang Cài đặt — team đã chốt **bắt buộc đăng nhập ngay khi mở app**, nên luồng này cần chuyển thành màn `LoginScreen` riêng, `SettingsScreen` chỉ còn hiển thị thông tin + đăng xuất.

## 2. `screens/home_screen.dart` (Trang chủ sinh viên)

- `double _balance = 500000;` — biến local giả, có comment `// test/demo state only`.
- Nạp/Rút tiền chỉ `setState`, không có ledger/transaction thật, mất khi thoát app.
- CTA "Đặt Tuyến Xe" và "Mua vé": `onTap: () {}` — **rỗng, chưa điều hướng đi đâu**.
- Avatar góc phải: `onTap` có comment "Navigate to Settings" nhưng chưa code thật.
- Số liệu CO2/cây xanh: dữ liệu trang trí, không phải nghiệp vụ — không ưu tiên sửa.
- Chưa nhận `user` qua constructor — cần sửa khi có `AppState`.

## 3. `screens/ticket_screen.dart` (Đặt vé / Vé của tôi)

- Đã gọi API thật (`fetchLocations`, `fetchMyTickets`, `bookTicket`) — tốt hơn kỳ vọng ban đầu.
- **Thiếu bước chọn ngày chạy**: `_serviceDate` hardcode `DateTime.now() + 1 ngày`, không cho user chọn.
- Ca chạy (`_sessionId`) hardcode cứng 4 giá trị + giờ cố định, không lấy từ backend.
- Giá vé: mọi trạm đều `7000đ` hardcode, không phải giá thật.
- Trạng thái vé chỉ có 2 mức (`active`/không) — thiếu state machine đầy đủ `reserved → assigned → checked_in/expired/cancelled` theo yêu cầu MVP.
- QR hiển thị ngay khi `active == true`, chưa phân biệt đã được `assigned` tuyến/xe hay chưa.
- Deadline 22:00 chỉ là dòng text tĩnh, không kiểm tra thời gian thật.

## 4. `screens/map_screen.dart` (Bản đồ sinh viên)

- **Vi phạm nghiêm trọng yêu cầu MVP**: xe di chuyển bằng `Timer.periodic` giả lập liên tục, không dựa trên dữ liệu thật. MVP yêu cầu polling API 15 giây khi có chuyến đang chạy, và không hiển thị xe giả khi không có chuyến.
- Trạm dừng: có cố gắng load từ `fetchLocations()`, fallback về danh sách 8 trạm hardcode khi lỗi/rỗng.
- Panel "Tuyến đang chọn" phía dưới dùng `_routeInfo` hoàn toàn tĩnh (giờ, tên trạm), không liên quan gì đến dữ liệu trạm thật hiển thị trên bản đồ — 2 nguồn dữ liệu không khớp.
- Filter tuyến 1/2/3 hardcode cứng, gán trạm vào tuyến thủ công qua field `routes: [1,2,3]`.
- Không có state "chưa có chuyến đang chạy" — bus marker luôn hiển thị và luôn chạy.
- Tự khởi tạo `ApiService()` riêng thay vì nhận qua constructor — không đồng nhất với các màn khác.

## 5. `screens/driver_shell.dart` + `features/driver/*` (App tài xế) — *thuộc TV5, không phải phạm vi sửa của TV4*

- Nhãn tab tiếng Anh/Việt lẫn lộn: `'Trang chủ'` (Việt) nhưng `'Route'`, `'Scan'`, `'Alerts'`, `'Profile'` (Anh) — đúng như audit ban đầu ghi nhận.
- Dùng `withOpacity` cũ (deprecated) thay vì `withValues(alpha:)` như các file khác — không đồng nhất style.
- Nội dung 5 tab con (`driver_home_tab`, `driver_map_tab`, `driver_qr_tab`, `driver_alerts_tab`, `driver_profile_tab`) chưa audit — ngoài phạm vi TV4, ghi nhận để tránh trùng việc khi TV5 code.

## 6. `screens/notification_screen.dart` (Thông báo)

- Hoàn toàn mock — 5 thông báo hardcode, đánh dấu đã đọc chỉ đổi state local.
- Đúng phạm vi: "push notification" nằm trong danh sách **không nhận trong 10 ngày MVP** (ảnh 4) — **không cần sửa**, giữ nguyên mock.

## 7. `services/api_service.dart` — ⚠️ Phát hiện quan trọng nhất

- `login()` vẫn gọi `/auth/login` (form-urlencoded username/password), tự quản lý `_authToken` nội bộ — **vi phạm trực tiếp yêu cầu bắt buộc #2**.
- **Lỗ hổng tích hợp nghiêm trọng**: mọi hàm gọi API nghiệp vụ (`fetchLocations`, `bookTicket`, `fetchMyTickets`, `verifyTicket`, `startRoute`, v.v.) đều dùng `Authorization: Bearer $_authToken`, nhưng `_authToken` **chỉ được set bên trong `login()` cũ**.
  → Nếu chuyển sang Supabase Auth mà không sửa `ApiService`, `_authToken` sẽ luôn `null` → **toàn bộ request nghiệp vụ bị 401**.
- **Việc bắt buộc phải làm ở Ngày 2**: sửa `ApiService` để lấy token từ `AuthRepository.currentAccessToken` (Supabase) thay vì `_authToken` nội bộ — nên inject `AuthRepository` qua constructor để luôn lấy token mới nhất, tránh token cũ bị stale khi hết hạn.
- Các hàm còn lại (`fetchLocations`, `bookTicket`, `verifyTicket`, `startRoute`...) có cấu trúc REST rõ ràng, xử lý lỗi ổn — không có vấn đề về chất lượng code, chỉ vấn đề nguồn token.

---

## Tổng kết ưu tiên xử lý (không theo thứ tự ngày, chỉ để tham khảo mức độ nghiêm trọng)

1. 🔴 **`api_service.dart`**: nối token với Supabase — nếu không sửa, mọi tính năng gọi API sẽ gãy ngay khi chuyển sang Supabase Auth.
2. 🔴 **`map_screen.dart`**: bỏ xe giả `Timer.periodic`, vi phạm trực tiếp yêu cầu MVP.
3. 🟡 **`ticket_screen.dart`**: thêm bước chọn ngày chạy, state machine vé đầy đủ, kiểm tra deadline 22:00 thật.
4. 🟡 **`settings_screen.dart`**: đổi sang Supabase Auth, tách `LoginScreen` riêng do team chốt bắt buộc đăng nhập.
5. 🟢 **`home_screen.dart`**: nối CTA điều hướng, ví thật (có thể làm sau khi backend ví sẵn sàng).
6. ⚪ **`notification_screen.dart`**: không cần sửa trong 10 ngày MVP.
7. ⚪ **`driver_shell.dart`**: thuộc TV5, chỉ ghi nhận tham khảo.