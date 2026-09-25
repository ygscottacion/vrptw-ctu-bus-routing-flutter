# Báo cáo D13 (Ngày 13) — Lợi: Flutter Tài xế & Tích hợp Hệ thống

**Người phụ trách:** Lợi (Flutter Tài xế & QA Lead)  
**Trạng thái:** ✅ **HOÀN TẤT 100%**  
**Nhiệm vụ chính:** QR scanner, check-in idempotent, GPS foreground; dùng Map Tiles key để hiển thị xe/trạm/polyline trên nền Goong.

---

## 1. Tóm Tắt Nhiệm Vụ & Kết Quả Thực Hiện

Căn cứ theo bảng kế hoạch cập nhật dự án Ngày 4–15:

| Hạng mục nhiệm vụ D13 | Chi tiết kỹ thuật | Trạng thái | File liên quan |
| :--- | :--- | :---: | :--- |
| **1. Bản đồ Goong Map Tiles** | Tích hợp `ApiConfig.goongTileUrl` (Raster tiles với `GOONG_MAPTILES_KEY`) vào `FlutterMap`. Hiển thị đầy đủ trạm đón, polyline đường bộ thực tế màu cam và icon xe buýt thời gian thực. | ✅ **ĐẠT** | [driver_map_tab.dart](file:///d:/NCKH/Pro_10days/vrptw-ctu-bus-routing-flutter/lib/features/driver/driver_map_tab.dart) |
| **2. QR Scanner & Check-in Idempotent** | Giao diện máy quét mã QR với Viewfinder laser animation; cơ chế chặn quét trùng 2 lớp (Client: `_scannedTickets` local Set; Backend: FastAPI `/tickets/verify-qr` chặn vé `USED`). | ✅ **ĐẠT** | [driver_qr_tab.dart](file:///d:/NCKH/Pro_10days/vrptw-ctu-bus-routing-flutter/lib/features/driver/driver_qr_tab.dart)<br>[tickets.py](file:///d:/NCKH/Pro_10days/vrptw-ctu-bus-routing-flutter/backend/app/api/v1/endpoints/tickets.py) |
| **3. GPS Foreground & Đồng bộ chuyến** | Quản lý phát GPS định kỳ 15s/lần qua `GpsService`. Tự động kích hoạt phát tọa độ khi tài xế bấm "Bắt đầu chuyến" và tự động ngắt thu hồi tài nguyên khi "Kết thúc chuyến". | ✅ **ĐẠT** | [driver_map_tab.dart](file:///d:/NCKH/Pro_10days/vrptw-ctu-bus-routing-flutter/lib/features/driver/driver_map_tab.dart)<br>[driver_home_tab.dart](file:///d:/NCKH/Pro_10days/vrptw-ctu-bus-routing-flutter/lib/features/driver/driver_home_tab.dart)<br>[gps_service.dart](file:///d:/NCKH/Pro_10days/vrptw-ctu-bus-routing-flutter/lib/services/gps_service.dart) |

---

## 2. Chi Tiết Triển Khai Kỹ Thuật

### A. Hiển thị Map Tiles Goong (`driver_map_tab.dart`)
- **Map Provider:** Sử dụng URL template chuẩn Goong:
  ```dart
  TileLayer(
    urlTemplate: ApiConfig.goongTileUrl, // https://tiles.goong.io/assets/tiles/{z}/{x}/{y}.png?api_key=...
    userAgentPackageName: 'com.ctu.myctubus',
  )
  ```
- **Lộ trình thực tế (Polyline):** Sử dụng `RoutingService` truy xuất polyline theo định tuyến Goong Direction, vẽ 2 lớp (lớp viền trắng tương phản và lớp lõi cam `#FF5D3D` rộng 4.5px).
- **Vị trí xe buýt thời gian thực:** Lắng nghe trực tiếp `GpsService().positionStream` để cập nhật icon xe buýt màu xanh teal ngay trên nền bản đồ Goong.

### B. Cơ chế Điểm danh & Chống Quét Lặp (Idempotent Check-in)
1. **Lớp 1 (Phía Flutter Client):**
   - Bộ nhớ `Set<String> _scannedTickets` ghi nhận các mã vé đã quét trong ca làm việc.
   - Khi quét lặp mã vé đã điểm danh, app ngay lập tức hiển thị cảnh báo `CẢNH BÁO: VÉ ĐÃ SỬ DỤNG` kèm thời gian quét trước đó mà không gửi thêm request thừa lên server.
   - Cung cấp nút `Xóa bộ nhớ quét` để tài xế chủ động làm mới khi cần.
2. **Lớp 2 (Phía Backend API `/api/v1/tickets/verify-qr`):**
   - Kiểm tra trạng thái vé trong cơ sở dữ liệu Supabase:
     ```python
     if ticket.status == TicketStatus.USED:
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail="Vé này đã được điểm danh trước đó.",
         )
     ```
   - Chuyển trạng thái vé sang `USED`, trả về đầy đủ thông tin: họ tên sinh viên, mã số sinh viên, mã tuyến xe.

### C. Quản lý Vòng đời GPS Foreground
- Đã cấu hình đầy đủ quyền trong `AndroidManifest.xml`:
  - `android.permission.FOREGROUND_SERVICE`
  - `android.permission.FOREGROUND_SERVICE_LOCATION`
  - `android.permission.ACCESS_FINE_LOCATION`
- Đã đồng bộ sự kiện bắt đầu / kết thúc chuyến:
  - Khi tài xế xác nhận **Bắt đầu chuyến**: Gọi `widget.api.startRoute(routeId)` đồng thời khởi động `GpsService().startTracking(routeId: routeId, api: widget.api)` (chu kỳ 15 giây/lần).
  - Khi tài xế xác nhận **Kết thúc chuyến**: Gọi `widget.api.endRoute(routeId)` đồng thời dừng `GpsService().stopTracking()`.
  - Tab Home tự động nhận biết trạng thái `GpsService().isTracking` để hiển thị nút trạng thái ca làm việc nhất quán.

---

## 3. Sẵn Sàng Cho Nhiệm Vụ Tiếp Theo (Ngày 14)

Sau khi hoàn tất Ngày 13:
- Tài xế đã có đầy đủ công cụ để vận hành thực tế (bản đồ Goong, bộ quét QR soát vé idempotent, phát GPS live).
- Sẵn sàng phối hợp cùng **Duy** và **Khánh** thực hiện **Ngày 14: Chạy 10 benchmark (baseline vs Tabu, số xe, tổng km, tổng ETA, trạm lỗi, request Goong, cache hit/miss và lỗi fallback)**.
