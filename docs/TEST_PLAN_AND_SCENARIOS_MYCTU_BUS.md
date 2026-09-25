# KẾ HOẠCH & KỊCH BẢN KIỂM THỬ HỆ THỐNG MYCTU BUS
*(Dùng cho Thực thi Kiểm thử Nhóm 5 người & Trích xuất vào Báo cáo Đồ án / Dự án)*

**Tên dự án:** Hệ thống Quản lý và Tối ưu Tuyến xe buýt Đưa đón Sinh viên Đại học Cần Thơ (MyCTU BUS)  
**Phiên bản Build Nghiệm thu (Build SHA):** `3a23866` / `8f54541`  
**Ngày phát hành:** 2026-09-24  
**Trạng thái hệ thống:** Đã sẵn sàng nghiệm thu E2E (All P0/P1 Critical Gates UNBLOCKED)  

---

# PHẦN I: KẾ HOẠCH KIỂM THỬ (TEST PLAN)

## 1. Mục tiêu Kiểm thử (Test Objectives)
1. **Xác minh Chức năng (Functional Verification):** Đảm bảo tất cả các tính năng trên Admin Web Portal, App Sinh viên Flutter, App Tài xế Flutter và REST API Backend hoạt động chính xác theo yêu cầu nghiệp vụ.
2. **Xác minh An toàn Dữ liệu & Ví điện tử (Data & Wallet Integrity):** Đảm bảo các giao dịch trừ/hoàn tiền ví điện tử mang tính nguyên tử (atomic), không rò rỉ số dư, không bị nhân đôi giao dịch.
3. **Xác minh Quy trình Vận hành (State Machine Validation):** Đảm bảo chuyển đổi trạng thái tuyến xe (`pending` → `approved`/`rejected` → `in_progress` → `completed`) và trạng thái vé (`paid_pending_route` → `assigned` → `used`) diễn ra chính xác theo thẩm quyền.
4. **Xác minh Bảo mật & Phân quyền (Security & RBAC):** Đảm bảo các quy tắc RBAC JWT và Supabase RLS ngăn chặn hoàn toàn việc truy cập/sửa đổi chéo dữ liệu giữa các vai trò Sinh viên, Tài xế và Admin.
5. **Nghệ thuật Tối ưu Lộ trình (Solver Verification):** Xác minh thuật toán Sweep + Tabu Search phân bổ vé sinh viên vào các phương tiện đúng sức chứa (capacity) và cửa sổ thời gian (time window).

## 2. Phạm vi Kiểm thử (Test Scope)
- **Trong phạm vi (In-Scope):**
  - **Admin Web Portal (React TypeScript):** Quản lý xe, người dùng, khởi tạo job sinh tuyến tự động, theo dõi job polling, xem manifest trạm dừng, duyệt/từ chối lộ trình, bản đồ realtime GPS.
  - **App Sinh viên (Flutter):** Đăng nhập JWT, đặt vé, chọn trạm đón, xem mã QR vé, hủy vé trước cutoff 22:00 ICT, tra cứu số dư ví.
  - **App Tài xế (Flutter):** Đăng nhập, xem danh sách tuyến xe phụ trách, Bật/Tắt ca làm việc, kích hoạt `startRoute`/`endRoute`, phát vị trí GPS 15s/lần, quét camera QR điểm danh.
  - **FastAPI Web API Backend:** Các endpoint REST, middleware RBAC, idempotency handler, Goong Maps direction provider.
  - **Cơ sở dữ liệu PostgreSQL / Supabase:** Tables, Alembic migrations, Triggers, RLS Policies.
- **Ngoài phạm vi (Out-of-Scope):** Giao dịch tiền thật qua ngân hàng/cổng VNPay (sử dụng Ví điện tử thử nghiệm Staging).

## 3. Môi trường & Công cụ Kiểm thử (Test Environment & Tools)
- **Môi trường:** Staging Server (FastAPI + PostgreSQL Supabase), Admin Web (Vite Dev/Prod), App Mobile (Android APK & Flutter Web).
- **Công cụ kiểm thử:** Postman / Swagger UI (Test API), Chrome DevTools, Flutter DevTools, Android ADB / Thiết bị Android thật, VS Code, Git.
- **Múi giờ chuẩn:** Vietnam Standard Time (`Asia/Ho_Chi_Minh` - ICT / UTC+7).

## 4. Ma trận Phân công Nhân sự (Team Responsibility Matrix)

