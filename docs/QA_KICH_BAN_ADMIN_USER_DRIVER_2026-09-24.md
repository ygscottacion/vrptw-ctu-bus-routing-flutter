# Kịch bản kiểm thử nghiệm thu Admin, User và Driver

**Ngày rà soát:** 2026-09-24  
**Phạm vi:** Luồng hiện có trong admin web, Flutter user/driver và FastAPI backend.  
**Trạng thái sẵn sàng:** Luồng admin sinh tuyến/duyệt và driver start/end đã được bổ sung từ vòng rà soát trước. Tuy nhiên chưa thể sign-off: còn lỗi chặn trạng thái job, state machine duyệt tuyến, bảo mật truy vấn job, và wallet/user screens còn dữ liệu local/mock. Các ca liên quan được đánh dấu **BLOCKED** cho tới khi sửa; các ca khác có thể chạy trên staging và ghi PASS/FAIL.

## 1. Phát hiện của vòng rà soát này

| Mức | Phát hiện | Bằng chứng / ảnh hưởng |
|---|---|---|
| P0 | Tài xế có thể start tuyến `pending` hoặc `rejected`; API start chỉ chặn `completed`, không bắt buộc `approved`. | `backend/app/api/v1/endpoints/routes.py::start_route`. Bước admin duyệt hiện không phải điều kiện vận hành. Sửa state transition trước khi nghiệm thu. |
| P1 | Admin poll job so sánh `QUEUED/RUNNING/SUCCEEDED` viết hoa, backend serialize enum thành `queued/running/succeeded/failed` chữ thường. | `myctu-bus-admin-web/src/App.tsx::pollJobStatus`; `backend/app/models/route_job.py`. Poll dừng sớm, không refresh route sau khi thành công. Chuẩn hóa enum casing. |
| P1 | `GET /routes/jobs/{job_id}` chỉ yêu cầu đăng nhập bất kỳ role nào; không giới hạn admin hoặc job được phép xem. | `backend/app/api/v1/endpoints/routes.py::read_job_status`. Thêm RBAC; test user/driver không dò job/error data của admin. |
| P1 | API approve/reject không kiểm tra trạng thái hiện tại; có thể approve tuyến đã rejected/completed/in_progress hoặc reject tuyến đã chạy. | `approve_route`, `reject_route` trong `routes.py`. Chỉ cho transition hợp lệ (thường pending → approved/rejected); các trạng thái khác trả 409. |
| P1 | Home user hiển thị số dư local cố định 500.000đ, thao tác nạp/rút không nối wallet backend; repository ví chỉ TODO. | `lib/screens/home_screen.dart`, `lib/features/wallet/wallet_repository.dart`. Không dùng số dư trên UI làm tiêu chí đối soát; chức năng ví cần nối API hoặc ghi rõ mock. |
| P1 | Reviews là danh sách trong RAM, schema dùng ID số trong khi hệ thống route/profile dùng UUID; không có kiểm tra chuyến đã hoàn tất/quyền đã đi. | `backend/app/api/v1/endpoints/reviews.py`. Chỉ kiểm thử giao diện mock; không nghiệm thu lưu review cho tới khi chuyển DB và thống nhất ID. |
| P1 | Notifications user hiện là danh sách mock local; trạng thái đọc cũng không lưu server. | `lib/screens/notification_screen.dart`. Không coi push/thông báo bền vững là chức năng backend đã đạt. |
| P2 | Tài xế chọn tuyến đầu tiên từ danh sách, chưa lọc rõ theo ngày, status approved hoặc “chuyến tiếp theo”; nếu không có routeId thì bật ca vẫn có thể set local active. | `driver_home_tab.dart`. Cần chọn tuyến phù hợp, bắt buộc route hợp lệ trước khi bật ca và khôi phục shift state từ server. |
| P2 | Có test file mới cho approval/driver nhưng phần hiện đọc được chưa thiết lập DB fixture thực tế; vòng này chưa chạy test hoặc build. | `backend/app/tests/test_route_approval_and_driver_flow.py`. Không xem sự tồn tại của file test là bằng chứng PASS; cần test hồi quy và staging evidence sau khi sửa. |

### Quyết định sẵn sàng

