# Mô tả và so sánh ba thuật toán: Sweep + Tabu, Sweep + ALNS và Sweep + GVNS

## 1. Mục đích

Nghiên cứu so sánh ba metaheuristic trên **cùng một dữ liệu đầu vào, cùng nghiệm khởi tạo Sweep, cùng evaluator và cùng time budget**:

1. Sweep + Tabu Search (Tabu)
2. Sweep + Adaptive Large Neighborhood Search (ALNS)
3. Sweep + General Variable Neighborhood Search (GVNS)

`Sweep` không phải thuật toán đối thủ thứ tư. Nó là bước xây dựng nghiệm ban đầu chung. Sự khác nhau cần đánh giá là cách ba solver tiếp tục cải thiện nghiệm Sweep đó.

Tài liệu này dùng cho hai môi trường benchmark độc lập trong dự án:

| Môi trường | Input | Distance/time | Evaluator/ràng buộc |
|---|---|---|---|
| Solomon Reverse-Pickup | 100 station từ một instance RP | Euclidean; `travel_time = distance` | capacity, station time window, depot horizon, số xe |
| CTU offline | Các station CTU mô phỏng và demand giả lập | Haversine; tốc độ tĩnh 25 km/h | capacity, time window, route duration, school deadline, fleet |

Các kết quả của hai môi trường không gộp chung vì khác input và evaluator. Tuy vậy, protocol so sánh bên trong mỗi môi trường là như nhau: mọi solver chạy trên cùng scenario/instance, cùng seed và cùng budget.

## 2. Luồng chung khi ba thuật toán xử lý cùng dữ liệu

```text
Input instance/scenario
    │  (depot, station, demand, vehicle, time window, distance/time matrix)
    ▼
Sweep construction
    │  tạo initial solution S0: nhiều route, mỗi route là một dãy station
    ├─────────────────┬─────────────────┬─────────────────┐
    ▼                 ▼                 ▼
Tabu(S0)           ALNS(S0)          GVNS(S0)
    │                 │                 │
    └──── evaluate bằng cùng evaluator và cùng objective ────┘
                              │
                              ▼
          Best feasible solution của từng thuật toán
          (số xe, distance, violation, runtime, route)
```

### 2.1. Dữ liệu mà mọi solver nhận giống nhau

Trong một lần chạy cụ thể, cả ba nhận cùng:

- danh sách depot và station, gồm demand, service time, time window;
- đội xe/sức chứa và số xe tối đa;
- ma trận distance và travel time;
- nghiệm Sweep ban đầu `S0`;
- evaluator và định nghĩa feasibility;
- seed tương ứng và time budget (thường 5 giây).

Vì vậy, nếu Tabu, ALNS và GVNS có distance khác nhau, nguyên nhân là **quá trình khám phá không gian nghiệm** khác nhau, không phải vì một solver nhận thêm station, xe, thời gian hoặc ràng buộc nới lỏng hơn.

### 2.2. Biểu diễn nghiệm chung

Một nghiệm có dạng danh sách route:

```text
S = [R1, R2, ..., Rk]
Rr = [station_1, station_2, ..., station_p]
```

Depot được evaluator tự hiểu là ở đầu và cuối mỗi route:

```text
depot -> station_1 -> ... -> station_p -> depot
```

Mọi solver phải duy trì các bất biến sau:

1. Mỗi station xuất hiện đúng một lần trong toàn nghiệm.
2. Không mất station và không tạo bản sao station sau move.
3. Route rỗng bị loại bỏ.
4. Nghiệm cuối chỉ được báo cáo là feasible khi không vi phạm mọi constraint của evaluator tương ứng.

## 3. Vai trò của Sweep: điểm xuất phát chung

Sweep sắp station theo góc quanh depot, rồi đưa lần lượt station vào route hiện tại; khi vượt giới hạn tải hoặc điều kiện xây dựng tuyến, Sweep tách route mới. Sweep có ưu điểm nhanh, tái lập và tạo một nghiệm có cấu trúc địa lý ban đầu. Tuy nhiên, nó chủ yếu nhìn theo thứ tự góc nên không đảm bảo phân chia route/tổ hợp station là tốt nhất sau khi xét đầy đủ time window và distance.

Do cả ba thuật toán bắt đầu tại cùng `S0`, phần cải thiện có thể viết:

```text
Improvement_A(%) = (D(S0) - D(S_A)) / D(S0) × 100
```

