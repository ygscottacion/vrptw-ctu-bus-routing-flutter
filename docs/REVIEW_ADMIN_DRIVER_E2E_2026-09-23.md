# Rà soát sẵn sàng kiểm thử Admin → Sinh tuyến → Tài xế

**Ngày rà soát:** 2026-09-23  
**Phạm vi:** Admin web, backend routing/route, app tài xế, hợp đồng sinh tuyến và matrix QA hiện có.  
**Kết luận:** Chưa nên giao team chạy nghiệm thu E2E theo cách hiểu mọi luồng đã sẵn sàng. Có lỗi tích hợp chặn luồng chính và một lỗi phân quyền cần xử lý trước khi dùng dữ liệu thật. Đây là review và kịch bản; không chỉnh sửa hành vi ứng dụng.

## 1. Phát hiện cần xử lý trước kiểm thử nghiệm thu

| Ưu tiên | Phát hiện | Bằng chứng trong repo | Tác động / việc cần làm |
|---|---|---|---|
| P0 | Admin chưa có luồng duyệt lộ trình. Trang `/routes` chỉ render form sinh tuyến; không có danh sách job/tuyến, xem manifest, duyệt/từ chối hay audit trail. | `myctu-bus-admin-web/src/App.tsx`, component `RouteGenerator` | Làm rõ “duyệt” là duyệt demand/trạm trước khi chạy solver hay duyệt kết quả tuyến sau solver. Bổ sung đúng bước nghiệp vụ và trạng thái trước khi gọi đây là E2E admin. |
| P0 | Form admin gọi `POST /routes/generate` với `{date, depot: number}`, trong khi backend yêu cầu `service_date`, `session_id`, `trip_type`, `depot_location_id` UUID và header `X-Cron-Secret`. | `myctu-bus-admin-web/src/App.tsx`; `backend/app/api/v1/endpoints/routes.py::generate_routes`; `backend/app/schemas/route.py` | Luồng bấm nút không khớp request contract; endpoint còn là cron-secret nội bộ, không phải API admin JWT. Cần endpoint admin được RBAC bảo vệ và UI gửi đúng payload; không đưa secret cron vào trình duyệt. |
| P0 | App tài xế gọi `PATCH /routes/{id}/start` và `/end`, nhưng `routes.py` hiện chỉ có generate, GET, detail, polyline; không có hai route mutation này. | `lib/services/api_service.dart::startRoute/endRoute`; `backend/app/api/v1/endpoints/routes.py` | Nút bắt đầu/kết thúc sẽ nhận 404 nếu không có endpoint được mount ở nơi khác. Cần triển khai và kiểm tra ownership/status transition phía server. |
| P0 | Fallback tải tuyến trực tiếp từ Supabase bỏ lọc theo tài xế khi không tìm thấy `vehicleId`, rồi lấy tối đa hai tuyến toàn hệ thống. | `lib/services/api_service.dart::fetchDriverRoutes` | Có nguy cơ hiển thị tuyến của tài xế khác. Bỏ fallback không an toàn hoặc luôn fail closed; xác minh RLS cũng chặn cross-driver. |
| P1 | UI admin dùng ID số cho user/vehicle/depot, còn backend models khai báo UUID; request tạo tuyến ép depot thành `Number`. | `myctu-bus-admin-web/src/App.tsx`; `backend/app/models/vehicle.py`, `backend/app/models/route.py` | Chốt API contract một kiểu ID xuyên suốt (UUID hiện là nguồn chuẩn). Sửa form nhập depot thành dropdown từ `/locations` và truyền UUID. Kiểm tra lại các trang Xe/Người dùng vì đang ép `Number(...)`. |
| P1 | `POST /routes/generate` chạy worker ngay trong request dù trả 202; UI hiển thị thông báo “đang tự động” nhưng không có polling trạng thái job hay xem lỗi/job kết quả. | `backend/app/api/v1/endpoints/routes.py::generate_routes`; `RouteGenerator` | Request có thể kéo dài hoặc phản hồi trạng thái cuối ngay; người vận hành không biết job queued/running/failed. Cần trả job thật và API tra cứu/poll, hiển thị failed/error và chống bấm lặp. |
| P1 | UI tài xế bật ca chỉ đổi state local và gọi GPS; nó chọn tuyến đầu tiên, không gọi `startRoute`. Tắt ca cũng chỉ dừng GPS, độc lập trạng thái route. | `lib/features/driver/driver_home_tab.dart::_toggleShift`; `lib/services/api_service.dart` | Trạng thái ca/tuyến có thể lệch nhau; cần định nghĩa chính xác ca làm việc và chuyến, chọn đúng tuyến/ngày/ca, và đồng bộ trạng thái qua backend. |
| P1 | QR verification chấp nhận `RESERVED` và `PAID_PENDING_ROUTE` dù chưa gán tuyến; đồng thời có hai QR UUID demo hardcoded trả thành công mà không kiểm tra DB. | `backend/app/api/v1/endpoints/tickets.py::verify_ticket_qr` | Có thể check-in vé chưa được phân tuyến; QR demo có thể tạo PASS giả. Tắt fixture trong staging nghiệm thu, chỉ cho trạng thái vé hợp lệ theo business rule và ràng buộc chuyến/xe/ngày. |
| P1 | Matrix E2E cũ đánh dấu 21/21 PASS nhưng bao gồm start/end route, realtime/GPS và QR mà chưa chỉ ra bằng chứng chạy trên đúng build/backend hiện tại; một số PASS tham chiếu report cũ. | `qa_test_matrix_e2e.md`; giới hạn staging ghi ở `KNOWN_LIMITATIONS_staging.md` | Reset trạng thái các ca chưa chạy lại trên commit/build đang bàn giao về NOT RUN; gắn build SHA, môi trường, tài khoản test và evidence thực tế. |
| P2 | Dashboard báo cáo admin có số liệu cố định; realtime map có dữ liệu demo/fallback và WebSocket được ghi nhận chưa auth. | `myctu-bus-admin-web/src/App.tsx`; `KNOWN_LIMITATIONS_staging.md` | Không dùng số liệu đó làm oracle nghiệm thu. Xác nhận bản đồ hiển thị dữ liệu backend thật; giới hạn WebSocket cần xử lý trước production. |

