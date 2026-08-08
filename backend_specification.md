# Tài Liệu Đặc Tả Dự Án (Backend Specification)
**Dự án:** Hệ thống quản lý và điều phối tuyến xe buýt (CTU Bus Routing / VRPTW)

> [!NOTE]
> Tài liệu này cung cấp các đặc tả kỹ thuật chi tiết dành riêng cho đội ngũ Backend để xây dựng hệ thống định tuyến xe buýt với các ràng buộc về thời gian (VRPTW - Vehicle Routing Problem with Time Windows).

---

## 1. Tổng Quan Công Nghệ (Tech Stack)

| Thành phần | Công nghệ sử dụng | Chi tiết & Thư viện đề xuất |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (Python) | Xử lý API bất đồng bộ nhanh, tự động tạo OpenAPI docs (Swagger). |
| **Cơ sở dữ liệu (Database)** | PostgreSQL | RDBMS mạnh mẽ, hỗ trợ tốt dữ liệu không gian (PostGIS nếu cần). |
| **ORM** | SQLAlchemy | Quản lý schema, migrations (Alembic) và truy vấn CSDL. |
| **Thuật toán cốt lõi** | Sweep + Tabu Search | Giải quyết bài toán VRPTW (Nhóm cụm điểm đón bằng Sweep, tối ưu lộ trình bằng Tabu Search). |
| **Giao tiếp API** | RESTful API | Kiến trúc API tiêu chuẩn cho giao tiếp với Mobile App. |
| **Xác thực (Auth)** | JWT (JSON Web Token) | Quản lý phiên đăng nhập và phân quyền (Admin, Tài xế, Người dùng). |
| **Triển khai (Deployment)**| Docker | Container hóa ứng dụng Backend và Database (Sử dụng `docker-compose`). |

---

## 2. Kiến Trúc Hệ Thống (Architecture)

Hệ thống nên được chia theo cấu trúc **N-Tier Architecture** (hoặc Clean Architecture) trong FastAPI để dễ dàng bảo trì:

```text
backend/
├── app/
│   ├── api/          # Các Router/Endpoints của REST API
│   ├── core/         # Cấu hình hệ thống, Security, JWT, Settings
│   ├── crud/         # Các thao tác tương tác với CSDL (Create, Read, Update, Delete)
│   ├── db/           # Kết nối Database, Session maker
│   ├── models/       # Định nghĩa các Table (SQLAlchemy)
│   ├── schemas/      # Pydantic models (Data validation, Request/Response format)
│   ├── services/     # Logic nghiệp vụ phức tạp (Thuật toán Sweep, Tabu Search)
│   └── main.py       # Entry point của FastAPI
├── alembic/          # Thư mục chứa cấu hình Migration
├── requirements.txt  # Danh sách thư viện Python
└── Dockerfile        # File build image Docker
```

---

## 3. Thiết Kế Cơ Sở Dữ Liệu Cơ Bản (Database Schema)

Dưới đây là các bảng (tables) quan trọng cần có:

### 3.1. Bảng `users` (Người dùng & Tài xế)
- `id` (UUID/Int, PK)
- `username` (Varchar, Unique)
- `password_hash` (Varchar)
- `role` (Enum: `admin`, `driver`, `student/passenger`)
- `full_name` (Varchar)
- `phone` (Varchar)

### 3.2. Bảng `vehicles` (Phương tiện/Xe buýt)
- `id` (UUID/Int, PK)
- `license_plate` (Varchar, Unique) - Biển số xe
- `capacity` (Int) - Sức chứa tối đa
- `driver_id` (FK -> users.id, Nullable)

### 3.3. Bảng `locations` (Trạm dừng/Điểm đón)
- `id` (UUID/Int, PK)
- `name` (Varchar)
- `latitude` (Float)
- `longitude` (Float)
- `time_window_start` (Time/DateTime) - Thời gian phục vụ sớm nhất
- `time_window_end` (Time/DateTime) - Thời gian phục vụ trễ nhất
- `demand` (Int) - Số lượng khách dự kiến tại điểm (hỗ trợ cho sức chứa xe)

### 3.4. Bảng `routes` (Lộ trình/Chuyến đi)
- `id` (UUID/Int, PK)
- `vehicle_id` (FK -> vehicles.id)
- `date` (Date)
- `status` (Enum: `pending`, `in_progress`, `completed`)
- `total_distance` (Float)

### 3.5. Bảng `route_stops` (Chi tiết lộ trình)
- `id` (UUID/Int, PK)
- `route_id` (FK -> routes.id)
- `location_id` (FK -> locations.id)
- `arrival_time` (DateTime) - Thời gian dự kiến đến
- `stop_order` (Int) - Thứ tự trạm trong lộ trình

