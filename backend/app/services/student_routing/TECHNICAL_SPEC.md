# ĐẶC TẢ KỸ THUẬT SERVICE TỐI ƯU LỘ TRÌNH RƯỚC & ĐƯA SINH VIÊN (STUDENT ROUTING SERVICE)
**Thuật toán: Sweep Algorithm (Khởi tạo Lời giải) & Tabu Search (Tối ưu Lộ trình & VRPTW)**

- **Tác giả:** Backend Tech Lead / System Architect
- **Thư mục:** `/backend/app/services/student_routing/TECHNICAL_SPEC.md`
- **Đối tượng:** Backend Developers, Algorithm Engineers
- **Phiên bản:** v2.5 — Vé Ngày, 4 Ca Cố Định, Bán kính 10km, Trường ĐH Cần Thơ, Sweep + Tabu Search

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1. Bối cảnh & Mục tiêu

Hệ thống tối ưu lộ trình xe buýt phục vụ sinh viên **Trường Đại học Cần Thơ (CTU)** trong bán kính **10km** tính từ trung tâm trường.

**Mục tiêu cốt lõi:**
- Tối thiểu hóa tổng quãng đường di chuyển và chi phí vận hành của tất cả xe
- Đảm bảo sinh viên đến trường đúng giờ học và về đúng ca tan
- Tối đa hóa số sinh viên được phục vụ trong giới hạn capacity xe
- Chứng minh hiệu quả cải thiện của thuật toán **Tabu Search** so với lời giải ban đầu do **Sweep Algorithm** khởi tạo trên dữ liệu VRPTW thực tế

### 1.2. Mô hình Vé Ngày

| Thuộc tính | Quy định |
| :--- | :--- |
| **Loại vé** | Vé ngày (Daily Ticket) |
| **Đơn vị vé** | 1 vé = 1 chiều (đi **hoặc** về — không gộp chung) |
| **Cutoff đặt vé** | Trước **22:00 hôm trước** |
| **Lợi ích cho thuật toán** | `pickup_student_count` chiều đi và `dropoff_student_count` chiều về **độc lập và chính xác 100%** mỗi ngày |

### 1.3. Lịch 4 Ca Cố Định

| Ca | Loại | Giờ chính thức | Xe xuất phát chậm nhất | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **Ca Sáng 1** | Chiều Đi | **07:00** | ~05:30 | Cao điểm sáng |
| **Ca Sáng 2** | Chiều Đi | **08:30** | ~07:00 | Sau cao điểm |
| **Ca Trưa 1** | Chiều Về | **10:00** | 10:00 + boarding | Tan học sớm |
| **Ca Trưa 2** | Chiều Về | **11:30** | 11:30 + boarding | Tan học chính |

> **Lưu ý:** Sinh viên tự chọn độc lập ca đi và ca về. Ví dụ: SV có thể đặt vé đi Ca Sáng 1 (07:00) nhưng về Ca Trưa 2 (11:30) — hoàn toàn hợp lệ.

### 1.4. Thông số Vận hành & Feasibility Policy

| Tham số | Giá trị | Tính chất Ràng buộc | Ghi chú |
| :--- | :--- | :--- | :--- |
| Trường phục vụ | Trường ĐH Cần Thơ | Center Point | Tọa độ: `10.0302°N, 105.7721°E` |
| Bán kính phục vụ | **10 km** | **HARD Feasibility** | `MAX_SERVICE_RADIUS_KM` trong `config.py` |
| Capacity mỗi xe | **45 chỗ** | **HARD Constraint** | Tính theo $\sum \text{student\_demand}_i \le 45$, không tính theo số trạm |
| Maximum Ride Time | **45 phút** | **HARD Feasibility** | $RideTime_i = ArrivalTime_i - RouteDepartureTime \le 45m$. Nếu vượt $\implies$ reject trạm đó với lý do `MAX_RIDE_TIME_EXCEEDED` |
| Time Window Policy | **SOFT** | **SOFT Penalty** | Penalty tính vào Objective. Late penalty ($10.0$) > Early penalty ($0.5$) |
| Buffer đến trường | 15 phút | Departure Buffer | Xe phải đến trường trước giờ học |
| Boarding tại trường | 10 phút | Return Boarding | Thời gian SV lên xe chiều về |

---

## 2. THIẾT KẾ HỆ THỐNG

### 2.1. Cấu trúc thư mục