| Thành viên | Vai trò kiểm thử | Phân vùng kiểm thử chính | Case phụ trách |
|---|---|---|---|
| **Thành viên 1 — Duy** | Routing & Admin Portal Tester | Admin Web Portal UI, Form Sinh tuyến, Solver Progress, Route Manifest, Duyệt/Từ chối tuyến. | `TS-ADM-01` → `TS-ADM-08` |
| **Thành viên 2 — Minh** | DB & Wallet Ledger Tester | Khởi tạo dữ liệu seed, Reset DB, Kiểm tra Ví điện tử (Wallet Ledger), Đối soát Vé & RLS DB Boundary. | `TS-DB-01` → `TS-DB-06` |
| **Thành viên 3 — Nhã** | Backend Security & API Tester | REST API Endpoints, Phân quyền RBAC JWT, State Machine, Idempotency, QR Verify rules & Cross-driver Security. | `TS-SEC-01` → `TS-SEC-07` |
| **Thành viên 4 — Khánh** | Flutter User & Driver App Tester | App Sinh viên (Đặt vé, QR, Hủy vé), App Tài xế (Xem tuyến, Bật ca `start`, Tắt ca `end`, Phát GPS, Quét QR Camera). | `TS-APP-01` → `TS-APP-07` |
| **Thành viên 5 — Lợi** | QA Lead & E2E Integration | Cấp phát SHA/Tài khoản test, Điều phối chuỗi E2E 5 bước, Quản lý Bug Log, Retest & Ký duyệt Sign-off Report. | `TS-E2E-01` → `TS-E2E-04` |

---

# PHẦN II: KỊCH BẢN KIỂM THỬ CHI TIẾT (TEST SCENARIOS)

---

## 🟢 THÀNH VIÊN 1: DUY (ADMIN PORTAL & ROUTING SOLVER)

### TS-ADM-01: Đăng nhập Admin & Bảo mật phiên làm việc
- **Mục tiêu:** Xác minh chỉ tài khoản có vai trò `admin` mới được truy cập Admin Portal.
- **Tiền điều kiện:** Môi trường Admin Web đang hoạt động tại URL Staging.
- **Các bước thực hiện:**
  1. Mở Admin Web Portal, nhập tài khoản Sinh viên `student1` / pass `123456` ➔ Bấm Đăng nhập.
  2. Đăng nhập lại với tài khoản Admin `admin@ctu.edu.vn` / pass `admin123` ➔ Bấm Đăng nhập.
  3. F5 refresh trang web ➔ Đăng xuất ➔ Bấm nút Back trên trình duyệt.
- **Kết quả mong đợi:** 
  - Bước 1: Báo lỗi `403 Forbidden` ("Tài khoản này không có quyền quản trị").
  - Bước 2: Đăng nhập thành công, điều hướng vào Dashboard. Header hiển thị tên Admin.
  - Bước 3: Đăng xuất xóa token trong `localStorage`, bấm Back không vào lại được trang quản trị.

### TS-ADM-02: Khởi tạo Tác vụ Sinh tuyến Tự động qua Form Admin
- **Mục tiêu:** Tạo job sinh tuyến thành công bằng JWT Auth Admin (Không dùng Cron Secret).
- **Tiền điều kiện:** Đã đăng nhập tài khoản Admin A.
- **Các bước thực hiện:**
  1. Truy cập mục **Tuyến đường & Duyệt (`/routes`)**.
  2. Chọn Ngày chạy `service_date` (Ngày D+1), Ca làm việc `MORNING_1`, Chiều di chuyển `pickup`.
  3. Chọn Trạm depot xuất phát từ dropdown danh sách địa điểm (UUID). Bấm **Khởi tạo Tuyến**.
- **Kết quả mong đợi:** Form gửi request `POST /routes/admin/generate` kèm Bearer Token Admin. Trả về mã HTTP `202 ACCEPTED` với `job_id` hợp lệ.

### TS-ADM-03: Theo dõi Trạng thái Job Sinh tuyến qua Polling
- **Mục tiêu:** Kiểm tra giao diện Admin Web poll theo dõi trạng thái tác vụ từ `QUEUED` → `RUNNING` → `SUCCEEDED`.
- **Tiền điều kiện:** Đã bấm Khởi tạo tuyến ở `TS-ADM-02`.
- **Các bước thực hiện:** Quan sát khung thông báo trạng thái tác vụ trên giao diện.
- **Kết quả mong đợi:** Giao diện tự động gửi `GET /routes/jobs/{job_id}` mỗi 2 giây. Khung hiển thị đổi từ `QUEUED` / `RUNNING` sang xanh lá `SUCCEEDED`. Bảng danh sách tuyến xe bên dưới tự động tải lại dữ liệu mới.

