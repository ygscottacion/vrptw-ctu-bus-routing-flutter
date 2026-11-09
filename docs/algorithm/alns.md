## ALNS – Adaptive Large Neighborhood Search: Tìm hiểu toàn diện và ứng dụng vào Solomon Reverse-Pickup VRPTW
* Một thuật toán Metaheuristic dùng để giải các bài toán tối ưu tổ hợp phức tạp, đặc biệt phù hợp với Vehicle Routing Problem (VRP), Vehicle Routing Problem with Time Windows (VRPTW), Pickup and Delivery Problem (PDP) và các bài toán lập lịch.
* Điểm đặc biệt của ALNS là nó không chỉ thay đổi một vài vị trí trong nghiệm hiện tại. Nó có thể loại bỏ một phần lớn nghiệm hiện tại rồi xây dựng lại phần đó theo nhiều chiến lược khác nhau.
* Sweep + Tabu chủ yếu bắt đầu bằng một cấu trúc phân tuyến rồi cải thiện nó. ALNS có khả năng phá vỡ cấu trúc phân tuyến đó và tái xây dựng một cấu trúc mới.

# PHẦN I. NỀN TẢNG LÝ THUYẾT
https://pubsonline.informs.org/doi/fpi/10.1287/trsc.1050.0135
https://www.sciencedirect.com/science/article/pii/S0305054822001654?utm_source=chatgpt.com

## ALNS mở rộng LNS bằng cách sử dụng nhiều phương pháp Destroy và Repair cạnh tranh với nhau.
Destroy Operators              Repair Operators

Random Removal                 Greedy Insertion
Worst Removal                  Regret-2 Insertion
Shaw Removal                   Regret-3 Insertion
Route Removal                  Randomized Insertion
Related Removal                ...

* ALNS là Metaheuristic, cụ thể có thể xem là một phương pháp tìm kiếm theo quỹ đạo (Trajectory-based Metaheuristic) kết hợp với cơ chế lựa chọn heuristic thích nghi.

Thuật toán	        Cách tìm kiếm
Tabu Search	        Di chuyển qua các nghiệm lân cận, dùng Tabu List
ALNS	            Phá hủy và tái xây dựng nghiệm bằng nhiều operator thích nghi

## PHẦN II. CẤU TRÚC VÀ CƠ CHẾ HOẠT ĐỘNG
             Reverse-Pickup Instance
                       |
                       v
              Initial Solution
                       |
                       v
               Current Solution
                       |
                       v
              Select Destroy Operator
                       |
                       v
                Destroy Solution
                       |
                       v
              Select Repair Operator
                       |
                       v
                Repair Solution
                       |
                       v
                Candidate Solution
                       |
                       v
             Evaluate Candidate
                       |
                       v
              Acceptance Criterion
                       |
                 +-----+-----+
                 |           |
               Accept      Reject
                 |           |
                 v           |
            Update Current   |
                 |           |
                 +-----+-----+
                       |
                       v
              Update Best Solution
                       |
                       v
             Update Operator Scores
                       |
                       v
              Adaptive Weight Update
                       |
                       v
                 Next Iteration

ALNS duy trì ba đối tượng quan trọng:
Đối tượng	        Ý nghĩa
Current Solution	Nghiệm đang được sử dụng để tiếp tục tìm kiếm
Candidate Solution	Nghiệm vừa được Destroy và Repair
Best Solution	    Nghiệm tốt nhất từng tìm được

# Solution Representation – Biểu diễn nghiệm ...
# Destroy Operators - ...
# Repair Operators - ...

## PHẦN III. CƠ CHẾ ADAPTIVE – ĐIỂM CỐT LÕI CỦA ALNS
* Adaptive Operator Selection - ...
# Acceptance Criterion - ...

# PHẦN IV. XỬ LÝ RÀNG BUỘC VRPTW REVERSE-PICKUP
Đây là vehicle capacity.

Với Reverse-Pickup, giả sử xe xuất phát rỗng và thu gom hàng tại mỗi station.

Tải trọng sau khi ghé station i:
L_i=L_{i-1}+q_i

Trong đó:
- L_i: Tải trọng sau station i.
- q_i: Demand cần thu gom.
- L_0=0: Xe xuất phát với tải trọng bằng 0.
Ràng buộc:
0<= leq L_i <=Q