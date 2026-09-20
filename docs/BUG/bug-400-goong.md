# Báo cáo phát hiện lỗi — Test 20 trạm thật (Ngày 6)

**Người phát hiện:** Minh (Backend Google Routes Integration — theo Newplan)
**Người sở hữu code cần fix:** Nhã (tác giả `GoongDistanceMatrixProvider`)
**Mức độ:** Blocker — không thể hoàn tất test 20 trạm (route factor, ETA anomaly, snap-to-road) cho tới khi fix xong, vì toàn bộ đang fallback sang Haversine giả lập.

---

## 1. Việc đã làm (thuộc phạm vi Ngày 6 của Minh)

- Chuẩn bị 20 trạm thật (toạ độ lấy thủ công từ Google Maps).
- Viết script test (`test_20real_stations.py`): kiểm tra bounds toạ độ, gọi Goong Distance Matrix, kiểm tra route factor bất thường, kiểm tra ETA bất thường (`goong_metrics.validate_eta_anomaly`), kiểm tra snap-to-road.
- Kết quả bounds check: ✅ toàn bộ 20 trạm hợp lệ trong vùng Cần Thơ.

## 2. Lỗi phát hiện — Goong Distance Matrix trả lỗi, không dùng được dữ liệu thật

Khi gọi `GoongDistanceMatrixProvider.get_matrix()` với 20 điểm, nhận:
```
status_code: 400
body: {"rows":[],"status":"NOT_FOUND"}
```

**Diễn giải:** `NOT_FOUND` ở đây là status **top-level** với `rows` rỗng hoàn toàn — khác với `NOT_FOUND` ở cấp phần tử (1 cặp điểm cụ thể không geocode được). Khi toàn bộ `rows` rỗng, nhiều khả năng server không parse được tham số `origins`/`destinations` gửi lên, chứ không phải do 1 toạ độ cụ thể sai.

## 3. Giả thuyết nguyên nhân (chưa xác nhận 100%, cần Nhã kiểm tra thêm)

Trong `distance_matrix.py`, dòng dựng URL:
```python
origins = "|".join([f"{p['lat']},{p['lng']}" for p in points])
destinations = "|".join([f"{p['lat']},{p['lng']}" for p in points])
url = f"{self.base_url}?origins={origins}&destinations={destinations}&vehicle=car&api_key={self.api_key}"
```

Ký tự `|` được gửi **thô, không encode** trong URL. Tài liệu Google Distance Matrix (Goong mô phỏng theo format này) thường minh hoạ với `|` giữ nguyên trong ví dụ, nhưng thực tế hành vi encode/không-encode có thể khác nhau tuỳ implementation phía Goong — mình đã thử encode `|` thành `%7C` (`urllib.parse.quote`) nhưng vẫn ra lỗi tương tự (đổi từ "400 Bad Request" chung chung sang "400 + body NOT_FOUND" chi tiết hơn), nên **chưa kết luận được hướng nào đúng**.

## 4. Đề xuất bước tiếp theo cho Nhã

1. Test trực tiếp bằng `curl` (bỏ qua code Python) để xác nhận Goong thực sự mong đợi format nào:
   ```bash
   curl -G "$GOONG_DISTANCE_MATRIX_BASE_URL" \
     --data-urlencode "origins=10.028200,105.768200|10.032213,105.787976" \
     --data-urlencode "destinations=10.028200,105.768200|10.032213,105.787976" \
     --data-urlencode "vehicle=car" \
     --data-urlencode "api_key=$GOONG_API_KEY"
   ```
2. Đối chiếu `GOONG_DISTANCE_MATRIX_BASE_URL` trong `config.py` — xác nhận đúng domain/path theo tài liệu Goong.
3. Kiểm tra `GOONG_API_KEY` có đang bị gán nhầm giá trị của `GOONG_MAPTILES_KEY` không (2 key khác mục đích, dễ nhầm khi set `.env`).
4. Sau khi Nhã xác nhận fix xong, Minh sẽ chạy lại `test_20real_stations.py` để hoàn tất phần còn lại của Ngày 6 (route factor, ETA anomaly, snap-to-road) trên dữ liệu Goong thật.

## 5. File liên quan

- File cần fix: `backend/app/services/student_routing/helpers/distance_matrix.py`
- Script test (Minh đã chuẩn bị sẵn, chạy ngay khi Nhã fix xong): `backend/app/tests/test_20real_stations.py`