# Lựa chọn và biến đổi bộ Solomon thành Solomon Reverse-Pickup VRPTW

## 1. Mục đích của bộ thực nghiệm

Phần thực nghiệm này đánh giá **hiệu quả thuật toán định tuyến** (Sweep + Tabu, Sweep + ALNS, Sweep + GVNS) trong một môi trường chuẩn hóa. Bộ Solomon được dùng vì nó là bộ dữ liệu VRPTW kinh điển, có cấu trúc rõ ràng về depot, khách hàng, nhu cầu, sức chứa xe, thời gian phục vụ và khung thời gian. Tuy nhiên, ngữ nghĩa gốc của Solomon là giao hàng từ depot đến khách hàng; hệ thống xe buýt CTU lại là bài toán **đón người tại trạm rồi trở về trường**. Vì thế dữ liệu gốc được biến đổi thành biến thể có tên **Solomon Reverse-Pickup VRPTW (RP)**.

Biến đổi này phục vụ mục tiêu kiểm thử/so sánh thuật toán. Nó không khẳng định tập Solomon đã trở thành dữ liệu vận hành thật của CTU, cũng không thay thế benchmark CTU offline hoặc dữ liệu ticket thật.

## 2. Bộ Solomon gốc

### 2.1. Cấu trúc một instance

Mỗi file Solomon gốc có một dòng phương tiện và 101 node: node `0` là depot, 100 node còn lại là customer. Một dòng customer có dạng:

```text
CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME
```

Ký hiệu gốc:

| Ký hiệu | Trường file | Ý nghĩa trong Solomon gốc |
|---|---|---|
| `i` | `CUST NO.` | Mã customer; `i = 0` là depot |
| `(x_i, y_i)` | `XCOORD., YCOORD.` | Tọa độ Cartesian của node `i` |
| `q_i` | `DEMAND` | Lượng hàng cần giao tại customer `i` |
| `a_i` | `READY TIME` | Thời điểm sớm nhất được bắt đầu phục vụ customer `i` |
| `b_i` | `DUE DATE` | Thời điểm muộn nhất được bắt đầu phục vụ customer `i` |
| `s_i` | `SERVICE TIME` | Thời lượng phục vụ tại customer `i` |
| `m` | `NUMBER` trong `VEHICLE` | Số xe tối đa |
| `Q` | `CAPACITY` trong `VEHICLE` | Sức chứa mỗi xe |

Trong Solomon chuẩn, xe xuất phát từ depot, ghé một tập customer, sau đó quay về depot. Với khoảng cách Euclidean, khoảng cách và thời gian di chuyển của cặp node `i, j` là:

```text
d(i, j) = sqrt((x_i - x_j)^2 + (y_i - y_j)^2)
t(i, j) = d(i, j)
```

Đây là quy ước benchmark; đơn vị thời gian là số nguyên Solomon, không phải giờ `HH:MM` hay phút vận hành CTU.

### 2.2. Sáu nhóm của 56 instance gốc

Bộ Solomon chuẩn có 56 instance 100-customer, phân theo đặc trưng không gian và độ rộng khung thời gian:

| Họ | Số instance | Phân bố customer | Nhóm window |
|---|---:|---|---|
| `C1` | 9 | Customer tạo cụm (clustered) | Hẹp |
| `C2` | 8 | Customer tạo cụm | Rộng hơn |
| `R1` | 12 | Customer phân bố ngẫu nhiên (random) | Hẹp |
| `R2` | 11 | Customer phân bố ngẫu nhiên | Rộng hơn |
| `RC1` | 8 | Kết hợp cụm và ngẫu nhiên | Hẹp |
| `RC2` | 8 | Kết hợp cụm và ngẫu nhiên | Rộng hơn |
| **Tổng** | **56** |  |  |

Hậu tố `1`/`2` là quy ước phân nhóm benchmark: nhóm `1` thường có time window chặt hơn, do đó việc ghép nhiều customer vào cùng một tuyến khó hơn; nhóm `2` cho nhiều không gian thời gian hơn. Điều này không có nghĩa mọi instance cùng nhóm có độ khó tuyệt đối giống nhau, nhưng là cơ sở hợp lý để lấy mẫu đại diện.

