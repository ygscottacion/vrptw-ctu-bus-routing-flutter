# QA Test Matrix E2E - MyCTU BUS (MVP 10 Days)

**Tester:** Lợi (Thành viên 5 - Flutter Tài xế & QA)  
**Mục tiêu:** Kiểm thử quy trình end-to-end từ đăng nhập, nhận tuyến, quét QR đến gửi GPS.  
**Thư mục lưu Evidence (Video/Ảnh):** `/docs/qa_evidence/` (hoặc Google Drive nội bộ).

## 1. Flow Đăng nhập (App Sinh viên & Tài xế)

| ID | Tính năng | Các bước thực hiện (Steps) | Dữ liệu Test (Input) | Kết quả mong đợi (Expected) | Trạng thái | Nơi lưu Evidence |
|---|---|---|---|---|---|---|
| TC_AUTH_01 | Đăng nhập Tài xế hợp lệ | 1. Mở app Driver<br>2. Nhập Email & Pass<br>3. Bấm "Đăng nhập" | Email: driver1@ctu.edu.vn<br>Pass: Driver@123 | Chuyển vào màn hình Home Tài xế, gọi API `/me` nhận role `driver`. | [x] | |
| TC_AUTH_02 | Đăng nhập Sinh viên hợp lệ | 1. Mở app Sinh viên<br>2. Nhập Email & Pass<br>3. Bấm "Đăng nhập" | Email: b2012345@student.ctu.edu.vn<br>Pass: Sv@12345 | Chuyển vào Home Sinh viên, nhận role `student`. | [x] | |

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

## 4. Flow GPS Tracking & Phát hiện chuyển động

| ID | Tính năng | Các bước thực hiện (Steps) | Dữ liệu Test (Input) | Kết quả mong đợi (Expected) | Trạng thái | Nơi lưu Evidence |
|---|---|---|---|---|---|---|
| TC_GPS_01 | Gửi vị trí Foreground định kỳ | 1. Tài xế bấm "Bắt đầu ca" / Start Shift<br>2. Di chuyển thực tế<br>3. Kiểm tra log API POST `/gps-logs` | Tài xế 1 (UUID) | Cứ 15 giây app tự gọi API gửi tọa độ GPS lên server khi ca đang bật. | [x] PASS | `docs/report/report_T7_Loi.md` |
| TC_GPS_02 | Dừng phát GPS khi kết ca | 1. Tài xế bấm "Kết thúc ca" / End Shift<br>2. Kiểm tra log định kỳ | Tài xế 1 | Timer GPS dừng lại, không phát sinh thêm log GPS. | [x] PASS | `docs/report/report_T7_Loi.md` |
| TC_GPS_03 | Hiển thị Live Bus Marker | 1. Mở Tab Map khi ca đang bật<br>2. Kiểm tra vị trí xe buýt | Tọa độ GPS hiện tại | Icon xe buýt màu xanh hiển thị chính xác tọa độ thực tế trên bản đồ. | [x] PASS | `docs/report/report_T7_Loi.md` |

## 5. Flow Retest A/B RLS (Bảo mật & Cô lập dữ liệu)

| ID | Tính năng | Các bước thực hiện (Steps) | Dữ liệu Test (Input) | Kết quả mong đợi (Expected) | Trạng thái | Nơi lưu Evidence |
|---|---|---|---|---|---|---|
| TC_SEC_01 | Student A đọc vé Student B | 1. Đăng nhập Sinh viên A<br>2. Gọi API lấy thông tin vé của Sinh viên B | Token A, Ticket ID của B | PostgREST / Supabase trả về rỗng hoặc 403 Forbidden. | [x] PASS | `docs/report/report_T7_Minh.md` |
| TC_SEC_02 | Driver A đọc xe / tuyến Driver B | 1. Đăng nhập Tài xế A<br>2. Truy vấn dữ liệu xe/tuyến gán cho Driver B | Token Driver A, Vehicle/Route Driver B | Kết quả trả về rỗng (Data isolation). | [x] PASS | `docs/report/report_T7_Minh.md` |
| TC_SEC_03 | Chống leo thang đặc quyền `profiles.role` | 1. Đăng nhập Sinh viên A<br>2. Gửi PATCH trực tiếp đổi `role: 'admin'` | Token Sinh viên A, payload `role: 'admin'` | Bị Trigger DB chặn trả về lỗi 403 Forbidden. Role không bị thay đổi. | [x] PASS | `docs/report/report_T7_Minh.md` |
| TC_SEC_04 | Deny-all bảng `users` legacy | 1. Gửi request đọc bảng `users` cũ | Token Authenticated | Bị RLS chặn hoàn toàn (Deny-all), 0 dòng được trả về. | [x] PASS | `docs/report/report_T7_Minh.md` |

## 6. Flow Deadline 21:59 vs 22:01 & Route Job Retry

| ID | Tính năng | Các bước thực hiện (Steps) | Dữ liệu Test (Input) | Kết quả mong đợi (Expected) | Trạng thái | Nơi lưu Evidence |
|---|---|---|---|---|---|---|
| TC_DL_01 | Đặt vé TRƯỚC deadline 22:00 | 1. Sinh viên đặt vé tại thời điểm 21:59:59 ngày D-1<br>2. Kiểm tra response API | D = 2026-09-10, Time = 21:59:59 (ICT) | Đặt vé thành công (200 OK), vé ở trạng thái `RESERVED`. | [x] PASS | `backend/tests/test_day7_failure_retry_deadline.py` |
| TC_DL_02 | Đặt vé SAU deadline 22:00 | 1. Sinh viên cố đặt vé tại thời điểm 22:01:00 ngày D-1<br>2. Kiểm tra response API | D = 2026-09-10, Time = 22:01:00 (ICT) | Bị từ chối (400 Bad Request / 422 Deadline Exceeded). | [x] PASS | `backend/tests/test_day7_failure_retry_deadline.py` |
| TC_DL_03 | Sinh tuyến trước 22:00 | 1. Admin/Scheduler chạy thuật toán sinh tuyến trước 22:00 (21:59) | Time = 21:59:59 (ICT) | Bị từ chối (400 Bad Request) do chưa đóng sổ đặt vé. | [x] PASS | `backend/tests/test_day7_failure_retry_deadline.py` |
| TC_DL_04 | Sinh tuyến sau 22:00 | 1. Scheduler chạy sinh tuyến sau 22:00 (22:01) | Time = 22:01:00 (ICT) | Sinh tuyến thành công, các vé RESERVED chuyển sang ASSIGNED. | [x] PASS | `backend/tests/test_day7_failure_retry_deadline.py` |
| TC_JOB_01 | Tự phục hồi Job FAILED (Retry Recovery) | 1. Job sinh tuyến ban đầu FAILED do thiếu vé<br>2. Bổ sung vé hợp lệ và retry lại | RouteJob đã FAILED | Job chuyển từ FAILED -> RUNNING -> SUCCEEDED, xóa error_message. | [x] PASS | `backend/tests/test_day7_failure_retry_deadline.py` |

---
**Tổng kết E2E Vòng 2:** 17/17 Test cases ĐẠT (PASS). Hệ thống sẵn sàng bước vào giai đoạn Release Staging (T8).

