# Phân tích thực nghiệm Solomon Reverse-Pickup VRPTW: Tabu, ALNS và GVNS

## 1. Phạm vi và cách đọc kết quả

Nguồn số liệu của báo cáo này là workbook `"vrptw-ctu-bus-routing-flutter\Thongkesolieu_tabu_anls_gvns.xlsx"`, gồm 72 lần chạy: 6 instance Solomon Reverse-Pickup (C101-RP, C201-RP, R101-RP, R201-RP, RC101-RP, RC201-RP) x 4 seed (100--103) x 3 thuật toán (Sweep + Tabu, Sweep + ALNS, Sweep + GVNS).

Mỗi thuật toán cùng bắt đầu từ nghiệm do Sweep sinh ra; mục tiêu đánh giá được ưu tiên theo thứ tự: (1) khả thi, (2) ít xe hơn, rồi (3) tổng khoảng cách Euclidean nhỏ hơn. Vì vậy, một nghiệm dùng ít xe hơn được xem là tốt hơn theo hàm mục tiêu ngay cả khi cần đánh đổi một lượng khoảng cách nhỏ. Tất cả kết quả dưới đây là mô tả của **phiên bản và cấu hình đang chạy**, không phải kết luận rằng một metaheuristic luôn hơn metaheuristic khác trong mọi cấu hình.

Các cột được sử dụng:

- `final distance`: tổng khoảng cách sau tối ưu; càng nhỏ càng tốt khi feasibility và số xe bằng nhau.
- `improvement(%)`: tỷ lệ giảm khoảng cách so với Sweep ban đầu, `(sweep distance - final distance) / sweep distance x 100%`.
- `vehicles`: số tuyến/xe có sử dụng trong nghiệm cuối.
- `Runtime(s)`: thời gian chạy đo được.
- `Iterations`: số vòng lặp ngoài đã hoàn tất. Chỉ số này **không thể so trực tiếp giữa các thuật toán**, vì một vòng ALNS, Tabu hay GVNS tạo và chấm số lượng lân cận khác nhau.

## 2. Kiểm tra tính khả thi

| Nội dung kiểm tra | Kết quả |
|---|---:|
| Tổng số lần chạy | 72 |
| Nghiệm feasible | 72/72 (100%) |
| Vi phạm sức chứa | 0 ở mọi lần chạy |
| Vi phạm khung thời gian trạm | 0 ở mọi lần chạy |
| Vi phạm thời hạn quay về depot | 0 ở mọi lần chạy |

Do đó, chênh lệch trong bảng là chênh lệch chất lượng tối ưu chứ không phải do thuật toán đổi lấy khoảng cách thấp bằng một nghiệm không hợp lệ.

## 3. Kết quả tổng hợp theo instance

Mỗi ô là `trung bình ± độ lệch chuẩn` trên 4 seed. Khoảng cách được làm tròn hai chữ số, phần trăm làm tròn hai chữ số. Dấu `--` ở độ lệch chuẩn bằng 0 chỉ cho biết bốn seed cho cùng một giá trị theo độ chính xác đã lưu.

