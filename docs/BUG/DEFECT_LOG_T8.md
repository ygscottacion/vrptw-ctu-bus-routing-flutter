# Bảng Theo Dõi Lỗi (Defect Log) — Môi Trường Staging (Ngày 8)

**Tester / QA Lead:** Lợi (Thành viên 5 - Flutter Tài xế & QA)  
**Môi trường:** Staging (Render Backend + Supabase DB + Thiết bị Android thật)  
**Phạm vi:** Kiểm thử tải phối hợp 2 Tài xế + 5 Sinh viên trên thiết bị di động thật.

---

## 1. Bảng tổng hợp lỗi phát hiện & xử lý (Defect Tracking Matrix)

| Defect ID | Phân hệ | Mô tả lỗi | Mức độ | Bước tái hiện (Steps to Reproduce) | Nguyên nhân gốc | Trạng thái | Giải pháp / Phân công |
|---|---|---|---|---|---|---|---|
| **DEF-STG-01** | Flutter Driver | Khi tài xế quét QR vé của sinh viên thuộc tuyến xe khác (khác `route_id`), modal quét vẫn nhận vé hợp lệ. | **P1 (Major)** | 1. Student 1 đặt vé thuộc Tuyến B.<br>2. Driver 1 (chạy Tuyến A) dùng Tab QR quét vé Student 1. | Do hàm xác thực QR trước đây chỉ kiểm tra `ticket.status == RESERVED/ASSIGNED` mà chưa so khớp `ticket.route_id == current_route.id`. | ✅ **ĐÃ KHẮC PHỤC** | Đã cập nhật logic kiểm tra khớp `route_id` của tuyến đang chạy trong `driver_qr_tab.dart`. |
| **DEF-STG-02** | GPS Service | Khi thiết bị tài xế mất kết nối 4G trong hầm/vùng sóng yếu, app bắn uncaught exception `SocketException` trong vòng lặp Timer GPS 15s. | **P2 (Normal)** | 1. Bắt đầu ca chạy xe.<br>2. Bật chế độ máy bay hoặc ngắt kết nối mạng.<br>3. Chờ 15 giây cho timer GPS kích hoạt. | `GpsService` gọi `api.sendGpsLog()` nhưng chưa bọc `try-catch` đầy đủ quanh lệnh gọi HTTP. | ✅ **ĐÃ KHẮC PHỤC** | Bổ sung `try-catch` trong `GpsService`, ghi log cảnh báo và tiếp tục retry ở chu kỳ 15s tiếp theo mà không dừng luồng. |
| **DEF-STG-03** | UI Scaling | Trên màn hình Android cỡ nhỏ (màn hình < 5.5 inch), card danh sách trạm `DriverRouteCard` bị cảnh báo tràn 6px (Overflow RenderFlex). | **P3 (Minor)** | 1. Cài app trên máy Android kích thước nhỏ.<br>2. Mở Tab Tuyến đường có từ 5 trạm trở lên. | `Column` trong sub-widget chưa có `Flexible`/`SingleChildScrollView` cho text địa chỉ dài. | ✅ **ĐÃ KHẮC PHỤC** | Bổ sung `TextOverflow.ellipsis` và `maxLines: 1` cho nhãn địa chỉ trạm. |

---

## 2. Thống kê theo mức độ nghiêm trọng

- **P0 (Blocker):** 0 lỗi (Không có lỗi làm sập hệ thống hoặc chặn luồng chính).
- **P1 (Critical / Major):** 1 lỗi (Đã khắc phục 100%).
- **P2 (Normal):** 1 lỗi (Đã khắc phục 100%).
- **P3 (Minor / UI):** 1 lỗi (Đã khắc phục 100%).
- **Tỷ lệ đóng lỗi (Defect Resolution Rate):** **3/3 (100%)**.

---

## 3. Kết luận
Sau khi hoàn tất kiểm thử và đóng toàn bộ các defect trên, bản build Staging Candidate đáp ứng đầy đủ tiêu chí ổn định cho kịch bản chạy song song 2 xe buýt và 5 sinh viên.
