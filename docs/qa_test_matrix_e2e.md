# QA E2E Test Matrix (Admin → Route Generation → Driver Flow)

**Build SHA**: `bef0a697f0e57f3e919d606a7a49886e5223886d`  
**Environment**: Staging / Local Test Harness  
**Updated Date**: 2026-09-24  

> [!IMPORTANT]
> Tất cả các case bên dưới đã được reset về trạng thái `NOT RUN` sau đợt cập nhật fix P0/P1 cho luồng Admin → Sinh tuyến → Duyệt lộ trình → Tài xế. Cần chạy lại nghiệm thu E2E trên môi trường Staging với dữ liệu thật.

| ID Case | Nhóm chức năng | Tên kịch bản test | Kết quả mong đợi | Trạng thái | Ghi chú / SHA |
|---|---|---|---|---|---|
| **ADM-01** | Admin / Route Gen | Form sinh tuyến Admin không dùng Cron Secret | Admin gửi `POST /routes/admin/generate` với JWT Admin, không truyền `X-Cron-Secret`. Payload gồm `service_date`, `session_id`, `trip_type`, `depot_location_id` (UUID). Trả về `202 ACCEPTED` với `job_id`. | `NOT RUN` | SHA: `bef0a69` |
| **ADM-02** | Admin / Route Gen | Polling trạng thái Job sinh tuyến | Admin poll `GET /routes/jobs/{job_id}` nhận trạng thái `QUEUED` → `RUNNING` → `SUCCEEDED`/`FAILED`. | `NOT RUN` | SHA: `bef0a69` |
| **ADM-03** | Admin / Route Approval | Xem danh sách & Manifest lộ trình | Admin thấy danh sách tuyến sinh tự động, xem được chi tiết các trạm dừng (Manifest) theo đúng `stop_order` và thời gian dự kiến. | `NOT RUN` | SHA: `bef0a69` |
| **ADM-04** | Admin / Route Approval | Duyệt lộ trình (`POST /routes/{id}/approve`) | Trạng thái tuyến chuyển sang `approved`, ghi nhận `approved_by` và `approved_at`. | `NOT RUN` | SHA: `bef0a69` |
| **ADM-05** | Admin / Route Approval | Từ chối lộ trình (`POST /routes/{id}/reject`) | Yêu cầu nhập lý do từ chối. Trạng thái chuyển sang `rejected`, ghi nhận `rejection_reason`. | `NOT RUN` | SHA: `bef0a69` |
| **DRV-01** | App Tài xế / Routes | Lấy danh sách tuyến tài xế phụ trách | `fetchDriverRoutes` gọi API FastAPI với RBAC driver. Nếu vehicle_id rỗng, fail closed (trả danh sách rỗng), không lộ tuyến của tài xế khác. | `NOT RUN` | SHA: `bef0a69` |
| **DRV-02** | App Tài xế / Shift | Bật ca làm việc & Bắt đầu tuyến (`startRoute`) | Bật ca trên app gọi `PATCH /routes/{id}/start`. Trạng thái chuyển sang `in_progress`. Bật GPS tracking. Trả lỗi 403 nếu tài xế không phụ trách xe đó. | `NOT RUN` | SHA: `bef0a69` |
| **DRV-03** | App Tài xế / Shift | Tắt ca làm việc & Kết thúc tuyến (`endRoute`) | Tắt ca gọi `PATCH /routes/{id}/end`. Trạng thái chuyển sang `completed`. Dừng GPS tracking. | `NOT RUN` | SHA: `bef0a69` |
| **DRV-04** | App Tài xế / Start-End | Double tap / Idempotent call `start` & `end` | Gọi lại `start` khi tuyến đang `in_progress` hoặc `end` khi `completed` không báo lỗi 500, trả về route hợp lệ (Idempotent). | `NOT RUN` | SHA: `bef0a69` |
| **QR-01** | App Tài xế / QR Verify | Chặn mã QR demo hardcode | Thử quét mã QR demo `550e8400...` → Hệ thống từ chối (404/Not Found hoặc không tìm thấy trong DB). | `NOT RUN` | SHA: `bef0a69` |
| **QR-02** | App Tài xế / QR Verify | Chặn điểm danh vé chưa xếp tuyến | Vé ở trạng thái `RESERVED` hoặc `PAID_PENDING_ROUTE` bị từ chối điểm danh với thông báo "Vé chưa được phân bổ vào tuyến buýt". | `NOT RUN` | SHA: `bef0a69` |
| **QR-03** | App Tài xế / QR Verify | Chặn điểm danh vé thuộc tài xế khác | Tài xế A quét vé thuộc tuyến của xe tài xế B → Trả lỗi 403 ("Vé này thuộc tuyến buýt do tài xế khác phụ trách"). | `NOT RUN` | SHA: `bef0a69` |
| **QR-04** | App Tài xế / QR Verify | Điểm danh thành công vé `ASSIGNED` | Vé `ASSIGNED` đúng tuyến/tài xế quét thành công → Đổi trạng thái vé thành `USED`. Quét lại lần 2 báo "Vé đã được điểm danh trước đó". | `NOT RUN` | SHA: `bef0a69` |
| **QR-05** | App Tài xế / QR Verify | Chặn điểm danh khi tuyến đã `COMPLETED` | Tuyến đã hoàn tất (`COMPLETED`) bị từ chối điểm danh vé mới với mã 409 Conflict. | `NOT RUN` | SHA: `bef0a69` |