trong đó `A` là Tabu, ALNS hoặc GVNS; `D(S)` là total distance. Công thức chỉ có ý nghĩa trực tiếp khi `S0` feasible. Nếu Sweep không feasible, mục tiêu trước hết là tìm nghiệm feasible, không dùng phần trăm giảm distance để kết luận chất lượng.

## 4. Tabu Search: cải thiện bằng các di chuyển cục bộ có bộ nhớ

### 4.1. Ý tưởng

Tabu Search xuất phát từ route hiện tại, thử các thay đổi nhỏ (local move), chọn một thay đổi tốt để đi tiếp và ghi nhớ những thay đổi vừa dùng trong tabu list. Nhờ tabu list, thuật toán không lập tức quay lại trạng thái cũ; do đó nó có thể đi qua một bước không tốt hơn hiện tại để thoát local optimum.

### 4.2. Ba local move

| Move | Cách thay đổi | Tác dụng chính |
|---|---|---|
| `2-opt` | Đảo thứ tự một đoạn trong cùng route. Ví dụ `[A,B,C,D,E] -> [A,D,C,B,E]`. | Rút ngắn đường đi, loại đoạn giao cắt/đi vòng trong route. |
| `swap` | Đổi vị trí của hai station, trong cùng route hoặc giữa hai route. | Đổi ghép cặp station--xe mà không đổi số station của từng route. |
| `relocate` | Lấy một station ra và chèn vào vị trí khác, cùng hoặc khác route. | Điều chỉnh thứ tự, tải và time window giữa các route; có thể làm một route rỗng và giảm số xe. |

### 4.3. Cơ chế chọn nghiệm

Trong Tabu benchmark, mỗi iteration lấy một mẫu candidate từ ba move trên, đánh giá bằng evaluator và chọn candidate tốt nhất được phép. Move vừa dùng bị cấm trong một số iteration kế tiếp (tenure động quanh giá trị cơ sở). **Aspiration** cho phép bỏ qua cấm tabu nếu move đó tạo global best mới. Khi không cải thiện trong nhiều iteration, diversification chọn một candidate khác để rời khỏi vùng tìm kiếm cũ.

### 4.4. Điểm mạnh và giới hạn

- Mạnh ở tinh chỉnh route đã khá tốt; 2-opt/swap/relocate trực tiếp và dễ kiểm soát.
- Memory tabu giảm nguy cơ lặp đi lặp lại giữa hai route tương tự.
- Một move chỉ đổi rất ít station, nên việc tái cấu trúc nhiều route hoặc làm trống hẳn một route có thể cần nhiều bước liên tiếp. Khi time window chặt, các bước trung gian có thể không feasible, khiến đường đi đến cấu trúc tốt hơn khó được khám phá.

## 5. ALNS: phá một phần nghiệm rồi xây lại có hướng dẫn

### 5.1. Ý tưởng

ALNS không chỉ đổi một hoặc hai station. Mỗi iteration chọn một **destroy operator** để lấy ra một tập station, sau đó chọn một **repair operator** để chèn lại. Việc “phá--sửa” cho phép thay đổi nhiều route đồng thời, vì thế có cơ hội vượt qua local optimum mà local move đơn lẻ khó vượt.

### 5.2. Destroy và repair operator

Triển khai Solomon RP có bốn destroy và hai repair operator:

| Loại | Operator | Cách làm | Mục tiêu |
|---|---|---|---|
| Destroy | `random_removal` | Lấy ngẫu nhiên `q` station. | Đa dạng hóa. |
| Destroy | `worst_removal` | Lấy station có mức tiết kiệm distance biên lớn khi bị bỏ. | Loại đoạn nối tốn kém. |
| Destroy | `related_removal` | Lấy nhóm station gần nhau theo tọa độ, window và demand. | Phá một cụm để ghép lại tốt hơn. |
| Destroy | `route_removal` | Lấy station từ một/vài route được chọn ngẫu nhiên. | Tạo cơ hội tái cấu trúc route và giảm xe. |
| Repair | `greedy_insertion` | Chèn từng station vào vị trí feasible làm tăng distance ít nhất. | Khai thác nhanh. |
| Repair | `regret_2_insertion` | Ưu tiên station có chênh lệch lớn giữa vị trí tốt nhất và tốt thứ hai. | Chèn trước station khó để tránh hết chỗ tốt. |