### Quyết định cổng kiểm thử

- **Có thể chạy ngay:** xác minh đăng nhập/role, đọc dữ liệu tuyến hiện có, danh sách tuyến driver theo RBAC, UI trạng thái rỗng/lỗi, cấu hình môi trường.
- **Chưa thể PASS E2E:** admin duyệt, admin sinh job qua UI, start/end route từ tài xế.
- **Không dùng dữ liệu thật trước khi vá:** fallback tuyến thiếu ràng buộc driver và QR demo/hành vi check-in chưa gán tuyến.
- Các test phía dưới vẫn hữu ích để chuẩn bị dữ liệu và tiêu chí; đánh dấu `BLOCKED` ở bước phụ thuộc chức năng còn thiếu, không giả lập thành công.

## 2. Quy ước chạy và dữ liệu chuẩn bị

Chạy trên staging riêng, không dùng production. Ghi lại commit SHA của backend, admin web, Flutter APK; URL môi trường; múi giờ `Asia/Ho_Chi_Minh`; thiết bị/browser; người chạy; thời gian; request/response đã che token; ảnh/video/log và ID bản ghi.

Chuẩn bị tối thiểu:

- Admin hợp lệ và user student/driver không có quyền admin.
- Hai tài xế A/B, hai xe A/B có capacity khác nhau, một xe bảo trì/unassigned.
- Depot và các location có UUID, tọa độ hợp lệ; một location thiếu tọa độ để negative test.
- Ca/ngày test riêng sau 22:00 ICT; một ngày/ca có vé đủ, một ca rỗng, một ca demand vượt tổng capacity.
- Vé: đã gán, chưa gán, đã dùng, đã hủy/refund, sai ngày/ca/trip type; ít nhất hai vé thuộc hai tài xế/tuyến khác nhau.
- Khóa/chặn QR demo fixtures khỏi test dữ liệu thật; nếu chưa thể tắt, ghi riêng là mock và không tính PASS bảo mật.

## 3. Kịch bản E2E đề xuất

### A. Quyền truy cập và dữ liệu ban đầu

| ID | Bước | Kết quả mong đợi |
|---|---|---|
| ADM-01 | Mở admin web khi chưa đăng nhập, đăng nhập bằng admin đúng | Điều hướng vào dashboard; `/auth/me` xác nhận role admin; không lộ token trong URL/log. |
| ADM-02 | Thử đăng nhập bằng driver/student và truy cập trực tiếp `/routes`/API quản trị | UI/API từ chối (401/403); không thể dựa riêng vào ẩn menu phía client. |
| ADM-03 | Đăng xuất rồi dùng nút back/refresh hoặc token hết hạn | Trang quản trị không còn truy cập được; session bị xóa và chuyển login. |
| ADM-04 | Đọc location, xe và driver; kiểm tra UUID, trạng thái, capacity, gán tài xế | Dữ liệu khớp DB; không có ID bị chuyển thành số hoặc dữ liệu demo được trình bày như thật. |

### B. Duyệt nhu cầu/lộ trình (BLOCKED đến khi chốt và có UI/API duyệt)

