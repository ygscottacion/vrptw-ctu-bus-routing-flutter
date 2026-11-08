# Thực nghiệm CTU mô phỏng: Sweep + Tabu, Sweep + ALNS và Sweep + GVNS

## 1. Phạm vi, nguồn dữ liệu và khả năng tái lập

Thực nghiệm dùng năm **kịch bản CTU mô phỏng dựa trên vị trí thực**. Depot và tọa độ các trạm `LOC-02` đến `LOC-20` được chép từ dữ liệu vị trí của hệ thống CTU. Demand tại trạm được thiết kế nhân tạo; không có profile, tên sinh viên, ticket, QR code hay thao tác đọc/ghi cơ sở dữ liệu nào được dùng. Vì vậy, đây không phải kết quả trên hành vi đặt vé thật.

Mỗi cặp `scenario × seed` chạy Tabu, ALNS và GVNS độc lập với budget 5 giây. Có năm seed `100`--`104`, nên có `5 × 5 × 3 = 75` lần chạy thuật toán. JSON nguồn theo từng seed nằm trong `backend/evidence/ctu/runs/`, có tên `ctu_<scenario>_three_algorithms_seed_<seed>.json`.

### 1.1. Cấu hình vận hành chung

| Thành phần | Giá trị |
|---|---|
| Depot | CTU Khu II `(10.0282, 105.7682)` |
| Ca và chiều | `MORNING_1`, `PICKUP`; lớp lúc 07:00 |
| Xuất phát / deadline | 05:30 / 06:50 |
| Đội xe | 3 xe, database capacity 30/xe |
| Effective capacity | 29/xe, tổng 87 sinh viên |
| Service time | 3 phút/trạm |
| Time window | 45 phút/trạm |
| Bán kính phục vụ | 10 km |
| Driving duration tối đa | 90 phút/tuyến, không tính waiting/service |
| Ride-time constraint | Tắt, khớp `ENFORCE_MAX_RIDE_TIME = False` |

### 1.2. Mô hình distance, travel time và time window

Khoảng cách dùng Haversine. Travel time cho `MORNING_1` dùng vận tốc cố định 25 km/h: `t(i,j) = 60 × d(i,j) / 25` phút. Với mỗi trạm, `latest_i = 410 − t(i,depot) − 3` và `TW_i = [latest_i − 45, latest_i]`. Đây là static fallback tương ứng backend, không gọi Goong/OSRM hay traffic thời gian thực.

### 1.3. Kịch bản demand

| Kịch bản | Ngày mô phỏng | Trạm | Vé | Mục đích |
|---|---|---:|---:|---|
| CTU-Low | 2026-11-09 | 6 | 24 | Nhu cầu thấp |
| CTU-Medium | 2026-11-10 | 9 | 48 | Nhu cầu trung bình |
| CTU-High | 2026-11-11 | 14 | 67 | Nhu cầu cao |
| CTU-Concentrated | 2026-11-12 | 8 | 60 | Demand tập trung |
| CTU-Dispersed | 2026-11-13 | 18 | 66 | Nhiều trạm phân tán |

## 2. Protocol và cấu hình thuật toán

Cả ba thuật toán nhận đúng cùng nghiệm đầu Sweep: trạm được sắp theo góc cực quanh depot, sau đó tách tuyến khi vượt capacity hoặc ước lượng driving duration. Tất cả dùng cùng evaluator offline. Feasible nghĩa là `capacity_violations`, `time_window_violations`, `route_duration_violations`, `school_arrival_violations` và `fleet_violations` đều bằng 0.