Trong CTU offline hiện tại, ALNS dùng phiên bản gọn hơn: `random_removal`, `worst_removal`, `greedy insertion` và `regret insertion`. Đây là khác biệt cấu hình có chủ đích theo benchmark; không được ghi rằng CTU offline đã dùng `related_removal` hoặc `route_removal` nếu mã chưa bổ sung chúng.

### 5.3. Adaptive selection và acceptance

Mỗi destroy/repair operator có trọng số ban đầu. Sau một segment iteration, trọng số được cập nhật theo phần thưởng: operator tạo global best được thưởng cao hơn operator chỉ tạo nghiệm được chấp nhận. Lần sau, roulette-wheel selection ưu tiên operator có trọng số cao hơn, nhưng không loại hẳn operator khác.

ALNS nhận candidate tốt hơn current solution. Với các candidate cùng mức feasibility và số xe, cơ chế simulated annealing có thể nhận tạm nghiệm distance lớn hơn theo xác suất giảm dần. Đây là cách ALNS duy trì đa dạng hóa mà không cần tabu list.

### 5.4. Điểm mạnh và giới hạn

- Có thể dịch chuyển nhiều station cùng lúc, nên thường hợp với scenario có nhiều station và nhiều cách chia route.
- Destroy/repair có thể làm một route rỗng, tạo cơ hội giảm fleet.
- Kết quả có thể nhạy seed và operator sequence hơn Tabu; mỗi iteration cũng tốn chi phí hơn một local move.
- Nếu destroy size hoặc repair operator không phù hợp, ALNS có thể phá cấu trúc tốt và cần thời gian để xây lại.

## 6. GVNS: đổi neighborhood để thoát local optimum, rồi VND để khai thác

### 6.1. Ý tưởng

GVNS kết hợp hai pha. **Shaking** làm nhiễu nghiệm hiện tại bằng một thay đổi ngẫu nhiên có cường độ tăng dần. Sau đó **Variable Neighborhood Descent (VND)** tìm cải thiện cục bộ một cách có hệ thống. Nếu tìm được global best mới, GVNS quay lại mức nhiễu nhẹ; nếu không, nó chuyển sang mức nhiễu mạnh hơn.

### 6.2. Shaking neighborhoods

| Mức | Operator | Tác động |
|---|---|---|
| N1 | `relocate_1` | Một relocate ngẫu nhiên. |
| N2 | `swap_1` | Một swap ngẫu nhiên. |
| N3 | `relocate_2_3` | Hai hoặc ba relocate ngẫu nhiên liên tiếp. |

### 6.3. VND

Sau Shaking, VND tuần tự xét:

```text
2-opt -> swap -> relocate
```

Tại mỗi neighborhood, GVNS chấm một mẫu candidate, chọn candidate tốt nhất; nếu candidate đó cải thiện current solution thì nhận nó và quay lại `2-opt`. Nếu không, chuyển sang neighborhood tiếp theo. Khi đã không còn cải thiện ở cả ba, VND kết thúc; GVNS so sánh kết quả với global best.

GVNS không dùng tabu memory hoặc adaptive operator weights. Đa dạng hóa đến từ Shaking; khai thác đến từ VND. Trong CTU offline, mỗi VND neighborhood bị giới hạn tối đa 120 candidate để giữ time budget 5 giây.

### 6.4. Điểm mạnh và giới hạn

- Nhiều mức Shaking cho phép GVNS rời local optimum mạnh hơn local search thuần.
- VND có trình tự rõ, dễ diễn giải và tái lập theo seed.
- Một outer iteration GVNS có thể chấm nhiều candidate ở tối đa ba neighborhood, do đó số `iterations_completed` thường thấp hơn Tabu/ALNS nhưng không có nghĩa GVNS làm ít công việc hơn.
- Hiệu quả phụ thuộc mạnh vào cường độ Shaking, thứ tự neighborhood và số candidate được sample; nếu cấu hình chưa phù hợp, GVNS có thể không khám phá đủ trong budget.

## 7. Ba thuật toán khác nhau thế nào trên cùng input?