Nguồn học thuật gốc: M. M. Solomon, “Algorithms for the Vehicle Routing and Scheduling Problems with Time Window Constraints”, *Operations Research*, 35(2), 254–265, 1987, [DOI: 10.1287/opre.35.2.254](https://doi.org/10.1287/opre.35.2.254).

## 3. Lý do chọn 6 trên 56 instance

### 3.1. Sáu instance được chọn

| Họ đại diện | Instance dùng | File raw trong dự án | File Reverse-Pickup tạo ra |
|---|---|---|---|
| C1 | `C101` | `backend/datasets/solomon/raw/In/c101.txt` | `backend/datasets/solomon/reverse_pickup/C101_reverse_pickup.json` |
| C2 | `C201` | `backend/datasets/solomon/raw/In/c201.txt` | `backend/datasets/solomon/reverse_pickup/C201_reverse_pickup.json` |
| R1 | `R101` | `backend/datasets/solomon/raw/In/r101.txt` | `backend/datasets/solomon/reverse_pickup/R101_reverse_pickup.json` |
| R2 | `R201` | `backend/datasets/solomon/raw/In/r201.txt` | `backend/datasets/solomon/reverse_pickup/R201_reverse_pickup.json` |
| RC1 | `RC101` | `backend/datasets/solomon/raw/In/rc101.txt` | `backend/datasets/solomon/reverse_pickup/RC101_reverse_pickup.json` |
| RC2 | `RC201` | `backend/datasets/solomon/raw/In/rc201.txt` | `backend/datasets/solomon/reverse_pickup/RC201_reverse_pickup.json` |

### 3.2. Lý do phương pháp luận

Chọn 6 instance này là một thiết kế lấy mẫu có chủ đích, được xác định **trước khi chạy** để tránh chọn instance theo kết quả có lợi cho một thuật toán:

1. **Phủ toàn bộ 6 họ chuẩn.** Mỗi kết hợp giữa ba kiểu phân bố không gian `C/R/RC` và hai mức window `1/2` có đúng một đại diện. Vì vậy, so sánh không chỉ xảy ra trên một loại địa lý hoặc một loại mức độ chặt của thời gian.
2. **Đối chiếu cặp hẹp--rộng trong cùng kiểu không gian.** Các cặp `C101`/`C201`, `R101`/`R201`, `RC101`/`RC201` cho phép quan sát ảnh hưởng của window khi đặc trưng không gian chính được giữ cùng họ.
3. **Đối chiếu ba cấu trúc không gian.** `C101`, `R101`, `RC101` phản ánh lần lượt trạm tập trung theo cụm, phân tán ngẫu nhiên và hỗn hợp. Đây là ba cấu trúc dễ tạo hành vi khác nhau cho Sweep và cho các operator tối ưu.
4. **Kiểm soát khối lượng thực nghiệm.** Mỗi instance có 100 station. Với 3 thuật toán và 4 seed `100`--`103`, sáu instance tạo `6 × 3 × 4 = 72` lần chạy. Quy mô này đủ để báo cáo mean/standard deviation theo seed, đồng thời vẫn kiểm tra được từng JSON, từng violation và từng route.
5. **Khả năng tái lập.** Chọn instance đầu tiên của từng họ (`101` và `201`) làm quy tắc đơn giản, công khai và không phụ thuộc kết quả chạy. Tất cả file raw, file RP và evidence đều nằm trong repository.

### 3.3. Điều sáu instance không đại diện

Sáu instance là **mẫu đại diện theo lớp**, không phải toàn bộ benchmark Solomon. Vì vậy, báo cáo chỉ nên kết luận theo hướng “trên sáu instance đại diện đã chọn”, không được kết luận một thuật toán thắng trên toàn bộ 56 instance. Các instance còn lại có thể có cấu trúc demand/window khác và tạo thứ hạng khác.

Để mở rộng nghiên cứu, có thể chạy toàn bộ 56 instance với cùng transformer, evaluator, seed và time budget. Khi đó cần công bố quy tắc tổng hợp rõ ràng (ví dụ mean theo instance, số lần thắng-hòa-thua và độ lệch chuẩn), thay vì chỉ lấy trung bình khoảng cách thô giữa các instance không cùng thang đo.

## 4. Lý do phải reverse cho bài toán xe buýt đón sinh viên

Trong hệ thống CTU, ý nghĩa mong muốn là:

```text
Trường/depot -> trạm đón -> ... -> trạm đón -> trường/depot
```

Xe rời trường, đón sinh viên tại nhiều trạm, rồi về trường trước thời hạn. Số sinh viên trên xe tăng dần sau mỗi trạm.

Trong Solomon delivery gốc, việc phục vụ customer được nhìn theo chiều xuôi của thời gian. Nếu lấy nguyên time window gốc và chỉ đổi tên customer thành trạm đón, ngữ nghĩa thời gian không đồng nhất với hành trình ngược về trường. Reverse-Pickup đảo trục thời gian quanh planning horizon, nhờ đó một tuyến Solomon khả thi được phản chiếu thành một tuyến đón có thứ tự node ngược lại, trong giả định khoảng cách/thời gian đối xứng.

Ví dụ tuyến giao hàng gốc:

```text
0 -> i1 -> i2 -> ... -> ik -> 0
```

Được diễn giải thành tuyến đón RP theo thứ tự ngược:

```text
0 (trường) -> ik -> ... -> i2 -> i1 -> 0 (trường)
```

Điều này phù hợp với logic xe phải đón tại trạm trước rồi kết thúc ở trường. Reverse là phép biến đổi **khung thời gian**, không phải đảo tọa độ, đảo demand hay đảo thứ tự các dòng trong file.

## 5. Công thức reverse time window

### 5.1. Định nghĩa biến

Gọi:

| Biến | Định nghĩa |
|---|---|
| `i` | Một customer gốc, sau transform là một trạm đón; `i = 1..100` |
| `0` | Depot gốc, sau transform là trường/depot |
| `a_i` | `READY TIME` gốc của node `i` |
| `b_i` | `DUE DATE` gốc của node `i` |
| `s_i` | `SERVICE TIME` gốc của node `i` |
| `H` | Planning horizon, được lấy bằng `DUE DATE` của depot gốc: `H = b_0` |
| `u_i` | Thời điểm bắt đầu phục vụ ở bài toán RP |
| `[a'_i, b'_i]` | Time window sau reverse của trạm `i` |

Trong file RP, `a'_i` và `b'_i` lần lượt được lưu là `time_window_start` và `time_window_end`; hai giá trị nguồn vẫn được giữ là `source_time_window_start` và `source_time_window_end` để truy vết.

### 5.2. Suy ra công thức

Giả sử trong tuyến gốc dịch vụ ở customer `i` bắt đầu tại `t_i`, với:

```text
a_i <= t_i <= b_i
```

Dịch vụ gốc chiếm khoảng thời gian `[t_i, t_i + s_i]`. Đảo thời gian quanh horizon `H` dùng phép ánh xạ:

```text
tau = H - t
```

Thời điểm bắt đầu phục vụ của node trong hành trình RP là ảnh của thời điểm **kết thúc** dịch vụ gốc:

```text
u_i = H - (t_i + s_i)
```

Khi `t_i` chạy từ `a_i` đến `b_i`, cận của `u_i` đổi chiều:

```text
H - (b_i + s_i) <= u_i <= H - (a_i + s_i)
```

Do đó quy tắc transform là:

```text
a'_i = H - (b_i + s_i)
b'_i = H - (a_i + s_i)
```

Hay theo tên trường trong chương trình:

```text
reverse_ready_i = H - (source_due_i + service_i)
reverse_due_i   = H - (source_ready_i + service_i)
```

`service_time` được giữ nguyên. Sau khi xe bắt đầu phục vụ tại thời điểm `u_i`, xe rời trạm lúc `u_i + s_i`, tương ứng với `H - t_i`; do đó thứ tự thời gian của dịch vụ được phản chiếu nhất quán.

### 5.3. Ví dụ C101, customer 1

Trong `C101`:

```text
H = b_0 = 1236
a_1 = 912
b_1 = 967
s_1 = 90
```

Áp dụng công thức:

```text
a'_1 = 1236 - (967 + 90) = 179
b'_1 = 1236 - (912 + 90) = 234
```

Vì vậy trạm `customer_1` trong `C101_reverse_pickup.json` có:

```json
{
  "source_customer_id": 1,
  "source_time_window_start": 912,
  "source_time_window_end": 967,
  "time_window_start": 179,
  "time_window_end": 234,
  "service_time": 90
}
```

### 5.4. Depot

Depot được transform bằng cùng công thức. Với depot Solomon thường có service time bằng 0, `a_0 = 0` và `b_0 = H`, nên:

```text
a'_0 = H - (H + 0) = 0
b'_0 = H - (0 + 0) = H
```

Do đó depot vẫn có window `[0, H]`. Trong JSON nó được đặt `id = "DEPOT"`, `name = "School Depot"`.

## 6. Những dữ liệu được giữ nguyên và cách diễn giải cho CTU

| Thành phần | Xử lý khi transform | Diễn giải trong Reverse-Pickup |
|---|---|---|
| `XCOORD., YCOORD.` | Giữ nguyên | Tọa độ trừu tượng của trạm đón; chỉ dùng cho Euclidean benchmark |
| `DEMAND = q_i` | Giữ nguyên | Số sinh viên chờ tại trạm `i` |
| `CAPACITY = Q` | Giữ nguyên | Sức chứa xe; tổng demand mỗi route không được vượt `Q` |
| `NUMBER = m` | Giữ nguyên | Giới hạn số xe tối đa |
| `SERVICE TIME = s_i` | Giữ nguyên | Thời gian xe dừng/phục vụ trạm |
| ID customer | Giữ nguyên trong `source_customer_id` | ID truy vết nguồn; JSON dùng `customer_<id>` |
| Thứ tự dòng customer | Giữ nguyên | Không phải thứ tự tuyến; solver quyết định thứ tự ghé |
| Time window | Transform bằng công thức ở Mục 5 | Khung thời gian phục vụ trạm đón trong benchmark RP |

Các thông tin **không** được áp dụng trong Solomon RP: GPS thật của CTU, Haversine, Goong/OSRM, traffic, session time theo `HH:MM`, giới hạn ride time 45 phút, giới hạn route 90 phút, service time cố định 3 phút và bán kính 10 km. Những điều kiện này thuộc benchmark CTU/offline hoặc production, không thuộc bộ Solomon chuẩn hóa.

## 7. Quy trình tạo file Reverse-Pickup trong dự án

### Bước 1: Giữ bất biến file raw

Parser đọc file `.txt` gốc tại `backend/datasets/solomon/raw/In/`. File raw không bị sửa. Parser yêu cầu đúng một dòng `NUMBER CAPACITY`, depot `0` và đủ customer `1..100`.

### Bước 2: Parse dữ liệu nguồn

Module [solomon_parser.py](D:\NCKH2026\vrptw-ctu-bus-routing-flutter\backend\app\services\student_routing\solomon\solomon_parser.py) tạo `SolomonInstance` gồm fleet, depot, 100 customer và đường dẫn file nguồn.

### Bước 3: Transform từng node

Module [reverse_pickup_transformer.py](D:\NCKH2026\vrptw-ctu-bus-routing-flutter\backend\app\services\student_routing\solomon\reverse_pickup_transformer.py) lấy `H = depot.due_date`, áp dụng công thức ở Mục 5 cho depot và toàn bộ 100 customer, đồng thời giữ metadata nguồn.

### Bước 4: Validate

Với mọi node, transformer kiểm tra:

```text
0 <= a'_i <= b'_i <= H
```

Nếu không thỏa, quá trình dừng với lỗi thay vì ghi một instance RP sai. Sau transform, evaluator tiếp tục kiểm tra capacity từng route, thời điểm bắt đầu service tại trạm, và thời điểm xe quay về depot.

### Bước 5: Ghi JSON có khả năng truy vết

File đầu ra mang schema `solomon_reverse_pickup`, gồm:

```text
schema_version, dataset_type, source_instance, source_file,
transform (H, công thức, metric), fleet, depot, stations
```

Mỗi station có cả window nguồn và window đã reverse. Nhờ vậy, người đọc báo cáo có thể kiểm chứng từng giá trị mà không cần đoán cách biến đổi.

## 8. Điều kiện để phép reverse được diễn giải đúng

Phép biến đổi có nền tảng toán học rõ nhất dưới các giả định benchmark sau:

1. **Thời gian di chuyển đối xứng:** `t(i,j) = t(j,i)`. Euclidean distance thỏa điều này.
2. **Không phụ thuộc thời điểm:** travel time không đổi theo giờ; không có traffic động.
3. **Depot dùng horizon `[0,H]`.** H được lấy trực tiếp từ due date depot.
4. **Service time không âm và giữ nguyên.** Khoảng service được phản chiếu khi đảo thời gian.
5. **Cùng ràng buộc tải.** Demand/capacity chỉ đổi diễn giải từ hàng hóa sang sinh viên, không đổi giá trị.

Do đó Reverse-Pickup phù hợp để đo năng lực thuật toán dưới các ràng buộc VRPTW chuẩn. Nó không mô phỏng hoàn toàn quá trình vận hành xe buýt thật: đường đô thị có thể bất đối xứng, ETA biến thiên, trạm có tọa độ GPS và quy định CTU có các ràng buộc khác. Đây là lý do báo cáo cần tách rõ kết quả Solomon RP và kết quả CTU benchmark/data thật.

## 9. Câu mô tả có thể dùng trong báo cáo

> Nghiên cứu chọn sáu instance đại diện từ 56 instance Solomon VRPTW gồm C101, C201, R101, R201, RC101 và RC201. Sáu instance phủ đồng thời ba đặc trưng phân bố khách hàng (cụm, ngẫu nhiên và hỗn hợp) và hai mức độ chặt của khung thời gian. Để đồng nhất ngữ nghĩa với bài toán xe buýt đón sinh viên, mỗi customer được diễn giải lại thành trạm đón, demand thành số sinh viên chờ, depot thành trường và time window được đảo quanh horizon `H = b_0`. Cụ thể, với customer `i` có window gốc `[a_i,b_i]` và service time `s_i`, window Reverse-Pickup được xác định bởi `[a'_i,b'_i] = [H-(b_i+s_i), H-(a_i+s_i)]`. Tọa độ, demand, số xe, sức chứa và service time được giữ nguyên. Cách biến đổi bảo toàn cấu trúc VRPTW chuẩn hóa trong giả định khoảng cách/thời gian di chuyển đối xứng, đồng thời tạo dữ liệu có ngữ nghĩa phù hợp để đánh giá các thuật toán sinh tuyến đón.
