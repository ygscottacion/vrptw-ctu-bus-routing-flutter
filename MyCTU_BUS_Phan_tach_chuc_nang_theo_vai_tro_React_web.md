MYCTU BUS
Ứng dụng xe buýt đưa đón sinh viên Trường Đại học Cần Thơ
BẢN THẢO PHÂN TÁCH CHỨC NĂNG THEO VAI TRÒ TÀI KHOẢN
Sinh viên · Tài xế (ứng dụng di động Flutter)  ·  Quản trị viên (ứng dụng web React)
# 1. Hiện trạng hệ thống
Qua kiểm tra mã nguồn Flutter (thư mục lib/), ứng dụng hiện có cơ chế đăng nhập và trả về trường role (admin / driver / student) từ backend (endpoint /auth/login), đồng thời đã có sẵn API dành riêng cho tài xế (/routes/driver/{id}) và cho quản trị (/vehicles/, /routes/generate). Tuy nhiên, ở tầng giao diện, toàn bộ người dùng — dù là khách, sinh viên, tài xế hay admin — đều nhìn thấy chính xác 5 tab giống nhau: Trang chủ, Bản đồ, Vé, Thông báo, Cài đặt (khai báo cứng trong MainShell tại lib/main.dart).
Nói cách khác: có "nhãn" phân quyền (role được lưu trong _currentUser) nhưng chưa có "luồng điều hướng" và "bộ màn hình" riêng cho từng vai trò. Tài xế đăng nhập vẫn thấy màn hình mua vé của sinh viên; Admin đăng nhập vẫn không có nơi quản lý xe/tuyến dù API đã tồn tại.
Ghi chú: tài liệu này là bản thảo (đề xuất) về phạm vi chức năng cho từng vai trò, làm cơ sở để lập trình tách luồng — không phải là code đã triển khai. Cập nhật quan trọng: vai trò Admin không còn nằm trong ứng dụng di động Flutter, mà được tách thành một ứng dụng web độc lập xây dựng bằng React, dùng chung backend API với app di động.
✅ = có sẵn/phù hợp   ⚠️ = có nhưng cần giới hạn lại   ❌ = không phù hợp, cần ẩn đi   ➡️ = chuyển hoàn toàn sang ứng dụng web quản trị riêng
# 2. Nguyên tắc thiết kế phân quyền
Một điểm vào duy nhất sau đăng nhập: dựa vào user.role trả về từ /auth/me hoặc /auth/login để điều hướng tới đúng nơi làm việc — StudentShell / DriverShell trong app di động Flutter, hoặc ứng dụng Admin Web (React) nếu role == 'admin', thay vì luôn mở MainShell hiện tại.
Tách biệt nền tảng theo vai trò: Sinh viên và Tài xế dùng chung một ứng dụng di động Flutter (2 shell riêng); Admin dùng một ứng dụng web độc lập (React), triển khai và deploy tách rời hoàn toàn khỏi app di động, chỉ dùng chung backend API.
Ẩn hoàn toàn, không chỉ vô hiệu hoá: trong app di động, nếu tài khoản có role admin đăng nhập nhầm, chỉ hiển thị thông báo hướng dẫn truy cập trang quản trị web, không hiển thị bất kỳ tab nào của sinh viên/tài xế.
Tách thư mục/dự án theo vai trò: app di động Flutter dùng lib/features/student/, lib/features/driver/, dùng chung lib/shared/ và lib/services/; ứng dụng Admin Web là một dự án React riêng biệt (repo hoặc thư mục con độc lập), có cấu trúc src/ riêng như trình bày ở mục 6.3.
Bảo vệ ở tầng API lẫn UI: dù ẩn nút trên UI (mobile hoặc web), backend vẫn phải kiểm tra role trong JWT trước khi cho phép các thao tác nhạy cảm (huỷ chuyến, tạo tuyến, xoá tài khoản...). Đồng thời cấu hình CORS ở backend để cho phép domain của Admin Web gọi API.
# 3. Vai trò: Sinh viên (Student)
Đối tượng sử dụng chính, chiếm số lượng lớn nhất. Trọng tâm là trải nghiệm đặt vé, tra cứu lộ trình và theo dõi xe theo thời gian thực.
## 3.1 Chức năng cốt lõi
## 3.2 Điều hướng đề xuất (Bottom navigation)
Trang chủ → Bản đồ (theo dõi xe) → Vé của tôi (nút trung tâm, giữ như hiện tại) → Thông báo → Cài đặt cá nhân.
Đây gần như là bộ 5 tab hiện có — chỉ cần giới hạn lại nội dung Cài đặt (ẩn các mục quản trị nếu có) và gắn dữ liệu vé/thông báo theo đúng student_id sau đăng nhập.
# 4. Vai trò: Tài xế (Driver)
Tài xế cần một giao diện gọn, tối giản thao tác vì họ sử dụng trong lúc lái xe. Không cần các màn hình mua vé/khuyến mãi của sinh viên.
## 4.1 Chức năng cốt lõi
## 4.2 Điều hướng đề xuất (Bottom navigation)
Chuyến hôm nay (danh sách tuyến được giao) → Bản đồ tuyến đang chạy (kèm nút Bắt đầu/Kết thúc) → Quét vé QR (nút trung tâm) → Thông báo điều phối → Hồ sơ tài xế.
Không hiển thị: mua vé, khuyến mãi, ví điện tử — các mục thuộc về sinh viên.
# 5. Vai trò: Quản trị viên (Admin) — Ứng dụng Web độc lập (React)
Admin cần cái nhìn tổng thể toàn hệ thống: quản lý người dùng, xe, tuyến đường và giám sát vận hành theo thời gian thực. Thay vì làm bản rút gọn trong app di động, chức năng Admin được tách hẳn thành một ứng dụng web riêng biệt xây dựng bằng React, triển khai và vận hành độc lập với app Flutter, chỉ dùng chung backend API hiện có.
## 5.1 Chức năng cốt lõi
## 5.2 Kiến trúc & bố cục giao diện đề xuất
Layout dạng dashboard web chuẩn: Sidebar menu bên trái (Tổng quan, Xe, Tuyến, Người dùng, Sự cố, Báo cáo, Cài đặt) + Topbar (tìm kiếm, thông báo, hồ sơ admin) + vùng nội dung chính bên phải, khác hẳn kiểu bottom navigation của app di động.
Định tuyến (routing) bằng React Router: mỗi mục trong sidebar tương ứng một route/trang riêng (/dashboard, /vehicles, /routes, /users, /incidents, /reports, /settings).
Xác thực: trang /login riêng cho Admin, gọi /auth/login, lưu JWT (khuyến nghị httpOnly cookie hoặc lưu token có kiểm soát), có route guard chỉ cho phép role == 'admin' truy cập, tự động chuyển hướng nếu hết phiên.
Gọi API & đồng bộ dữ liệu: dùng Axios/Fetch kết hợp TanStack Query (React Query) để cache, refetch và xử lý trạng thái loading/error cho các bảng dữ liệu; dùng WebSocket hoặc polling cho vị trí xe realtime trên bản đồ.
Quản lý state: Zustand hoặc Redux Toolkit cho state toàn cục (thông tin admin đăng nhập, bộ lọc, thông báo); state cục bộ của từng trang dùng React state/hooks.
Thư viện UI & hiển thị dữ liệu: bộ component UI dựng sẵn (Ant Design hoặc MUI) cho bảng, form, modal CRUD xe/tuyến/người dùng; Recharts hoặc Chart.js cho biểu đồ thống kê ở Dashboard và Báo cáo.
Vì màn hình quản trị thường nhiều bảng dữ liệu và thao tác CRUD, ưu tiên dạng bảng có phân trang, lọc, tìm kiếm và form thay vì các card đồ hoạ như bản sinh viên/tài xế trên di động.
## 5.3 Ngăn xếp công nghệ đề xuất (Tech stack)
# 6. Đề xuất triển khai kỹ thuật
## 6.1 Điều hướng theo vai trò sau đăng nhập
Sau khi API /auth/login trả về role, hệ thống điều hướng người dùng tới đúng nền tảng tương ứng:
role == 'student' → mở StudentShell trong app di động Flutter (5 tab như mục 3.2).
role == 'driver' → mở DriverShell trong app di động Flutter (5 tab như mục 4.2).
role == 'admin' → không mở bất kỳ shell nào trong app di động; hướng dẫn/đăng nhập vào ứng dụng Admin Web (React) riêng biệt, dùng chung API nhưng là một dự án frontend độc lập.
Chưa đăng nhập (trên app di động) → cho phép xem giới hạn ở chế độ Khách (Home + Bản đồ công khai), các tab còn lại dẫn tới màn hình đăng nhập.
## 6.2 Cấu trúc thư mục đề xuất — Ứng dụng di động Flutter (Student / Driver)
lib/core/ — auth_provider.dart, role.dart (enum Student/Driver), router.dart
lib/shared/ — theme/, widgets/ dùng chung (nút, thẻ, app bar)
lib/services/ — api_service.dart (đã có), tách thêm student_api.dart, driver_api.dart theo domain
lib/features/student/ — home, map, ticket, notification, profile
lib/features/driver/ — my_routes, live_trip, qr_scan, dispatch_notification, profile
Lưu ý: lib/features/admin/ không còn tồn tại trong app Flutter — toàn bộ chức năng quản trị chuyển sang dự án React Web riêng ở mục 6.3.
## 6.3 Cấu trúc dự án đề xuất — Ứng dụng Admin Web (React)
myctu-bus-admin-web/ (repository/thư mục dự án độc lập, tách khỏi mã nguồn Flutter)
src/pages/ — Dashboard, Vehicles, Routes, Users, Incidents, Reports, Settings, Login
src/components/ — các thành phần UI dùng chung: Sidebar, Topbar, DataTable, FormModal, StatCard, MapView
src/features/ — logic nghiệp vụ theo domain: vehicles/, routes/, users/, incidents/, reports/ (hooks, types, mutations riêng cho từng domain)
src/services/ — apiClient.ts (cấu hình Axios + interceptor gắn JWT), vehicles.api.ts, routes.api.ts, users.api.ts...
src/store/ — authStore.ts (thông tin admin đăng nhập), uiStore.ts (trạng thái sidebar, filter...)
src/routes/ — cấu hình React Router, AdminRouteGuard (chỉ cho phép role == 'admin')
src/hooks/ — useVehicles, useRoutes, useUsers... (bọc TanStack Query)
src/assets/, src/styles/ — hình ảnh, theme, biến CSS dùng chung
## 6.4 Việc cần làm ở backend
Bổ sung middleware kiểm tra role trong JWT cho từng nhóm endpoint (student/*, driver/*, admin/*).
Bổ sung các endpoint còn thiếu đã liệt kê ở các bảng trên: /tickets, /bookings, /reviews, /incidents, /users, /reports, /audit-logs.
Chuẩn hoá endpoint /auth/me để trả về đầy đủ role + thông tin hồ sơ, dùng để tự động điều hướng khi mở lại app (giữ phiên đăng nhập) hoặc khi Admin Web tải lại trang.
Cấu hình CORS ở backend để cho phép domain/subdomain của Admin Web (ví dụ admin.myctubus.edu.vn) gọi các endpoint /vehicles, /routes, /users, /reports...
Cân nhắc endpoint/kênh WebSocket riêng phục vụ giám sát realtime nhiều xe cùng lúc trên Admin Web (khác với luồng theo dõi 1 tuyến của sinh viên/tài xế).
# 7. Kết luận
Hệ thống backend đã có nền tảng phân quyền (role, endpoint riêng cho driver) khá tốt, nhưng ứng dụng Flutter hiện tại chưa khai thác — toàn bộ vai trò đang dùng chung một bộ giao diện. Hướng đề xuất là tách thành hai luồng độc lập theo nền tảng: (1) ứng dụng di động Flutter chỉ còn hai shell Student và Driver, và (2) một ứng dụng web quản trị riêng biệt xây dựng bằng React cho vai trò Admin. Việc tách Admin ra khỏi app di động giúp Admin có trải nghiệm phù hợp hơn với công việc quản trị (bảng dữ liệu, biểu đồ, thao tác CRUD trên màn hình lớn), đơn giản hoá app di động (chỉ phục vụ sinh viên và tài xế), giảm rủi ro thao tác nhầm, và mở đường phát triển thêm các tính năng chuyên biệt (quét vé QR cho tài xế, dashboard quản trị đầy đủ cho admin trên web) mà không làm rối trải nghiệm của sinh viên.

| Màn hình / Chức năng hiện có | Khách (chưa đăng nhập) | Sinh viên | Tài xế | Admin |
| --- | --- | --- | --- | --- |
| Trang chủ (Home) | ✅ Xem | ✅ Xem + đặt chuyến | ❌ Không cần | ❌ Không thuộc app di động |
| Bản đồ (Map) | ✅ Xem tuyến | ✅ Theo dõi xe realtime | ✅ Xem tuyến được phân công | ➡️ Chuyển sang bản đồ giám sát trên web |
| Vé của tôi (Ticket) | ⚠️ Giới hạn | ✅ Mua vé, QR check-in | ❌ Không liên quan | ❌ Không thuộc app di động |
| Thông báo | ⚠️ Chung | ✅ Cá nhân hoá | ✅ Lịch trình / điều phối | ➡️ Chuyển sang trung tâm thông báo trên web |
| Cài đặt & đăng nhập | ✅ Chỉ đăng nhập | ✅ Hồ sơ sinh viên | ✅ Hồ sơ tài xế | ➡️ Đăng nhập/hồ sơ quản trị trên web riêng |

| Mức độ | Chức năng | Ghi chú kỹ thuật / API liên quan |
| --- | --- | --- |
| Bắt buộc | Xem danh sách tuyến xe, trạm dừng, giờ chạy (dựa trên Home hiện có) | GET /locations/ |
| Bắt buộc | Theo dõi vị trí xe buýt theo thời gian thực trên bản đồ | GET /vehicles/ (polling/WebSocket) |
| Bắt buộc | Đặt vé / mua vé điện tử, sinh mã QR check-in lên xe | Dựa trên TicketScreen hiện có + endpoint vé (cần bổ sung backend) |
| Bắt buộc | Lịch sử vé đã mua, trạng thái (đã dùng/còn hạn/hết hạn) | Cần bổ sung endpoint /tickets/me |
| Nên có | Đặt trước chuyến / đăng ký tuyến cố định theo lịch học | Cần bổ sung endpoint /bookings |
| Nên có | Thông báo cá nhân hoá: xe sắp đến trạm, trễ giờ, đổi tuyến | WebSocket/Push notification |
| Nên có | Đánh giá chuyến đi / phản hồi tài xế sau khi xuống xe | Cần bổ sung endpoint /reviews |
| Tuỳ chọn | Ví điện tử / lịch sử thanh toán, giảm giá sinh viên | Tích hợp cổng thanh toán |
| Tuỳ chọn | Chia sẻ vị trí xe cho bạn bè / người thân đưa đón | Deep link |

| Mức độ | Chức năng | Ghi chú kỹ thuật / API liên quan |
| --- | --- | --- |
| Bắt buộc | Xem lịch trình / tuyến được phân công trong ngày | GET /routes/driver/{driverId} (đã có sẵn trong ApiService.fetchDriverRoutes) |
| Bắt buộc | Bắt đầu / kết thúc chuyến (check-in ca làm, bật chia sẻ vị trí GPS cho hệ thống) | Cần bổ sung PATCH /routes/{id}/start, /end + gửi toạ độ định kỳ |
| Bắt buộc | Danh sách trạm dừng của tuyến hiện tại kèm thứ tự, giờ dự kiến | Tái sử dụng dữ liệu _RouteStop trong MapScreen nhưng lọc theo tuyến được giao |
| Bắt buộc | Quét mã QR vé của sinh viên khi lên xe để xác nhận check-in | Dùng camera + cần bổ sung endpoint xác thực vé |
| Nên có | Báo cáo sự cố nhanh (kẹt xe, hỏng xe, tai nạn) gửi thẳng về Admin | Cần bổ sung endpoint /incidents |
| Nên có | Thông báo điều phối từ Admin (đổi tuyến gấp, thông báo khẩn) | Push notification riêng kênh driver |
| Nên có | Lịch sử các ca đã chạy, số lượt đón/trả khách trong ngày | Cần bổ sung endpoint thống kê theo driverId |
| Tuỳ chọn | Ghi chú bàn giao xe (tình trạng xe đầu/cuối ca) | Cần bổ sung form nhỏ |

| Mức độ | Chức năng | Ghi chú kỹ thuật / API liên quan |
| --- | --- | --- |
| Bắt buộc | Bảng điều khiển tổng quan (Dashboard): số xe đang chạy, số sinh viên đang trên xe, cảnh báo trễ giờ | Tổng hợp từ /vehicles/ + /routes/driver/* |
| Bắt buộc | Quản lý danh sách xe buýt (thêm/sửa/xoá, gán tài xế cho xe) | GET/POST/PUT /vehicles/ (đã có GET) |
| Bắt buộc | Quản lý tuyến đường & trạm dừng, tạo tuyến tự động | POST /routes/generate (đã có sẵn endpoint) |
| Bắt buộc | Giám sát vị trí toàn bộ đội xe trên một bản đồ chung | Bản đồ web (Leaflet/Google Maps JS/Mapbox GL), realtime qua WebSocket |
| Bắt buộc | Quản lý tài khoản người dùng: sinh viên, tài xế (khoá/mở, đổi vai trò) | Cần bổ sung endpoint /users (CRUD) |
| Nên có | Xem báo cáo sự cố do tài xế gửi lên và xử lý | Liên kết với /incidents đề xuất ở mục 4 |
| Nên có | Thống kê doanh thu vé, lượt sử dụng theo tuyến/thời gian (biểu đồ) | Cần bổ sung endpoint /reports |
| Nên có | Gửi thông báo hệ thống / khẩn cấp tới toàn bộ hoặc theo nhóm (sinh viên/tài xế) | Push notification có phân loại người nhận |
| Tuỳ chọn | Nhật ký hoạt động (audit log) các thay đổi trong hệ thống | Cần bổ sung endpoint /audit-logs |

| Thành phần | Đề xuất |
| --- | --- |
| Ngôn ngữ / Framework | React 18+ với TypeScript, dựng bằng Vite |
| Định tuyến | React Router v6 |
| Gọi API / cache dữ liệu | Axios + TanStack Query (React Query) |
| Quản lý state toàn cục | Zustand hoặc Redux Toolkit |
| Thư viện UI | Ant Design hoặc MUI (Material UI) |
| Bản đồ realtime | Leaflet, Mapbox GL JS hoặc Google Maps JavaScript API |
| Biểu đồ / thống kê | Recharts hoặc Chart.js |
| Realtime (vị trí xe, cảnh báo) | WebSocket (socket.io-client hoặc native WebSocket) |
| Xác thực | JWT (từ /auth/login, /auth/me), route guard theo role |
| Triển khai | Build tĩnh (Vite build) → deploy độc lập trên hosting web (Vercel, Netlify, hoặc server nội bộ), tách domain/subdomain riêng với app di động, ví dụ admin.myctubus.edu.vn |