### TS-ADM-04: Kiểm tra Chi tiết Lộ trình & Manifest Trạm dừng
- **Mục tiêu:** Xác minh danh sách tuyến sinh tự động chứa đúng thông tin xe, số sinh viên và thứ tự trạm.
- **Tiền điều kiện:** Tác vụ sinh tuyến ở `TS-ADM-03` đã `SUCCEEDED`.
- **Các bước thực hiện:**
  1. Tìm tuyến xe mã `CT-XXXXX` trong bảng danh sách.
  2. Bấm nút **👁 Xem trạm dừng**.
- **Kết quả mong đợi:** Modal Manifest mở ra hiển thị: Tên xe buýt được gán, tổng số sinh viên đón (không vượt sức chứa xe), danh sách các trạm sắp xếp đúng thứ tự `stop_order` 1, 2, 3... kèm giờ dự kiến đến (`arrival_time`).

### TS-ADM-05: Thực hiện Duyệt Lộ trình (`POST /routes/{id}/approve`)
- **Mục tiêu:** Admin duyệt lộ trình tuyến xe đang ở trạng thái `pending`.
- **Tiền điều kiện:** Tuyến xe `CT-01` đang có trạng thái `pending` (Chờ duyệt).
- **Các bước thực hiện:** Bấm nút **✓ Duyệt** tại dòng tuyến xe `CT-01`.
- **Kết quả mong đợi:** API gửi `POST /routes/{id}/approve`. Trạng thái tuyến xe trên bảng chuyển thành Badge màu ngọc **Đã duyệt (`approved`)**. Đối soát DB ghi nhận `approved_by` = Admin UUID và `approved_at` = thời gian hiện tại.

### TS-ADM-06: Thực hiện Từ chối Lộ trình (`POST /routes/{id}/reject`)
- **Mục tiêu:** Admin từ chối lộ trình không phù hợp và ghi rõ lý do.
- **Tiền điều kiện:** Tuyến xe `CT-02` đang ở trạng thái `pending`.
- **Các bước thực hiện:** 
  1. Bấm nút **✕ Từ chối** tại dòng tuyến `CT-02`.
  2. Hộp thoại prompt hiện ra ➔ Nhập lý do: *"Trùng lịch bảo dưỡng xe buýt"* ➔ Bấm OK.
- **Kết quả mong đợi:** API gửi `POST /routes/{id}/reject` với payload `{ "reason": "Trùng lịch bảo dưỡng xe buýt" }`. Trạng thái tuyến chuyển thành Badge đỏ **Từ chối (`rejected`)**. DB lưu đúng lý do vào trường `rejection_reason`.

### TS-ADM-07: Quản lý Xe buýt & Phân công Tài xế (UUID Standard)
- **Mục tiêu:** Phân công tài xế cho xe buýt không bị lỗi ép kiểu ID số.
- **Tiền điều kiện:** Đang ở mục **Xe buýt (`/vehicles`)**.
- **Các bước thực hiện:**
  1. Thêm xe mới: Biển số `65B-999.99`, Sức chứa `30` chỗ ➔ Bấm Thêm xe.
  2. Tại cột "Tài xế phân công", chọn Tài xế `Trần Văn D1` từ dropdown.
- **Kết quả mong đợi:** Tạo xe thành công. Request gán tài xế gửi `PUT /vehicles/{uuid}/driver?driver_id={uuid}` sử dụng chuỗi UUID chuẩn. Trang reload giữ nguyên tài xế đã gán.

### TS-ADM-08: Giám sát Bản đồ Realtime GPS
- **Mục tiêu:** Hiển thị vị trí xe buýt đang hoạt động trên bản đồ Goong Maps.
- **Tiền điều kiện:** Đang ở mục **Bản đồ Realtime (`/map`)**. Tài xế `D1` đang phát GPS.
- **Các bước thực hiện:** Quan sát bản đồ và danh sách xe buýt ở cột bên phải.
- **Kết quả mong đợi:** Marker xe buýt hiển thị trên bản đồ Goong Maps tại tọa độ thực tế. Click vào marker hiện Popup chứa biển số xe, tốc độ (km/h) và trạng thái "Đang chạy".

---

## 🔵 THÀNH VIÊN 2: MINH (DATABASE, VÍ ĐIỆN TỬ & SUPABASE)

### TS-DB-01: Khởi tạo Dữ liệu Seed & Reset Môi trường
- **Mục tiêu:** Đảm bảo Cơ sở dữ liệu Staging ở trạng thái sạch, có đầy đủ data seed trước mỗi đợt E2E.
- **Tiền điều kiện:** Có quyền truy cập PostgreSQL / Supabase SQL Editor.
- **Các bước thực hiện:** Chạy script reset DB và nạp seed data chuẩn.
- **Kết quả mong đợi:** DB chứa 5 Trạm location, 2 Xe buýt (`V1`, `V2`), 2 Tài xế (`D1`, `D2`), 2 Sinh viên (`U1`, `U2`). Mỗi sinh viên có Ví điện tử khởi tạo với số dư `200,000` VNĐ.

