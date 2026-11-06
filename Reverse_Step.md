## Quy trình chuyển đổi Solomon gốc sang Solomon Reverse-Pickup
Bộ dữ liệu Solomon gốc mô tả bài toán VRPTW theo ngữ nghĩa giao hàng: xe xuất phát từ depot, phục vụ các customer theo time window, sau đó quay về depot. Trong đề tài, bộ dữ liệu được chuyển đổi thành biến thể Reverse-Pickup VRPTW để mô phỏng xe buýt xuất phát từ trường, đón sinh viên tại nhiều trạm và quay lại trường.

Việc chuyển đổi chỉ phục vụ thực nghiệm, không thay thế dữ liệu vận hành thật của app.
Solomon gốc
  → parser đọc depot, customer, fleet
  → tính planning horizon H
  → reverse time window từng node
  → giữ nguyên tọa độ, demand, capacity, service time
  → tạo JSON Reverse-Pickup
  → Sweep + Tabu Search chạy benchmark
1. Dữ liệu đầu vào Solomon gốc
Mỗi file như c101.txt, c201.txt gồm:
VEHICLE
NUMBER     CAPACITY
25         200

CUSTOMER
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
0          40       50       0       0           1236      0
1          45       68       10      912         967       90
...
Ý nghĩa các tham số:
Tham số	Ký hiệu	Ý nghĩa trong Solomon gốc
NUMBER	K	Số xe tối đa có thể sử dụng
CAPACITY	Q	Sức chứa tối đa mỗi xe
CUST NO.	i	Mã customer; 0 là depot
XCOORD., YCOORD.	(xᵢ, yᵢ)	Tọa độ Cartesian của node
DEMAND	qᵢ	Lượng hàng cần phục vụ tại customer
READY TIME	eᵢ	Thời điểm sớm nhất có thể bắt đầu phục vụ
DUE DATE	lᵢ	Thời điểm muộn nhất được phép bắt đầu phục vụ
SERVICE TIME	sᵢ	Thời lượng dừng để phục vụ customer


Customer 0 là depot và có demand = 0, service_time = 0.
2. Ánh xạ sang bài toán xe buýt đón sinh viên
Solomon gốc	Reverse-Pickup của đề tài
Depot	Trường/điểm xuất phát và kết thúc
Customer i	Trạm đón i
Demand qᵢ	Số sinh viên chờ tại trạm i
Capacity Q	Số chỗ tối đa của xe
Ready/Due time	Khung giờ xe được phép bắt đầu đón tại trạm
Service time sᵢ	Thời gian xe dừng đón sinh viên
Tuyến giao hàng	Tuyến xe đón sinh viên về trường


Ví dụ customer 1 có demand = 10 được diễn giải thành một trạm có 10 sinh viên cần đón. Đây tương tự production hiện tại: các ticket cùng trạm được gom lại thành một station với demand bằng số ticket.
3. Các tham số được giữ nguyên
Để bảo toàn độ khó không gian và năng lực phục vụ của instance, phép transform giữ nguyên:
xᵢ, yᵢ          Tọa độ
qᵢ              Demand / số sinh viên
K               Số xe tối đa
Q               Sức chứa mỗi xe
sᵢ              Service time
Không thực hiện các thao tác sau:
Không đổi vị trí trạm.
Không đổi demand.
Không đảo thứ tự dòng customer trong file.
Không sửa file Solomon gốc.
Không dùng GPS, Goong, OSRM, Haversine hay dữ liệu giao thông.
Khoảng cách và thời gian di chuyển dùng metric Solomon:
d(i, j) = √[(xᵢ - xⱼ)² + (yᵢ - yⱼ)²]

travel_time(i, j) = d(i, j)
Do đó, total_distance và total_travel_time trong kết quả benchmark bằng nhau về giá trị.
4. Công thức reverse time window
Đây là bước quan trọng nhất.
Planning horizon
Đầu tiên, lấy giới hạn thời gian của toàn bộ instance:
H = due date của depot
Ví dụ với C101:
Depot: [ready, due] = [0, 1236]
⇒ H = 1236
Công thức
Với một customer/trạm i có:
Time window gốc: [eᵢ, lᵢ]
Service time: sᵢ
Planning horizon: H
Time window sau reverse là:
eᵢ' = H - (lᵢ + sᵢ)

lᵢ' = H - (eᵢ + sᵢ)
Hay:
Reverse time window = [H - (due date + service time),
                       H - (ready time + service time)]
