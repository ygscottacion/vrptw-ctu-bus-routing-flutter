# Báo cáo sự cố kỹ thuật: Thiếu trạm dừng (route_stops) khi sinh tuyến

- **Mã sự cố:** `BUG-VRPTW-01`
- **Thành phần ảnh hưởng:** `app/services/route_worker.py`, `app/services/vrptw_solver.py`
- **Mức độ nghiêm trọng:** High — ảnh hưởng dữ liệu hiển thị lộ trình trên Flutter App
- **Người phát hiện:** Minh
- **Ngày phát hiện:** trong quá trình E2E routing (T4.2)
- **Trạng thái:** Open — chờ fix

---

## 1. Mô tả triệu chứng (Symptoms)

- API `POST /api/v1/routes/generate` báo hoàn tất công việc (`status: SUCCEEDED`).
- Bảng `tickets` chuyển trạng thái chính xác từ `RESERVED → ASSIGNED` cho đủ 5 vé.
- Bảng `routes` khởi tạo thành công 1 tuyến xe với `passenger_count = 5`.
- **Bất thường:** bảng `route_stops` chỉ ghi nhận đúng **1 trạm dừng duy nhất** (trạm depot xuất phát); toàn bộ 5 trạm đón sinh viên bị bỏ qua.

Đây là lỗi silent — job vẫn báo `SUCCEEDED` và ticket vẫn chuyển trạng thái đúng, nên không bị chặn ở bước smoke test cấp job/ticket; chỉ lộ ra khi kiểm tra chi tiết `route_stops`.

## 2. Phân tích nguyên nhân gốc rễ (Root Cause)

### 2.1 Mất đồng bộ data contract giữa solver và worker

`VRPTWSolverService` trả về trường `id` của điểm dừng dưới dạng chỉ số node tạm thời do solver tự sinh (ví dụ `"location_0"`, `"0"`, `"1"`) thay vì giữ nguyên chuỗi UUID gốc từ PostgreSQL (`e9eac4c8-b5a2-...`). Solver không có khái niệm UUID — nó chỉ làm việc với index nội bộ của bài toán tối ưu, và tầng gọi solver (`route_worker.py`) đang giả định sai rằng `id` trả về luôn là UUID hợp lệ.

### 2.2 Bắt lỗi không an toàn (unsafe type casting)

Tại `route_worker.py`:

```python
stop_loc_id = uuid.UUID(stop_data.get("id"))
```

Dòng này văng `ValueError` ngay khi gặp id dạng `"location_0"`/`"0"` không đúng định dạng UUID — tức là **luôn luôn fail** với node đầu tiên không phải depot, vì solver không trả UUID gốc cho bất kỳ node nào.

### 2.3 Hành vi transaction sai khi exception xảy ra trong vòng lặp

Khi `ValueError` được ném ra trong vòng lặp ghi từng `RouteStop`, tiến trình bị ngắt giữa chừng và rơi vào khối `except`. Vì các thao tác ghi trước đó (depot) và sau đó (5 trạm đón) đang nằm chung một transaction/session, hành vi hiện tại là:

- Trạm đã ghi trước khi exception xảy ra (depot) vẫn được commit hoặc còn nằm trong session chưa rollback đúng cách.
- Các trạm còn lại trong vòng lặp (5 trạm đón) bị bỏ qua hoàn toàn, không có cơ chế retry hay rollback toàn bộ route để đảm bảo tính toàn vẹn — dẫn đến trạng thái dữ liệu nửa vời (route tồn tại, ticket đã assigned, nhưng route_stops thiếu).
- Job vẫn được đánh dấu `SUCCEEDED` vì exception bị nuốt ở tầng xử lý từng stop mà không propagate lên để đổi trạng thái job thành `FAILED`.

## 3. Tác động (Impact)