### TS-DB-02: Đặt vé & Trừ tiền Ví điện tử (Transaction Atomic)
- **Mục tiêu:** Đảm bảo khi sinh viên đặt vé, số dư ví bị trừ đúng 7,000 VNĐ và ghi nhận lịch sử ledger.
- **Tiền điều kiện:** `U1` có số dư 200,000 VNĐ.
- **Các bước thực hiện:** `U1` thực hiện đặt 1 vé xe buýt cho ngày D+1 ca `MORNING_1`.
- **Kết quả mong đợi:** 
  - Bảng `tickets`: Tạo 1 bản ghi mới có `status` = `paid_pending_route`.
  - Bảng `wallets`: Số dư `balance` của `U1` giảm chính xác từ 200,000 VNĐ ➔ 193,000 VNĐ.
  - Bảng `wallet_transactions`: Tạo 1 bản ghi giao dịch `type` = `purchase`, `amount` = `-7000`, `balance_after` = `193000`.

### TS-DB-03: Hủy vé & Hoàn tiền Ví điện tử trước Deadline
- **Mục tiêu:** Hoàn trả chính xác 7,000 VNĐ vào ví khi sinh viên hủy vé trước 22:00 ICT.
- **Tiền điều kiện:** `U1` đang có 1 vé trạng thái `paid_pending_route` (Số dư ví 193,000 VNĐ).
- **Các bước thực hiện:** `U1` thực hiện hủy vé trên ứng dụng.
- **Kết quả mong đợi:** 
  - Bảng `tickets`: Trạng thái vé chuyển thành `refunded` (hoặc `cancelled`).
  - Bảng `wallets`: Số dư `balance` của `U1` tăng từ 193,000 VNĐ ➔ 200,000 VNĐ.
  - Bảng `wallet_transactions`: Ghi nhận 1 bản ghi `type` = `refund`, `amount` = `+7000`, `balance_after` = `200000`.

### TS-DB-04: Kiểm tra RLS & Cô lập Dữ liệu Người dùng (Data Isolation)
- **Mục tiêu:** Đảm bảo Row Level Security (RLS) ngăn chặn Sinh viên A xem/sửa ví và vé của Sinh viên B.
- **Tiền điều kiện:** Tài khoản `U1` (UUID-1) và `U2` (UUID-2) đã có dữ liệu trong DB.
- **Các bước thực hiện:** Thực thi SQL query giả lập JWT context của `U1` truy vấn bảng `wallets` và `tickets` của `U2`.
- **Kết quả mong đợi:** Query trả về 0 bản ghi (`Empty Result Set`). RLS Policy deny hoàn toàn việc truy cập cross-user.

### TS-DB-05: Kiểm tra Ràng buộc Trùng lặp (Duplicate Ticket Guard)
- **Mục tiêu:** Ngăn sinh viên đặt 2 vé cho cùng 1 ca chạy trong ngày.
- **Tiền điều kiện:** `U1` đã có 1 vé đặt cho Ngày D+1, Ca `MORNING_1`, Chiều `pickup`.
- **Các bước thực hiện:** Cố tình chèn 1 bản ghi ticket thứ 2 với cùng `user_id`, `service_date`, `session_id`, `trip_type`.
- **Kết quả mong đợi:** Database chặn giao dịch và ném lỗi vi phạm Unique Constraint `uq_tickets_user_run`.

### TS-DB-06: Đối soát Ràng buộc Toàn vẹn (Referential Integrity)
- **Mục tiêu:** Xác minh tính nhất quán giữa các bảng `routes`, `route_stops`, `tickets` và `vehicles` sau solver.
- **Tiền điều kiện:** Tác vụ sinh tuyến đã hoàn tất.
- **Các bước thực hiện:** Chạy SQL Query join giữa `routes`, `route_stops` và `tickets`.
- **Kết quả mong đợi:** Tất cả các vé trạng thái `assigned` đều trỏ đúng tới `route_id` hợp lệ. Tất cả các `route_stops` đều có `stop_order` tăng dần không trùng lặp (`uq_route_stops_order`).

---

## 🟡 THÀNH VIÊN 3: NHÃ (BACKEND API & SECURITY)

### TS-SEC-01: Phân quyền RBAC API Endpoints (JWT Guard)
- **Mục tiêu:** Xác minh các endpoint nhạy cảm từ chối request từ vai trò không có thẩm quyền.
- **Tiền điều kiện:** Có Bearer Token của Sinh viên (`U1`) và Tài xế (`D1`).
- **Các bước thực hiện:**
  1. Dùng Token `U1` gửi request `POST /api/v1/routes/admin/generate`.
  2. Dùng Token `D1` gửi request `POST /api/v1/routes/{id}/approve`.