---

## 4. Đặc Tả Thuật Toán (Core Algorithm Service)

> [!IMPORTANT]
> Đây là trái tim của hệ thống. Team Backend cần xây dựng một Service độc lập trong thư mục `services/` để xử lý bài toán **VRPTW (Vehicle Routing Problem with Time Windows)**.

**Quy trình kết hợp Sweep + Tabu Search:**
1. **Giai đoạn 1: Gom cụm (Sweep Algorithm)**
   - Lấy tọa độ trạm xuất phát (Depot) làm tâm.
   - Quét các điểm đón (Locations) theo góc tọa độ cực.
   - Gom các điểm đón thành các cụm (clusters) sao cho tổng `demand` không vượt quá `capacity` của xe buýt.
2. **Giai đoạn 2: Tối ưu lộ trình (Tabu Search)**
   - Với mỗi cụm (một xe buýt), tạo một lộ trình khởi tạo (Initial Solution).
   - Áp dụng thuật toán Tabu Search để hoán đổi thứ tự các điểm dừng nhằm tìm ra lộ trình ngắn nhất.
   - **Ràng buộc (Constraints):**
     - Sức chứa của xe.
     - Khung thời gian (`time_window_start` đến `time_window_end` của từng trạm).
3. **Đầu ra (Output):** Trả về danh sách các xe (vehicles) cùng mảng thứ tự các điểm đến tối ưu, lưu vào CSDL bảng `routes` và `route_stops`.

---

## 5. Đặc Tả API (REST Endpoints)

FastAPI sẽ tự động tạo tài liệu Swagger tại `/docs`. Dưới đây là các nhóm API chính:

### Authentication APIs (`/api/v1/auth`)
- `POST /login`: Nhận `username` + `password`, trả về JWT `access_token`.
- `GET /me`: Lấy thông tin user hiện tại (Yêu cầu Header `Authorization: Bearer <token>`).

### Locations/Stops APIs (`/api/v1/locations`)
- `GET /`: Lấy danh sách điểm đón.
- `POST /`: Thêm điểm đón mới (dành cho Admin).

### Vehicles APIs (`/api/v1/vehicles`)
- `GET /`: Lấy danh sách xe buýt.
- `PUT /{id}/driver`: Gán tài xế cho xe.

### Routing & Algorithm APIs (`/api/v1/routes`)
- `POST /generate`: Trigger chạy thuật toán **Sweep + Tabu Search**. (Input: Ngày, danh sách trạm, danh sách xe có sẵn. Output: Bảng lộ trình phân bổ).
  > [!TIP]
  > Quá trình chạy thuật toán có thể mất thời gian. Cân nhắc sử dụng Background Tasks của FastAPI hoặc Celery nếu dữ liệu điểm đón rất lớn.
- `GET /driver/{driver_id}`: Lấy lịch trình hoạt động trong ngày của một tài xế cụ thể.
- `GET /{route_id}`: Lấy chi tiết các điểm dừng (latitude, longitude, thứ tự) để Mobile App (Flutter) vẽ lên Google Maps.

---

## 6. Yêu Cầu Về Bảo Mật (Security)
- Mật khẩu phải được hash trước khi lưu vào DB (sử dụng `PassLib` với thuật toán `bcrypt`).
- API bảo vệ bằng Dependency Injection của FastAPI (`OAuth2PasswordBearer`).
- Thiết lập CORS (Cross-Origin Resource Sharing) hợp lý để cho phép Flutter App và Web Admin (nếu có) gọi API.

---

## 7. Yêu Cầu Triển Khai (Deployment - Docker)

Team Backend cần cung cấp file `docker-compose.yml` bao gồm 2 services chính:
1. **web:** Chứa app FastAPI (sử dụng server `Uvicorn`).
2. **db:** Chứa PostgreSQL database.

**Mẫu `docker-compose.yml` cơ bản:**
```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - db

volumes:
  postgres_data:
```

## 8. Hướng dẫn các bước tiếp theo cho team Backend
1. Khởi tạo project Python, cài đặt `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `pyjwt`.
2. Định nghĩa các Model trong CSDL và chạy migration (`alembic revision --autogenerate`, `alembic upgrade head`).
3. Viết module Auth và cấu hình JWT.
4. Phát triển module Thuật toán (Sweep + Tabu Search). Đây là phần khó nhất, nên viết unit tests (`pytest`) kỹ cho module này.
5. Viết các API CRUD và API tích hợp thuật toán.
6. Build Docker và deploy.
