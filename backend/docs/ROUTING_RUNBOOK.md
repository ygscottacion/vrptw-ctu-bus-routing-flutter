# ROUTING & SCHEDULER OPERATIONAL RUNBOOK (MVP)

> **Phụ trách Subsystem**: Duy (Routing/Scheduler Engineer)  
> **Phiên bản**: MVP v1.0  
> **Cập nhật gần nhất**: T9-T10 (Thực nghiệm & Hướng dẫn Vận hành)

---

## 1. Cách Trigger Job Thủ Công (Manual Job Trigger)

Hệ thống phân tuyến thường được kích hoạt tự động theo lịch (Cron Job). Tuy nhiên, khi cần chạy lại hoặc kiểm thử thủ công, quản trị viên có thể gửi yêu cầu HTTP POST tới API Backend.

### 1.1 HTTP Endpoint & Security Header

- **Endpoint**: `POST /api/v1/routing/jobs/generate`
- **Authentication**: Yêu cầu Secret Key trong Header để đảm bảo an toàn.
  - Header Key: `X-Cron-Secret`
  - Header Value: Cấu hình trong file `.env` của Backend (`CRON_SECRET` value).

### 1.2 Request Body Format

```json
{
  "service_date": "2026-09-08",
  "session_id": "MORNING_1",
  "trip_type": "pickup",
  "depot_location_id": "00000000-0000-0000-0000-000000000000"
}
```

- `service_date`: Ngày thực hiện chuyến xe (`YYYY-MM-DD`).
- `session_id`: Ca chạy (`MORNING_1`, `MORNING_2`, `NOON_1`, `NOON_2`).
- `trip_type`: Loại chuyến (`pickup` - đón đi học, `dropoff` - trả về nhà).
- `depot_location_id` *(Optional)*: UUID của điểm tập kết/trường ĐH Cần Thơ (nếu không truyền sẽ dùng Depot mặc định).

### 1.3 Lệnh Mẫu (cURL & PowerShell)

#### cURL (Linux / macOS / Git Bash)
```bash
curl -X POST "http://localhost:8000/api/v1/routing/jobs/generate" \
  -H "Content-Type: application/json" \
  -H "X-Cron-Secret: YOUR_CRON_SECRET_HERE" \
  -d '{
    "service_date": "2026-09-08",
    "session_id": "MORNING_1",
    "trip_type": "pickup"
  }'
```

#### PowerShell (Windows)
```powershell
$headers = @{
    "Content-Type"  = "application/json"
    "X-Cron-Secret" = "YOUR_CRON_SECRET_HERE"
}
$body = @{
    service_date = "2026-09-08"
    session_id   = "MORNING_1"
    trip_type    = "pickup"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/routing/jobs/generate" -Method POST -Headers $headers -Body $body
```

---

## 2. Cách Kiểm Tra Trạng Thái Job (Job Monitoring)

### 2.1 Trạng thái của `RouteJob`

Mỗi lượt phân tuyến tạo ra một bản ghi trong bảng `route_jobs`. Trạng thái job bao gồm:

| Trạng thái (`status`) | Ý nghĩa | Hành động khuyến nghị |
| :--- | :--- | :--- |
| `QUEUED` | Job vừa được khởi tạo, đang chờ worker tiếp nhận. | Chờ worker xử lý (thường < 1 giây). |
| `RUNNING` | Worker đang thực thi Sweep & Tabu Search optimization. | Đang tính toán (thường từ 1 đến 30 giây). |
| `SUCCEEDED` | Phân tuyến thành công! Các `Route`, `RouteStop` đã được lưu, vé chuyển sang `ASSIGNED`. | Xem kết quả trên giao diện Admin / App. |
| `FAILED` | Job thất bại do vi phạm ràng buộc dữ liệu hoặc lỗi hệ thống. | Đọc `error_message` để xử lý sự cố. |

### 2.2 Query Kiểm Tra Trạng Thái (SQL)

```sql
SELECT id, service_date, session_id, trip_type, status, error_message, created_at, updated_at
FROM route_jobs
WHERE service_date = '2026-09-08'
  AND session_id = 'MORNING_1'
  AND trip_type = 'pickup'
ORDER BY created_at DESC
LIMIT 1;
```

---

## 3. Cách Debug & Xử Lý Khi Job FAILED