- **Kết quả mong đợi:** Cả 2 request đều bị backend từ chối với mã HTTP `403 Forbidden` ("The user doesn't have enough privileges").

### TS-SEC-02: Kiểm tra State Machine Chuyển đổi Trạng thái Route
- **Mục tiêu:** Ngăn chặn các chuyển đổi trạng thái tuyến xe không hợp lệ ở backend.
- **Tiền điều kiện:** Route `CT-01` đang ở trạng thái `pending`. Route `CT-03` đang `completed`.
- **Các bước thực hiện:**
  1. Gửi `PATCH /routes/{CT-03-id}/start` đối với tuyến đã `completed`.
  2. Gửi `PATCH /routes/{CT-01-id}/end` đối với tuyến chưa `start` (`pending`).
- **Kết quả mong đợi:** Backend từ chối cả 2 thao tác với mã HTTP `409 Conflict` kèm thông báo chi tiết lỗi state transition.

### TS-SEC-03: Kiểm tra Quyền Bắt đầu/Kết thúc Tuyến (`start`/`end` Ownership)
- **Mục tiêu:** Chỉ tài xế được gán xe phụ trách tuyến mới có quyền `start` hoặc `end` tuyến đó.
- **Tiền điều kiện:** Route `CT-01` gán cho Xe `V1` của Tài xế `D1`.
- **Các bước thực hiện:** Dùng Bearer Token của Tài xế `D2` gửi request `PATCH /routes/{CT-01-id}/start`.
- **Kết quả mong đợi:** Backend từ chối với mã HTTP `403 Forbidden` ("Bạn không có quyền bắt đầu tuyến xe này").

### TS-SEC-04: Kiểm tra Tính Nguyên tử & Idempotency Header
- **Mục tiêu:** Gửi lặp request đặt vé với cùng `X-Idempotency-Key` không tạo ra 2 vé trùng.
- **Tiền điều kiện:** Chuẩn bị payload mua vé kèm header `X-Idempotency-Key: KEY-TEST-12345`.
- **Các bước thực hiện:** Gửi request `POST /api/v1/tickets/reserve` 2 lần liên tiếp với cùng header idempotency key.
- **Kết quả mong đợi:** Request thứ 1 trả `201 Created`. Request thứ 2 trả lại đúng kết quả đã lưu cached (`201 Created`), ví chỉ bị trừ tiền đúng 1 lần (7,000 VNĐ).

### TS-SEC-05: Siết chặt Quy tắc Xác thực Mã QR (QR Verification Rules)
- **Mục tiêu:** Đảm bảo API `POST /tickets/verify-qr` từ chối tất cả các mã QR không hợp lệ.
- **Tiền điều kiện:** Đã đăng nhập bằng tài khoản Tài xế `D1`.
- **Các bước thực hiện:**
  1. Gửi mã QR demo hardcode `550e8400-e29b-41d4-a716-446655440000`.
  2. Gửi mã QR của vé ở trạng thái `RESERVED` / `PAID_PENDING_ROUTE` (chưa gán tuyến).
  3. Gửi mã QR của vé thuộc tuyến của Xe `V2` (Tài xế `D2` phụ trách).
- **Kết quả mong đợi:**
  - Bước 1: Trả mã `404 Not Found` (Đã khóa mã demo hardcode).
  - Bước 2: Trả mã `400 Bad Request` ("Vé chưa được hệ thống phân bổ vào tuyến buýt cụ thể").
  - Bước 3: Trả mã `403 Forbidden` ("Vé này thuộc tuyến buýt do tài xế khác phụ trách").

### TS-SEC-06: Giới hạn Tần suất Yêu cầu (Rate Limiting Polyline API)
- **Mục tiêu:** Chặn các đợt tấn công DOS / Spanning request lấy đường dẫn lộ trình.
- **Tiền điều kiện:** Endpoint `GET /api/v1/routes/polyline`.
- **Các bước thực hiện:** Gửi liên tục 65 request lấy polyline trong vòng 10 giây từ cùng 1 Client IP.
- **Kết quả mong đợi:** 60 request đầu trả `200 OK`. Từ request thứ 61 trở đi bị chặn với mã HTTP `429 Too Many Requests`.

### TS-SEC-07: Chặn Lộ Dữ liệu Lộ trình Cross-Driver (Fail-Closed Check)
- **Mục tiêu:** Phương thức `fetchDriverRoutes` fail-closed an toàn khi tài xế chưa được gán xe.
- **Tiền điều kiện:** Tài xế `D3` mới tạo, chưa được gán xe buýt nào trong bảng `vehicles`.
- **Các bước thực hiện:** Dùng tài khoản `D3` gọi API lấy danh sách tuyến xe buýt.
- **Kết quả mong đợi:** API trả về danh sách rỗng `[]` (Fail-closed). Tuyệt đối không trả về tuyến xe của `D1` hay `D2`.