```
backend/app/services/student_routing/
├── TECHNICAL_SPEC.md                  # Tài liệu đặc tả kỹ thuật
├── __init__.py
├── config.py                          # Cấu hình 4 ca, buffer, ride time, bán kính, penalties
├── schemas.py                         # Pydantic Schemas Input/Output API
├── student_routing_service.py         # Orchestrator chính
├── benchmark.py                       # Bộ công cụ Benchmark (Sweep vs Sweep + Tabu)
├── core/
│   ├── __init__.py
│   ├── evaluator.py                   # Lượng giá giải pháp độc lập (SolutionEvaluator)
│   ├── sweep_clustering.py            # Sweep Algorithm (Polar Angle & Demand-based Capacity)
│   └── tabu_optimizer.py              # Tabu Search Optimization (Swap, Relocate, 2-Opt)
└── helpers/
    ├── __init__.py
    ├── path_flexibility.py            # Phân tích khung giờ (Morning/Noon/Normal Peak)
    ├── distance_matrix.py             # OSRM Public API + 3s Timeout Fallback to Static Matrix
    └── response_formatter.py          # Format JSON output & Partial Rejection Results
```

### 2.2. Cấu hình mặc định (`config.py`)

```python
# ── Ca học ────────────────────────────────────────────────────────────
PICKUP_SESSIONS = {
    "MORNING_1": {"id": "MORNING_1", "school_start": "07:00", "vehicle_depart_latest": "05:30"},
    "MORNING_2": {"id": "MORNING_2", "school_start": "08:30", "vehicle_depart_latest": "07:00"},
}

DROPOFF_SESSIONS = {
    "NOON_1": {"id": "NOON_1", "school_end": "10:00", "vehicle_depart_after": "10:10"},
    "NOON_2": {"id": "NOON_2", "school_end": "11:30", "vehicle_depart_after": "11:40"},
}

# ── Thông số vận hành ─────────────────────────────────────────────────
VEHICLE_CAPACITY         = 45       # Chỗ ngồi
MAX_SERVICE_RADIUS_KM    = 10.0     # Bán kính phục vụ tính từ CTU
BUFFER_MINUTES           = 15       # Đệm an toàn trước giờ học
BOARDING_AT_SCHOOL_MIN   = 10       # Thời gian lên xe tại trường (chiều về)
MAX_RIDE_TIME_MINUTES    = 45       # Thời gian ngồi xe tối đa (HARD constraint)

# ── Speed by Time of Day (km/h) ───────────────────────────────────────
SPEED_MORNING_PEAK_KMH   = 25.0     # Cao điểm sáng (06:30 - 08:30)
SPEED_NOON_PEAK_KMH      = 28.0     # Cao điểm trưa (11:00 - 13:00)
SPEED_NORMAL_KMH         = 30.0     # Tốc độ bình thường

# ── OSRM & Matrix Settings ─────────────────────────────────────────────
OSRM_PUBLIC_URL          = "http://router.project-osrm.org/table/v1/driving/"
OSRM_TIMEOUT_SECONDS     = 3.0      # Timeout 3 giây kích hoạt fallback
TRAFFIC_CACHE_TTL        = 300      # 5 phút

# ── Objective Function Penalties ───────────────────────────────────────
DISTANCE_WEIGHT          = 1.0
EARLY_PENALTY_WEIGHT     = 0.5
LATE_PENALTY_WEIGHT      = 10.0     # Late penalty > Early penalty
CAPACITY_PENALTY_WEIGHT  = 1000.0
RIDE_TIME_PENALTY_WEIGHT = 10000.0

# ── Tabu Search Settings ──────────────────────────────────────────────
TABU_MAX_ITERATIONS      = 300
TABU_TENURE_BASE         = 10
EARLY_STOPPING_ROUNDS    = 30
DIVERSIFY_ROUNDS         = 15

# ── Trường ĐH Cần Thơ ────────────────────────────────────────────────
SCHOOL_LOCATION          = {"lat": 10.0302, "lng": 105.7721}
SCHOOL_NAME              = "Trường Đại học Cần Thơ"
```

---

## 3. DATA MODELS

### 3.1. Enums & Schemas (`schemas.py`)

- `TripType`: `PICKUP`, `DROPOFF`
- `SessionId`: `MORNING_1`, `MORNING_2`, `NOON_1`, `NOON_2`
- `VehicleStatus`: `IDLE_AT_SCHOOL`, `ON_PICKUP`, `ON_DROPOFF`, `IDLE_AT_DEPOT`, `UNAVAILABLE`
- `Station`: `id`, `name`, `location`, `time_window_start`, `time_window_end`, `pickup_student_count`, `dropoff_student_count`
- `InfeasibleStation`: `station_id`, `reason` (`MAX_RIDE_TIME_EXCEEDED` / `STATION_OUT_OF_RADIUS`), `detail`
- `OptimizationResponse`: `status` (`SUCCESS`, `PARTIAL_SUCCESS`, `ERROR`), `data`, `partial_result`, `error_code`, `error_message`

