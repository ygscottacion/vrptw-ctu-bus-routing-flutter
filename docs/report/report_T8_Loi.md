# Báo cáo T8 (Ngày 8) — Lợi, Flutter Tài xế & QA Lead

**Trạng thái: Hoàn tất 100% — Kiểm thử Staging trên 2 thiết bị Tài xế + 5 Sinh viên thành công. Đã lập Defect Log và giải quyết 3/3 lỗi phát sinh. Sẵn sàng cho UAT thực địa Ngày 9.**

---

## 1. Mục tiêu nhiệm vụ Ngày 8 (D8 / T8)
Căn cứ theo bảng phân công công việc 10 ngày (`implementation_plan_1-2_weeks_revised.md`):
1. **Kiểm thử đa thiết bị Staging (Multi-device Testing):** Thực hiện kiểm thử phối hợp đồng thời trên 2 thiết bị Android tài xế (`driver1@test.example.com`, `driver2@test.example.com`) và 5 tài khoản sinh viên (`student1` -> `student5`) kết nối trực tiếp vào Backend Staging (Render & Supabase).
2. **Kiểm thử tải & vận hành đồng thời 2 xe buýt:** Xác minh 2 tài xế nhận 2 tuyến xe độc lập, bắt đầu ca, phát GPS định kỳ 15s/lần đồng thời và hiển thị live bus marker trên bản đồ mà không bị đè hay lẫn lộn tọa độ.
3. **Quét mã QR vé chéo (Cross-verification):** Kiểm tra quét mã vé từ 5 sinh viên trên đúng xe được phân công và xử lý từ chối nếu quét nhầm xe/nhầm tuyến.
4. **Quản lý & xử lý lỗi (Defect Logging):** Lập bảng theo dõi lỗi `docs/BUG/DEFECT_LOG_T8.md`, phân loại và xử lý dứt điểm các lỗi phát sinh trong quá trình kiểm thử Staging.

---

## 2. Kết quả kiểm thử đa thiết bị Staging (2 Drivers + 5 Students)

### A. Ma trận tài khoản & thiết bị thử nghiệm (Seed Data)
- **Tài khoản Tài xế:**
  - `driver1@test.example.com` — Gán Xe `51F-000.01` (Tuyến Tuyến 01: Bến xe Cần Thơ ⇄ KTX A ⇄ Khu II ĐHCT).
  - `driver2@test.example.com` — Gán Xe `51F-000.02` (Tuyến Tuyến 02: Khu I ĐHCT ⇄ Viện CNTT ⇄ Khu II ĐHCT).
- **Tài khoản Sinh viên:** 5 sinh viên (`student1` đến `student5`) đặt vé và nhận mã QR vé đã được gán tuyến (`ASSIGNED`).

### B. Kết quả kiểm thử kịch bản vận hành thực tế

| Kịch bản kiểm thử | Mô tả & Dữ liệu đầu vào | Kết quả mong đợi | Kết quả thực tế | Trạng thái |
|---|---|---|---|---|
| **STG_01: Phân ca 2 Tài xế song song** | Driver 1 & Driver 2 đăng nhập đồng thời trên 2 máy Android riêng biệt | Mỗi tài xế chỉ nhìn thấy tuyến đường và xe của chính mình | UI Driver 1 hiển thị xe `51F-000.01`, Driver 2 hiển thị xe `51F-000.02`. | ✅ **PASS** |
| **STG_02: Phát GPS song song 2 xe** | Cả 2 tài xế bấm "Bắt đầu ca" và di chuyển đồng thời | 2 luồng GPS 15s/lần gửi lên `/gps-logs` độc lập, lưu đúng `route_id` | Backend ghi nhận đầy đủ 2 luồng log tọa độ riêng biệt, không có xung đột. | ✅ **PASS** |
| **STG_03: Live Marker 2 xe trên Map** | Mở Tab Bản đồ xem vị trí các xe đang chạy | Bản đồ hiển thị chính xác 2 marker xe buýt tương ứng với 2 vị trí thực tế | 2 Icon xe buýt màu xanh hiển thị rõ ràng, cập nhật mượt mà theo chu kỳ GPS. | ✅ **PASS** |
| **STG_04: Quét QR đúng tuyến** | Driver 1 quét vé của Student 1 (được gán trên Tuyến 01) | Thông báo "XÁC NHẬN VÉ HỢP LỆ", hiển thị trạm đón và tên SV | Quét thành công, vé chuyển trạng thái sử dụng, ghi nhận vào danh sách chuyến. | ✅ **PASS** |
| **STG_05: Quét QR sai tuyến** | Driver 1 quét vé của Student 4 (được gán trên Tuyến 02 của Driver 2) | Báo từ chối hoặc cảnh báo vé thuộc chuyến xe khác | Hệ thống nhận diện và cảnh báo chính xác, tránh nhầm lẫn hành khách giữa 2 xe. | ✅ **PASS** |
| **STG_06: Kết ca độc lập** | Driver 1 bấm "Kết thúc ca" trước Driver 2 | Xe 1 dừng phát GPS, Xe 2 vẫn tiếp tục phát GPS bình thường | Hủy Timer GPS xe 1 an toàn, luồng xe 2 không bị ảnh hưởng. | ✅ **PASS** |

---

## 3. Tổng hợp Bảng theo dõi lỗi (Defect Log T8)

Chi tiết xem tại tài liệu: [`docs/BUG/DEFECT_LOG_T8.md`](file:///d:/NCKH/Pro_10days/vrptw-ctu-bus-routing-flutter/docs/BUG/DEFECT_LOG_T8.md)

- **Tổng số lỗi phát hiện:** 3 lỗi.
  - `DEF-STG-01 (P1)`: Quét QR kiểm tra chéo `route_id` giữa 2 xe -> **ĐÃ FIX**.
  - `DEF-STG-02 (P2)`: Xử lý ngoại lệ ngắt mạng đột ngột khi gửi GPS 15s -> **ĐÃ FIX**.
  - `DEF-STG-03 (P3)`: Tinh chỉnh hiển thị văn bản trạm trên màn hình nhỏ -> **ĐÃ FIX**.
- **Tỷ lệ giải quyết lỗi:** **3/3 (100% Resolved)**. Không còn lỗi Blocker (P0) hay Critical (P1) tồn đọng.

---

## 4. Đánh giá chất lượng mã nguồn & Build Candidate
- `flutter test`: **100% Passed** (1/1 widget smoke test).
- `flutter analyze`: **0 Errors, 0 Warnings** (Mã nguồn sạch, tuân thủ Flutter Linting).
- **Candidate Staging:** Sẵn sàng nghiệm thu kỹ thuật và bước vào đợt UAT thực địa Ngày 9.

---

## 5. Kế hoạch tiếp theo cho Ngày 9 (D9 / T9)
1. **UAT Thực địa (Field Test):** Đưa 2 thiết bị tài xế ra ngoài thực địa khuôn viên ĐH Cần Thơ để test bắt sóng GPS thực tế, kiểm tra độ chính xác tọa độ và độ trễ quét QR dưới ánh sáng mặt trời.
2. **Hoàn thiện nghiệm thu E2E Vòng 2:** Đóng toàn bộ checklist nghiệm thu trước ngày đóng gói bàn giao (D10).
