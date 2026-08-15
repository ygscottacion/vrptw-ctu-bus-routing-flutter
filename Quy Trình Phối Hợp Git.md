Quy Trình Phối Hợp Git & Kiểm Duyệt Demo (Workflow Rule)
Để đảm bảo thành viên không push trực tiếp code chưa qua kiểm duyệt lên main:
Nhánh main sẽ bị khóa/bảo vệ (Protected Branch).
Thành viên làm việc trên các nhánh tính năng (feature/...).
Trước khi push/merge lên main, thành viên chạy demo trực tiếp cho Leader xem.
Sau khi duyệt demo, Leader thực hiện merge/push vào main.

👥 Phân Chia Vai Trò & Nhiệm Vụ Cho 5 Thành Viên
👑 1. Người 1 - Leader (Trưởng nhóm / Core Architect & Auth & Deployment)
Trách nhiệm chính: Quản trị Repository, thiết lập khung dự án (Boilerplate), Auth (JWT), Dockerize, kiểm thử tích hợp (Integration Test) và kiểm duyệt code (Code Review/Merge).
Nhiệm vụ chi tiết:
Tuần 1: Cấu hình Repo Git, khởi tạo cấu trúc thư mục FastAPI, setup PostgreSQL & Alembic migration base, làm API Auth (/login, /me, JWT Token, bcrypt password hashing).
Tuần 2: Thiết lập docker-compose.yml (FastAPI + PostgreSQL), cấu hình CORS, hỗ trợ 2 nhóm thuật toán.
Tuần 3: Viết Middleware bảo mật, phân quyền Admin/Driver/User. Review và kiểm thử tích hợp API từ các thành viên.
Tuần 4: Tối ưu hiệu năng, deploy staging/local server, hỗ trợ team Flutter kết nối API.






📦 2. Người 2 - Thành viên Minh (Database Architecture & CRUD Data Modules)
Trách nhiệm chính: Thiết kế chi tiết Schemas, ORM Models (SQLAlchemy), Pydantic Schemas và các API CRUD dữ liệu nền tảng.
Nhiệm vụ chi tiết:
Tuần 1: Xây dựng SQLAlchemy Models (users, vehicles, locations) & Pydantic validation schemas.
Tuần 2: Xây dựng CRUD APIs cho /api/v1/locations (Lấy danh sách điểm đón, thêm điểm đón mới kèm khung giờ time_window_start/end, demand).
Tuần 3: Xây dựng CRUD APIs cho /api/v1/vehicles (Danh sách xe, gán tài xế vào xe PUT /{id}/driver). Viết script Seed Data (tạo dữ liệu giả lập ban đầu để test).
Tuần 4: Sửa lỗi API, hoàn thiện tài liệu OpenAPI/Swagger docs (/docs).


🌀 3. Người 3 - Thành viên Lợi (Algorithmic Specialist 1 - Sweep Algorithm)
Trách nhiệm chính: Xây dựng module gom cụm các điểm đón theo góc cực (Sweep Algorithm).
Nhiệm vụ chi tiết:
Tuần 1: Nghiên cứu bài toán Sweep trong không gian tọa độ (Depot làm gốc, chuyển tọa độ Lat/Long sang Polar Angles).
Tuần 2: Phát triển logic gom cụm: Quét các điểm đón theo góc cực, gom cụm đảm bảo tổng demand $\le$ capacity của xe buýt.
Tuần 3: Xử lý các điểm đón ngoại lệ (Outliers) và tối ưu thuật toán gom cụm. Viết Unit Test (pytest) riêng cho module Sweep.
Tuần 4: Tích hợp output của Sweep làm input khởi tạo (Initial Solution) cho Module Tabu Search.


🎯 4. Người 4 - Thành viên Duy (Algorithmic Specialist 2 - Tabu Search Optimizer)
Trách nhiệm chính: Tối ưu lộ trình và đảm bảo các ràng buộc thời gian (VRPTW - Vehicle Routing Problem with Time Windows).
Nhiệm vụ chi tiết:
Tuần 1: Thiết kế cấu trúc dữ liệu cho giải thuật Tabu Search (Tabu List, Neighborhood Search operations like 2-opt/Swap).
Tuần 2: Cài đặt hàm đánh giá Fitness/Cost Function (khoảng cách + thời gian chờ + hình phạt vi phạm time_window_start/end).
Tuần 3: Viết thuật toán Tabu Search hoàn chỉnh cho từng cụm xe. Viết Unit Test (pytest) đo thời gian chạy và độ tối ưu lộ trình.
Tuần 4: Tối ưu số vòng lặp và ngưỡng Tabu Tenure để thuật toán không bị kẹt ở hố tối ưu địa phương (Local Optima).


🗺️ 5. Người 5 - Thành viên Khánh (Routing APIs, Service Integration & Background Tasks)
Trách nhiệm chính: Nối thuật toán vào FastAPI Service, xây dựng các API lộ trình cho Mobile App (Flutter).
Nhiệm vụ chi tiết:
Tuần 1: Thiết kế CSDL các bảng kết quả: routes và route_stops.
Tuần 2: Xây dựng API POST /api/v1/routes/generate (Trigger gọi chuỗi kết hợp Sweep + Tabu Search, lưu kết quả lộ trình vào DB).
Tuần 3: Thêm FastAPI Background Tasks (hoặc Celery) để xử lý tính toán bất đồng bộ khi chạy thuật toán dài hạn. Xây dựng API GET /api/v1/routes/driver/{driver_id} (Xem lịch trình tài xế).
Tuần 4: Xây dựng API GET /api/v1/routes/{route_id} (Trả về danh sách tọa độ Lat/Long đã sắp xếp thứ tự chuẩn cho Flutter vẽ lên Google Maps).