| ID | Bước | Kết quả mong đợi |
|---|---|---|
| ADM-APP-01 | Admin mở hàng chờ duyệt theo service date/session/trip type; xem tổng vé theo trạm, danh sách điểm, tổng demand/capacity | Hiển thị đủ vé hợp lệ, lọc đúng ngày/ca/chiều; tổng demand khớp các vé chưa gán; có thể mở chi tiết nguồn dữ liệu. |
| ADM-APP-02 | Duyệt demand hợp lệ | Lưu đúng admin, thời gian, phiên bản dữ liệu; trạng thái chuyển một lần sang approved; refresh không tạo bản duyệt trùng. |
| ADM-APP-03 | Từ chối demand và nhập lý do | Không chạy solver; trạng thái rejected và lý do/audit trail được lưu; có thể lọc/tìm lại. |
| ADM-APP-04 | Sửa/hủy vé hoặc location sau khi duyệt, thử chạy với bản duyệt cũ | Hệ thống phát hiện dữ liệu đổi và yêu cầu duyệt lại hoặc áp dụng quy tắc đã thống nhất; không sinh từ demand stale. |
| ADM-APP-05 | Driver/student gọi API duyệt trực tiếp | Bị 403; không thay trạng thái. |

**Cần chốt business:** duyệt demand hay kết quả solver, vai trò nào duyệt, có yêu cầu hai bước không, trạng thái/rollback/re-approval ra sao và audit fields nào bắt buộc.

### C. Sinh tuyến và kiểm tra kết quả

| ID | Bước | Kết quả mong đợi |
|---|---|---|
| RTG-01 | Gửi request thiếu auth/secret theo cơ chế admin đã chốt | Bị 401/403; không tạo job hay route. Cron secret không xuất hiện trong bundle trình duyệt. |
| RTG-02 | Sinh tuyến trước 22:00 ngày D-1 ICT | Bị từ chối; vé/job/routes không đổi. Kiểm tra 21:59:59, 22:00:00, 22:00:01. |
| RTG-03 | Sinh tuyến sau cutoff với demand hợp lệ, depot/xe hợp lệ | Job có ID và trạng thái quan sát được; kết quả cuối rõ succeeded/failed; chỉ vé đủ điều kiện được gán. |
| RTG-04 | Kiểm tra manifest cho mỗi route | Đúng service date/session/trip type/vehicle; route_stops đủ, thứ tự duy nhất/liên tục, location UUID hợp lệ, giờ đến hợp lý; tổng khách không vượt capacity. |
| RTG-05 | Ca không có vé đủ điều kiện | Báo empty/no-demand rõ; không sinh tuyến rỗng thành công giả, không sửa vé. |
| RTG-06 | Demand vượt capacity hoặc không khả thi time window | Báo thiếu xe/không khả thi, nêu nguyên nhân; không gán thiếu/nhân đôi vé; không báo succeeded giả. |
| RTG-07 | Depot/location không tồn tại hoặc thiếu tọa độ | Validation từ chối hoặc job failed dễ hiểu; không có route/stops/assignment dở dang. |
| RTG-08 | Bấm tạo hai lần đồng thời cho cùng ngày/ca/chiều | Tối đa một job active, không route/assignment trùng; lần hai trả job hiện tại hoặc conflict theo contract. |
| RTG-09 | Retry job FAILED sau khi sửa nguyên nhân | Attempt/audit rõ; dọn dữ liệu dở dang atomically; không tạo route duplicate. |
| RTG-10 | Tạo lại ca đã SUCCEEDED | Bị chặn 409 hoặc có re-run chủ đích với xác nhận/audit; không chạy trùng âm thầm. |
| RTG-11 | Lỗi giữa ghi routes, stops và gán vé | Transaction rollback toàn bộ; job failed có lỗi; không để vé gán vào route thiếu stops. |
| RTG-12 | Refresh trang/poll job hoặc mở lại sau khi job xong | Trạng thái và kết quả vẫn truy xuất được; không chỉ hiện toast tạm thời. |

### D. Phân công xe và tài xế

| ID | Bước | Kết quả mong đợi |
|---|---|---|
| ASN-01 | Admin gán một driver cho một vehicle hợp lệ | API dùng UUID; xe hiển thị đúng tài xế sau refresh; route mới phản ánh đúng xe. |
| ASN-02 | Gán driver không tồn tại, user không phải driver hoặc xe không tồn tại | Validation 4xx; dữ liệu cũ không đổi. |
| ASN-03 | Gán một driver cho hai xe/đổi tài xế khi chuyến đang chạy | Áp đúng quy tắc đã chốt, không để hai xe/tuyến mơ hồ; thao tác đang chạy bị chặn hoặc audit đầy đủ. |
| ASN-04 | Driver A gọi list/detail route của B hoặc sửa route không thuộc xe A | List không trả tuyến B; detail/mutation trả 403/404; DB không đổi. Lặp qua query trực tiếp/Supabase fallback. |
| ASN-05 | Admin bỏ gán rồi gán lại | Trạng thái khớp backend; lỗi được hiển thị, không bị nuốt im lặng. |