Khi `RouteJob` có trạng thái `FAILED`, cột `error_message` sẽ chứa thông báo có định dạng chuẩn: `[ERROR_CODE] Thông báo chi tiết`.

### 3.1 Bảng Mã Lỗi Đã Biết & Cách Xử Lý

| Mã lỗi (`ERROR_CODE`) | Nguyên nhân | Hướng khắc phục |
| :--- | :--- | :--- |
| `[MVP_DATA_LIMIT_EXCEEDED]` | Số lượng booking (>100 vé), trạm (>100 trạm), hoặc xe (>20 xe) vượt quá giới hạn MVP. | Giảm số lượng booking trong ca hoặc chia thành nhiều ca chạy khác nhau. |
| `[CAPACITY_EXCEEDED]` | Tổng số sinh viên đặt vé trong ca lớn hơn tổng sức chứa (capacity) của tất cả xe buýt khả dụng. | Bổ sung thêm xe buýt / tài xế vào hệ thống cho ca chạy đó. |
| `[NO_VEHICLE_AVAILABLE]` | Không tìm thấy xe buýt nào ở trạng thái sẵn sàng trong hệ thống. | Kiểm tra bảng `vehicles` và đảm bảo xe đã được gán tài xế. |
| `[NO_RESERVED_TICKETS]` | Không có vé nào ở trạng thái `RESERVED` cho ngày và ca chạy này. | Xác nhận lại sinh viên đã đặt vé thành công trước khi chạy job. |
| `[INFEASIBLE_ROUTE]` | Tất cả trạm đón đều nằm ngoài bán kính phục vụ (10km) hoặc vượt quá thời gian di chuyển tối đa (45 phút). | Kiểm tra tọa độ trạm đón của sinh viên so với Depot ĐH Cần Thơ. |
| `[SOLVER_ERROR]` | Thuật toán VRPTW không tìm thấy lời giải khả thi thỏa mãn các ràng buộc time window. | Kiểm tra khung giờ đón (time window) của các trạm đón có quá hẹp không. |

---

## 4. Giới Hạn Đã Biết (MVP Known Limits)

Dựa trên kết quả thực nghiệm T9 và các thông số thiết kế MVP T8:

1. **Giới hạn quy mô dữ liệu**:
   - **Tối đa 100 vé đặt (bookings)** cho mỗi lượt chạy job.
   - **Tối đa 100 trạm đón (stops)**.
   - **Tối đa 20 xe buýt (vehicles)**.
2. **Không tái tối ưu động sau khi Job SUCCEEDED**:
   - Nếu sinh viên hủy vé sau khi job đã hoàn tất (`SUCCEEDED`), tuyến xe hiện tại không tự động điều chỉnh. Để tái phân tuyến, quản trị viên cần trigger lại job thủ công cho ca đó.
3. **Mô hình tính khoảng cách OSRM Fallback**:
   - Mặc định hệ thống gọi OSRM API (thời gian chờ 3 giây). Nếu OSRM không phản hồi hoặc offline, hệ thống tự động chuyển sang **Static Matrix (Haversine)**. Khoảng cách Haversine là khoảng cách đường chim bay kết hợp hệ số vận tốc trung bình (25-30 km/h), nên quãng đường thực tế có thể chênh lệch 10-15%.
4. **Đặc điểm phân cụm Sweep theo góc cực**:
   - Các trạm ở rất xa trung tâm (ví dụ: Phong Điền ~15-20km) nếu nằm cùng hướng góc cực với các trạm nội ô sẽ được gom chung tuyến. Điều này có thể khiến quãng đường tuyến đó dài hơn (~25-30km), tuy nhiên vẫn nằm trong giới hạn thời gian di chuyển tối đa (45 phút).

---

## 5. Liên Hệ Hỗ Trợ Sự Cố (Incident Support)

Khi gặp sự cố phân tuyến nghiêm trọng không thể tự khắc phục theo Runbook:

- **Người phụ trách Routing / Scheduler Subsystem**: Duy (Routing/Scheduler Engineer)
- **Kênh hỗ trợ internal**: Discord / Zalo nhóm kỹ thuật VRPTW CTU
- **Tài liệu tham khảo liên quan**:
  - `backend/ROUTE_GENERATION_CONTRACT.md` — Hợp đồng dữ liệu phân tuyến
  - `backend/scripts/experiment_day9_realistic_run.py` — Script thực nghiệm phân tuyến thực tế