| Thành phần | Tabu benchmark offline | ALNS benchmark offline | GVNS benchmark offline |
|---|---|---|---|
| Nghiệm đầu | Sweep chung | Sweep chung | Sweep chung |
| Cơ chế chính | 2-opt, swap, relocate; tabu tenure động và aspiration | Random/worst removal; greedy/regret insertion; adaptive weights và SA acceptance | Shaking `relocate_1`, `swap_1`, `relocate_2_3`; VND với 2-opt, swap, relocate |
| Kiểm soát candidate | Tối đa 120 move/iteration | Destroy 12--30% số trạm, repair lại | Tối đa 120 move cho mỗi VND neighborhood |
| Seed/budget | 100--104; 5 giây | 100--104; 5 giây | 100--104; 5 giây |

`Z` là objective nội bộ của evaluator CTU, gồm distance, waiting và penalty ràng buộc. Với nghiệm feasible, bảng ưu tiên đọc theo feasibility, số xe rồi distance; `Z` được giữ để kiểm chứng hành vi tìm kiếm, không thay thế distance.

Lệnh tái lập một lần chạy:

```powershell
cd D:\NCKH2026\vrptw-ctu-bus-routing-flutter\backend
python data/ctu_algorithms_benchmark.py --scenario CTU-High --iterations 1000000 --runs 1 --seed 100 --max-runtime-seconds 5 --candidates-per-neighborhood 120 --output evidence/ctu/runs/ctu_high_three_algorithms_seed_100.json
```

## 3. Bảng kết quả chính

Mỗi giá trị là trung bình ± độ lệch chuẩn mẫu của năm seed. `Không áp dụng*` có nghĩa Sweep ban đầu không feasible, nên không được tính phần trăm cải thiện distance từ Sweep.

| Kịch bản | Trạm | Vé | Sweep feasible | Thuật toán | Feasible rate | Xe TB ± SD | Distance km TB ± SD | Z TB ± SD | Runtime s TB ± SD | Iterations TB ± SD | Cải thiện distance so với Sweep |
|---|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| CTU-Low | 6 | 24 | Có | Tabu | 5/5 | 1.00 ± 0.00 | 7.358 ± 0.000 | 19.47 ± 0.00 | 5.000 ± 0.000 | 2844 ± 48 | 12.21% |
|  |  |  |  | ALNS | 5/5 | 1.00 ± 0.00 | 7.358 ± 0.000 | 19.48 ± 0.03 | 5.000 ± 0.000 | 9412 ± 514 | 12.21% |
|  |  |  |  | GVNS | 5/5 | 1.00 ± 0.00 | 7.358 ± 0.000 | 19.47 ± 0.00 | 5.000 ± 0.000 | 1429 ± 235 | 12.21% |
| CTU-Medium | 9 | 48 | Có | Tabu | 5/5 | 2.00 ± 0.00 | 14.505 ± 0.000 | 34.24 ± 0.00 | 5.000 ± 0.000 | 856 ± 67 | 8.02% |
|  |  |  |  | ALNS | 5/5 | 2.00 ± 0.00 | 14.505 ± 0.000 | 34.24 ± 0.00 | 5.002 ± 0.001 | 2726 ± 144 | 8.02% |
|  |  |  |  | GVNS | 5/5 | 2.00 ± 0.00 | 14.505 ± 0.000 | 34.24 ± 0.00 | 5.000 ± 0.000 | 262 ± 14 | 8.02% |
| CTU-High | 14 | 67 | Có | Tabu | 5/5 | 3.00 ± 0.00 | 28.137 ± 0.000 | 51.16 ± 0.00 | 5.000 ± 0.000 | 550 ± 65 | 4.50% |
|  |  |  |  | ALNS | 5/5 | 3.00 ± 0.00 | **24.479 ± 0.000** | **50.40 ± 0.00** | 5.003 ± 0.002 | 591 ± 23 | **16.94%** |
|  |  |  |  | GVNS | 5/5 | 3.00 ± 0.00 | 25.176 ± 1.407 | 50.52 ± 0.16 | 5.000 ± 0.000 | 73 ± 5 | 14.58% |
| CTU-Concentrated | 8 | 60 | Có | Tabu | 5/5 | 3.00 ± 0.00 | 10.808 ± 0.000 | 47.40 ± 0.00 | 5.000 ± 0.000 | 1080 ± 37 | 0.24% |
|  |  |  |  | ALNS | 5/5 | 3.00 ± 0.00 | 10.808 ± 0.000 | 47.40 ± 0.00 | 5.001 ± 0.001 | 3273 ± 113 | 0.24% |
|  |  |  |  | GVNS | 5/5 | 3.00 ± 0.00 | 10.808 ± 0.000 | 47.40 ± 0.00 | 5.000 ± 0.000 | 399 ± 17 | 0.24% |
| CTU-Dispersed | 18 | 66 | Không | Tabu | 5/5 | 3.00 ± 0.00 | **35.248 ± 0.108** | **51.45 ± 0.11** | 5.000 ± 0.000 | 484 ± 23 | Không áp dụng* |
|  |  |  |  | ALNS | 5/5 | 3.00 ± 0.00 | 35.441 ± 0.000 | 51.64 ± 0.00 | 5.013 ± 0.004 | 255 ± 12 | Không áp dụng* |
|  |  |  |  | GVNS | 5/5 | 3.00 ± 0.00 | 35.377 ± 0.395 | 51.58 ± 0.39 | 5.000 ± 0.000 | 41 ± 3 | Không áp dụng* |

