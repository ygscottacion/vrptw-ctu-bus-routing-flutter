# 📱 Hướng Dẫn Tích Hợp API Backend Cho Mobile App (Flutter)

Tài liệu này hướng dẫn chi tiết cách ứng dụng Mobile (Flutter) kết nối, đăng nhập và sử dụng các dịch vụ của **CTU Bus Routing Backend System (VRPTW)**.

---

## 🛠️ 1. Thông Tin Chung

* **Base URL (Local/Emulator)**:
  * **Android Emulator**: `http://10.0.2.2:8000/api/v1`
  * **iOS Simulator / Web**: `http://localhost:8000/api/v1`
  * **Thiết bị thật (Cùng Wi-Fi)**: `http://<IP_MAY_TINH>:8000/api/v1`
* **Swagger UI Documentation**: `http://localhost:8000/docs`
* **Format Dữ Liệu**: `application/json`
* **Authentication Header**: `Authorization: Bearer <access_token>`

---

## 🔑 2. Tài Khoản Thử Nghiệm (Test Accounts)

Dữ liệu giả lập sẵn sau khi chạy `python seed_data.py`:

| Username | Password | Vai trò (Role) | Họ và tên | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `admin123` | `admin` | Quản trị viên CTU | Quyền tạo trạm, xe, tạo lộ trình |
| `driver1` | `driver123` | `driver` | Tài xế Nguyễn Văn A | Phụ trách xe `65B-012.34` |
| `driver2` | `driver123` | `driver` | Tài xế Trần Văn B | Phụ trách xe `65B-056.78` |

---

## 🔐 3. Luồng Xác Thực Đăng Nhập (Authentication)

### 3.1. Đăng Nhập (`POST /auth/login`)
* **URL**: `/api/v1/auth/login`
* **Content-Type**: `application/x-www-form-urlencoded`
* **Body**:
  ```form-data
  username: admin
  password: admin123
  ```
* **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI...",
    "token_type": "bearer"
  }
  ```

### 3.2. Lấy Thông Tin Người Dùng Hiện Tại (`GET /auth/me`)
* **Header**: `Authorization: Bearer <access_token>`
* **Response (200 OK)**:
  ```json
  {
    "id": 1,
    "username": "admin",
    "full_name": "Quản trị viên CTU",
    "phone": "0901234567",
    "role": "admin"
  }
  ```

---

## 📍 4. API Trạm Dừng & Xe Buýt

### 4.1. Lấy Danh Sách Trạm Dừng (`GET /locations/`)
* **Header**: `Authorization: Bearer <token>`
* **Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "name": "Depot - ĐH Cần Thơ (Khu II)",
      "latitude": 10.0299,
      "longitude": 105.7684,
      "time_window_start": null,
      "time_window_end": null,
      "demand": 0
    },
    {
      "id": 2,
      "name": "Trạm 1 - Bến Ninh Kiều",
      "latitude": 10.0342,
      "longitude": 105.7876,
      "demand": 5
    }
  ]
  ```

### 4.2. Lấy Danh Sách Xe Buýt (`GET /vehicles/`)
* **Header**: `Authorization: Bearer <token>`
* **Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "license_plate": "65B-012.34",
      "capacity": 20,
      "driver_id": 2,
      "driver": {
        "id": 2,
        "username": "driver1",
        "full_name": "Tài xế Nguyễn Văn A"
      }
    }
  ]
  ```

---

## 🗺️ 5. Luồng Tính Toán & Xem Lộ Trình (VRPTW Routing)

### 5.1. Kích Hoạt Tính Lộ Trình (`POST /routes/generate`) - Admin Only
* **Header**: `Authorization: Bearer <admin_token>`
* **Body**:
  ```json
  {
    "date": "2026-08-15",
    "depot_location_id": 1
  }
  ```
* **Response (202 Accepted)**:
  ```json
  {
    "job_id": "8f3a12bc-...",
    "status": "pending",
    "message": "Route generation started in background..."
  }
  ```

### 5.2. Poll Trạng Thái Tính Lộ Trình (`GET /routes/generate/status/{job_id}`)
* **Header**: `Authorization: Bearer <admin_token>`
* **Response (200 OK khi hoàn thành)**:
  ```json
  {
    "job_id": "8f3a12bc-...",
    "status": "completed",
    "routes": [
      {
        "id": 10,
        "vehicle_id": 1,
        "date": "2026-08-15",
        "status": "scheduled",
        "total_distance": 14.25,
        "stops": [
          {
            "id": 1,
            "location_id": 1,
            "stop_order": 1,
            "location_name": "Depot - ĐH Cần Thơ (Khu II)",
            "latitude": 10.0299,
            "longitude": 105.7684,
            "arrival_time": "2026-08-15T07:00:00"
          }
        ]
      }
    ]
  }
  ```

### 5.3. Xem Lịch Trình Của Tài Xế (`GET /routes/driver/{driver_id}`)
* **Header**: `Authorization: Bearer <driver_token>`
* **Mô tả**: Trả về danh sách lộ trình được gán cho tài xế để hiển thị lên ứng dụng tài xế.

### 5.4. Lấy Chi Tiết Tọa Độ Vẽ Bản Đồ Polyline (`GET /routes/{route_id}`)
* **Header**: `Authorization: Bearer <token>`
* **Mô tả**: Trả về danh sách đầy đủ tọa độ `latitude`, `longitude` được sắp xếp theo thứ tự `stop_order` chuẩn để Flutter vẽ đường thẳng Polyline kết nối các điểm dừng trên Google Maps.