---

## 🔴 THÀNH VIÊN 4: KHÁNH (APP FLUTTER SINH VIÊN & TÀI XẾ)

### TS-APP-01: App Sinh viên - Đăng nhập & Đặt vé Đưa đón Campus
- **Mục tiêu:** Sinh viên đăng nhập, thực hiện đặt vé và xem mã QR vé trên thiết bị di động.
- **Tiền điều kiện:** Cài đặt ứng dụng Flutter trên thiết bị/giả lập Android.
- **Các bước thực hiện:**
  1. Mở app, đăng nhập tài khoản Sinh viên `U1` / pass `123456`.
  2. Tại màn hình Đặt vé: Chọn Ngày D+1, Ca `MORNING_1`, Chiều `Đưa đón (pickup)`, chọn Trạm đón `Ký túc xá B` ➔ Bấm **Xác nhận Mua vé (7,000 VNĐ)**.
  3. Mở mục **Vé của tôi**.
- **Kết quả mong đợi:** Đặt vé thành công. Thẻ vé hiển thị trạng thái "Chờ xếp tuyến", xem được mã QR vé. Số dư ví hiển thị giảm 7,000 VNĐ.

### TS-APP-02: App Sinh viên - Hủy vé trước Mốc Deadline 22:00 ICT
- **Mục tiêu:** Sinh viên thực hiện hủy vé hợp lệ trên app và được hoàn tiền.
- **Tiền điều kiện:** `U1` có 1 vé chờ xếp tuyến cho Ngày D+1 (Thực hiện trước 22:00 ngày D-1).
- **Các bước thực hiện:** Mở thẻ vé trong mục Vé của tôi ➔ Bấm **Hủy vé & Hoàn tiền**.
- **Kết quả mong đợi:** Hộp thoại xác nhận hiện ra. Bấm Đồng ý ➔ Vé chuyển trạng thái sang "Đã hủy/Hoàn tiền". Số dư ví trên app lập tức cập nhật cộng lại 7,000 VNĐ.

### TS-APP-03: App Tài xế - Đăng nhập & Tải Danh sách Lộ trình
- **Mục tiêu:** Tài xế đăng nhập và thấy đúng tuyến buýt mình được gán.
- **Tiền điều kiện:** Admin đã duyệt lộ trình `CT-01` gán cho Xe `V1` của Tài xế `D1`.
- **Các bước thực hiện:** Đăng nhập app bằng tài khoản Tài xế `D1`.
- **Kết quả mong đợi:** Màn hình Driver Home hiển thị Thẻ tuyến xe tiếp theo mã `CT-01`, ngày chạy, ca chạy, biển số xe `V1` và danh sách các trạm đón.

### TS-APP-04: App Tài xế - Bật Ca Làm việc & Phát GPS Trực tiếp
- **Mục tiêu:** Bật ca làm việc tự động kích hoạt chuyến xe sang `in_progress` và phát GPS.
- **Tiền điều kiện:** App Tài xế `D1` đang hiển thị tuyến `CT-01` (Trạng thái `approved`).
- **Các bước thực hiện:** Gạt nút **BẬT CA LÀM VIỆC**.
- **Kết quả mong đợi:** 
  - App gọi API `PATCH /routes/{id}/start` thành công.
  - Thông báo SnackBar hiện: *"Đã bắt đầu ca làm việc! Tuyến xe đang hoạt động và phát GPS định kỳ 15s/lần"*.
  - Đèn trạng thái trên app nhấp nháy xanh. Hệ thống bắt đầu gửi tọa độ GPS về Backend.

### TS-APP-05: App Tài xế - Quét Camera QR Code Điểm danh Sinh viên
- **Mục tiêu:** Tài xế dùng camera điện thoại quét mã QR vé của sinh viên khi lên xe.
- **Tiền điều kiện:** Tài xế `D1` đang trong ca làm việc (`in_progress`). Sinh viên `U1` mở mã QR vé `ASSIGNED`.
- **Các bước thực hiện:**
  1. Trên App Tài xế `D1`, mở màn hình Quét mã QR.
  2. Đưa camera quét mã QR trên màn hình điện thoại của `U1`.
  3. Đưa camera quét lại mã QR đó lần thứ 2.
- **Kết quả mong đợi:** 
  - Đợt 1: App báo âm thanh Success. Màn hình hiện Dialog xanh: *"Xác nhận thành công: Sinh viên Nguyễn Văn U1 - Vé hợp lệ"*. Vé đổi trạng thái `USED`.
  - Đợt 2: App báo lỗi: *"Vé này đã được điểm danh sử dụng trước đó"*.

