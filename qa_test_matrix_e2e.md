# QA Test Matrix E2E - MyCTU BUS (MVP 10 Days)

**Tester:** Lợi (Thành viên 5 - Flutter Tài xế & QA)  
**Mục tiêu:** Kiểm thử quy trình end-to-end từ đăng nhập, nhận tuyến, quét QR đến gửi GPS.  
**Thư mục lưu Evidence (Video/Ảnh):** `/docs/qa_evidence/` (hoặc Google Drive nội bộ).

## 1. Flow Đăng nhập (App Sinh viên & Tài xế)

| ID | Tính năng | Các bước thực hiện (Steps) | Dữ liệu Test (Input) | Kết quả mong đợi (Expected) | Trạng thái | Nơi lưu Evidence |
|---|---|---|---|---|---|---|
| TC_AUTH_01 | Đăng nhập Tài xế hợp lệ | 1. Mở app Driver<br>2. Nhập Email & Pass<br>3. Bấm "Đăng nhập" | Email: driver1@ctu.edu.vn<br>Pass: Driver@123 | Chuyển vào màn hình Home Tài xế, gọi API `/me` nhận role `driver`. | [ ] | |
| TC_AUTH_02 | Đăng nhập Sinh viên hợp lệ | 1. Mở app Sinh viên<br>2. Nhập Email & Pass<br>3. Bấm "Đăng nhập" | Email: b2012345@student.ctu.edu.vn<br>Pass: Sv@12345 | Chuyển vào Home Sinh viên, nhận role `student`. | [ ] | |

## 2. Flow Tài xế nhận tuyến và theo dõi bản đồ

| ID | Tính năng | Các bước thực hiện (Steps) | Dữ liệu Test (Input) | Kết quả mong đợi (Expected) | Trạng thái | Nơi lưu Evidence |
|---|---|---|---|---|---|---|
| TC_DRV_01 | Giao diện trống khi chưa có tuyến | 1. Đăng nhập tài khoản chưa được gán tuyến<br>2. Kiểm tra Home | Tài khoản driver chưa có job | Card "Up Next" hiển thị trạng thái "Chưa có tuyến tiếp theo". | [x] | |
| TC_DRV_02 | Hiển thị tuyến được phân công | 1. Đăng nhập tài khoản có tuyến<br>2. Xem thông tin tuyến tại Home | driver1 có chuyến mã CT-01 | Hiển thị thông tin tuyến (tổng trạm, dự kiến khách). | [x] | |
| TC_DRV_03 | Bắt đầu và Kết thúc chuyến | 1. Bấm "Bắt đầu chuyến" trên bản đồ tuyến<br>2. Chờ API xử lý<br>3. Bấm "Kết thúc chuyến" | CT-01 (pending -> in_progress -> completed) | Trạng thái chuyến thay đổi thành "Đang chạy" rồi thành "Hoàn tất". | [x] | |

## 3. Flow Quét QR vé Sinh viên

| ID | Tính năng | Các bước thực hiện (Steps) | Dữ liệu Test (Input) | Kết quả mong đợi (Expected) | Trạng thái | Nơi lưu Evidence |
|---|---|---|---|---|---|---|
| TC_QR_01 | Quét vé hợp lệ | 1. Mở Tab QR<br>2. Đưa Camera quét mã sinh viên đã mua | QR string hợp lệ: UUID ticket thực | Popup báo "XÁC NHẬN VÉ HỢP LỆ", hiển thị tên, MSV. | [x] | |
| TC_QR_02 | Quét vé không hợp lệ / Hết hạn | 1. Quét vé chưa tới giờ hoặc đã hủy | QR string cũ hoặc random | Popup báo "VÉ KHÔNG HỢP LỆ" màu đỏ. | [x] | |
| TC_QR_03 | Chống quét lặp (Duplicate scan) | 1. Quét lại vé vừa quét ở TC_QR_01 | Cùng mã QR của TC_QR_01 | Lần 2 báo lỗi vé đã được sử dụng. | [x] | |

## 4. Flow GPS Tracking & Phân quyền RLS

| ID | Tính năng | Các bước thực hiện (Steps) | Dữ liệu Test (Input) | Kết quả mong đợi (Expected) | Trạng thái | Nơi lưu Evidence |
|---|---|---|---|---|---|---|
| TC_GPS_01 | Gửi vị trí Foreground | 1. Tài xế bấm "Bắt đầu ca" / Start Shift<br>2. Di chuyển thực tế<br>3. Kiểm tra log API POST GPS | Tài xế 1 | Cứ 15-20 giây app tự gọi API gửi tọa độ một lần khi màn hình bật. | [ ] | |
| TC_SEC_01 | RLS Data Isolation | 1. Đăng nhập Sinh viên A<br>2. Cố gọi API lấy vé của Sinh viên B | Token A, Ticket ID của B | API trả về 403 Forbidden hoặc 404 Not Found. | [ ] | |

*(Các kịch bản sẽ được bổ sung tiếp trong quá trình tích hợp API ở T3-T5)*