`*` Sweep CTU-Dispersed không feasible: 2 vi phạm time window và 1 vi phạm deadline; `Z = 181862.04` chủ yếu do penalty. Cả ba thuật toán khôi phục được nghiệm feasible.

## 4. Cách các số liệu được tạo ra và cách kiểm chứng

### 4.1. Một dòng trong bảng được tính từ đâu?

Với mỗi `scenario` và mỗi seed `r` từ 100 đến 104, runner thực hiện độc lập theo chuỗi sau:

```text
SCENARIOS (tọa độ trạm + demand giả lập)
    -> build_case (Haversine matrix, travel time, time window)
    -> sweep_initial (cùng một nghiệm đầu cho cả ba solver)
    -> Tabu / ALNS / GVNS trong tối đa 5 giây
    -> evaluate (distance, waiting, mọi violation, Z, routes)
    -> JSON evidence theo scenario × seed
    -> trung bình và độ lệch chuẩn của 5 seed trong Bảng 3
```

Do demand, tọa độ, matrix, time window và nghiệm Sweep đầu vào là cố định trong một scenario, khác biệt giữa năm lần chạy chỉ đến từ seed của thao tác ngẫu nhiên trong solver và từ thời điểm solver dừng ở time budget. Không có dữ liệu ticket/database nào được đọc trong chuỗi này.

Với một thuật toán `A` trên một scenario, gọi `D_r` là `total_distance_km` của seed `r`, bảng sử dụng:

```text
Distance TB = (D_100 + D_101 + D_102 + D_103 + D_104) / 5

SD mẫu = sqrt( sum((D_r - Distance TB)^2) / (5 - 1) )

Improvement(%) = (D_sweep - Distance TB) / D_sweep × 100
```

`Improvement(%)` chỉ được tính khi Sweep ban đầu feasible. Với CTU-Dispersed, Sweep có vi phạm nên mẫu số `D_sweep` không phải một baseline khả thi; vì vậy bảng ghi “Không áp dụng”, dù ba solver sau đó vẫn tìm được nghiệm feasible.

`Feasible rate = số seed feasible / 5`. Đối với các route cuối được báo cáo, các trường `capacity_violations`, `time_window_violations`, `route_duration_violations`, `school_arrival_violations`, `fleet_violations` đều bằng 0. Do đó chênh lệch distance trong Bảng 3 không phải do solver đổi lấy một route ngắn hơn nhưng không đáp ứng ràng buộc.

### 4.2. Vì sao distance và Z không luôn bằng nhau?