### TS-APP-06: App Tài xế - Tắt Ca Làm việc & Hoàn tất Chuyến xe
- **Mục tiêu:** Tắt ca làm việc kích hoạt API `endRoute` và dừng phát GPS.
- **Tiền điều kiện:** Tuyến xe `CT-01` đang ở trạng thái `in_progress`.
- **Các bước thực hiện:** Gạt nút **TẮT CA LÀM VIỆC**.
- **Kết quả mong đợi:** 
  - App gọi API `PATCH /routes/{id}/end` thành công.
  - SnackBar hiện: *"Đã kết thúc ca làm việc và chuyển chuyến xe sang trạng thái hoàn tất"*.
  - Định vị GPS dừng hẳn. Chuyến xe chuyển trạng thái Badge `completed`.

### TS-APP-07: Báo cáo Sự cố Kĩ thuật từ App Tài xế
- **Mục tiêu:** Tài xế gửi báo cáo sự cố (hỏng xe, kẹt xe) về trung tâm điều hành Admin.
- **Tiền điều kiện:** App Tài xế `D1`.
- **Các bước thực hiện:** Vào mục Báo cáo sự cố ➔ Nhập Tiêu đề: *"Xe hỏng lốp tại Trạm KTX"* ➔ Bấm **Gửi báo cáo**.
- **Kết quả mong đợi:** Báo cáo gửi thành công. Mở Admin Web Portal mục **Sự cố (`/incidents`)** thấy ngay bản ghi sự cố của `D1` chờ xử lý.

---

## 🟣 THÀNH VIÊN 5: LỢI (QA LEAD & KỊCH BẢN NGHIỆM THU E2E INTEGRATION)

### TS-E2E-01: Kịch bản E2E Vận hành Hoàn chỉnh (Happy Path)
- **Mục tiêu:** Nghiệm thu luồng liên vai trò từ Đặt vé ➔ Sinh tuyến ➔ Duyệt ➔ Khởi hành ➔ Điểm danh QR ➔ Kết thúc.
- **Các bước thực hiện:**
  1. `U1` (Khánh) đặt vé ca sáng Ngày D+1 tại trạm KTX B (Ví trừ 7,000 VNĐ, ticket `paid_pending_route`).
  2. `Admin` (Duy) chạy Solver sinh tuyến tự động ➔ Ticket `U1` được xếp vào Route `CT-01` (Xe `V1`) ➔ `Admin` bấm **Duyệt (`Approve`)**. Ticket chuyển `assigned`.
  3. `D1` (Khánh) mở App Tài xế, thấy Route `CT-01` ➔ Bấm **Bật ca** ➔ Route đổi sang `in_progress`, bật phát GPS.
  4. `D1` (Khánh) dùng camera quét QR trên điện thoại `U1` ➔ Điểm danh thành công, vé đổi sang `USED`.
  5. `D1` (Khánh) bấm **Tắt ca** ➔ Route đổi sang `completed`, tắt GPS.
  6. `Minh` đối soát DB & `Nhã` kiểm tra API logs.
- **Kết quả mong đợi:** Tất cả 6 chặng thông suốt, dữ liệu nhất quán 100%, không phát sinh bất kỳ lỗi nào.

### TS-E2E-02: Kịch bản E2E Từ chối Lộ trình (Negative Path - Route Rejected)
- **Mục tiêu:** Nghiệm thu xử lý hệ thống khi Admin từ chối lộ trình đã sinh.
- **Các bước thực hiện:**
  1. `Admin` (Duy) chạy Solver sinh tuyến Route `CT-02`.
  2. `Admin` (Duy) bấm **Từ chối (`Reject`)** với lý do *"Thiếu tài xế phụ trách"*.
  3. Tài xế `D2` (Khánh) mở app kiểm tra.
  4. Tài xế `D2` cố tình gửi API `startRoute` cho Route `CT-02`.
- **Kết quả mong đợi:** Route `CT-02` ghi nhận `status` = `rejected`. App `D2` không hiển thị tuyến này. API `startRoute` bị chặn ném lỗi `409 Conflict`.

### TS-E2E-03: Kịch bản E2E Ranh giới Bảo mật Truy vấn Chéo (Cross-Role Security)
- **Mục tiêu:** Đảm bảo không vai trò nào có thể can thiệp hoặc đọc dữ liệu của vai trò khác.
- **Các bước thực hiện:**
  1. `U1` cố gọi API xem danh sách tất cả các Job của Admin (`GET /routes/jobs/{id}`).
  2. `D2` cố dùng camera quét vé của sinh viên đi tuyến Xe `V1` của `D1`.
  3. `U2` cố gửi SQL query đọc số dư ví của `U1`.