| Khía cạnh | Tabu | ALNS | GVNS |
|---|---|---|---|
| Đơn vị thay đổi chính | Một local move | Một tập station bị remove rồi insert lại | Shaking + chuỗi local move VND |
| Quy mô thay đổi mỗi iteration | Nhỏ | Trung bình đến lớn | Nhỏ ở N1/N2, lớn hơn ở N3 |
| Cách thoát local optimum | Tabu memory, aspiration, diversification | Destroy--repair và simulated annealing | Shaking với nhiều mức neighborhood |
| Cách học trong khi chạy | Tabu list ngắn hạn | Adaptive weights của operator | Không học trọng số; đổi level theo kết quả |
| Khả năng tái cấu trúc liên route | Có, chủ yếu qua relocate/swap từng bước | Cao, vì nhiều station có thể được chèn lại giữa route | Có, qua relocate/swap và Shaking nhiều bước |
| Khả năng giảm xe | Có nhưng có thể cần nhiều relocate | Tự nhiên hơn khi repair không cần dùng lại route cũ | Có nếu relocate làm route rỗng |
| Độ nhạy seed | Thường vừa phải | Có thể cao hơn do operator/destroy sequence | Phụ thuộc mạnh vào Shaking và sample move |

Do đó không nên hỏi “thuật toán nào tốt hơn” mà không nêu instance, evaluator, budget, seed và chỉ số ưu tiên. Một thuật toán có thể thắng ở scenario phức tạp cần tái cấu trúc nhiều route, nhưng hòa hoặc thua ở scenario có không gian nghiệm nhỏ/chặt.

## 8. Ví dụ cách cùng một initial solution có thể dẫn đến ba nghiệm khác nhau

Giả sử Sweep tạo ba route, trong đó một route chứa một station ở xa nhưng các station gần nó lại nằm ở hai route khác.

- **Tabu:** có thể relocate station xa, rồi swap/2-opt các route liên quan qua nhiều iteration. Nếu một bước trung gian vi phạm time window hoặc bị tabu, nó có thể không đến được cấu trúc mong muốn trong budget.
- **ALNS:** có thể remove đồng thời nhóm station xa/gần liên quan rồi repair chúng vào ba route theo vị trí feasible rẻ nhất. Vì thay đổi lớn, nó có thể tìm một phân hoạch khác chỉ sau một iteration.
- **GVNS:** Shaking có thể vô tình tạo một phân hoạch mới bằng 2--3 relocate; VND sau đó 2-opt/swap/relocate để làm mịn. Nếu Shaking không tạo được vùng nghiệm tốt, GVNS chuyển sang level khác và thử lại.

Ba solver đều đánh giá bằng cùng evaluator. Nếu candidate vi phạm constraint, nó không thể trở thành best feasible result; do đó khác biệt cuối cùng là cách mỗi solver tìm đến vùng nghiệm feasible tốt, không phải cách nới ràng buộc.

## 9. Quy tắc đọc và báo cáo kết quả công bằng

1. Trước tiên báo feasible rate và mọi loại violation. Không so distance của nghiệm không feasible với nghiệm feasible.
2. Nếu objective là phân cấp, so số xe trước distance.
3. Với cùng số xe và cùng feasibility, distance nhỏ hơn là tốt hơn.
4. Báo cáo nhiều seed: mean, sample standard deviation, best/worst hoặc win--tie--loss; không kết luận chỉ từ một seed.
5. Giữ cùng input, Sweep, evaluator, budget và hardware/môi trường gần tương đương cho các solver.
6. Không so `iterations` giữa các thuật toán như thước đo tốc độ; thay vào đó báo runtime thực đo và nếu có, evaluations.
7. Nêu rõ cấu hình operator/candidate limit. Kết luận chỉ áp dụng cho cấu hình đã công bố.

## 10. Đoạn văn có thể dùng trong báo cáo

> Ba phương pháp được so sánh trên cùng nghiệm khởi tạo Sweep, cùng dữ liệu, cùng evaluator và cùng ngân sách thời gian. Tabu Search cải thiện nghiệm bằng các di chuyển cục bộ 2-opt, swap và relocate, kết hợp tabu memory để tránh quay lại nghiệm cũ. ALNS loại bỏ một tập trạm rồi chèn lại bằng các repair heuristic, đồng thời điều chỉnh trọng số chọn operator theo hiệu quả quan sát được; vì vậy nó có khả năng tái cấu trúc nhiều tuyến trong một iteration. GVNS dùng Shaking để tạo nhiễu ở các neighborhood có cường độ khác nhau, sau đó áp dụng Variable Neighborhood Descent với 2-opt, swap và relocate. Do ba cơ chế khám phá không gian nghiệm khác nhau, chúng có thể cho các nghiệm khác nhau dù nhận cùng input; kết quả được đánh giá theo feasibility, số xe và tổng khoảng cách thay vì chỉ theo số iteration.
