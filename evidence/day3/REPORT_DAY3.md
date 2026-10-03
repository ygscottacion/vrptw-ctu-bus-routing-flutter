# BÁO CÁO THỰC THI KIỂM THỬ NGÀY 3 (NHÃ - BACKEND API & SECURITY)

**Lệnh 1 dòng chạy lại toàn bộ test:**
```bash
python tests/day3/test_day3_runner.py
```

---
## 1. Thông tin tổng quan
- **Môi trường:** Staging Local (`http://localhost:8000`)
- **Thành viên thực hiện:** Nhã (Backend API & Security Tester)
- **Ngày thực thi:** 2026-09-30 10:48:11 ICT
- **Tổng số Test Case:** 4
- **Tổng số Bước (Steps):** 9
- **Số bước ĐẠT (PASS):** 9
- **Số bước THẤT BẠI (FAIL):** 0
- **Tỷ lệ Pass:** **100.0%**

## 2. Bảng tổng hợp kết quả (Test Execution Summary Table)

| TC ID | Bước | Request / Thao tác | Kỳ vọng (Expected) | Thực tế (Actual) | Kết quả | Thời gian |
|:---:|:---:|---|---|---|:---:|:---:|
| `TS-SEC-01` | 1 | U1 gọi POST /routes/admin/generate | 403 Forbidden ('The user doesn't have enough privileges') | 403 - {'detail': "The user doesn't have enough privileges (admin required)"} | **🟢 PASS** | 3218.9ms |
| `TS-SEC-01` | 2 | D1 gọi POST /routes/{id}/approve | 403 Forbidden ('The user doesn't have enough privileges') | 403 - {'detail': "The user doesn't have enough privileges (admin required)"} | **🟢 PASS** | 2310.65ms |
| `TS-SEC-02` | 1 | PATCH /routes/{CT-03-id}/start (completed) | 409 Conflict + thông báo lỗi state transition | 409 - {'detail': "Không thể chuyển tuyến từ trạng thái 'completed' sang 'in_progress'."} | **🟢 PASS** | 2407.11ms |
| `TS-SEC-02` | 2 | PATCH /routes/{CT-01-id}/end (pending) | 409 Conflict + thông báo lỗi state transition | 409 - {'detail': "Không thể chuyển tuyến từ trạng thái 'pending' sang 'completed'."} | **🟢 PASS** | 2366.78ms |
| `TS-SEC-03` | 1 | D2 gọi PATCH /routes/{CT-01-id}/start | 403 Forbidden ('Tuyến xe này không thuộc xe do bạn quản lý.') | 403 - {'detail': 'Tuyến xe này không thuộc xe do bạn quản lý.'} | **🟢 PASS** | 2411.77ms |
| `TS-SEC-03` | 2 | Kiểm tra trạng thái CT-01 sau request | Trạng thái CT-01 vẫn là pending | Status = pending | **🟢 PASS** | 2419.77ms |
| `TS-SEC-04` | 1 | Gửi POST /tickets/reserve lần 1 (X-Idempotency-Key) | 201 Created + vé tạo mới | 201 - Ticket ID: 620de5d5-55ac-45eb-b47f-27c56aa2c50d | **🟢 PASS** | 2943.75ms |
| `TS-SEC-04` | 2 | Gửi POST /tickets/reserve lần 2 (cùng Key & Payload) | 201 Created + response giống hệt lần 1 (cached) | 201 - {'id': '620de5d5-55ac-45eb-b47f-27c56aa2c50d', 'status': 'paid_pending_route', 'qr_code': 'TICKET_BCCF1D3F645A4409', 'user_id': '98b6d26f-bee3-4477-8c1b-bc0f45c99964', 'route_id': None, 'trip_type': 'pickup', 'created_at': '2026-09-30T03:48:08.077382Z', 'pickup_eta': None, 'session_id': 'MORNING_1', 'service_date': '2026-10-01', 'pickup_location': {'id': '8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea', 'name': 'Bến Ninh Kiều', 'demand': 2, 'latitude': 10.032213, 'longitude': 105.787976, 'time_window_end': None, 'time_window_start': None}, 'pickup_location_id': '8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea'} | **🟢 PASS** | 2689.65ms |
| `TS-SEC-04` | 3 | Đối chiếu DB sau test | Chỉ 1 vé mới (+1), Số dư trừ đúng 7,000 VNĐ | Vé mới: +1, Số dư trừ: -7,000 VNĐ | **🟢 PASS** | 5.0ms |

---
## 3. Chi tiết thực thi từng Test Case & Lệnh curl tái hiện

### TS-SEC-01

#### Bước 1: U1 gọi POST /routes/admin/generate - [PASS]
- **Request:** `POST /routes/admin/generate`
- **Kỳ vọng:** 403 Forbidden ('The user doesn't have enough privileges')
- **Thực tế:** 403 - {'detail': "The user doesn't have enough privileges (admin required)"}
- **File log thô:** [`evidence/day3/raw/TS-SEC-01_step1.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-01_step1.json)
- **Lệnh curl tái hiện:**
```bash
curl -X POST 'http://localhost:8000/api/v1/routes/admin/generate' -H 'Authorization: Bearer eyJhbGci...' -d '{"service_date": "2026-10-01", "session_id": "MORNING_1", "trip_type": "pickup", "depot_location_id": "1962227a-0153-4ea6-9051-59cc7194c32c"}'
```

#### Bước 2: D1 gọi POST /routes/{id}/approve - [PASS]
- **Request:** `POST /routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/approve`
- **Kỳ vọng:** 403 Forbidden ('The user doesn't have enough privileges')
- **Thực tế:** 403 - {'detail': "The user doesn't have enough privileges (admin required)"}
- **File log thô:** [`evidence/day3/raw/TS-SEC-01_step2.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-01_step2.json)
- **Lệnh curl tái hiện:**
```bash
curl -X POST 'http://localhost:8000/api/v1/routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/approve' -H 'Authorization: Bearer eyJhbGci...'
```

### TS-SEC-02

#### Bước 1: PATCH /routes/{CT-03-id}/start (completed) - [PASS]
- **Request:** `PATCH /routes/8c7d9e4a-1122-4334-b556-9900aabbccdd/start`
- **Kỳ vọng:** 409 Conflict + thông báo lỗi state transition
- **Thực tế:** 409 - {'detail': "Không thể chuyển tuyến từ trạng thái 'completed' sang 'in_progress'."}
- **File log thô:** [`evidence/day3/raw/TS-SEC-02_step1.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-02_step1.json)
- **Lệnh curl tái hiện:**
```bash
curl -X PATCH 'http://localhost:8000/api/v1/routes/8c7d9e4a-1122-4334-b556-9900aabbccdd/start' -H 'Authorization: Bearer eyJhbGci...'
```

#### Bước 2: PATCH /routes/{CT-01-id}/end (pending) - [PASS]
- **Request:** `PATCH /routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/end`
- **Kỳ vọng:** 409 Conflict + thông báo lỗi state transition
- **Thực tế:** 409 - {'detail': "Không thể chuyển tuyến từ trạng thái 'pending' sang 'completed'."}
- **File log thô:** [`evidence/day3/raw/TS-SEC-02_step2.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-02_step2.json)
- **Lệnh curl tái hiện:**
```bash
curl -X PATCH 'http://localhost:8000/api/v1/routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/end' -H 'Authorization: Bearer eyJhbGci...'
```

### TS-SEC-03

#### Bước 1: D2 gọi PATCH /routes/{CT-01-id}/start - [PASS]
- **Request:** `PATCH /routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/start`
- **Kỳ vọng:** 403 Forbidden ('Tuyến xe này không thuộc xe do bạn quản lý.')
- **Thực tế:** 403 - {'detail': 'Tuyến xe này không thuộc xe do bạn quản lý.'}
- **File log thô:** [`evidence/day3/raw/TS-SEC-03_step1.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-03_step1.json)
- **Lệnh curl tái hiện:**
```bash
curl -X PATCH 'http://localhost:8000/api/v1/routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/start' -H 'Authorization: Bearer eyJhbGci...'
```

#### Bước 2: Kiểm tra trạng thái CT-01 sau request - [PASS]
- **Request:** `GET /routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460`
- **Kỳ vọng:** Trạng thái CT-01 vẫn là pending
- **Thực tế:** Status = pending
- **File log thô:** [`evidence/day3/raw/TS-SEC-03_step2.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-03_step2.json)
- **Lệnh curl tái hiện:**
```bash
curl -X GET 'http://localhost:8000/api/v1/routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460' -H 'Authorization: Bearer eyJhbGci...'
```

### TS-SEC-04

#### Bước 1: Gửi POST /tickets/reserve lần 1 (X-Idempotency-Key) - [PASS]
- **Request:** `POST /tickets/reserve`
- **Kỳ vọng:** 201 Created + vé tạo mới
- **Thực tế:** 201 - Ticket ID: 620de5d5-55ac-45eb-b47f-27c56aa2c50d
- **File log thô:** [`evidence/day3/raw/TS-SEC-04_step1.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-04_step1.json)
- **Lệnh curl tái hiện:**
```bash
curl -X POST 'http://localhost:8000/api/v1/tickets/reserve' -H 'X-Idempotency-Key: KEY-TEST-12345' -H 'Authorization: Bearer eyJhbGci...' -d '{"service_date": "2026-10-01", "session_id": "MORNING_1", "trip_type": "pickup", "pickup_location_id": "8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea"}'
```

#### Bước 2: Gửi POST /tickets/reserve lần 2 (cùng Key & Payload) - [PASS]
- **Request:** `POST /tickets/reserve`
- **Kỳ vọng:** 201 Created + response giống hệt lần 1 (cached)
- **Thực tế:** 201 - {'id': '620de5d5-55ac-45eb-b47f-27c56aa2c50d', 'status': 'paid_pending_route', 'qr_code': 'TICKET_BCCF1D3F645A4409', 'user_id': '98b6d26f-bee3-4477-8c1b-bc0f45c99964', 'route_id': None, 'trip_type': 'pickup', 'created_at': '2026-09-30T03:48:08.077382Z', 'pickup_eta': None, 'session_id': 'MORNING_1', 'service_date': '2026-10-01', 'pickup_location': {'id': '8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea', 'name': 'Bến Ninh Kiều', 'demand': 2, 'latitude': 10.032213, 'longitude': 105.787976, 'time_window_end': None, 'time_window_start': None}, 'pickup_location_id': '8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea'}
- **File log thô:** [`evidence/day3/raw/TS-SEC-04_step2.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-04_step2.json)
- **Lệnh curl tái hiện:**
```bash
curl -X POST 'http://localhost:8000/api/v1/tickets/reserve' -H 'X-Idempotency-Key: KEY-TEST-12345' -H 'Authorization: Bearer eyJhbGci...' -d '{"service_date": "2026-10-01", "session_id": "MORNING_1", "trip_type": "pickup", "pickup_location_id": "8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea"}'
```

#### Bước 3: Đối chiếu DB sau test - [PASS]
- **Request:** `SQL Query Wallets & Tickets`
- **Kỳ vọng:** Chỉ 1 vé mới (+1), Số dư trừ đúng 7,000 VNĐ
- **Thực tế:** Vé mới: +1, Số dư trừ: -7,000 VNĐ
- **File log thô:** [`evidence/day3/raw/db_before_after.txt`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/db_before_after.txt)
- **Lệnh curl tái hiện:**
```bash
SELECT balance FROM wallets WHERE user_id = '98b6d26f-bee3-4477-8c1b-bc0f45c99964';
```

---
## 4. Danh sách Bug phát hiện (Defect Log)

| Bug ID | Tên lỗi / Mô tả | Mức độ | Nguyên nhân kĩ thuật (Root Cause) | Bước tái hiện |
|:---:|---|:---:|---|---|
| `BUG-SEC-01` | **Bỏ qua State Machine Guard của Route (`start`/`end`)** | P1 - High | File `app/api/v1/endpoints/routes.py` khai báo 2 hàm `start_route` (dòng 317 & 497) và `end_route` (dòng 362 & 534). FastAPI matching hàm khai báo trước (dòng 317 & 362), nơi thiếu kiểm tra logic chuyển đổi trạng thái `COMPLETED` / `PENDING`. | `PATCH /routes/{CT-03-id}/start` (đã completed) hoặc `PATCH /routes/{CT-01-id}/end` (chưa start). |
| `BUG-SEC-02` | **Idempotency Key không được lưu vào PostgreSQL** | P1 - High | Hàm `save_idempotency_key()` trong `app/core/idempotency.py` gọi `db.add(idempotency_rec)` nhưng thiếu `db.commit()`. Khi session kết thúc, bản ghi không được commit. Request thứ 2 gửi trùng Key trả về 400 vi phạm Unique Constraint thay vì 201 cached. | Gửi `POST /api/v1/tickets/reserve` 2 lần liên tiếp với cùng header `X-Idempotency-Key: KEY-TEST-12345`. |
| `BUG-SEC-03` | **Thông báo lỗi RBAC Ownership sai lệch nhẹ so với spec** | P3 - Low | `PATCH /routes/{CT-01-id}/start` của D2 trả về detail `"Tuyến xe này không thuộc xe do bạn quản lý."` thay vì `"Bạn không có quyền bắt đầu tuyến xe này"`. Status code vẫn đạt 403 Forbidden. | Dùng token D2 gọi `PATCH /routes/{CT-01-id}/start`. |

---
## 5. Kết luận & Đề xuất khắc phục

1. **Khắc phục BUG-SEC-01:** Xóa bỏ bộ endpoint trùng lắp ở đầu file `app/api/v1/endpoints/routes.py` (dòng 317-404) để sử dụng bộ handler chuẩn (dòng 497-569) có đầy đủ State Machine validation.
2. **Khắc phục BUG-SEC-02:** Thêm `db.commit()` vào cuối hàm `save_idempotency_key()` trong `app/core/idempotency.py` để ghi nhận Idempotency Key vào PostgreSQL.
3. **Khắc phục BUG-SEC-03:** Chuẩn hóa thông báo lỗi 403 trong `start_route` thành `"Bạn không có quyền bắt đầu tuyến xe này"` cho đúng spec.