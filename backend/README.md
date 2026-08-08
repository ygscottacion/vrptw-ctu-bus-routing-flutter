# CTU Bus Routing - Backend API

Dự án Backend sử dụng **FastAPI**, **PostgreSQL**, **SQLAlchemy** & **Alembic**.

## 🛠️ Hướng Dẫn Khởi Chạy Nhanh Cho Thành Viên

### Cách 1: Sử dụng Docker Compose (Khuyên dùng)
```bash
cd backend
docker-compose up -d --build
```
Truy cập Swagger Documentation tại: `http://localhost:8000/docs`

---

### Cách 2: Khởi Chạy Local (Python Virtual Environment)

1. **Khởi tạo môi trường ảo Python:**
   ```bash
   cd backend
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

2. **Cài đặt dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình môi trường:**
   Tạo file `.env` từ `.env.example` và điều chỉnh thông tin kết nối PostgreSQL.

4. **Chạy Migration CSDL (Alembic):**
   ```bash
   alembic revision --autogenerate -m "Initial users table"
   alembic upgrade head
   ```

5. **Chạy Server Uvicorn:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

## 🔑 Authentication Endpoints
- `POST /api/v1/auth/register`: Đăng ký tài khoản mới (Admin / Driver / Passenger)
- `POST /api/v1/auth/login`: Đăng nhập lấy Bearer Token (OAuth2 Form)
- `POST /api/v1/auth/login/json`: Đăng nhập lấy Bearer Token (JSON Body cho Mobile App)
- `GET /api/v1/auth/me`: Lấy thông tin user hiện tại (Yêu cầu Header `Authorization: Bearer <token>`)
