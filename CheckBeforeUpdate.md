## Tập Solomon 
    ****Bộ dữ liệu Solomon VRPTW do Marius M. Solomon giới thiệu năm 1987 cho bài toán Vehicle Routing Problem with Time Windows (VRPTW)
    
    Bài báo gốc: https://pubsonline.informs.org/doi/10.1287/opre.35.2.254
    Là một benchmark kinh điển, dùng để đánh giá thuật toán xây dựng tuyến cho nhiều xe khi có giới hạn sức chứa và khung giờ phục vụ.
    *Mỗi instance mô tả 
    {
        1 depot
        100 customer
        một đội xe đồng nhất
        capacity Q
        tọa độ 2D
        demand tại mỗi customer
        time window tại mỗi customer
        service time tại mỗi customer
    }
    Bài toán cần tìm nhiều tuyến dạng: Depot → customer … → customer → Depot, sao cho:
        Mỗi customer được phục vụ đúng một lần.
        Tổng demand mỗi tuyến không vượt capacity Q.
        Thời điểm phục vụ customer nằm trong time window của customer.
        Mỗi tuyến bắt đầu và kết thúc trong time window của depot.
        Mục tiêu truyền thống là giảm số xe trước, sau đó giảm tổng quãng đường.

    ***Quy mô & Phân loại
        Bộ Solomon gốc gồm 56 instance, mỗi instance có 100 customer và 1 depot
        | Nhóm         | Ý nghĩa phân bố không gian            | Số instance |
        |------        |---------------------------------------|-------------|
        | `C1`, `C2`   | Customer phân bố theo cụm (clustered) |        17   |
        | `R1`, `R2`   | Customer phân bố ngẫu nhiên/rải đều   |        23   |
        | `RC1`, `RC2` | Kết hợp clustered và random           |        16   |

    ***Cấu trúc file
        Ví dụ của C101.txt

        VEHICLE
        NUMBER     CAPACITY
        25         200

        CUSTOMER
        CUST NO.  XCOORD.  YCOORD.  DEMAND  READY TIME  DUE DATE  SERVICE TIME

            0      40       50        0        0          1236        0
            1      45       68       10      912           967       90
            2      45       70       30      825           870       90
        ...
        100      ...      ...      ...     ...           ...       ...

    
    | Trường | Ý nghĩa |
    |---|---|
    | `CUST NO.` | Mã node; `0` luôn là depot |
    | `XCOORD.`, `YCOORD.` | Tọa độ Cartesian trên lưới giả lập, không phải GPS |
    | `DEMAND` | Lượng nhu cầu của customer |
    | `READY TIME` | Thời điểm sớm nhất được phục vụ |
    | `DUE DATE` | Thời điểm muộn nhất được phục vụ |
    | `SERVICE TIME` | Thời gian xe dừng để phục vụ customer |
    | `NUMBER` | Số xe tối đa/tham chiếu trong instance |
    | `CAPACITY` | Sức chứa tối đa của mỗi xe, ký hiệu `Q` |

    Các instance Solomon dùng khoảng cách Euclidean giữa các tọa độ; time và distance dùng cùng hệ đơn vị chuẩn hóa. Depot cũng có time window riêng

    **Công thức khoảng cách giữa hai node i, j: [--d(i, j) = √[(xᵢ - xⱼ)² + (yᵢ - yⱼ)²]--]

    **Trong benchmark Solomon, thường dùng:     [--travel_time(i, j) = d(i, j)--]
    
    **Không có Goong, GPS, tốc độ km/h hay dữ liệu giao thông thực tế

    *Nó có sẵn các thành phần mà solver hiện tại cần, Ánh xạ:
        Depot           → CTU/trường
        Customer        → trạm đón
        Demand          → số sinh viên tại trạm
        Capacity Q      → sức chứa xe
        Time window     → khung giờ đón
        Service time    → thời gian xe dừng đón

        *Solomon gốc mô tả: Customer i tại tọa độ (x[i], y[i]) có nhu cầu demand q[i], cần được phục vụ trong time window [e(i), l(i)] xe dừng service_time[i]
        -> Ánh xạ đến bài : Trạm i tại tọa độ (x[i], y[i]) có q[i] sinh viên chờ đón, xe cần ghé trong time window [e(i), l(i)] và xe dừng trong s[i] phút để sinh viên lên xe.

        **Solomon Reverse-Pickup
            → đồng nhất về: depot/trường, trạm, demand/sinh viên,
            capacity/ghế xe, time window, service time, đa xe.

            → chưa đồng nhất về: GPS thật, mạng lưới đường thật,
            giao thông Goong, demand vé phát sinh theo ngày/ca.

    *Đây là dữ liệu giả lập:
        Customer Solomon không phải trạm CTU có thật.
        Demand Solomon không phải số sinh viên khảo sát thực tế.
        Tọa độ Solomon không phải GPS.
        Phép ánh xạ nhằm bảo toàn cấu trúc tối ưu: nhiều điểm đón, demand theo điểm, capacity, time window và service time.

    *Giúp đánh giá thuật toán trên ba kiểu địa lý khác nhau:
        C  → các trạm tập trung theo khu vực
        R  → trạm phân tán
        RC → vừa tập trung vừa phân tán, gần với thực tế hơn

    
    -------------------------------------------------------------------------------------------------------------------------------------
    **Nghiên cứu không sử dụng trực tiếp Solomon VRPTW để đánh giá bài toán giao hàng. Bộ dữ liệu Solomon được sử dụng làm nguồn instance chuẩn, sau đó được biến đổi thành bộ dữ liệu Reverse-Pickup VRPTW nhằm mô phỏng bài toán xe buýt đón sinh viên từ nhiều trạm về trường
    **Tập Solomon reverse-pickup sẽ trả lời cho tình huống cùng các instance pickup VRPTW có kiểm soát, thuật toán nào tạo nghiệm khả thi, ngắn hơn, ít xe hơn và ổn định hơn?
    **Kết quả chỉ cho thấy thuật toán nào tốt hơn trên “Solomon Reverse-Pickup VRPTW do đề tài chuyển đổi”, không phải trên benchmark Solomon gốc, và nhằm đánh giá ở mức “hiệu quả thuật toán”, cần triển khai dữ liệu thật mới đánh giá chính xác thực tế.