| Bảng | Trạng thái sau lỗi | Hệ quả |
|---|---|---|
| `tickets` | `ASSIGNED` (đúng) | Sinh viên nghĩ vé đã có route, nhưng route thực tế không có điểm đón của họ |
| `routes` | Tạo thành công, `passenger_count = 5` | Route có vẻ hợp lệ nhưng rỗng nội dung |
| `route_jobs` | `SUCCEEDED` | Sai — job thực chất fail giữa chừng, che giấu lỗi khỏi giám sát |
| `route_stops` | Chỉ có 1 row (depot) | Flutter App không có dữ liệu để hiển thị lộ trình đón sinh viên |

Vì `route_jobs.status = SUCCEEDED`, các cơ chế alerting/monitoring dựa trên job status sẽ **không phát hiện được sự cố này**.

## 4. Đề xuất hướng fix

1. **Chuẩn hoá data contract solver ↔ worker:** solver không nên tự sinh `id`; worker cần tự map node index nội bộ của solver sang UUID gốc thông qua một mảng/dict tra cứu (`node_index -> location_uuid`) được worker truyền vào solver và giữ lại, thay vì đọc `id` từ output của solver.
2. **Loại bỏ ép kiểu không an toàn:** thay `uuid.UUID(stop_data.get("id"))` bằng việc tra UUID qua mapping ở trên; nếu không tìm thấy, raise lỗi rõ ràng có ngữ cảnh (route nào, node index nào) thay vì để `ValueError` chung chung.
3. **Sửa hành vi transaction:** toàn bộ việc ghi `route_stops` cho một route phải nằm trong một transaction duy nhất — nếu bất kỳ stop nào lỗi, rollback toàn bộ route đó (kể cả `routes` và cập nhật `tickets` liên quan), và job phải được set `FAILED` kèm lý do cụ thể, không được set `SUCCEEDED`.
4. **Thêm test tái hiện lỗi:** viết test cho `route_worker.py` với input mock từ solver trả `id` dạng `"location_0"`, xác nhận worker map đúng UUID và không văng exception; thêm test rollback khi một stop bị lỗi giữa chừng.
5. **Bổ sung giám sát:** thêm kiểm tra sau khi job `SUCCEEDED`: `count(route_stops) WHERE route_id = X` phải khớp số lượng điểm đón dự kiến (số ticket assigned + depot); nếu lệch, không nên coi job là thành công.

## 5. Việc cần làm và phân công đề xuất

| Việc | Đề xuất phụ trách | Ghi chú |
|---|---|---|
| Sửa mapping node index → UUID trong `vrptw_solver.py`/`route_worker.py` | Duy (chủ sở hữu worker/solver) | Đây là lỗi logic nghiệp vụ, không thuộc phạm vi DB/Supabase của Minh |
| Sửa transaction boundary cho route + route_stops | Duy/Nhã | Cần đảm bảo rollback toàn bộ khi lỗi |
| Cập nhật job status thành FAILED khi lỗi | Duy | |
| Test lại E2E routing (T4.2) sau khi fix | Minh (phối hợp Duy) | Chạy lại `EXPLAIN` và verify route_stops sau fix |

## 6. Cách tái hiện (Steps to reproduce)

1. Chạy seed UUID idempotent (T4.1) trên staging sạch.
2. Reserve 5 ticket qua `POST /api/v1/tickets/reserve`.
3. Gọi `POST /api/v1/routes/generate`.
4. Kiểm tra:
   ```sql
   SELECT count(*) FROM route_stops WHERE route_id = '<route_id>';
   -- Kết quả hiện tại: 1 (chỉ depot)
   -- Kết quả kỳ vọng: 6 (1 depot + 5 điểm đón)
   ```

## 7. Trạng thái các hạng mục liên quan trong kế hoạch Ngày 3–4

Do lỗi này, mục T4.2 bước 3 ("Xác minh route/route_stops có UUID và run key đúng") **chưa đạt** — route tồn tại nhưng route_stops không đầy đủ. Cần Duy fix xong và Minh chạy lại verify + `EXPLAIN` trước khi coi T4.2 là hoàn tất.