Evaluator CTU tính objective nội bộ theo dạng:

```text
Z = distance
  + 0.5 × early_arrival_minutes
  + 10 × late_arrival_minutes
  + các penalty rất lớn cho time-window, capacity,
    route-duration và school-arrival violation
```

Vì tất cả route cuối đều feasible và không late, ở các nghiệm cuối đang báo cáo thực tế:

```text
Z = distance + 0.5 × early_arrival_minutes
```

Do đó hai route có thể có distance khác nhau nhưng `Z` không chênh tương ứng nếu route ngắn hơn phải chờ lâu hơn tại trạm. Ví dụ seed 100 của CTU-High: ALNS có distance `24.479 km`, ngắn hơn Tabu `28.137 km`, nhưng early waiting là `51.85` phút thay vì `46.05` phút. Khi cộng `0.5 × waiting`, Z của ALNS là `50.40`, chỉ thấp hơn Z Tabu `51.16` một lượng nhỏ hơn chênh distance. Vì mục tiêu báo cáo sau feasibility và số xe ưu tiên distance, Bảng 3 vẫn đặt distance làm chỉ số so sánh chính; Z dùng để minh bạch quyết định nội bộ của evaluator.

### 4.3. Truy vết tuyến điển hình (seed 100)

Các tuyến dưới đây trích từ JSON evidence seed 100. Chúng là ví dụ kiểm chứng cấu trúc nghiệm, không thay thế cho trung bình năm seed trong Bảng 3. Đổi thứ tự liệt kê xe không làm đổi nghiệm, vì vehicle index không mang ý nghĩa địa lý.

| Scenario | Thuật toán | Distance (km) | Các tuyến station code theo thứ tự ghé |
|---|---|---:|---|
| Low | Cả 3 | 7.358 | `[LOC-12, LOC-06, LOC-08, LOC-04, LOC-18, LOC-05]` |
| Medium | Cả 3 | 14.505 | `[LOC-02, LOC-12, LOC-06, LOC-15, LOC-08]`; `[LOC-03, LOC-09, LOC-04, LOC-05]` |
| High | Tabu | 28.137 | `[LOC-14, LOC-02, LOC-06, LOC-12, LOC-13, LOC-07]`; `[LOC-10, LOC-05]`; `[LOC-11, LOC-03, LOC-09, LOC-15, LOC-08, LOC-04]` |
| High | ALNS | 24.479 | `[LOC-02, LOC-12, LOC-06, LOC-15, LOC-08]`; `[LOC-14, LOC-13, LOC-07, LOC-05]`; `[LOC-10, LOC-11, LOC-03, LOC-09, LOC-04]` |
| High | GVNS | 24.760 | `[LOC-14, LOC-13, LOC-07, LOC-05, LOC-04]`; `[LOC-10, LOC-11, LOC-03, LOC-09, LOC-15, LOC-08]`; `[LOC-02, LOC-12, LOC-06]` |
| Concentrated | Cả 3 | 10.808 | `[LOC-12, LOC-06, LOC-20, LOC-04]`; `[LOC-05, LOC-18]`; `[LOC-15, LOC-08]` |
| Dispersed | Tabu/GVNS | 35.200 | `[LOC-14, LOC-13, LOC-07, LOC-05]`; `[LOC-16, LOC-19, LOC-10, LOC-11, LOC-03, LOC-18, LOC-04]`; `[LOC-17, LOC-09, LOC-02, LOC-12, LOC-06, LOC-15, LOC-08]` |
| Dispersed | ALNS | 35.441 | `[LOC-14, LOC-02, LOC-06, LOC-12, LOC-13, LOC-07, LOC-05]`; `[LOC-16, LOC-19, LOC-10, LOC-11, LOC-18, LOC-04]`; `[LOC-17, LOC-03, LOC-09, LOC-15, LOC-08]` |

### 4.4. Giải thích từng pattern trong số liệu