## Triển khai tập solomon reverse-pickup
  Phạm vi thực hiện, chỉ dựng lại 6/56 instances [C101, C201, R101, R201, RC101, RC201], có chủ đích.
    C101: Trạm phân bố theo cụm, Time window: chặt / horizon: ngắn, Y/n: Kiểm tra gom cụm và tính khả thi khi deadline gấp.
    C201: Trạm phân bố theo cụm, Time window: rộng / horizon: dài, Y/n: Kiểm tra khả năng giảm quãng đường khi có nhiều tự do hơn.
    R101: Trạm rải đều, Time window: chặt / horizon: ngắn, Y/n: Tình huống khó do trạm phân tán và TW nghiêm ngặt.
    R201: Trạm rải đều, Time window: rộng / horizon: dài, Y/n: Đo chất lượng route trên không gian phân tán, ít bị deadline ép hơn.
    RC101: Vừa cụm vừa rải đều, Time window: chặt / horizon: ngắn, Y/n: Kịch bản phức tạp nhất, gần với trạm thực tế.
    RC201: Vừa cụm vừa rải đều, Time window: rộng / horizon: dài, Y/n: 	Kiểm tra độ ổn định khi bài toán hỗn hợp nhưng linh hoạt thời gian hơn.

    3 loại địa lý * 2 mức ràng buộc thời gian = 6 trường hợp đại diện

    Công thức reverse
        H = depot.DUE_DATE của chính file đang chạy

        reverse_ready = H - (source_due + service_time)
        reverse_due   = H - (source_ready + service_time)


## Luồng sinh tuyến của hệ thống
    1. Admin thiết lập sẵn các trạm trong hệ thống.

    2. Sinh viên đặt vé:
    chọn ngày + ca + loại chuyến + trạm đón(pick_up_location).

    3. Ticket được lưu ở trạng thái chờ sinh tuyến.

    4. Khi tạo route job cho một ngày/ca:
    hệ thống lấy các ticket hợp lệ,
    gom các sinh viên cùng trạm thành một station có demand.

    5. Sweep Algorithm:
    quét các station theo góc quanh trường,
    gom station thành các cụm/tuyến ban đầu
    theo sức chứa xe và thời lượng tuyến ước tính.

    6. Tabu Search:
    nhận các tuyến ban đầu từ Sweep,
    tối ưu thứ tự trạm và có thể chuyển/đổi trạm giữa các tuyến,
    để giảm quãng đường/độ trễ mà vẫn thỏa capacity và time window.

    7. Evaluator + RouteValidator:
    kiểm tra nghiệm cuối có hợp lệ không.

    8. Output:
    tạo tuyến cho từng xe,
    lưu thứ tự trạm, thời gian dự kiến,
    gán từng ticket vào route phù hợp,
    chuyển ticket sang ASSIGNED.