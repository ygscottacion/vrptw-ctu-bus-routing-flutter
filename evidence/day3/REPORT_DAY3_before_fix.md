# BÁO CÁO THỰC THI KIỂM THỬ NGÀY 3 (NHÃ - BACKEND API & SECURITY)

**Lệnh 1 dòng chạy lại toàn bộ test:**
```bash
python tests/day3/test_day3_runner.py
```

---
## 1. Thông tin tổng quan
- **Môi trường:** Staging Local (`http://localhost:8000`)
- **Thành viên thực hiện:** Nhã (Backend API & Security Tester)
- **Ngày thực thi:** 2026-09-30 01:05:00 ICT
- **Tổng số Test Case:** 4
- **Tổng số Bước (Steps):** 9
- **Số bước ĐẠT (PASS):** 2
- **Số bước THẤT BẠI (FAIL):** 7
- **Tỷ lệ Pass:** **22.22%**

## 2. Bảng tổng hợp kết quả (Test Execution Summary Table)

| TC ID | Bước | Request / Thao tác | Kỳ vọng (Expected) | Thực tế (Actual) | Kết quả | Thời gian |
|:---:|:---:|---|---|---|:---:|:---:|
| `TS-SEC-01` | 1 | U1 gọi POST /routes/admin/generate | 403 Forbidden ('The user doesn't have enough privileges') | 403 - {'detail': "The user doesn't have enough privileges (admin required)"} | **🟢 PASS** | 2319.11ms |
| `TS-SEC-01` | 2 | D1 gọi POST /routes/{id}/approve | 403 Forbidden ('The user doesn't have enough privileges') | 403 - {'detail': "The user doesn't have enough privileges (admin required)"} | **🟢 PASS** | 2309.27ms |
| `TS-SEC-02` | 1 | PATCH /routes/{CT-03-id}/start (completed) | 409 Conflict + thông báo lỗi state transition | 200 - {'id': '8c7d9e4a-1122-4334-b556-9900aabbccdd', 'route_job_id': None, 'service_date': '2026-09-29', 'session_id': 'MORNING_1', 'trip_type': 'pickup', 'vehicle_id': 'bc04c529-8f2a-4a62-8b9d-281a47474b5a', 'status': 'in_progress', 'total_distance': 10.0, 'stops': [], 'passenger_count': 0, 'approved_by': None, 'approved_at': None, 'rejection_reason': None} | **🔴 FAIL** | 2822.99ms |
| `TS-SEC-02` | 2 | PATCH /routes/{CT-01-id}/end (pending) | 409 Conflict + thông báo lỗi state transition | 200 - {'id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'route_job_id': None, 'service_date': '2026-09-21', 'session_id': 'MORNING_1', 'trip_type': 'pickup', 'vehicle_id': 'bc04c529-8f2a-4a62-8b9d-281a47474b5a', 'status': 'completed', 'total_distance': 14.8, 'stops': [{'id': '093db662-0b46-4410-b6df-1e96a9025e54', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '1962227a-0153-4ea6-9051-59cc7194c32c', 'stop_order': 1, 'arrival_time': '2026-09-21T15:53:29.794806Z', 'location': {'name': 'ĐH Cần Thơ - Khu II (Depot chính)', 'latitude': 10.0282, 'longitude': 105.7682, 'time_window_start': None, 'time_window_end': None, 'demand': 0, 'id': '1962227a-0153-4ea6-9051-59cc7194c32c'}}, {'id': '4f0423a3-4e90-4a1a-aeb2-5f50e7528869', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea', 'stop_order': 2, 'arrival_time': '2026-09-21T16:05:29.794806Z', 'location': {'name': 'Bến Ninh Kiều', 'latitude': 10.032213, 'longitude': 105.787976, 'time_window_start': None, 'time_window_end': None, 'demand': 2, 'id': '8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea'}}, {'id': 'c8fc2715-b7fb-461f-886f-9c8fca07e546', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '44ef2b46-d9d0-49ad-97ec-8453762a1ad1', 'stop_order': 3, 'arrival_time': '2026-09-21T16:17:29.794806Z', 'location': {'name': 'Bến xe Trung tâm Cần Thơ', 'latitude': 10.005198, 'longitude': 105.772084, 'time_window_start': None, 'time_window_end': None, 'demand': 6, 'id': '44ef2b46-d9d0-49ad-97ec-8453762a1ad1'}}, {'id': '66887ad6-4a9b-455b-a8ac-96fbe604ca2b', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '040a181f-47a2-48d9-ac88-7fdb9fcde4b8', 'stop_order': 4, 'arrival_time': '2026-09-21T16:29:29.794806Z', 'location': {'name': 'Hẻm 51 - Hồ Búng Xán', 'latitude': 10.024814, 'longitude': 105.767565, 'time_window_start': None, 'time_window_end': None, 'demand': 2, 'id': '040a181f-47a2-48d9-ac88-7fdb9fcde4b8'}}, {'id': '9fb08cd6-69ca-4b7d-86e7-2f15f1df148e', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': 'ecdbfc40-6060-417c-827a-f14d45bfbb5f', 'stop_order': 5, 'arrival_time': '2026-09-21T16:41:29.794806Z', 'location': {'name': 'ĐH Y Dược Cần Thơ', 'latitude': 10.034498, 'longitude': 105.755812, 'time_window_start': None, 'time_window_end': None, 'demand': 4, 'id': 'ecdbfc40-6060-417c-827a-f14d45bfbb5f'}}, {'id': '8e80a096-8dc5-4809-a6c9-5e1c3e23ce8b', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '2e1fea7c-167a-4225-aca3-c2c32e9dd6b2', 'stop_order': 6, 'arrival_time': '2026-09-21T16:53:29.794806Z', 'location': {'name': 'Bệnh viện Đa khoa thành phố Cần Thơ', 'latitude': 10.030945, 'longitude': 105.781573, 'time_window_start': None, 'time_window_end': None, 'demand': 3, 'id': '2e1fea7c-167a-4225-aca3-c2c32e9dd6b2'}}], 'passenger_count': 0, 'approved_by': None, 'approved_at': None, 'rejection_reason': None} | **🔴 FAIL** | 3179.34ms |
| `TS-SEC-03` | 1 | D2 gọi PATCH /routes/{CT-01-id}/start | 403 Forbidden ('Bạn không có quyền bắt đầu tuyến xe này') | 403 - {'detail': 'Tuyến xe này không thuộc xe do bạn quản lý.'} | **🔴 FAIL** | 2669.98ms |
| `TS-SEC-03` | 2 | Kiểm tra trạng thái CT-01 sau request | Trạng thái CT-01 vẫn là pending | Status = completed | **🔴 FAIL** | 2849.78ms |
| `TS-SEC-04` | 1 | Gửi POST /tickets/reserve lần 1 (X-Idempotency-Key) | 201 Created + vé tạo mới | 400 - Ticket ID: None | **🔴 FAIL** | 2476.9ms |
| `TS-SEC-04` | 2 | Gửi POST /tickets/reserve lần 2 (cùng Key & Payload) | 201 Created + response giống hệt lần 1 (cached) | 400 - {'detail': 'Bạn đã mua vé cho chuyến đi trong ca/chiều này rồi.'} | **🔴 FAIL** | 2518.39ms |
| `TS-SEC-04` | 3 | Đối chiếu DB sau test | Chỉ 1 vé mới (+1), Số dư trừ đúng 7,000 VNĐ | Vé mới: +0, Số dư trừ: -0 VNĐ | **🔴 FAIL** | 5.0ms |

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

#### Bước 1: PATCH /routes/{CT-03-id}/start (completed) - [FAIL]
- **Request:** `PATCH /routes/8c7d9e4a-1122-4334-b556-9900aabbccdd/start`
- **Kỳ vọng:** 409 Conflict + thông báo lỗi state transition
- **Thực tế:** 200 - {'id': '8c7d9e4a-1122-4334-b556-9900aabbccdd', 'route_job_id': None, 'service_date': '2026-09-29', 'session_id': 'MORNING_1', 'trip_type': 'pickup', 'vehicle_id': 'bc04c529-8f2a-4a62-8b9d-281a47474b5a', 'status': 'in_progress', 'total_distance': 10.0, 'stops': [], 'passenger_count': 0, 'approved_by': None, 'approved_at': None, 'rejection_reason': None}
- **File log thô:** [`evidence/day3/raw/TS-SEC-02_step1.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-02_step1.json)
- **Lệnh curl tái hiện:**
```bash
curl -X PATCH 'http://localhost:8000/api/v1/routes/8c7d9e4a-1122-4334-b556-9900aabbccdd/start' -H 'Authorization: Bearer eyJhbGci...'
```

#### Bước 2: PATCH /routes/{CT-01-id}/end (pending) - [FAIL]
- **Request:** `PATCH /routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/end`
- **Kỳ vọng:** 409 Conflict + thông báo lỗi state transition
- **Thực tế:** 200 - {'id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'route_job_id': None, 'service_date': '2026-09-21', 'session_id': 'MORNING_1', 'trip_type': 'pickup', 'vehicle_id': 'bc04c529-8f2a-4a62-8b9d-281a47474b5a', 'status': 'completed', 'total_distance': 14.8, 'stops': [{'id': '093db662-0b46-4410-b6df-1e96a9025e54', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '1962227a-0153-4ea6-9051-59cc7194c32c', 'stop_order': 1, 'arrival_time': '2026-09-21T15:53:29.794806Z', 'location': {'name': 'ĐH Cần Thơ - Khu II (Depot chính)', 'latitude': 10.0282, 'longitude': 105.7682, 'time_window_start': None, 'time_window_end': None, 'demand': 0, 'id': '1962227a-0153-4ea6-9051-59cc7194c32c'}}, {'id': '4f0423a3-4e90-4a1a-aeb2-5f50e7528869', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea', 'stop_order': 2, 'arrival_time': '2026-09-21T16:05:29.794806Z', 'location': {'name': 'Bến Ninh Kiều', 'latitude': 10.032213, 'longitude': 105.787976, 'time_window_start': None, 'time_window_end': None, 'demand': 2, 'id': '8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea'}}, {'id': 'c8fc2715-b7fb-461f-886f-9c8fca07e546', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '44ef2b46-d9d0-49ad-97ec-8453762a1ad1', 'stop_order': 3, 'arrival_time': '2026-09-21T16:17:29.794806Z', 'location': {'name': 'Bến xe Trung tâm Cần Thơ', 'latitude': 10.005198, 'longitude': 105.772084, 'time_window_start': None, 'time_window_end': None, 'demand': 6, 'id': '44ef2b46-d9d0-49ad-97ec-8453762a1ad1'}}, {'id': '66887ad6-4a9b-455b-a8ac-96fbe604ca2b', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '040a181f-47a2-48d9-ac88-7fdb9fcde4b8', 'stop_order': 4, 'arrival_time': '2026-09-21T16:29:29.794806Z', 'location': {'name': 'Hẻm 51 - Hồ Búng Xán', 'latitude': 10.024814, 'longitude': 105.767565, 'time_window_start': None, 'time_window_end': None, 'demand': 2, 'id': '040a181f-47a2-48d9-ac88-7fdb9fcde4b8'}}, {'id': '9fb08cd6-69ca-4b7d-86e7-2f15f1df148e', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': 'ecdbfc40-6060-417c-827a-f14d45bfbb5f', 'stop_order': 5, 'arrival_time': '2026-09-21T16:41:29.794806Z', 'location': {'name': 'ĐH Y Dược Cần Thơ', 'latitude': 10.034498, 'longitude': 105.755812, 'time_window_start': None, 'time_window_end': None, 'demand': 4, 'id': 'ecdbfc40-6060-417c-827a-f14d45bfbb5f'}}, {'id': '8e80a096-8dc5-4809-a6c9-5e1c3e23ce8b', 'route_id': '6a34cb4f-3e16-4236-bfa7-5d39d2724460', 'location_id': '2e1fea7c-167a-4225-aca3-c2c32e9dd6b2', 'stop_order': 6, 'arrival_time': '2026-09-21T16:53:29.794806Z', 'location': {'name': 'Bệnh viện Đa khoa thành phố Cần Thơ', 'latitude': 10.030945, 'longitude': 105.781573, 'time_window_start': None, 'time_window_end': None, 'demand': 3, 'id': '2e1fea7c-167a-4225-aca3-c2c32e9dd6b2'}}], 'passenger_count': 0, 'approved_by': None, 'approved_at': None, 'rejection_reason': None}
- **File log thô:** [`evidence/day3/raw/TS-SEC-02_step2.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-02_step2.json)
- **Lệnh curl tái hiện:**
```bash
curl -X PATCH 'http://localhost:8000/api/v1/routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/end' -H 'Authorization: Bearer eyJhbGci...'
```

### TS-SEC-03

#### Bước 1: D2 gọi PATCH /routes/{CT-01-id}/start - [FAIL]
- **Request:** `PATCH /routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/start`
- **Kỳ vọng:** 403 Forbidden ('Bạn không có quyền bắt đầu tuyến xe này')
- **Thực tế:** 403 - {'detail': 'Tuyến xe này không thuộc xe do bạn quản lý.'}
- **File log thô:** [`evidence/day3/raw/TS-SEC-03_step1.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-03_step1.json)
- **Lệnh curl tái hiện:**
```bash
curl -X PATCH 'http://localhost:8000/api/v1/routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460/start' -H 'Authorization: Bearer eyJhbGci...'
```

#### Bước 2: Kiểm tra trạng thái CT-01 sau request - [FAIL]
- **Request:** `GET /routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460`
- **Kỳ vọng:** Trạng thái CT-01 vẫn là pending
- **Thực tế:** Status = completed
- **File log thô:** [`evidence/day3/raw/TS-SEC-03_step2.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-03_step2.json)
- **Lệnh curl tái hiện:**
```bash
curl -X GET 'http://localhost:8000/api/v1/routes/6a34cb4f-3e16-4236-bfa7-5d39d2724460' -H 'Authorization: Bearer eyJhbGci...'
```

### TS-SEC-04

#### Bước 1: Gửi POST /tickets/reserve lần 1 (X-Idempotency-Key) - [FAIL]
- **Request:** `POST /tickets/reserve`
- **Kỳ vọng:** 201 Created + vé tạo mới
- **Thực tế:** 400 - Ticket ID: None
- **File log thô:** [`evidence/day3/raw/TS-SEC-04_step1.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-04_step1.json)
- **Lệnh curl tái hiện:**
```bash
curl -X POST 'http://localhost:8000/api/v1/tickets/reserve' -H 'X-Idempotency-Key: KEY-TEST-12345' -H 'Authorization: Bearer eyJhbGci...' -d '{"service_date": "2026-10-01", "session_id": "MORNING_1", "trip_type": "pickup", "pickup_location_id": "8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea"}'
```

#### Bước 2: Gửi POST /tickets/reserve lần 2 (cùng Key & Payload) - [FAIL]
- **Request:** `POST /tickets/reserve`
- **Kỳ vọng:** 201 Created + response giống hệt lần 1 (cached)
- **Thực tế:** 400 - {'detail': 'Bạn đã mua vé cho chuyến đi trong ca/chiều này rồi.'}
- **File log thô:** [`evidence/day3/raw/TS-SEC-04_step2.json`](file:///C:/Users/ACER/myctubus_flutter/evidence/day3/raw/TS-SEC-04_step2.json)
- **Lệnh curl tái hiện:**
```bash
curl -X POST 'http://localhost:8000/api/v1/tickets/reserve' -H 'X-Idempotency-Key: KEY-TEST-12345' -H 'Authorization: Bearer eyJhbGci...' -d '{"service_date": "2026-10-01", "session_id": "MORNING_1", "trip_type": "pickup", "pickup_location_id": "8dbcf64d-a447-4b8d-9e80-3b4eb2b838ea"}'
```

#### Bước 3: Đối chiếu DB sau test - [FAIL]
- **Request:** `SQL Query Wallets & Tickets`
- **Kỳ vọng:** Chỉ 1 vé mới (+1), Số dư trừ đúng 7,000 VNĐ
- **Thực tế:** Vé mới: +0, Số dư trừ: -0 VNĐ
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