**CTU-Low.** Sáu trạm có tổng demand 24, thấp hơn effective capacity 29, nên một xe là đủ. Không gian nghiệm khả thi nhỏ: sau khi loại đoạn đi vòng của Sweep, cả ba cách tìm kiếm đều đi đến cùng thứ tự sáu trạm và cùng distance `7.358 km`. Improvement `12.21%` xuất phát trực tiếp từ `(8.381 - 7.358) / 8.381`. Việc ba thuật toán hòa không chứng minh chúng giống nhau; nó chỉ cho thấy instance này không còn nhiều cơ hội tái cấu trúc route.

**CTU-Medium.** Tổng demand 48 buộc phải dùng ít nhất hai xe vì một xe chỉ chở tối đa 29. Cả ba tìm cùng phân hoạch 5 trạm và 4 trạm như bảng truy vết, do đó cùng distance `14.505 km`. Sweep có `15.769 km`; phần giảm `8.02%` đến chủ yếu từ sửa thứ tự ghé trong từng nhóm địa lý, không phải giảm số xe.

**CTU-High.** Demand 67 yêu cầu ít nhất ba xe (`ceil(67/29) = 3`), nên không solver nào có thể giảm fleet. Khác biệt đến từ cách chia 14 trạm giữa ba xe. ALNS destroy một nhóm trạm rồi repair lại, nên có thể đồng thời chuyển các trạm như `LOC-15`, `LOC-08`, `LOC-04`, `LOC-05` giữa nhiều tuyến để tạo ba cụm tuyến liên tục hơn. Từ seed 100, việc này giảm distance từ route Tabu tổng `28.137 km` xuống `24.479 km`. GVNS với Shaking + VND cũng tìm được cấu trúc gần tốt (`24.760 km` ở seed 100), nhưng kết quả biến động giữa seed, làm mean là `25.176 ± 1.407 km`. Tabu dựa trên move cục bộ nên trong cấu hình/budget này dễ giữ lại phân hoạch ban đầu có một route rất ngắn `[LOC-10, LOC-05]` và hai route dài hơn.

**CTU-Concentrated.** Tổng demand 60 cũng yêu cầu ba xe (`ceil(60/29) = 3`). Một số trạm có demand lớn (đặc biệt `LOC-08:16`, `LOC-04:14`, `LOC-18:10`) làm capacity thu hẹp mạnh các cách ghép tuyến. Vì vậy, sau Sweep gần như chỉ còn một cấu trúc feasible ngắn nhất; cả ba đều đạt `10.808 km`. Improvement chỉ `0.24%` vì Sweep vốn đã gần optimum theo distance của scenario này, không phải vì solver không hoạt động.

**CTU-Dispersed.** Có 18 trạm phân tán, total demand 66 nên cần ba xe. Sweep theo góc tạo baseline `40.993 km` nhưng không xét đầy đủ time window tại thời điểm xây dựng, dẫn đến 2 time-window và 1 school-deadline violation. Ba metaheuristic chấm lại bằng evaluator đầy đủ và tái phân tuyến để loại toàn bộ violation. Tabu/GVNS có thể cùng tìm cấu trúc `35.200 km` ở một số seed; ALNS có cấu trúc feasible khác, dài hơn `35.441 km`. Trung bình Tabu `35.248 km` tốt hơn GVNS `35.377 km` chỉ `0.129 km` (0.37%); SD GVNS `0.395 km` cho thấy đây là kết quả nhạy seed, nên không đủ căn cứ khẳng định Tabu ưu việt tuyệt đối.

## 5. Phân tích kết quả sau khi thêm GVNS

1. **Feasibility và số xe.** Cả 75 lần chạy đều feasible. Cả ba dùng cùng số xe trên từng scenario: Low 1 xe, Medium 2 xe, High/Concentrated/Dispersed 3 xe. Vì vậy, distance là chỉ số phân biệt chất lượng chính trong các kết quả này.