- **Đã có thể kiểm thử chức năng (chưa đồng nghĩa đã PASS):** UI admin sinh tuyến, xem danh sách/manifest, duyệt/từ chối; API start/end và QR validation; user mua/hủy vé bằng ticket/wallet backend; driver route fetch fail-closed khi thiếu vehicle.
- **BLOCKED nghiệm thu:** start tuyến chỉ sau duyệt; job poll/status và phân quyền job; quy trình ví trong UI; review persistence; notifications server-backed.
- Wallet tiền thật/payment gateway không thuộc phạm vi MVP. Seed wallet chỉ dùng staging test; không thực hiện giao dịch thật.

## 2. Cách chạy và quy tắc ghi nhận

Chạy staging riêng. Trước mỗi lượt ghi commit SHA của backend/admin/Flutter, URL môi trường, thời điểm ICT, thiết bị/browser, tài khoản test (không ghi mật khẩu/token), ID job/route/ticket/transaction và evidence đã che thông tin nhạy cảm.

Dữ liệu cần chuẩn bị:

- Admin A; user/sinh viên U1, U2; driver D1, D2.
- Xe V1 → D1, V2 → D2; một xe chưa gán hoặc bảo trì.
- Depot và ít nhất ba trạm có UUID/tọa độ hợp lệ; một trạm không nằm trên manifest.
- Ngày chạy D có ca đủ demand, ca rỗng, và ca vượt capacity; kiểm tra deadline D-1 lúc 21:59:59, 22:00:00, 22:00:01 ICT.
- U1 wallet đủ số dư, U2 số dư thấp; vé assigned/used/cancelled/refunded và vé chưa phân tuyến.
- Không dùng QR/demo fixture. Chỉ dùng QR của ticket thực tạo trong staging.

**Kết quả:** PASS khi expected được xác minh ở UI và API/DB; FAIL khi lệch; BLOCKED khi code/contract chưa hỗ trợ; NOT RUN khi chưa chạy. Chỉ ghi PASS với evidence của build đang được nghiệm thu.

## 3. Admin Portal

| ID | Kiểm thử / bước | Kết quả mong đợi | Trạng thái rà soát |
|---|---|---|---|
| ADM-01 | Mở portal chưa login; login Admin A; refresh, logout rồi back | Chỉ admin vào được; token hết hạn/logout quay về login; không lộ token | Có thể chạy |
| ADM-02 | Login bằng U1/D1; thử mở UI admin và gọi API admin trực tiếp | 401/403; không sinh job, sửa xe hoặc duyệt route | Có thể chạy |
| ADM-03 | Tạo job với ngày, ca, trip type, depot hợp lệ sau cutoff | Payload UUID đúng; job được tạo một lần; UI theo dõi tới terminal state và refresh danh sách route | **BLOCKED:** lowercase status làm poll dừng/không refresh |
| ADM-04 | Tạo job trước cutoff; depot UUID sai; payload thiếu/enum sai | 4xx rõ; không tạo job/route hoặc thay đổi vé | Có thể chạy |
| ADM-05 | Cùng ngày/ca/chiều bấm submit liên tục/hai request song song | Chỉ một job active; không có route hoặc assignment trùng | Có thể chạy |
| ADM-06 | Mở manifest route vừa sinh, đối chiếu xe/số khách/distance/trạm/thứ tự/arrival time | Số liệu khớp DB; stops có order duy nhất, location đúng; khách không quá capacity | Có thể chạy |
| ADM-07 | Duyệt route pending | Status thành approved; approved_by/approved_at lưu đúng; sau reload vẫn approved | Có thể chạy |
| ADM-08 | Từ chối pending route với lý do rỗng/ngắn/hợp lệ | Lý do không hợp lệ bị chặn; lý do hợp lệ lưu; tài xế không được chạy route rejected | **BLOCKED:** server start vẫn chấp nhận rejected |
| ADM-09 | Approve/reject route đã approved/rejected/in_progress/completed | Transition không hợp lệ trả 409 và trạng thái/audit không đổi | **BLOCKED:** API chưa kiểm soát transition |
| ADM-10 | U1/D1 gọi `GET /routes/jobs/{job_id}` của job admin | 403 (hoặc 404 theo policy); admin xem được | **BLOCKED:** endpoint hiện cho mọi authenticated profile |
| ADM-11 | Gán/bỏ gán xe cho driver, refresh, nhập ID không hợp lệ | UUID chính xác, backend/UI đồng nhất; lỗi 4xx hiển thị, dữ liệu không đổi | Có thể chạy |
| ADM-12 | Xem dashboard/report/map và so với DB | Chỉ số khớp dữ liệu thật; dữ liệu demo phải được gắn nhãn | **BLOCKED nếu dashboard/map còn mock/fallback** |
| ADM-13 | Admin xem và resolve incident do D1 tạo | Incident gắn đúng driver/xe; resolved bền vững sau reload | Có thể chạy |