| Instance | Thuật toán | Xe TB | Khoảng cách cuối TB ± SD | Cải thiện so với Sweep TB | Runtime TB (s) | Iteration TB |
|---|---|---:|---:|---:|---:|---:|
| C101-RP | Tabu | 10.00 | 887.37 ± 14.99 | 0.84% | 5.01 | 26.00 |
|  | ALNS | 10.00 | **828.94 ± 0.00** | **7.37%** | 5.20 | 65.25 |
|  | GVNS | 10.00 | 894.86 ± 0.00 | 0.00% | 5.00 | 3.00 |
| C201-RP | Tabu | 4.00 | 990.27 ± 89.84 | 10.24% | 5.01 | 25.00 |
|  | ALNS | 4.00 | **638.38 ± 17.72** | **42.14%** | 5.24 | 28.75 |
|  | GVNS | 4.00 | 1,103.28 ± 0.00 | 0.00% | 5.00 | 2.00 |
| R101-RP | Tabu | 22.00 | 1,885.75 ± 27.45 | 7.96% | 5.01 | 22.00 |
|  | ALNS | **20.50** | **1,799.44 ± 66.42** | **12.17%** | 5.14 | 39.50 |
|  | GVNS | 22.00 | 2,008.58 ± 48.95 | 1.96% | 5.00 | 1.25 |
| R201-RP | Tabu | 5.00 | 1,328.71 ± 14.86 | 9.92% | 5.01 | 25.00 |
|  | ALNS | 5.00 | **1,274.78 ± 11.46** | **13.58%** | 5.32 | 27.00 |
|  | GVNS | 5.00 | 1,444.45 ± 42.04 | 2.07% | 5.00 | 1.50 |
| RC101-RP | Tabu | 18.00 | 2,026.13 ± 5.75 | 8.90% | 5.02 | 23.00 |
|  | ALNS | **16.75** | **1,846.76 ± 71.25** | **16.96%** | 5.19 | 50.25 |
|  | GVNS | 18.00 | 2,143.87 ± 92.55 | 3.60% | 5.00 | 1.00 |
| RC201-RP | Tabu | 5.00 | 1,740.95 ± 31.03 | 17.10% | 5.01 | 24.50 |
|  | ALNS | 5.00 | **1,542.16 ± 78.16** | **26.57%** | 5.54 | 32.50 |
|  | GVNS | 5.00 | 1,987.32 ± 130.48 | 5.37% | 5.00 | 1.00 |

### Tổng quan trên sáu instance

| Thuật toán | Cải thiện TB trên 24 lần chạy | Runtime TB (s) | Iteration TB | Nhận xét tóm tắt |
|---|---:|---:|---:|---|
| Sweep + Tabu | 9.16% | 5.01 | 24.25 | Cải thiện ổn định, nhưng không giảm số xe trong các lần chạy này. |
| Sweep + ALNS | **19.80%** | 5.27 | 40.54 | Cải thiện khoảng cách lớn nhất; giảm số xe ở R101-RP và RC101-RP. |
| Sweep + GVNS | 2.17% | 5.00 | 1.63 | Giữ được feasibility, nhưng khả năng tìm kiếm trong cấu hình hiện tại còn hạn chế. |

Không lấy trung bình thô `final distance` của cả sáu instance để xếp hạng, vì các instance có quy mô và độ khó khác nhau. Tỷ lệ cải thiện so với đúng Sweep của từng instance phù hợp hơn để tổng hợp xu hướng.

## 4. Đối chiếu trực tiếp theo từng seed

So sánh trên 24 cặp `(instance, seed)` với cùng dữ liệu đầu vào và cùng nghiệm Sweep ban đầu:

| Kết quả đối chiếu | Số cặp |
|---|---:|
| ALNS có khoảng cách cuối thấp nhất | 23 |
| ALNS hòa Tabu (R101-RP, seed 103) | 1 |
| Tabu tốt hơn hoặc bằng GVNS | 24 |
| Tabu tốt hơn GVNS một cách nghiêm ngặt | 21 |
| GVNS có khoảng cách tốt nhất | 0 |

ALNS còn giảm số xe so với Sweep/Tabu/GVNS ở hai nhóm:

- `R101-RP`: từ 22 xe xuống 20 hoặc 21 xe (trung bình 20.50 xe).
- `RC101-RP`: từ 18 xe xuống 16 hoặc 17 xe (trung bình 16.75 xe).

Đây là lợi thế quan trọng vì số xe là tiêu chí thứ hai của mục tiêu phân cấp. Với bốn instance còn lại, cả ba thuật toán giữ số xe như nghiệm Sweep, nên khoảng cách là tiêu chí phân biệt trực tiếp.

## 5. Đánh giá khách quan từng thuật toán

### Sweep + ALNS