### E. App tài xế: nhận chuyến, chạy tuyến, GPS, QR, sự cố

| ID | Bước | Kết quả mong đợi |
|---|---|---|
| DRV-01 | Đăng nhập driver A, tải trang chủ khi có tuyến và khi không có | Chỉ thấy route thuộc xe A; phân biệt empty state với lỗi mạng; hiển thị đúng ngày/ca/chiều/xe/số trạm/khách từ API. |
| DRV-02 | Tải tuyến khi endpoint chính lỗi và fallback bật | Không thấy tuyến B hay tuyến toàn hệ thống; hiển thị lỗi/empty an toàn. **BLOCKED bởi fallback hiện tại.** |
| DRV-03 | Bắt đầu tuyến pending | Server chuyển pending → in_progress đúng một lần; double tap/retry không tạo hiệu ứng kép. **BLOCKED: chưa thấy endpoint start trong backend.** |
| DRV-04 | Bắt đầu route đã in_progress/completed hoặc không thuộc xe | Báo trạng thái không hợp lệ hoặc 403; không cập nhật route khác. |
| DRV-05 | Xem bản đồ và danh sách điểm dừng | Marker/polyline đúng route, thứ tự/vị trí; lỗi Goong hiển thị fallback có nhãn, không giả vị trí thật. |
| DRV-06 | Bật ca/GPS, cấp quyền, quan sát lần gửi; thu hồi quyền/mất GPS/mất mạng | Chỉ gửi cho driver/route active; tọa độ hợp lệ; lỗi/retry kiểm soát; không tạo dữ liệu giả. |
| DRV-07 | Tắt ca/kết thúc tuyến | Server chuyển in_progress → completed theo nghiệp vụ; GPS dừng; không check-in tiếp nếu route đóng. **BLOCKED nếu chỉ dừng timer client.** |
| DRV-08 | Quét QR vé ASSIGNED đúng tuyến/ngày/ca | Một lần scan chuyển vé sang trạng thái check-in chuẩn; đúng thông tin SV; response và DB nhất quán. |
| DRV-09 | Quét lặp cùng vé hoặc hai tài xế scan đồng thời | Chỉ một thao tác thành công; lần sau báo đã sử dụng; không có race hai check-in thành công. |
| DRV-10 | Quét random, canceled/refunded, sai ngày/ca, chưa gán tuyến, tuyến xe khác | Từ chối rõ; DB giữ nguyên. **BLOCKED bởi QR fixtures và rule hiện có.** |
| DRV-11 | Báo sự cố đủ/thiếu mô tả, xe và mất mạng | Sự cố gắn đúng driver/vehicle; admin thấy và resolve; driver thấy cập nhật sau refresh. |
| DRV-12 | Mở profile, alerts/notifications, settings và đăng xuất | Dữ liệu đúng user; empty/error rõ; logout xóa session và không tiếp tục phát GPS. |

### F. Đối soát sau một vòng E2E

| ID | Bước | Kết quả mong đợi |
|---|---|---|
| AUD-01 | Đối chiếu DB/API sau flow vé → approval → job → route/stops → driver → GPS → QR → complete | Mỗi vé gán đúng một route; stops/vehicle đúng; trạng thái hợp lệ; timestamp có timezone và hiển thị ICT. |
| AUD-02 | Kiểm tra audit/log và quyền | Có actor/time/status transition/error correlation ID; không log token/cron secret; student/driver không đọc/sửa chéo dữ liệu. |
| AUD-03 | Chạy lại cùng input sau hoàn tất | Idempotency rõ; không tạo duplicate job/route/assignment. |

## 4. Điều kiện bàn giao cho team QA

1. Chốt và triển khai quy trình admin duyệt; bổ sung API/UI sinh job dùng UUID, session/trip type và trạng thái job.
2. Bổ sung API start/end route có RBAC và transition hợp lệ; nối nút tài xế với trạng thái server.
3. Sửa fallback route để luôn giới hạn theo tài xế; kiểm thử cross-driver.
4. Chốt quy tắc check-in và tắt QR fixture trong build nghiệm thu.
5. Chuẩn hóa ID/response contract giữa React, FastAPI, Supabase và Flutter; bỏ mock khỏi tiêu chí nghiệm thu.
6. Chạy lại các case cũ trên đúng build; cập nhật PASS chỉ khi có evidence và trạng thái backend xác nhận.

**Quy tắc kết quả:** `PASS` chỉ khi có evidence UI + API/DB phù hợp; `FAIL` khi lệch expected; `BLOCKED` khi thiếu endpoint/luồng hoặc môi trường không đáp ứng; `NOT RUN` khi chưa thực hiện. Không kế thừa PASS từ report cũ sang build mới.