Ý nghĩa công thức
Trong dữ liệu gốc, xe bắt đầu phục vụ tại thời điểm tᵢ, thỏa:
eᵢ ≤ tᵢ ≤ lᵢ
Xe rời trạm sau thời gian phục vụ:
tᵢ + sᵢ
Khi đảo chiều thời gian theo horizon H, thời điểm bắt đầu phục vụ trong bài toán reverse là:
tᵢ' = H - (tᵢ + sᵢ)
Từ bất đẳng thức ban đầu suy ra:
H - (lᵢ + sᵢ) ≤ tᵢ' ≤ H - (eᵢ + sᵢ)
Đó chính là công thức của time window mới [eᵢ', lᵢ'].

Việc cộng service_time là cần thiết. Nếu chỉ dùng [H - lᵢ, H - eᵢ], phép phản chiếu sẽ không tính đúng khoảng thời gian xe đang dừng phục vụ tại trạm.
5. Ví dụ customer 1 của C101
Dữ liệu gốc:
Customer:      1
Tọa độ:        (45, 68)
Demand:        10
Time window:   [912, 967]
Service time:  90
H:             1236
Áp dụng công thức:
e₁' = 1236 - (967 + 90) = 179
l₁' = 1236 - (912 + 90) = 234
Dữ liệu reverse-pickup:
Trạm:          customer_1
Tọa độ:        (45, 68)
Sinh viên:     10
Time window:   [179, 234]
Service time:  90
Trong file JSON, node này được lưu cả dữ liệu gốc để có thể truy vết:
{
  "id": "customer_1",
  "source_customer_id": 1,
  "x": 45.0,
  "y": 68.0,
  "demand": 10,
  "time_window_start": 179,
  "time_window_end": 234,
  "service_time": 90,
  "source_time_window_start": 912,
  "source_time_window_end": 967
}
6. Transform depot
Depot cũng áp dụng cùng công thức:
e₀' = H - (l₀ + s₀)
l₀' = H - (e₀ + s₀)
Vì với C101:
e₀ = 0
l₀ = 1236
s₀ = 0
H = 1236
nên:
e₀' = 1236 - (1236 + 0) = 0
l₀' = 1236 - (0 + 0) = 1236
Time window depot không thay đổi:
[0, 1236] → [0, 1236]
7. Kiểm tra hợp lệ sau reverse
Với mọi station, code kiểm tra:
0 ≤ eᵢ' ≤ lᵢ' ≤ H
Một tuyến reverse-pickup được xem là khả thi nếu:
1. Tổng demand trên xe không vượt Q.
2. Mỗi trạm được phục vụ đúng một lần.
3. Xe đến sớm thì chờ đến eᵢ'.
4. Thời điểm bắt đầu phục vụ không vượt lᵢ'.
5. Sau khi phục vụ, xe cộng đúng service time sᵢ.
6. Xe quay về depot không muộn hơn l₀'.
7. Số xe sử dụng không vượt K.
Các ràng buộc đặc thù CTU không được dùng trong benchmark:
Không áp bán kính 10 km.
Không áp max ride time 45 phút.
Không áp route duration 90 phút.
Không áp service time cố định 3 phút.
Không áp ca MORNING_1/MORNING_2.
8. Đầu ra sau reverse
Mỗi instance tạo một JSON mới, ví dụ:
backend/datasets/solomon/reverse_pickup/C101_reverse_pickup.json
File này gồm:
metadata transform
fleet
depot reverse
100 station reverse
source time window và reverse time window của từng station
File raw vẫn được giữ nguyên ở:
backend/datasets/solomon/raw/In/c101.txt
Đoạn mô tả có thể dùng trong báo cáo
Bộ dữ liệu Solomon VRPTW được chuyển đổi thành bộ dữ liệu Solomon Reverse-Pickup VRPTW nhằm phù hợp với ngữ nghĩa bài toán xe buýt đón sinh viên. Depot được ánh xạ thành trường học, customer được ánh xạ thành trạm đón, demand được diễn giải là số sinh viên chờ tại trạm, capacity được diễn giải là sức chứa xe buýt và service time là thời gian xe dừng đón sinh viên.  

Để đảo chiều phục vụ theo planning horizon, time window của mỗi node được biến đổi từ [eᵢ, lᵢ] thành [H - (lᵢ + sᵢ), H - (eᵢ + sᵢ)], trong đó H là due date của depot và sᵢ là service time tại node i. Tọa độ, demand, số xe, sức chứa xe và service time được giữ nguyên. Khoảng cách Euclidean và quy ước travel time bằng distance của Solomon được duy trì để đảm bảo tính tái lập và công bằng khi so sánh thuật toán.