ALNS là thuật toán cho kết quả tốt nhất trên bộ số liệu hiện có: tất cả 24 nghiệm đều feasible, đứng đầu 23/24 cặp seed và hòa vị trí đầu ở cặp còn lại. Chênh lệch nổi bật nhất nằm ở C201-RP (cải thiện trung bình 42.14% so với Sweep) và RC201-RP (26.57%). ALNS cũng là thuật toán duy nhất giảm xe ở R101-RP và RC101-RP.

Tuy nhiên, kết quả không đồng nghĩa ALNS luôn ổn định hơn Tabu. Độ lệch chuẩn khoảng cách của ALNS ở R101-RP, RC101-RP và RC201-RP lần lượt là 66.42, 71.25 và 78.16; điều này cho thấy seed và chuỗi phá--sửa có ảnh hưởng. Trong khi đó, Tabu ổn định hơn rõ ở RC101-RP (SD 5.75), nhưng nghiệm trung bình vẫn kém ALNS.

### Sweep + Tabu

Tabu là phương pháp đứng thứ hai trong toàn bộ kết quả này: cải thiện trên tất cả nhóm instance, trung bình 9.16%, và luôn tốt hơn hoặc bằng GVNS. Trên R101-RP seed 103, Tabu hòa ALNS (1,886.50). Runtime của Tabu gần sát 5 giây ở mọi lần chạy và dao động rất thấp.

Điểm hạn chế là Tabu chưa hề giảm số xe trong 24 lần chạy. Các phép di chuyển cục bộ hiện có giúp giảm khoảng cách tốt, nhưng khó tạo bước tái cấu trúc lớn để gộp hai tuyến mà vẫn thỏa sức chứa và time window. Do vậy, trong cấu hình thực nghiệm này Tabu là một baseline mạnh, dễ kiểm soát và khá ổn định, nhưng không phải thuật toán tốt nhất về chất lượng nghiệm.

### Sweep + GVNS

Trong 24 lần chạy GVNS, cả 24/24 nghiệm đều feasible. Nó có cải thiện nhỏ trên R101-RP, R201-RP, RC101-RP, RC201-RP, nhưng hoàn toàn không cải thiện C101-RP và C201-RP. Đồng thời, GVNS không giảm xe ở bất kỳ instance nào.

Điểm cần diễn giải cẩn thận là `Iterations` của GVNS chỉ từ 1 đến 3 (trung bình 1.63) dù runtime luôn chạm 5 giây. Vì mỗi vòng Shaking/VND đang xét các lân cận lớn và kiểm tra feasibility tốn chi phí, một vòng ngoài đã tiêu thụ gần hết time budget. Vì vậy, kết quả này phản ánh **GVNS với cấu hình lân cận, số candidate và time budget hiện tại**, không đủ để kết luận bản chất GVNS yếu hơn Tabu hay ALNS. Nếu muốn đánh giá GVNS sâu hơn, cần tối ưu việc đánh giá lân cận hoặc giảm/cân bằng candidate trước khi tăng số vòng tìm kiếm.

## 6. Vì sao ba thuật toán cho kết quả khác nhau?

1. **Cơ chế khám phá không gian nghiệm khác nhau.** Tabu đi qua các di chuyển cục bộ như 2-opt, swap và relocate, dùng tabu tenure để hạn chế quay lại nghiệm cũ. Nó mạnh trong việc tinh chỉnh tuyến hiện có. ALNS phá một phần nghiệm rồi chèn lại các trạm bằng repair operator; nhờ vậy nó có thể thay đổi đồng thời nhiều tuyến và mở ra cơ hội bỏ một tuyến. GVNS Shaking rồi VND theo các lân cận cố định; hiệu quả phụ thuộc mạnh vào việc có đủ vòng để chuyển giữa các neighborhood hay không.

2. **Khả năng tái cấu trúc số xe.** Việc giảm xe đòi hỏi lấy các trạm của một tuyến, phân bổ lại sang các tuyến khác mà vẫn thỏa capacity/time window. Destroy--repair của ALNS phù hợp tự nhiên cho thao tác này; còn các move cục bộ của Tabu/GVNS trong cấu hình đã chạy dễ dừng ở một nghiệm khả thi cùng số xe.