## 4. User / Sinh viên

| ID | Kiểm thử / bước | Kết quả mong đợi | Trạng thái rà soát |
|---|---|---|---|
| USR-01 | Đăng nhập U1, xem profile/home; đăng xuất và thử mở màn sau logout | Role student; dữ liệu đúng tài khoản; session bị xóa khi logout | Có thể chạy |
| USR-02 | Xem location/tuyến và chi tiết manifest trên map/ticket screen | Chỉ hiển thị tuyến active/được phép; trạm, thứ tự, ngày/ca và thời gian đúng API | Có thể chạy; xác minh filter API |
| USR-03 | Mua vé hợp lệ trước 22:00 ngày D-1 | Ticket được tạo `paid_pending_route`; wallet giảm đúng giá một lần; ledger purchase và balance_after khớp | Có thể chạy bằng API/DB; UI wallet balance không đáng tin |
| USR-04 | Mua sau cutoff; U2 mua khi thiếu tiền; location không tồn tại | Request bị từ chối; không tạo ticket/ledger và không trừ số dư | Có thể chạy |
| USR-05 | Gửi lặp purchase cùng idempotency key; thử mua trùng cùng user/date/session/trip | Trả lại kết quả idempotent hoặc từ chối duplicate theo contract; chỉ một vé và một giao dịch trừ | Có thể chạy |
| USR-06 | Hủy vé pending/reserved trước cutoff; gọi hủy lặp; hủy sau cutoff/đã assigned | Hoàn tiền đúng một lần; trạng thái vé/ledger/balance nhất quán; trường hợp không hợp lệ bị chặn | Có thể chạy, đối soát DB |
| USR-07 | Sau sinh tuyến, mở vé assigned và QR; U2 cố đọc ticket U1 | U1 thấy vé/QR đúng; U2 bị 403/404 hoặc không có kết quả | Có thể chạy |
| USR-08 | So sánh số dư home với wallet DB sau mua/hủy; bấm nạp/rút | UI phải khớp backend nếu chức năng được bật; không chấp nhận thao tác local giả như giao dịch | **BLOCKED:** wallet UI local/mock, chưa có API balance/deposit/withdraw |
| USR-09 | Mở notifications, đánh dấu đã đọc, restart app/đăng nhập thiết bị khác | Thông báo và read state đồng bộ server nếu tính năng được nghiệm thu | **BLOCKED:** notifications local mock |
| USR-10 | Gửi review route đã hoàn tất; gửi rating 0/6, review route chưa đi, U2 sửa review U1 | Rating 1–5; chỉ chủ chuyến đủ điều kiện được đánh giá; dữ liệu lưu bền vững và tách user | **BLOCKED:** reviews mock RAM, ID contract chưa khớp |
| USR-11 | Đặt/đổi booking nếu màn hình/API booking được bật; chọn trạm không thuộc route | Chỉ vé của chính user và stop thuộc route; sửa trước trạng thái/deadline được phép; chặn cross-user | Chỉ chạy nếu booking UI nằm trong build nghiệm thu; API hiện có contract riêng cần kiểm tra |

### Đối soát user wallet

Không dùng con số 500.000đ hiển thị ở trang home làm expected. Ghi số dư thật trong DB trước/sau; mỗi purchase phải có đúng một transaction `purchase`, mỗi refund đúng một `refund`; tổng balance_after phải khớp ledger. Nếu UI vẫn hiển thị dữ liệu demo, đánh dấu case USR-08 BLOCKED thay vì PASS.

## 5. Driver App