2. **Các kịch bản hòa.** Low, Medium và Concentrated hòa hoàn toàn về distance giữa ba thuật toán. Đây không chứng minh ba phương pháp tương đương nói chung; ở các scenario nhỏ/cấu trúc chặt, capacity và time window đã giới hạn rất mạnh số cấu trúc tuyến khả thi tốt.

3. **CTU-High.** ALNS tốt nhất và ổn định nhất: 24.479 km ở cả năm seed. GVNS đạt trung bình 25.176 km, tốt hơn Tabu 28.137 km nhưng có độ lệch chuẩn 1.407 km. Cơ chế Shaking + VND cho phép GVNS thoát local optimum do Sweep tạo ra, nhưng các bước local search vẫn phụ thuộc mạnh vào vị trí Shaking/seed. ALNS có ưu thế vì destroy--repair có thể tái cấu trúc nhiều trạm cùng lúc.

4. **CTU-Dispersed.** Sweep ban đầu không feasible, nên bài toán trước hết là khôi phục feasibility. Tabu đạt distance trung bình tốt nhất 35.248 km. GVNS rất gần (35.377 km, chênh 0.129 km hay khoảng 0.37% so với Tabu) nhưng biến thiên lớn hơn; ALNS đạt 35.441 km. Đây là chênh lệch nhỏ, không đủ để kết luận Tabu vượt trội tuyệt đối.

5. **Runtime và iterations.** Ba solver đều bị chặn ở xấp xỉ 5 giây. ALNS vượt nhẹ vài mili-giây do chỉ kiểm tra deadline giữa iteration và hoàn tất repair đang chạy. Iteration không là đơn vị so sánh công bằng: một vòng GVNS thực hiện Shaking và có thể quét tối đa 120 candidate cho mỗi trong ba VND neighborhood; một vòng Tabu/ALNS có chi phí khác. GVNS có ít outer iteration hơn, nhất là High/Dispersed, nhưng vẫn chấm hàng chục nghìn candidate trong 5 giây.

## 6. Kết luận hiện tại

Việc thêm GVNS xác nhận rằng Tabu không phải lúc nào cũng cho khoảng cách nhỏ nhất: ALNS thắng rõ ở CTU-High, còn GVNS là phương án cạnh tranh và vượt Tabu trung bình ở CTU-High. Tuy vậy, Tabu tốt nhất trên CTU-Dispersed, và ba thuật toán hòa trên ba scenario còn lại. Do tất cả đều feasible và số xe không khác, kết luận khách quan là **không có một thuật toán duy nhất thắng nhất quán trên cả năm scenario**.

Giữ Sweep + Tabu Search làm solver production hiện tại vẫn hợp lý vì Tabu đã tích hợp với `StudentRoutingService`, matrix provider, RouteJob, RouteValidator và luồng gán ticket. ALNS và GVNS tại đây chỉ là benchmark offline: dùng demand giả lập, Haversine/static speed và không đi qua pipeline production. Kết quả mới là cơ sở để xem ALNS/GVNS như ứng viên nâng cấp, không phải căn cứ để thay solver production ngay.

## 7. Giới hạn và bước tiếp theo

1. Demand mô phỏng không đại diện trực tiếp cho hành vi đặt vé thật.
2. Static Haversine matrix không phản ánh đường một chiều, giao thông hay ETA thật như Goong/OSRM.
3. Tabu benchmark chỉ mô phỏng các cơ chế production, không gọi trực tiếp `TabuSearchOptimizer` hoặc pipeline database.
4. Nếu bật ride-time constraint hoặc đổi cấu hình CTU, toàn bộ benchmark phải chạy lại.
5. Khi so sánh tiếp, phải giữ nguyên scenario, evaluator, matrix, seed `100`--`104`, budget 5 giây và số candidate của solver tương ứng.