3. **Time window làm cho nghiệm lân cận không đối xứng.** Một hoán đổi ngắn về hình học có thể khiến thời gian phục vụ vượt window. Do đó nhiều move bị loại bởi evaluator, đặc biệt ở các instance có cấu trúc thời gian chặt. C201-RP cho thấy ALNS vẫn tìm được các tái chèn tốt, trong khi Tabu và nhất là GVNS bị giới hạn hơn bởi neighborhood hiện có.

4. **Ngân sách tính toán phân bổ khác nhau.** `Iteration` không phải đơn vị công bằng: một vòng GVNS có thể đánh giá nhiều candidate hơn một vòng Tabu/ALNS. Dù vậy, số vòng GVNS rất thấp là dấu hiệu rõ rằng cấu hình hiện tại không khai thác được đầy đủ 5 giây để đa dạng hóa tìm kiếm.

5. **Ngẫu nhiên và seed.** Seed quyết định thứ tự lựa chọn candidate/operator và các bước ngẫu nhiên, nên tạo khác biệt giữa các lần chạy. Ví dụ Tabu trên C201-RP biến thiên từ 870.52 đến 1,083.70; ALNS RC201-RP biến thiên từ 1,472.17 đến 1,642.69. Ngược lại, ALNS C101-RP cho cùng một nghiệm ở bốn seed; đây là tính ổn định trên instance này, không nên suy rộng cho mọi instance.

## 7. Cơ chế tìm kiếm đã cài đặt

Phần này mô tả đúng các module benchmark đang tạo các tệp `sweep_tabu_v2_*`, `sweep_alns_*` và `sweep_gvns_*`. Cả ba đều nhận cùng biểu diễn nghiệm: một danh sách các tuyến, trong đó mỗi tuyến là danh sách trạm; depot không nằm trong danh sách mà được evaluator tự thêm ở đầu/cuối khi tính thời gian và khoảng cách. Sau mỗi move, bộ đánh giá Solomon kiểm tra coverage (không mất/trùng trạm), capacity, time window và thời hạn depot.

### 7.1. Sweep + Tabu v2: di chuyển cục bộ, tabu và đa dạng hóa

Tên `Tabu` trong workbook là **Tabu v2 benchmark**, một phiên bản lấy cơ chế từ Tabu production nhưng hoàn toàn dùng evaluator/ràng buộc Solomon độc lập. Tại mỗi iteration, thuật toán sinh toàn bộ mô tả move từ nghiệm hiện tại, lấy ngẫu nhiên tối đa 500 move để chấm, rồi chọn candidate có `guided score` nhỏ nhất trong các candidate không bị tabu (trừ trường hợp aspiration). Ba neighborhood là:

| Move | Cách tác động lên tuyến | Vai trò |
|---|---|---|
| `2-opt` | Chọn hai vị trí trong **cùng một tuyến** và đảo ngược đoạn trạm nằm giữa chúng. Ví dụ `[A, B, C, D, E]` có thể thành `[A, D, C, B, E]`. | Loại các đoạn đi vòng/chéo và cải thiện thứ tự ghé trạm trong một tuyến. Chỉ sinh khi tuyến có ít nhất 4 trạm. |
| `swap` | Chọn hai trạm, có thể thuộc cùng tuyến hoặc hai tuyến khác nhau, rồi đổi vị trí của chúng. | Thay đổi ghép cặp trạm--xe mà không đổi tổng số trạm của từng tuyến. Hữu ích khi hai trạm phù hợp hơn với vị trí/tuyến của nhau. |
| `relocate` | Lấy **một** trạm khỏi vị trí hiện tại và chèn vào bất kỳ vị trí nào của cùng tuyến hoặc một tuyến khác. Nếu tuyến nguồn rỗng thì loại tuyến rỗng. | Điều chỉnh tải và thời gian giữa các tuyến; về mặt cơ chế đây cũng là move có thể làm giảm xe nếu toàn bộ trạm của một tuyến lần lượt được chuyển đi. |