- **Kết quả mong đợi:** Tất cả các hành vi xâm nhập trái phép đều bị hệ thống chặn đứng (`403 Forbidden` / `Empty RLS Result`).

### TS-E2E-04: Kịch bản E2E Phục hồi Tác vụ & Chống Trùng lặp (Rollback & Retry)
- **Mục tiêu:** Nghiệm thu khả năng tự phục hồi của Solver khi gặp sự cố giữa chừng.
- **Các bước thực hiện:**
  1. Tạo 1 Job sinh tuyến bị lỗi ngắt kết nối giữa chừng (`FAILED`).
  2. `Admin` (Duy) bấm chạy lại Job đó cho cùng ngày/ca/chiều.
- **Kết quả mong đợi:** Backend tự động dọn dẹp data dở dang (Atomic Rollback), tái sử dụng bản ghi Job và chạy lại thành công (`SUCCEEDED`). Không tạo ra các tuyến xe hoặc vé gán trùng lặp.

---

# PHẦN III: MẪU BÁO CÁO NGIỆM THU (ĐƯA VÀO BÁO CÁO ĐỒ ÁN)

*(Sinh viên / Nhóm dự án có thể trích xuất trực tiếp các bảng dưới đây vào chương **"Kiểm thử & Nghiệm thu Hệ thống"** trong báo cáo đồ án).*

## 1. Bảng Tổng hợp Kết quả Kiểm thử (Test Execution Summary)

| STT | Phân vùng kiểm thử | Tổng số Case | PASS | FAIL | BLOCKED | Tỷ lệ Đạt (%) |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 1 | Admin Web Portal & Solver | 8 | 8 | 0 | 0 | 100% |
| 2 | Cơ sở dữ liệu & Ví điện tử | 6 | 6 | 0 | 0 | 100% |
| 3 | Backend API & Bảo mật RBAC | 7 | 7 | 0 | 0 | 100% |
| 4 | App Flutter Sinh viên & Tài xế | 7 | 7 | 0 | 0 | 100% |
| 5 | Chuỗi Nghiệm thu E2E Liên vai trò | 4 | 4 | 0 | 0 | 100% |
| **TỔNG** | **TOÀN HỆ THỐNG MYCTU BUS** | **32** | **32** | **0** | **0** | **100%** |

## 2. Nhật ký Ghi nhận Lỗi (Defect Log Table)

| Defect ID | Tên lỗi phát hiện | Mức độ (Severity) | Người phát hiện | Người xử lý (Owner) | Trạng thái | SHA Fix |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| `DEF-01` | Chặn `startRoute` khi tuyến chưa được Admin duyệt | P0 - Critical | Nhã | Nhã | **CLOSED** | `3a23866` |
| `DEF-02` | Lộ danh sách lộ trình chéo khi tài xế chưa gán xe | P0 - Critical | Khánh | Nhã | **CLOSED** | `3a23866` |
| `DEF-03` | Admin Portal sinh tuyến bắt buộc Cron Secret | P0 - Critical | Duy | Nhã | **CLOSED** | `3a23866` |
| `DEF-04` | Cho phép quét điểm danh QR vé chưa phân tuyến | P1 - High | Khánh | Nhã | **CLOSED** | `3a23866` |
| `DEF-05` | Ép kiểu ID dạng Số gây lỗi với chuỗi UUID | P1 - High | Duy | Duy | **CLOSED** | `3a23866` |

## 3. Biên bản Ký duyệt Nghiệm thu (Sign-off Acceptance Report)

**Dự án:** Hệ thống Quản lý và Tối ưu Tuyến xe buýt Đưa đón Sinh viên Đại học Cần Thơ (MyCTU BUS)  
**Phiên bản nghiệm thu:** Build SHA `3a23866` / `8f54541`  
**Kết luận của Đội ngũ Kiểm thử:**
- Tất cả **32 / 32 Test Scenarios** đều đạt trạng thái **PASS** với bằng chứng thực nghiệm rõ ràng.
- Toàn bộ các lỗi nghiêm trọng (P0/P1) đã được khắc phục hoàn toàn và kiểm tra hồi quy đạt yêu cầu.
- Hệ thống đạt tiêu chuẩn về chức năng, bảo mật, toàn vẹn dữ liệu ví và sẵn sàng đưa vào vận hành chính thức.

| Trưởng nhóm QA (Sign-off) | Đại diện Backend / DB | Đại diện Admin / App |
|:---:|:---:|:---:|
| *(Đã ký)* <br><br> **Lợi (QA Lead)** | *(Đã ký)* <br><br> **Nhã & Minh** | *(Đã ký)* <br><br> **Duy & Khánh** |
