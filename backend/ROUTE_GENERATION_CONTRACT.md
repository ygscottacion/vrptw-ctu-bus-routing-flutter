# Hợp Đồng Thiết Kế API & Dữ Liệu: Tác Vụ Sinh Lộ Trình (VRPTW Routing Job)
**Phiên bản:** v1.0  
**Ngày chốt:** 27/08/2026  
**Thành viên thống nhất:** Duy (Routing/Scheduler), Minh (DB/Supabase), Nhã (Backend/Cloud)

---

## 1. Bối cảnh & Nguyên tắc thiết kế
1. **Múi giờ hoạt động:** Tất cả giao dịch thời gian, giờ chạy xe, giờ đón khách và mốc chốt sổ phải tính theo múi giờ Việt Nam (`Asia/Ho_Chi_Minh`, GMT+7) và lưu dưới dạng `timestamptz` hoặc chuỗi có định dạng rõ ràng.
2. **Hạn đặt vé (Deadline):** Chỉ chấp nhận vé đặt trước **22:00** ngày hôm trước (`service_date - 1`). Mọi yêu cầu đặt/hủy sau 22:00 sẽ bị hệ thống API chặn.
3. **Idempotency & Khóa duy nhất (Unique Key):**
   - Mỗi bộ ba `(service_date, session_id, trip_type)` được xác định là một **ca chạy** (Run).
   - Chỉ được phép có **tối đa một** job sinh lộ trình ở trạng thái `pending` hoặc `processing` cho mỗi ca chạy tại một thời điểm để tránh race-conditions.
   - Khi chạy lại thuật toán, nếu đã có lộ trình hợp lệ (`completed`), cần có cơ chế hủy các lộ trình cũ và gán lại, hoặc báo lỗi tùy theo business rule. Nhằm đảm bảo an toàn MVP, job thành công rồi thì **không** được sinh trùng dữ liệu.

---

## 2. Đặc tả dữ liệu đầu vào: `DemandInput`
Đây là cấu trúc dữ liệu mà service định tuyến cần đọc để chuẩn bị dữ liệu cho thuật toán Sweep + Tabu.

```json
{
  "depot": {
    "id": "SCHOOL",
    "name": "Đại học Cần Thơ - Khu II",
    "latitude": 10.0299,
    "longitude": 105.7684
  },
  "service_date": "2026-08-28",
  "session_id": "MORNING_1",
  "trip_type": "PICKUP",
  "stations": [
    {
      "id": "1",
      "name": "Trạm 1 - Bến Ninh Kiều",
      "latitude": 10.0342,
      "longitude": 105.7876,
      "demand": 5,
      "time_window_start": "06:00",
      "time_window_end": "06:10"
    },
    {
      "id": "2",
      "name": "Trạm 2 - Cầu Đầu Sấu",
      "latitude": 10.0055,
      "longitude": 105.7578,
      "demand": 3,
      "time_window_start": "06:05",
      "time_window_end": "06:20"
    }
  ],
  "vehicles": [
    {
      "id": "1",
      "license_plate": "65B-012.34",
      "capacity": 20
    },
    {
      "id": "2",
      "license_plate": "65B-056.78",
      "capacity": 20
    }
  ]
}
```

*Ý nghĩa các trường:*
- `depot`: Điểm tập kết / trường học (điểm cuối cùng của `PICKUP` hoặc điểm xuất phát của `DROPOFF`).
- `stations`: Danh sách các trạm dừng mà sinh viên đăng ký có vé chưa gán trong ca này.
  - `demand`: Tổng số lượng vé đã chốt đón/trả ở trạm này trong ca tương ứng.
  - `time_window_start` / `time_window_end`: Khung thời gian yêu cầu phục vụ trạm (Định dạng: `HH:MM`).
- `vehicles`: Danh sách xe khả dụng trong hệ thống để thực hiện định tuyến.

---

## 3. Đặc tả dữ liệu đầu ra: `RouteOutput`
Đây là cấu trúc dữ liệu thuật toán Routing trả về cho Backend để lưu vào database (bảng `routes` và `route_stops`).

```json
[
  {
    "vehicle_id": "1",
    "total_distance_km": 12.45,
    "total_demand": 8,
    "ordered_stops": [
      {
        "id": "1",
        "name": "Trạm 1 - Bến Ninh Kiều",
        "stop_order": 1,
        "arrival_time": "06:05",
        "departure_time": "06:07",
        "demand": 5
      },
      {
        "id": "2",
        "name": "Trạm 2 - Cầu Đầu Sấu",
        "stop_order": 2,
        "arrival_time": "06:18",
        "departure_time": "06:20",
        "demand": 3
      }
    ]
  }
]
```

*Quy tắc ghi nhận DB:*
1. Tạo một bản ghi trong `routes` cho mỗi xe: `vehicle_id`, `date = service_date`, `status = pending`, `total_distance`.
2. Tạo các bản ghi trong `route_stops` tương ứng với mảng `ordered_stops`.
3. Gán `route_id` vào các vé (`tickets`) của sinh viên có `pickup_location_id` thuộc các trạm nằm trong tuyến này, ca và ngày này.

---

## 4. Quản lý trạng thái Job: `JobStatus`
Để phục vụ việc gọi bất đồng bộ từ Flutter và Admin Dashboard, vòng đời của Job sinh lộ trình được thiết lập như sau:

### Các trạng thái:
- `pending`: Tác vụ đã được ghi nhận và đưa vào hàng đợi chạy nền.
- `processing`: Thuật toán Sweep + Tabu Search đang tính toán lộ trình tối ưu.
- `completed`: Hoàn tất định tuyến, kết quả đã ghi vào DB.
- `failed`: Xảy ra lỗi trong lúc xử lý thuật toán hoặc ghi DB.

### Cơ cấu bảng `route_jobs` đề xuất (cho Minh thiết kế DB):
- `id` (UUID, PK)
- `service_date` (Date, Not Null)
- `session_id` (Varchar, Not Null)
- `trip_type` (Varchar, Not Null)
- `status` (Enum/Varchar, Default: `pending`)
- `error_message` (Text, Nullable)
- `created_at` (DateTime, Default: UTC/Asia_Ho_Chi_Minh)
- `updated_at` (DateTime)

**Ràng buộc duy nhất (Unique Constraint):**
Bảng `route_jobs` có chỉ mục duy nhất:
`UNIQUE (service_date, session_id, trip_type)`
*Lưu ý:* Nếu chạy lại (re-run) khi job trước đó đã `failed`, hệ thống có thể cập nhật trạng thái dòng cũ hoặc xóa dòng cũ đi để tạo dòng mới, đảm bảo tại một thời điểm chỉ có 1 job cho ca đó.