| ID | Kiểm thử / bước | Kết quả mong đợi | Trạng thái rà soát |
|---|---|---|---|
| DRV-01 | Login D1 có approved route và D2 không có route; refresh/re-login | Mỗi driver chỉ thấy route gắn vehicle mình; empty state phân biệt lỗi tải | Có thể chạy; xác minh role/API |
| DRV-02 | D1 tải tuyến khi REST API lỗi và Supabase fallback chạy | Không trả route V2 hoặc route không assigned cho D1 | Có thể chạy; code hiện trả [] nếu không tìm được vehicle |
| DRV-03 | D1 start route approved; kiểm tra server và map/GPS | Route chuyển approved → in_progress một lần; owner mới được phép; GPS bắt đầu gắn đúng route | **BLOCKED:** hiện backend start chuyển cả pending/rejected |
| DRV-04 | D1 start pending/rejected/completed; D2 start route V1 | Trả 409 cho trạng thái không hợp lệ, 403 cho sai owner; DB không đổi | **BLOCKED:** pending/rejected hiện được start; phải vá rồi chạy |
| DRV-05 | Bật GPS, cấp quyền; mất quyền, mất mạng, khôi phục; so log/location | Chỉ gửi khi route active; tọa độ/time hợp lệ; xử lý lỗi rõ, không báo gửi thành công giả | Có thể chạy, staging GPS foreground |
| DRV-06 | D1 quét QR ticket ASSIGNED route V1 | Check-in thành công một lần; thông tin user/route đúng; ticket thành used | Có thể chạy; đối chiếu DB |
| DRV-07 | Quét lại ticket used, ticket reserved/paid_pending, cancelled/refunded, random QR | Từ chối; trạng thái ticket không đổi | Có thể chạy |
| DRV-08 | D2 quét QR ticket của route V1; scan đồng thời hai thiết bị | D2 bị 403; scan đồng thời chỉ một check-in thắng | Có thể chạy; cần kiểm tra race trên staging |
| DRV-09 | Kết thúc route in_progress; kết thúc pending; gửi lại end sau completed | In-progress → completed; pending trả 409; gửi lặp idempotent theo policy; GPS dừng | Có thể chạy sau DRV-03 |
| DRV-10 | Bật/tắt ca khi không có route hoặc route không được duyệt | Không bật shift/GPS; UI giải thích cần route approved | **BLOCKED:** cần sửa chọn route/status và chặn local active |
| DRV-11 | Tạo incident, xem lịch sử; Admin resolve; D1 refresh | Incident đúng actor/vehicle; state resolved thấy sau reload | Có thể chạy |
| DRV-12 | Mở profile/alerts, logout khi GPS đang bật | Dữ liệu cá nhân đúng; logout dừng timer/GPS và xóa session | Có thể chạy |

## 6. E2E liên vai trò

| ID | Luồng | Tiêu chí đạt |
|---|---|---|
| E2E-01 | Admin sinh tuyến → xem manifest → approve → D1 nhận tuyến → start → GPS → U1 check-in → end | Route đi đúng chuỗi pending → approved → in_progress → completed; ticket paid_pending_route → assigned → used; cùng service date/session/trip type và vehicle xuyên suốt. Chỉ PASS sau khi khóa start-before-approval và sửa job polling. |
| E2E-02 | Admin reject → driver thử xem/start → user ticket liên quan | Driver không thể chạy rejected; vé được giữ/hoàn/đưa về xử lý theo business rule đã chốt; lý do reject có audit. |
| E2E-03 | D1/U1 thử truy cập job, route, ticket của D2/U2; gọi API ngoài UI | Tất cả đọc/sửa chéo bị 403/404; DB không đổi. |
| E2E-04 | Job failed giữa khi ghi route/stops/ticket assignments rồi retry | Rollback sạch; retry không tạo duplicate; mọi vé được gán đúng một lần hoặc còn pending theo policy. |

## 7. Điều kiện trước sign-off

1. Chuẩn hóa status casing và để admin poll tới terminal state, refresh route thành công.
2. Chỉ cho start route đã approved; chặn approve/reject transition sau khi route rời pending; bổ sung regression test cho state machine.
3. Bảo vệ truy vấn job bằng admin role (hoặc policy ownership rõ ràng).
4. Nối wallet home với API backend hoặc ẩn/đánh dấu rõ nạp/rút và balance là demo; không trộn số dư giả với ledger thật.
5. Quyết định reviews/notifications là MVP server-backed hay mock ngoài phạm vi nghiệm thu; ghi rõ trong acceptance scope.
6. Chạy build/API integration trên staging; lưu evidence cho từng case. Matrix E2E cũ đang chứa PASS từ vòng trước và không được coi là bằng chứng của build hiện tại.