📅 Lộ Trình 4 Tuần (Milestone Summary)


💻 Bộ Lệnh Git & GitHub Chi Tiết Theo Tiến Độ Dự Án
🚀 Giai Đoạn 0: Leader Khởi Tạo Repository Ban Đầu
Leader thực hiện:
```bash
# 1. Khởi tạo Git repository trong thư mục dự án backend
git init
git branch -M main
# 2. Tạo file .gitignore (bỏ qua venv, __pycache__, .env)
echo "venv/\n__pycache__/\n*.pyc\n.env\n.idea/\n.vscode/" > .gitignore
# 3. Commit ban đầu và đẩy lên GitHub
git add .
git commit -m "chore: initial FastAPI project boilerplate with specs"
git remote add origin https://github.com/username/ctu-bus-routing-backend.git
git push -u origin main


```

🔄 Giai Đoạn Hàng Tuần: Quy Trình Phát Triển Công Việc Của Thành Viên
Bước 1: Thành viên clone dự án và tạo nhánh công việc (feature)
Thành viên thực hiện tại máy cá nhân:
```bash
# Clone dự án về máy (chỉ làm lần đầu)
git clone https://github.com/username/ctu-bus-routing-backend.git
cd ctu-bus-routing-backend
# Đảm bảo đang ở code mới nhất của main
git checkout main
git pull origin main
# Tạo và chuyển sang branch công việc được giao (ví dụ: Người 2 làm module Locations)
git checkout -b feature/locations-crud
Bước 2: Thành viên code, kiểm thử và commit tại local
Thành viên thực hiện:
```bash
# Kiểm tra các file đã thay đổi
git status
# Add và commit với message rõ ràng
git add .
git commit -m "feat(locations): implement location CRUD APIs and schemas"
Bước 3: Thành viên push nhánh công việc lên GitHub (Chưa push vào main)
Thành viên thực hiện:
```bash
# Push branch cá nhân lên GitHub để lưu trữ
git push origin feature/locations-crud

🎥 Giai Đoạn Duyệt Demo & Merge Về main (Leader Duyệt)
Bước 4: Thành viên chạy demo tại máy cho Leader xem
Thành viên bật Uvicorn server (uvicorn app.main:app --reload), mở Swagger UI (http://localhost:8000/docs) và chạy pytest/demo tính năng trực tiếp cho Leader kiểm tra.
Bước 5: Leader pull branch của thành viên về kiểm tra & Merge vào main
Sau khi xem demo đạt yêu cầu, Leader thực hiện merge tại máy Leader:
```bash
# 1. Leader chuyển sang main và lấy code mới nhất
git checkout main
git pull origin main
# 2. Leader lấy branch của thành viên về (nếu cần test lại trên máy Leader)
git fetch origin feature/locations-crud
git checkout feature/locations-crud
# (Leader test thử code ở máy mình tại bước này nếu muốn)
# 3. Leader chuyển về main và Merge nhánh của thành viên vào main
git checkout main
git merge --no-ff feature/locations-crud -m "merge: accept feature/locations-crud from Member A"
# 4. Leader push kết quả chính thức lên main
git push origin main
# 5. (Tùy chọn) Leader xóa branch tính năng trên remote sau khi đã merge thành công
git push origin --delete feature/locations-crud

```

🔁 Bước 6: Các Thành Viên Cập Nhật Code Mới Từ main Về Nhánh Cá Nhân
Sau khi Leader đã push code mới lên main, các thành viên còn lại cần cập nhật code mới về máy mình để không bị xung đột (conflict):
Các thành viên thực hiện:
```bash
# Chuyển về main và kéo code mới nhất về
git checkout main
git pull origin main
# Chuyển lại về branch công việc tiếp theo của mình và rebase/merge từ main sang
git checkout feature/nhiem-vu-moi
git merge main

```

💡 Lời Khuyên Quản Lý Cho Leader
Quy tắc Message Commit: Bắt buộc thành viên đặt tên commit theo chuẩn Conventional Commits (ví dụ: feat: ..., fix: ..., docs: ..., test: ...).
Setup file .env.example: Tạo sẵn file .env.example mẫu chứa các biến môi trường như DATABASE_URL, JWT_SECRET_KEY để thành viên chỉ cần copy thành .env trên máy cá nhân mà không lỡ push thông tin nhạy cảm lên Git.
Lịch Demo Cố Định: Đặt mốc demo nhỏ 2 lần/tuần (ví dụ: Chiều Thứ 4 & Chiều Thứ 7) để kiểm tra tiến độ của 4 thành viên, tránh dồn việc đến cuối tuần.


| Tuần | Mục tiêu chính | Đầu ra (Deliverables) |
| --- | --- | --- |
| Tuần 1 | Setup dự án, CSDL, Auth, Chuẩn bị Thuật toán | Skeleton dự án, Auth API (/login, /me), Schemas DB, thuật toán Sweep/Tabu cơ bản. |
| Tuần 2 | CRUD APIs & Thuật toán gom cụm Sweep | API Locations, Vehicles, Thuật toán Sweep gom cụm chạy độc lập có Unit Test. |
| Tuần 3 | Thuật toán Tabu Search & API Trigger Routing | Thuật toán VRPTW hoàn chỉnh, API /routes/generate lưu kết quả vào DB. |
| Tuần 4 | Dockerization, Tối ưu & Tích hợp Mobile App | Docker compose hoạt động mượt mà, API xem lộ trình cho tài xế/app, Hướng dẫn tích hợp. |
```