Candidate được evaluator chấm lại đầy đủ. `report score` công khai vẫn là `feasible -> số xe -> khoảng cách`. Trong lúc tìm kiếm, `guided score` còn phân biệt số lỗi fleet/capacity/time-window/depot để nếu thuật toán đi tạm vào nghiệm không khả thi thì ưu tiên quay lại nghiệm ít vi phạm hơn; nghiệm báo cáo cuối cùng luôn là `best` theo `report score`.

Tabu list lưu **khóa move**, không chỉ lưu toàn bộ nghiệm. Tenure cơ sở là 10 iteration và thay đổi ngẫu nhiên thành 9, 10 hoặc 11 (không nhỏ hơn 3). Một move đang tabu chỉ được phép nếu nó tạo nghiệm tốt hơn global best theo mục tiêu công khai; đây là **aspiration criterion**. Tabu không bắt buộc mọi bước phải tốt hơn current solution, nên có thể vượt local optimum. Sau 15 iteration không cải thiện global best, cơ chế diversification chọn lại một candidate khả thi đã chấm (nếu không có thì chọn candidate ít vi phạm nhất), giúp đổi vùng tìm kiếm.

### 7.2. Sweep + ALNS: destroy, repair và chọn operator thích nghi

Mỗi iteration ALNS lấy một nghiệm hiện tại, loại bỏ `q` trạm, rồi chèn lại toàn bộ `q` trạm. Trong cấu hình đang dùng, `q` được chọn ngẫu nhiên trong khoảng từ 5 đến min(20, 20% số trạm), vì thế đây là thay đổi lớn hơn một move đơn lẻ của Tabu. Bốn destroy operator là:

| Destroy operator | Cách chọn trạm để loại bỏ | Mục đích tìm kiếm |
|---|---|---|
| `random_removal` | Chọn ngẫu nhiên `q` trạm. | Đa dạng hóa không thiên lệch, mở các vùng nghiệm mới. |
| `worst_removal` | Tính mức tiết kiệm khoảng cách biên khi bỏ từng trạm khỏi tuyến; lấy `q` trạm có mức tiết kiệm lớn nhất. | Bỏ các trạm đang gây đường vòng/đoạn nối tốn chi phí để repair xây lại cấu trúc tốt hơn. |
| `related_removal` | Chọn một trạm hạt giống rồi lấy các trạm “gần liên quan” nhất. Điểm liên quan = khoảng cách tọa độ Euclidean + `0.05` x chênh lệch hai biên time window + `0.10` x chênh lệch demand. | Phá một cụm không gian--thời gian--tải để tái ghép đồng thời. |
| `route_removal` | Lần lượt chọn ngẫu nhiên các tuyến và lấy trạm của chúng cho đến khi đủ `q`; nếu tuyến cuối làm vượt `q`, lấy ngẫu nhiên `q` trạm trong tập đã chọn. | Làm suy yếu một phần cấu trúc tuyến, tạo cơ hội gộp/đổi trạm giữa các xe. |

Hai repair operator là:

| Repair operator | Cách chèn lại | Ý nghĩa |
|---|---|---|
| `greedy_insertion` | Theo thứ tự các trạm đã bị loại, thử mọi vị trí trong mọi tuyến hiện có (và một tuyến mới nếu chưa chạm giới hạn xe); chỉ xét vị trí feasible, rồi lấy vị trí làm tăng khoảng cách ít nhất. | Nhanh, khai thác tốt cấu trúc vừa bị phá. |
| `regret_2_insertion` | Với mỗi trạm chưa chèn, tìm vị trí tốt nhất và tốt thứ hai. Chọn trước trạm có `regret = cost_thứ_hai - cost_tốt_nhất` lớn nhất, sau đó chèn vào vị trí tốt nhất. Trạm chỉ có một vị trí khả thi được ưu tiên cao. | Bảo vệ các trạm “khó chèn”: nếu để sau, phương án tốt của chúng có thể bị trạm khác chiếm mất. |

