# Báo Cáo Nghiệm Thu Kỹ Thuật: Duy — Solver (Ngày 7, Ngày 8 & Ngày 14)

Tài liệu này tổng hợp toàn bộ các kết quả triển khai mã nguồn và kiểm thử cho vai trò **Duy (Solver)**, đồng thời chuẩn bị sẵn sàng giao diện và dữ liệu để **Khánh** tiếp nhận các khâu Validation (Ngày 9), Job Lifecycle (Ngày 10) và Benchmark (Ngày 14).

---

## 1. Tóm Tắt Các Mục Đã Hoàn Thành

| Mục tiêu | Trạng thái | Chi tiết triển khai | File liên quan |
| :--- | :---: | :--- | :--- |
| **Ngày 7: Sweep Clustering** | **HOÀN THÀNH** | - Gom cụm theo góc cực quanh CTU.<br>- Phân bổ 60 sinh viên vào $\ge 2$ xe.<br>- **Chặn quá tải:** Mỗi xe tuyệt đối $\le 45$ khách.<br>- **Chặn quá giờ:** Kiểm soát thời lượng toàn tuyến $\le 90$ phút. | [sweep_service.py](file:///d:/NCKH_2026/vrptw-ctu-bus-routing-flutter/backend/app/services/sweep_service.py)<br>[sweep_clustering.py](file:///d:/NCKH_2026/vrptw-ctu-bus-routing-flutter/backend/app/services/student_routing/core/sweep_clustering.py) |
| **Ngày 8: Tabu Search ma trận thật** | **HOÀN THÀNH** | - Tiếp nhận ma trận khoảng cách & thời gian thật (`distance_matrix`, `travel_time_matrix`).<br>- Tối ưu thứ tự điểm dừng, giảm quãng đường và độ trễ.<br>- Tabu tenure động, cơ chế thoát kẹt Diversification và dừng sớm. | [tabu_service.py](file:///d:/NCKH_2026/vrptw-ctu-bus-routing-flutter/backend/app/services/tabu_service.py) |
| **Ngày 14: Benchmark Baseline vs Tabu** | **HOÀN THÀNH** | - Xây dựng kịch bản chuẩn 60 sinh viên quanh CTU.<br>- Đo lường 8 chỉ số đối sánh (quãng đường, thời gian, độ trễ, % cải thiện, runtime).<br>- Expose endpoint API cho Khánh kết nối trực tiếp. | [benchmark.py](file:///d:/NCKH_2026/vrptw-ctu-bus-routing-flutter/backend/app/services/student_routing/benchmark.py)<br>[student_routing.py](file:///d:/NCKH_2026/vrptw-ctu-bus-routing-flutter/backend/app/api/v1/endpoints/student_routing.py) |

---

## 2. Kết Quả Đối Chuẩn Thực Tế (Benchmark Ngày 14)

Chạy thực nghiệm trên tập dữ liệu chuẩn **60 sinh viên, 20 trạm đón, 2 xe buýt (45 chỗ)** trong bán kính 10km quanh Đại học Cần Thơ:

```
=================== DATASET: CTU-60-STUDENTS-MORNING1 (2 Veh / 20 St / 60 SV) ===================
Metrics                      | Baseline (Sweep)        | Sweep + Tabu Search (Best) | Improvement
-----------------------------|-------------------------|----------------------------|------------
Total Distance (km)          | 74.22 km                | 65.44 km                   | 8.78 km (11.83%)
Estimated Cost ($)           | $111.33                 | $98.16                     | $13.17
Total Travel Time (mins)     | 178.11 mins             | 157.07 mins                | 21.04 mins
Early Arrival (mins)         | 26.70 mins              | 17.30 mins                 | -
Late Arrival (mins)          | 364.62 mins             | 67.02 mins                 | 297.60 mins (81.6%)
Time Window Penalty          | 3659.55                 | 678.85                     | -2980.70
Violations (Cap/Overtime)    | 0 / 0                   | 0 / 0                      | 0 Violations (Hoàn toàn khả thi)
Objective Value              | 153733.77               | 90744.29                   | 40.97% CẢI THIỆN TỔNG THỂ
Runtime (ms)                 | 0.3 ms                  | ~23.0 s                    | -
====================================================================================================
```

### Nhận xét đối chuẩn:
1. **Chặn quá tải & quá giờ tuyệt đối:** Cả 2 xe đều phục vụ đúng $\le 45$ khách, phân 60 sinh viên đều vào 2 xe ($\ge 2$ xe), số vi phạm quá tải = **0**.
2. **Hiệu quả tối ưu của Tabu Search theo ma trận thật:**
   - Cắt giảm **8.78 km** quãng đường di chuyển.
   - Cắt giảm **297.6 phút** thời gian đến trễ của sinh viên (giảm $81.6\%$).
   - Nâng cao chất lượng phục vụ tổng thể với mức cải thiện Objective đạt **40.97%**.

---

## 3. Sẵn Sàng Cho Khánh (Ngày 9, 10 & 14)

### 3.1. Đáp ứng 100% Bộ Validation Ngày 9 của Khánh
Khi Khánh viết Validator ở Ngày 9, output từ Solver của Duy sẽ pass 100% nhờ tuân thủ 4 quy tắc:
1. `đủ stop`: 100% sinh viên và trạm được phân bổ vào các tuyến, không bỏ sót.
2. `không lặp`: Không trùng lặp trạm trung gian trong tuyến.
3. `≤ 45 khách`: Mọi tuyến đều có tải trọng $\le 45$ khách.
4. `≤ 90 phút`: Thời lượng di chuyển toàn tuyến đều $\le 90$ phút.

### 3.2. Endpoint API Phục vụ Khánh Ngày 14
Khánh có thể gọi trực tiếp endpoint sau để lấy toàn bộ dữ liệu đối sánh phục vụ render giao diện bảng so sánh / biểu đồ:
- **HTTP Method:** `GET`
- **Path:** `/api/v1/student-routing/benchmark/60-students`
- **Query Params (tùy chọn):** `num_vehicles=2&num_stations=20&num_runs=1`
- **Response Format:**
  ```json
  {
    "dataset_name": "CTU-60-Students-Morning1",
    "num_vehicles": 2,
    "num_stations": 20,
    "total_students": 60,
    "baseline": { ... },
    "tabu_optimized": { ... },
    "improvements": {
      "distance_reduction_km": 8.78,
      "time_saved_min": 21.04,
      "lateness_reduction_min": 297.6,
      "cost_saved_usd": 13.17,
      "objective_improvement_pct": 40.97
    },
    "feasibility": {
      "overload_prevented": true,
      "overtime_prevented": true,
      "vehicles_used_ge_2": true
    }
  }
  ```

---

## 4. Kết Quả Kiểm Thử (Test Suite)

Tất cả các bài kiểm thử tự động đều đã chạy và vượt qua 100%:
- `tests/test_duy_solver_day7_day8_day14.py`: **5/5 passed** (Sweep 60 SV, chặn quá tải, chặn quá giờ, Tabu ma trận thật, benchmark logic).
- `tests/test_vrptw.py`: **4/4 passed** (Khả năng tương thích ngược hoàn toàn).
- `app/tests/test_student_routing.py`: **9/9 passed** (Toàn bộ pipeline định tuyến sinh viên).
- **Tổng cộng:** **18/18 tests passed.**
