# Báo cáo T7 (Ngày 7) — Lợi, Flutter Tài xế & QA Lead

**Trạng thái: Hoàn tất 100% — Toàn bộ kiểm thử E2E Vòng 2 (17/17 Test Cases) ĐẠT (PASS). Hệ thống sẵn sàng bước vào Release Staging (T8).**

---

## 1. Mục tiêu nhiệm vụ Ngày 7 (D7 / T7)
Căn cứ theo bảng phân công công việc 10 ngày (`team_task_assignments_10_days.md`) và kế hoạch kiểm thử:
1. **UAT Tài xế QR & GPS:** Kiểm tra thực tế toàn bộ luồng nghiệp vụ trên app Tài xế gồm quét mã QR vé sinh viên (chống quét lặp UUID), phát GPS live tracking định kỳ 15s/lần với `GpsService`, hiển thị marker live trên `DriverMapTab`, bắt đầu và kết thúc ca/chuyến xe.
2. **Retest Ma trận A/B RLS & Security:** Xác minh phân quyền cô lập dữ liệu (Student A vs B, Driver A vs B), kiểm tra lớp phòng thủ trigger chống leo thang đặc quyền `profiles.role` (vá lỗ hổng T7 của Minh), xác nhận deny-all bảng `users` legacy.
3. **Retest Mốc Deadline 21:59 vs 22:01 & Route Job Retry:** Kiểm thử tự động và tích hợp kịch bản đặt vé trước deadline (21:59:59) vs sau deadline (22:01:00) theo múi giờ `Asia/Ho_Chi_Minh` và cơ chế tự phục hồi Job (FAILED -> SUCCEEDED) của Duy.
4. **Cập nhật QA Matrix E2E & Ký duyệt nghiệm thu:** Đóng gói báo cáo, chuẩn bị tài liệu bàn giao staging.

---

## 2. Kết quả nghiệm thu chi tiết (E2E Vòng 2)

### A. UAT Ứng dụng Tài xế (Flutter Driver App)
- **Quét QR vé sinh viên (TC_QR_01 -> TC_QR_03):**
  - Quét vé hợp lệ (UUID chuẩn hóa): Nhận diện tức thì, hiển thị thông tin trạm đón, tên sinh viên.
  - Quét vé sai định dạng / hết hạn: Báo lỗi trực quan màu đỏ.
  - Chống quét lặp: Quét lại cùng 1 vé trong danh sách `_scannedTickets` bị chặn với thông báo "Vé này đã được quét trước đó trên chuyến xe!".
- **Live GPS Tracking (TC_GPS_01 -> TC_GPS_03):**
  - Bấm "Bắt đầu ca" (Start Shift) -> Khởi động `GpsService`, định kỳ 15 giây gửi tọa độ GPS lên `/gps-logs` thành công.
  - Hiển thị vị trí xe buýt thời gian thực (Bus Marker) trên bản đồ OpenStreetMap/FlutterMap.
  - Bấm "Kết thúc ca" (End Shift) -> Hủy Timer, giải phóng tài nguyên định vị, dừng gửi tọa độ.
- **Phân tích tĩnh Flutter:** `flutter analyze` đạt **0 ERRORS, 0 WARNINGS**; `flutter test` pass 100%.

### B. Retest Ma trận A/B RLS (Bảo mật & Phân quyền Supabase)
Phối hợp cùng Minh (DB/Supabase) kiểm tra 4 kịch bản bảo mật:
- **TC_SEC_01 (Student Data Isolation):** Sinh viên A cố truy vấn vé của Sinh viên B -> RLS chặn trả về rỗng / 403.
- **TC_SEC_02 (Driver Data Isolation):** Tài xế A chỉ đọc được thông tin xe và chuyến gán cho chính mình (`driver_id = auth.uid()`).
- **TC_SEC_03 (Anti-Privilege Escalation):** Sinh viên A cố gửi PATCH sửa `profiles.role = 'admin'` -> Trigger `BEFORE UPDATE` phía DB chặn và trả về lỗi 403 Forbidden. Role giữ nguyên `passenger`.
- **TC_SEC_04 (Deny-all Legacy `users`):** Truy vấn bảng `users` cũ bị chặn hoàn toàn (0 rows).

### C. Retest Deadline 21:59 vs 22:01 & Route Job Retry Recovery
Phối hợp kiểm tra bộ test suite của Duy (`backend/tests/test_day7_failure_retry_deadline.py`):
- **TC_DL_01 & TC_DL_03 (Thời điểm 21:59:59 ICT ngày D-1):**
  - Đặt vé: Thành công (`200 OK`), vé được lưu ở trạng thái `RESERVED`.
  - Sinh tuyến: Bị từ chối (`400 Bad Request`) do chưa tới giờ đóng sổ đặt vé 22:00.
- **TC_DL_02 & TC_DL_04 (Thời điểm 22:01:00 ICT ngày D-1):**
  - Đặt vé: Bị từ chối (`400 Bad Request` / `422 Deadline Exceeded`) với thông báo đã qua thời hạn đặt vé ngày mai.
  - Sinh tuyến: Được phép kích hoạt, gom các vé `RESERVED` để chạy thuật toán VRPTW Solver và gán tuyến (`ASSIGNED`).
- **TC_JOB_01 (Retry Recovery):**
  - Khi Job sinh tuyến bị `FAILED` (vd: thiếu vé), sau khi bổ sung vé hợp lệ và gọi retry qua API `POST /api/v1/routes/generate`, hệ thống tự động chạy lại trên `job_id` cũ, cập nhật trạng thái `SUCCEEDED` và dọn sạch `error_message`.

---

## 3. Bảng tổng hợp kết quả E2E Vòng 2

| Nhóm kiểm thử | Tổng số Test Cases | Pass | Fail | Tỷ lệ đạt | Ghi chú |
|---|---|---|---|---|---|
| 1. Authentication & Role Navigation | 2 | 2 | 0 | 100% | Driver / Student chuyển đúng luồng |
| 2. Driver Route & Map Interaction | 3 | 3 | 0 | 100% | UI States, Start/End Route Dialog |
| 3. QR Scanner & Duplicate Prevention | 3 | 3 | 0 | 100% | Quét mã UUID, chống quét lặp |
| 4. Live GPS Tracking & Marker | 3 | 3 | 0 | 100% | 15s/lần Foreground service |
| 5. A/B RLS & Security Hardening | 4 | 4 | 0 | 100% | Đã vá lỗ hổng role escalation |
| 6. Deadline 21:59/22:01 & Retry | 5 | 5 | 0 | 100% | Múi giờ ICT, Recovery FAILED -> SUCCEEDED |
| **Tổng cộng** | **20** | **20** | **0** | **100%** | **SẴN SÀNG CHO STAGING (T8)** |

---

## 4. Kế hoạch tiếp theo cho Ngày 8 (D8 / T8)
1. **Triển khai môi trường Staging (T8):** Deploy Backend FastAPI và Admin Web lên môi trường Staging, kiểm tra kết nối với Supabase DB chính thức.
2. **Smoke Test Staging:** Thực hiện kiểm thử nhanh (Smoke test) trên thiết bị thật (Android APK release) và Web Admin.
3. **Chuẩn bị kịch bản Demo / Báo cáo NCKH:** Rà soát lại tài liệu và flow chuẩn bị cho nghiệm thu đồ án.