---

## 4. LUỒNG XỬ LÝ (EXECUTION PIPELINE)

```text
Student Requests
      ↓
Input Validation
      ↓
Service Radius Check (≤ 10km)
      ↓
Ride Time Feasibility Preprocessing (Max Ride Time ≤ 45m)
      │
      ├── Infeasible → Reject individual station (Reason = MAX_RIDE_TIME_EXCEEDED)
      │
      └── Feasible Stations
             ↓
      Distance / Travel Time Matrix (OSRM with 3s Timeout & Fallback)
             ↓
      Sweep Algorithm (SweepClusterer -> Initial Solution)
             ↓
      Tabu Search Optimization (TabuSearchOptimizer -> Neighborhood: Swap, Relocate, 2-Opt)
             ↓
      Solution Evaluator (SolutionEvaluator -> Distance + Early/Late Penalties)
             ↓
      Best Optimized Solution
             ↓
      Response Formatter (JSON Contract)
```

---

## 5. THIẾT KẾ THUẬT TOÁN

### 5.1. Giai đoạn 1 — Sweep Algorithm (Initial Solution Generator)
- **Tính góc cực (Polar Angle):**
  $$\theta_i = \text{atan2}(lat_i - lat_0, lng_i - lng_0) \pmod{2\pi}$$
- **Sắp xếp:** Sắp xếp tất cả trạm theo góc cực $\theta_i$ ($0^\circ \to 360^\circ$).
- **Phân cụm nhu cầu (Demand-based Clustering):** Tích lũy số lượng sinh viên $\sum \text{student\_demand}_i$. Tạo route mới khi vượt `VEHICLE_CAPACITY` (45 sinh viên). Không phân cụm theo số lượng trạm.

### 5.2. Giai đoạn 2 — Tabu Search Optimization Engine
- **Neighborhood Moves:**
  1. `Swap`: Hoán đổi 2 trạm (intra-route hoặc inter-route).
  2. `Relocate`: Di chuyển 1 trạm sang vị trí mới.
  3. `2-Opt`: Đảo ngược đoạn con trong route.
- **Tabu List & Dynamic Tenure:** Cấm lặp lại các nước đi gần nhất để tránh kẹt hố cực trị địa phương.
- **Aspiration Criterion:** Bỏ qua cấm Tabu nếu candidate đạt objective value tốt hơn kỷ lục toàn cục (`best_objective`).
- **Diversification & Early Stopping:** Nhảy ngẫu nhiên (Random Walk) khi kẹt địa phương và dừng sớm sau 30 vòng lặp không cải thiện.

### 5.3. Solution Evaluator (`evaluator.py`)
Logic đánh giá độc lập tính toán:
$$\text{Objective} = (\text{Total Distance} \times w_{\text{dist}}) + (\text{Early Arrival} \times w_{\text{early}}) + (\text{Late Arrival} \times w_{\text{late}}) + \text{Hard Penalties}$$
Trong đó: $w_{\text{late}} (10.0) > w_{\text{early}} (0.5)$.

---

## 6. KẾT QUẢ BENCHMARK THỰC TẾ (`benchmark.py`)

Thực hiện benchmark trên 3 bộ dữ liệu thử nghiệm bán kính 10km quanh CTU:

| Dataset | Xe | Trạm | Sinh viên | Baseline Objective (Sweep) | Optimized Objective (Sweep + Tabu) | Tải quãng đường cắt giảm | Giảm thời gian trễ | Improvement % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Small** | 3 | 15 | 45 | 146,346.47 | **93,083.47** | -0.20 km | -325.88 mins | **36.40%** |
| **Medium** | 4 | 30 | 90 | 269,181.73 | **163,751.13** | -1.95 km | -541.75 mins | **39.17%** |
| **Large** | 5 | 50 | 150 | 392,956.84 | **223,552.10** | -12.83 km | -937.67 mins | **43.11%** |

---

*Tài liệu đặc tả v2.5 — Vé Ngày, 4 Ca Cố Định, Bán kính 10km, Sweep Algorithm + Tabu Search, Trường ĐH Cần Thơ.*