Nếu một repair không có vị trí feasible, mã dùng `least_bad_insertion` để giữ đủ coverage và evaluator ghi nhận vi phạm; candidate như vậy bị mục tiêu feasibility phạt, nên không thể thay thế một nghiệm feasible tốt hơn trong kết quả cuối.

ALNS chọn destroy và repair riêng rẽ bằng **roulette-wheel selection** theo trọng số. Ban đầu mọi operator có trọng số 1. Sau mỗi 25 iteration, trọng số được cập nhật với reaction factor 0.20 từ phần thưởng trung bình: 8 cho global best mới, 4 cho nghiệm tốt hơn current, 1 cho nghiệm được chấp nhận nhưng không tốt hơn, và 0 khi bị từ chối. Vì vậy operator hiệu quả trên instance/seed đang chạy sẽ dần được gọi nhiều hơn, nhưng operator khác vẫn còn cơ hội được chọn.

Nghiệm tốt hơn luôn được nhận. Với hai nghiệm cùng trạng thái feasibility và cùng số xe, ALNS còn dùng simulated annealing để đôi khi nhận nghiệm dài hơn với xác suất `exp(-delta/temperature)`; nhiệt độ bắt đầu 20, nhân 0.995 sau mỗi iteration và không thấp hơn 0.01. Điều này giải thích vì sao ALNS có thể thoát local optimum và tái cấu trúc nhiều tuyến, nhưng cũng làm kết quả nhạy seed hơn Tabu ở một số instance.

### 7.3. Sweep + GVNS: Shaking và Variable Neighborhood Descent

GVNS có hai pha lặp lại. Trước hết **Shaking** tạo một nghiệm lân cận ngẫu nhiên để rời local optimum; sau đó **VND** cải thiện nghiệm đó có hệ thống. Ba mức Shaking được duyệt tuần hoàn nếu chưa có global best mới:

| Mức | Shaking thực hiện | Mục đích |
|---|---|---|
| `relocate_1` | Một relocate ngẫu nhiên. | Nhiễu nhẹ. |
| `swap_1` | Một swap ngẫu nhiên. | Nhiễu cấu trúc bằng hoán đổi hai trạm. |
| `relocate_2_3` | Hai hoặc ba relocate ngẫu nhiên liên tiếp. | Nhiễu mạnh hơn để thoát khỏi vùng nghiệm cũ. |

Sau Shaking, VND lần lượt xét `2-opt`, `swap`, `relocate` theo đúng nghĩa như phần Tabu. Ở mỗi neighborhood, GVNS lấy ngẫu nhiên tối đa 500 move, chọn move có `guided score` tốt nhất. Move chỉ được nhận khi nó cải thiện nghiệm đang xét; nếu được nhận, VND quay lại neighborhood đầu (`2-opt`). Nếu không cải thiện, VND chuyển sang neighborhood kế tiếp. Khi đã thử hết ba neighborhood, nếu nghiệm cuối tốt hơn global best thì cập nhật best và quay về Shaking mức đầu; nếu không, giữ nghiệm đó làm current và chuyển sang mức Shaking kế tiếp.

Khác với Tabu, GVNS không có tabu memory, aspiration, diversification theo stale counter hay adaptive operator weight; khả năng thoát bẫy đến từ Shaking. Khác với ALNS, GVNS không phá/chèn lại một nhóm trạm lớn theo destroy--repair. Với `candidates_per_neighborhood = 500`, một vòng VND có thể rất tốn thời gian; đây là lý do thực nghiệm chỉ hoàn tất 1--3 outer iteration trong 5 giây. GVNS vẫn có thể giảm số xe về mặt kỹ thuật vì relocate sẽ loại tuyến rỗng, nhưng điều đó chưa xảy ra trong 24 lần chạy đã thống kê.

## 8. Lưu ý về tính công bằng của thời gian

Mục tiêu được cấu hình là 5 giây. Tabu và GVNS ghi nhận xấp xỉ 5.00--5.02 giây. ALNS có trung bình 5.27 giây và một số lần chạy vượt 5 giây, lớn nhất 5.73 giây (dài hơn 14.6% so với 5 giây). Điều này nhiều khả năng do ALNS chỉ kiểm tra deadline ở ranh giới iteration, trong khi một destroy--repair đang chạy vẫn được hoàn tất.

Vì vậy:

- Kết luận về chất lượng nghiệm vẫn rất mạnh: ALNS tốt nhất ở 23/24 cặp, và nhiều chênh lệch lớn hơn phần thời gian vượt thêm.
- Nhưng không nên tuyên bố runtime của ALNS “bằng đúng 5 giây” hoặc dùng bảng hiện tại để kết luận ALNS nhanh/chậm tuyệt đối.
- Khi công bố so sánh chính thức, nên sửa runner để kiểm tra deadline trong candidate loop/repair loop, hoặc báo cáo rõ `runtime thực đo` và dùng cùng một hard deadline được mọi solver tuân thủ.

Ngoài ra, bốn seed là số mẫu nhỏ. Báo cáo nên trình bày từng seed, trung bình và độ lệch chuẩn như ở trên; không nên tuyên bố ý nghĩa thống kê tổng quát chỉ từ bốn lần chạy mỗi instance.

## 9. Kết luận có thể dùng trong báo cáo

Trên sáu instance Solomon Reverse-Pickup, tất cả ba phương pháp đều sinh nghiệm thỏa sức chứa, khung thời gian và thời hạn depot. Với cùng nghiệm khởi tạo Sweep và ngân sách thời gian danh nghĩa 5 giây, Sweep + ALNS cho chất lượng nghiệm tốt nhất: giảm khoảng cách trung bình 19.80% so với Sweep, đứng đầu 23/24 cặp `(instance, seed)` và giảm số xe ở R101-RP, RC101-RP. Sweep + Tabu đạt mức cải thiện trung bình 9.16%, ổn định về runtime và tốt hơn hoặc bằng GVNS trong toàn bộ các cặp chạy, do đó là baseline/thuật toán chính hợp lý khi ưu tiên cấu hình đơn giản và hành vi dễ kiểm soát. Sweep + GVNS chỉ cải thiện trung bình 2.17%; số vòng tìm kiếm rất thấp cho thấy cần tinh chỉnh cấu hình trước khi xem đây là đối thủ cạnh tranh hoàn toàn công bằng.

Kết quả thực nghiệm này **không tự động buộc phải thay Tabu trong production CTU**. Solomon Reverse-Pickup dùng khoảng cách Euclidean và ràng buộc benchmark riêng, còn production có dữ liệu đường đi, ticket và các ràng buộc vận hành khác. Kết luận phù hợp là: ALNS là ứng viên mạnh nhất để tiếp tục kiểm chứng trên bộ test CTU cùng một protocol; Tabu hiện vẫn có thể giữ vai trò thuật toán production cho đến khi so sánh đó hoàn tất.

## 10. Đoạn văn gợi ý để đưa vào báo cáo

> Với sáu instance Solomon Reverse-Pickup và bốn seed từ 100 đến 103, cả Sweep + Tabu, Sweep + ALNS và Sweep + GVNS đều tạo nghiệm khả thi, không phát sinh vi phạm sức chứa, khung thời gian hoặc thời hạn depot. ALNS đạt chất lượng tốt nhất với tỷ lệ giảm khoảng cách trung bình 19,80% so với nghiệm Sweep, đứng đầu ở 23 trong 24 cặp thử nghiệm và đồng thời giảm số xe trên R101-RP, RC101-RP. Tabu đạt mức cải thiện trung bình 9,16%, thời gian chạy ổn định và vượt GVNS ở toàn bộ cặp thử nghiệm; do đó đây là baseline mạnh để đối chiếu. GVNS chỉ đạt 2,17% trong cấu hình hiện tại, chủ yếu do số vòng tìm kiếm hoàn tất rất thấp trong ngân sách 5 giây. Cần lưu ý một số lần chạy ALNS vượt nhẹ time budget danh nghĩa, vì vậy so sánh thời gian được diễn giải theo runtime thực đo và cần siết cơ chế dừng trong các thử nghiệm tiếp theo.

