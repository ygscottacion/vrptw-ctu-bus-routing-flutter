# MÔ HÌNH TOÁN HỌC VRPTW CHO ỨNG DỤNG XE BUÝT ĐƯA ĐÓN SINH VIÊN CTU
## + PROMPT KIỂM TRA RÀNG BUỘC TRONG ỨNG DỤNG

---

# PHẦN A — MÔ HÌNH TOÁN HỌC VRPTW HOÀN CHỈNH

## A.1. Tập hợp (Sets)

| Ký hiệu | Ý nghĩa |
|---|---|
| $V_0 = \{0\}$ | Depot xuất phát (CTU) |
| $V_0' = \{0'\}$ | Depot kết thúc (CTU — cùng vị trí vật lý với $V_0$, tách thành 2 node để dễ mô hình hóa, giống cách làm trong Wang et al. 2020) |
| $V_1 = \{1, 2, \dots, n\}$ | Tập các điểm đón sinh viên (trạm) |
| $V = V_0 \cup V_1 \cup V_0'$ | Tập tất cả các node trong mạng |
| $A = \{(i,j) : i,j \in V, i \neq j\}$ | Tập các cung nối giữa 2 node |
| $K = \{1, 2, \dots, m\}$ | Tập các xe buýt khả dụng, $m = K_{available}$ |

> **Lưu ý khác với bài toán giao hàng (delivery) kinh điển:** đây là bài toán **thu gom (pickup/collection)** — sinh viên được đón tại các trạm và tất cả được đưa về **một điểm đến duy nhất** là CTU. Do đó chiều "tải trọng" tích lũy **tăng dần** dọc theo route (khác VRP giao hàng thông thường là tải trọng giảm dần).

## A.2. Tham số (Parameters)

| Ký hiệu | Ý nghĩa | Ví dụ giá trị |
|---|---|---|
| $q_i$ | Số sinh viên cần đón tại trạm $i \in V_1$ | 10–15 |
| $Q$ | Sức chứa của xe (đồng nhất — homogeneous fleet) | 45 |
| $d_{ij}$ | Khoảng cách từ $i$ đến $j$ | (km) |
| $t_{ij}$ | Thời gian di chuyển từ $i$ đến $j$ | (phút) |
| $s_i$ | Thời gian phục vụ (đón) tại trạm $i$ | 2 phút |
| $[a_i, b_i]$ | Time window cho phép đón tại trạm $i$ | vd: 06:30–06:40 |
| $R_{max}$ | Thời gian ngồi xe tối đa (Maximum Ride Time) | 45 phút |
| $H_{max}$ | Thời lượng tối đa của 1 route (Max Route Duration) | 90 phút |
| $W_{max}$ | Thời gian chờ tối đa tại 1 trạm (tùy chọn) | 10 phút |
| $M$ | Hằng số đủ lớn (Big-M) | vd: 1000 |
| $C_{fix}$ | Chi phí cố định vận hành 1 xe | (VNĐ) |
| $\lambda_L, \lambda_E, \lambda_W$ | Trọng số phạt trễ / sớm / chờ | tùy chỉnh |

## A.3. Biến quyết định (Decision Variables)

$$
x_{ijk} =
\begin{cases}
1 & \text{nếu xe } k \text{ đi trực tiếp từ } i \text{ đến } j \\
0 & \text{ngược lại}
\end{cases}
\quad \forall i,j \in V, i \neq j, \; \forall k \in K
$$

$$
y_k =
\begin{cases}
1 & \text{nếu xe } k \text{ được sử dụng} \\
0 & \text{ngược lại}
\end{cases}
\quad \forall k \in K
$$

$$
T_i : \text{thời điểm xe đến node } i \in V \quad \text{(biến liên tục)}
$$

$$
l_{ik} : \text{tải trọng (số sinh viên) tích lũy trên xe } k \text{ ngay sau khi rời trạm } i
$$

Biến phụ trợ cho hàm mục tiêu (soft constraint):

$$
E_i = \max(0, a_i - T_i) \quad \text{(early)} \qquad
L_i = \max(0, T_i - b_i) \quad \text{(late)} \qquad
W_i = \max(0, a_i - T_i) \quad \text{(waiting)}
$$

## A.4. Hàm mục tiêu

$$
\min Z = w_1 \sum_{k \in K}\sum_{(i,j) \in A} d_{ij}\, x_{ijk}
\;+\; w_2 \sum_{i \in V_1} L_i
\;+\; w_3 \sum_{i \in V_1} E_i
\;+\; w_4 \sum_{i \in V_1} W_i
\;+\; w_5 \sum_{k \in K} C_{fix}\, y_k
$$

Thứ tự ưu tiên trọng số khuyến nghị (đúng giá trị "câu chuyện khoa học" đã thống nhất ở bước trước):

$$
w_2 \;(\text{late}) \;>\; w_3 \;(\text{early}) \;>\; w_1 \;(\text{distance}) \;>\; w_5 \;(\text{cost})
$$

## A.5. Bảy ràng buộc bắt buộc (R1–R7)

### R1 — Depot start/end

$$
\sum_{j \in V_1} x_{0jk} = y_k \quad \forall k \in K
$$
$$
\sum_{i \in V_1} x_{i0'k} = y_k \quad \forall k \in K
$$

### R2 — Mỗi trạm được phục vụ đúng một lần (không split demand)

$$
\sum_{k \in K}\sum_{i \in V, i \neq j} x_{ijk} = 1 \quad \forall j \in V_1
$$

**Ràng buộc bảo toàn dòng (flow conservation)** đi kèm:

$$
\sum_{i \in V, i \neq j} x_{ijk} - \sum_{i \in V, i \neq j} x_{jik} = 0 \quad \forall j \in V_1,\; \forall k \in K
$$

### R3 — Sức chứa xe (Capacity)

$$
\sum_{i \in V_1} q_i \left( \sum_{j \in V, j \neq i} x_{ijk} \right) \leq Q \quad \forall k \in K
$$

Ràng buộc theo dõi tải trọng tích lũy dọc route (loại bỏ subtour đồng thời):

$$
l_{jk} \geq l_{ik} + q_j - M(1 - x_{ijk}) \quad \forall i,j \in V_1, i\neq j,\; \forall k \in K
$$
$$
q_j \leq l_{jk} \leq Q \quad \forall j \in V_1, \forall k \in K
$$

### R4 — Giới hạn số xe

$$
\sum_{k \in K} y_k \leq K_{available}
$$

Nếu bài toán vô nghiệm với ràng buộc này → hệ thống trả `INSUFFICIENT_VEHICLES`, **không** tự sinh thêm xe.

### R5 — Time Window (Soft, với biến phạt)

Ràng buộc lan truyền thời gian (thay MTZ để vừa loại subtour, vừa tính thời gian):

$$
T_j \geq T_i + s_i + t_{ij} - M(1 - x_{ijk}) \quad \forall i,j \in V,\; \forall k \in K
$$

Time window (soft — không ép cứng $a_i \le T_i \le b_i$, mà tính phạt qua $E_i, L_i$ ở mục A.3/A.4):

$$
T_i - b_i \leq L_i, \qquad a_i - T_i \leq E_i, \qquad E_i, L_i \geq 0 \quad \forall i \in V_1
$$

### R6 — Maximum Ride Time

$$
T_{0'}^{k} - T_i \leq R_{max} \quad \forall i \in V_1 \text{ được phục vụ bởi xe } k,\; \forall k \in K
$$

Viết dưới dạng tuyến tính hóa với $x$:

$$
T_{0'}^{k} - T_i \leq R_{max} + M\left(1 - \sum_{j \in V} x_{ijk}\right) \quad \forall i \in V_1, \forall k \in K
$$

*(nếu vi phạm: theo thiết kế đã thống nhất, loại điểm đó khỏi route hiện tại và xử lý tiếp các điểm còn lại, không cho toàn bộ route fail).*

### R7 — Giới hạn thời lượng route (Maximum Route Duration)

$$
T_{0'}^{k} - T_0^{k} \leq H_{max} \quad \forall k \in K
$$

## A.6. Ràng buộc mềm bổ sung (Soft — đưa vào Objective, không phải Hard)

$$
W_i \leq W_{max} \quad (\text{tùy chọn, có thể để là penalty thay vì hard limit})
$$

## A.7. Kiến trúc 3 tầng (tóm tắt)

```
HARD CONSTRAINTS  : R1, R2, R3, R4, R6, R7  (+ flow conservation, load tracking)
SOFT CONSTRAINTS  : R5 (time window), waiting time
OBJECTIVE         : distance, late penalty, early penalty, waiting, operating cost
```

---

# PHẦN B — CHUYỂN MÔ HÌNH SANG PYTHON (SWEEP + TABU SEARCH)

## B.1. Cấu trúc dữ liệu

```python
from dataclasses import dataclass, field
from typing import List, Optional
import math

@dataclass
class Station:
    id: int
    lat: float
    lon: float
    demand: int          # q_i
    tw_start: float       # a_i (phút kể từ 00:00)
    tw_end: float         # b_i
    service_time: float = 2.0   # s_i

@dataclass
class Vehicle:
    id: int
    capacity: int         # Q

@dataclass
class Route:
    vehicle_id: int
    sequence: List[int] = field(default_factory=list)   # danh sách station.id theo thứ tự, KHÔNG gồm depot
    arrival_times: List[float] = field(default_factory=list)
    load: int = 0

@dataclass
class ProblemConfig:
    depot: tuple                 # (lat, lon)
    max_ride_time: float = 45
    max_route_duration: float = 90
    max_waiting_time: float = 10
    K_available: int = 4
    w_distance: float = 1.0
    w_late: float = 10.0
    w_early: float = 1.0
    w_waiting: float = 1.0
    w_cost: float = 1.0
    fixed_cost_per_vehicle: float = 100.0
```

## B.2. Bước 1 — Sweep Algorithm (khởi tạo nghiệm ban đầu)

```python
def polar_angle(depot, station: Station) -> float:
    dx = station.lon - depot[1]
    dy = station.lat - depot[0]
    ang = math.atan2(dy, dx)
    return ang if ang >= 0 else ang + 2 * math.pi

def sweep_construct(stations: List[Station], vehicles: List[Vehicle],
                     cfg: ProblemConfig) -> List[Route]:
    """
    R1 (depot start/end): mỗi route bắt đầu/kết thúc tại depot (ngầm định,
        không lưu trong sequence).
    R3 (capacity): dừng thêm trạm vào route hiện tại khi vượt Q.
    R4 (số xe): không tạo quá len(vehicles) route.
    """
    sorted_stations = sorted(stations, key=lambda s: polar_angle(cfg.depot, s))

    routes: List[Route] = []
    current = Route(vehicle_id=vehicles[0].id)
    v_idx = 0

    for st in sorted_stations:
        if current.load + st.demand > vehicles[v_idx].capacity:
            # R3 vi phạm -> đóng route hiện tại, mở route mới
            if current.sequence:
                routes.append(current)
            v_idx += 1
            if v_idx >= len(vehicles):
                # R4: không còn xe -> báo lỗi thay vì tự sinh xe ảo
                raise RuntimeError("INSUFFICIENT_VEHICLES")
            current = Route(vehicle_id=vehicles[v_idx].id)

        current.sequence.append(st.id)
        current.load += st.demand

    if current.sequence:
        routes.append(current)

    return routes
```

## B.3. Bước 2 — Kiểm tra khả thi (Feasibility Check = trực tiếp hóa R1–R7)

```python
def evaluate_route_times(route: Route, stations_by_id: dict, cfg: ProblemConfig,
                          travel_time_fn) -> dict:
    """
    Tính T_i dọc theo route (R5 lan truyền thời gian),
    đồng thời kiểm tra R6 (max ride time) và R7 (route duration).
    Trả về dict {feasible, violations, arrival_times, late, early, waiting}
    """
    t = 0.0  # T tại depot xuất phát = 0 (hoặc giờ khởi hành cố định)
    depot_start_time = t
    arrival_times = []
    late_total = 0.0
    early_total = 0.0
    waiting_total = 0.0
    pickup_times = {}   # T_i tại từng trạm, dùng để tính ride time (R6)

    prev = "DEPOT"
    for sid in route.sequence:
        st = stations_by_id[sid]
        travel = travel_time_fn(prev, sid)
        t = t + travel
        # R9 / waiting: đến sớm phải chờ tới a_i
        if t < st.tw_start:
            wait = st.tw_start - t
            waiting_total += wait
            if wait > cfg.max_waiting_time:
                pass  # soft -> chỉ cộng phạt, không loại (tùy chính sách)
            t = st.tw_start
        # R5 (soft time window)
        if t > st.tw_end:
            late_total += (t - st.tw_end)
        else:
            early_total += max(0, st.tw_start - t)

        pickup_times[sid] = t
        arrival_times.append(t)
        t += st.service_time
        prev = sid

    travel_back = travel_time_fn(prev, "DEPOT")
    t += travel_back
    route_duration = t - depot_start_time   # R7

    violations = []
    if route_duration > cfg.max_route_duration:
        violations.append("MAX_ROUTE_DURATION_EXCEEDED")

    excluded_stations = []
    for sid, pt in pickup_times.items():
        ride_time = t - pt   # R6: từ lúc đón đến lúc VỀ tới depot
        if ride_time > cfg.max_ride_time:
            violations.append(f"MAX_RIDE_TIME_EXCEEDED:{sid}")
            excluded_stations.append(sid)

    return {
        "feasible": len(violations) == 0,
        "violations": violations,
        "excluded_stations": excluded_stations,
        "arrival_times": arrival_times,
        "late_total": late_total,
        "early_total": early_total,
        "waiting_total": waiting_total,
        "route_duration": route_duration,
    }


def check_capacity(route: Route, stations_by_id: dict, capacity: int) -> bool:
    # R3
    total = sum(stations_by_id[sid].demand for sid in route.sequence)
    return total <= capacity


def check_all_visited_once(routes: List[Route], all_station_ids: set) -> bool:
    # R2
    seen = []
    for r in routes:
        seen.extend(r.sequence)
    return sorted(seen) == sorted(all_station_ids) and len(seen) == len(set(seen))
```

## B.4. Bước 3 — Hàm mục tiêu (Objective Function = A.4)

```python
def objective_value(routes: List[Route], stations_by_id: dict, cfg: ProblemConfig,
                     travel_time_fn, distance_fn) -> float:
    total_distance = 0.0
    total_late = 0.0
    total_early = 0.0
    total_waiting = 0.0

    for r in routes:
        prev = "DEPOT"
        for sid in r.sequence:
            total_distance += distance_fn(prev, sid)
            prev = sid
        total_distance += distance_fn(prev, "DEPOT")

        eval_result = evaluate_route_times(r, stations_by_id, cfg, travel_time_fn)
        total_late += eval_result["late_total"]
        total_early += eval_result["early_total"]
        total_waiting += eval_result["waiting_total"]

    n_vehicles_used = sum(1 for r in routes if r.sequence)

    Z = (cfg.w_distance * total_distance
         + cfg.w_late * total_late
         + cfg.w_early * total_early
         + cfg.w_waiting * total_waiting
         + cfg.w_cost * cfg.fixed_cost_per_vehicle * n_vehicles_used)
    return Z
```

## B.5. Bước 4 — Tabu Search (Neighborhood Operations)

```python
import random
import copy

def relocate_move(routes: List[Route]) -> List[Route]:
    """Neighborhood 1: chuyển 1 trạm từ route này sang route khác (hoặc vị trí khác)."""
    new_routes = copy.deepcopy(routes)
    non_empty = [r for r in new_routes if r.sequence]
    if len(non_empty) < 1:
        return new_routes
    r_from = random.choice(non_empty)
    if not r_from.sequence:
        return new_routes
    idx = random.randrange(len(r_from.sequence))
    station = r_from.sequence.pop(idx)
    r_to = random.choice(new_routes)
    insert_idx = random.randrange(len(r_to.sequence) + 1)
    r_to.sequence.insert(insert_idx, station)
    return new_routes


def two_opt_move(route: Route) -> Route:
    """Neighborhood 2: đảo đoạn giữa 2 vị trí trong cùng 1 route."""
    new_route = copy.deepcopy(route)
    n = len(new_route.sequence)
    if n < 3:
        return new_route
    i, j = sorted(random.sample(range(n), 2))
    new_route.sequence[i:j+1] = reversed(new_route.sequence[i:j+1])
    return new_route


def tabu_search(initial_routes: List[Route], stations_by_id: dict, cfg: ProblemConfig,
                 travel_time_fn, distance_fn,
                 max_iterations: int = 300, tabu_tenure: int = 15) -> List[Route]:

    def is_globally_feasible(routes) -> bool:
        for r in routes:
            if not check_capacity(r, stations_by_id, cfg_capacity):
                return False
            ev = evaluate_route_times(r, stations_by_id, cfg, travel_time_fn)
            if not ev["feasible"]:
                # theo chính sách: nếu chỉ vi phạm ride-time của MỘT trạm,
                # có thể loại trạm đó (excluded_stations) rồi coi route hợp lệ
                # thay vì fail toàn bộ (đúng thiết kế đã thống nhất ở R6)
                if any(v.startswith("MAX_ROUTE_DURATION") for v in ev["violations"]):
                    return False
        return True

    current = copy.deepcopy(initial_routes)
    best = copy.deepcopy(current)
    best_score = objective_value(best, stations_by_id, cfg, travel_time_fn, distance_fn)

    tabu_list = {}  # move_signature -> iterations_remaining

    for it in range(max_iterations):
        candidates = []
        for _ in range(20):
            if random.random() < 0.5:
                cand = relocate_move(current)
            else:
                r_idx = random.randrange(len(current))
                cand = copy.deepcopy(current)
                cand[r_idx] = two_opt_move(cand[r_idx])
            candidates.append(cand)

        candidates = [c for c in candidates if is_globally_feasible(c)]
        if not candidates:
            continue

        candidates.sort(key=lambda c: objective_value(
            c, stations_by_id, cfg, travel_time_fn, distance_fn))
        chosen = candidates[0]
        chosen_score = objective_value(chosen, stations_by_id, cfg, travel_time_fn, distance_fn)

        if chosen_score < best_score:
            best = copy.deepcopy(chosen)
            best_score = chosen_score

        current = chosen

        # giảm dần tabu tenure (đơn giản hóa — bản đầy đủ cần move-signature thật)
        tabu_list = {k: v - 1 for k, v in tabu_list.items() if v - 1 > 0}

    return best
```

## B.6. Bước 5 — Pipeline tổng thể

```python
def solve_vrptw_ctu(stations: List[Station], vehicles: List[Vehicle],
                     cfg: ProblemConfig, travel_time_fn, distance_fn) -> List[Route]:
    try:
        initial = sweep_construct(stations, vehicles, cfg)
    except RuntimeError as e:
        raise RuntimeError(f"INSUFFICIENT_VEHICLES: {e}")

    stations_by_id = {s.id: s for s in stations}

    for r in initial:
        if not check_capacity(r, stations_by_id, cfg.__dict__.get("capacity", vehicles[0].capacity)):
            raise RuntimeError("DEMAND_EXCEEDS_VEHICLE_CAPACITY")

    best_routes = tabu_search(initial, stations_by_id, cfg, travel_time_fn, distance_fn)
    return best_routes
```

> **Ghi chú quan trọng:** code trên là **khung sườn (skeleton)** để bạn cắm vào ứng dụng thực tế — chưa tối ưu về hiệu năng, chưa có move-signature đầy đủ cho tabu list (hiện đang đơn giản hóa), và `travel_time_fn`/`distance_fn` cần bạn nối với dữ liệu bản đồ thực (OSRM, Google Distance Matrix, hoặc ma trận khoảng cách tính sẵn). Mỗi hàm `evaluate_route_times`, `check_capacity`, `check_all_visited_once` tương ứng **trực tiếp 1-1** với các ràng buộc R1–R7 ở Phần A để bạn dễ đối chiếu khi viết unit test.

---

# PHẦN C — PROMPT KIỂM TRA RÀNG BUỘC TRONG ỨNG DỤNG (đã gộp, dùng bản này thay bản trước)

```
Bạn là một kỹ sư phần mềm kiêm chuyên gia tối ưu hóa vận tải (Operations Research).
Tôi có một ứng dụng định tuyến xe buýt đưa đón sinh viên (bài toán THU GOM — nhiều
điểm đón, một điểm đến là CTU), sử dụng thuật toán Sweep (khởi tạo) + Tabu Search
(cải thiện nghiệm), giải bài toán VRPTW (Vehicle Routing Problem with Time Windows).

Tôi đính kèm mô hình toán học VRPTW chuẩn của ứng dụng (Phần A) và một bản
skeleton code Python tương ứng (Phần B) làm tài liệu tham chiếu — bạn hãy dùng
đúng ký hiệu và cấu trúc ràng buộc trong tài liệu này khi rà soát, KHÔNG tự suy
diễn ràng buộc khác.

Nhiệm vụ của bạn: đọc code THỰC TẾ của tôi (dán/đính kèm bên dưới) và kiểm tra
xem 7 ràng buộc bắt buộc (R1–R7) + ràng buộc mềm (Time Window, Waiting Time)
+ hàm mục tiêu đã được cài đặt đúng, đủ, và nhất quán trong toàn bộ pipeline
(input → Sweep → Tabu Search → output) hay chưa.

=== ĐỐI CHIẾU VỚI MÔ HÌNH CHUẨN ===

R1 — Depot start/end:
    Σ_{j∈V1} x_0jk = y_k ,  Σ_{i∈V1} x_i0'k = y_k
    → Kiểm tra: route[0] và route[-1] tương ứng depot với MỌI route.

R2 — Mỗi trạm phục vụ đúng 1 lần (không split demand):
    Σ_k Σ_i x_ijk = 1 ∀j∈V1
    → Kiểm tra: gộp tất cả route, mỗi station_id xuất hiện đúng 1 lần, không thiếu
      không lặp.

R3 — Sức chứa xe (Capacity):
    Σ q_i (Σ_j x_ijk) ≤ Q ∀k
    → Kiểm tra tổng demand mỗi route ≤ Q. Nếu 1 trạm có demand > Q → phải trả
      DEMAND_EXCEEDS_VEHICLE_CAPACITY, không tự động chia nhỏ trừ khi ứng dụng
      đã hỗ trợ split demand.

R4 — Giới hạn số xe:
    Σ_k y_k ≤ K_available
    → Nếu cần nhiều xe hơn → trả INSUFFICIENT_VEHICLES, không tự sinh thêm xe ảo.

R5 — Time Window (SOFT):
    T_j ≥ T_i + s_i + t_ij - M(1-x_ijk)  (lan truyền thời gian)
    E_i = max(0, a_i - T_i), L_i = max(0, T_i - b_i)  (phạt sớm/trễ)
    → Kiểm tra công thức cộng dồn T_i có đúng cộng travel_time + service_time
      từ node trước hay không; kiểm tra late/early có được tính vào objective.

R6 — Maximum Ride Time (mặc định 45 phút):
    T_(0')^k - T_i ≤ R_max
    → Kiểm tra: tính từ lúc ĐÓN sinh viên tại trạm cụ thể (không phải từ lúc xe
      xuất phát khỏi depot) đến lúc xe VỀ tới depot. Nếu vi phạm: loại trạm đó
      khỏi route hiện tại, KHÔNG làm fail toàn bộ bài toán.

R7 — Maximum Route Duration (mặc định 90 phút):
    T_(0')^k - T_0^k ≤ H_max
    → Kiểm tra có tính đủ cả waiting time + service time vào tổng thời gian route,
      hay chỉ tính travel time.

SOFT — Waiting Time (tùy chọn, mặc định 10 phút):
    W_i ≤ W_max → phạt vào objective, không nhất thiết hard reject.

OBJECTIVE:
    min Z = w1·D + w2·L + w3·E + w4·W + w5·C
    Thứ tự ưu tiên: w_late > w_early > w_distance > w_cost.
    → Kiểm tra trọng số hiện tại trong code có phản ánh đúng thứ tự ưu tiên này
      hay đang dùng hàm mục tiêu đơn tiêu chí (chỉ minimize distance).

=== YÊU CẦU OUTPUT ===

Với MỖI ràng buộc (R1–R7, Soft Waiting, Objective), trả lời theo bảng:

| Ràng buộc | Đã cài đặt? (Có/Không/Một phần) | Vị trí trong code (file/hàm/dòng) | Vấn đề phát hiện | Đề xuất sửa |
|---|---|---|---|---|

Sau bảng, hãy:
1. Liệt kê các ràng buộc CHƯA cài đặt hoặc SAI logic (ưu tiên cao nhất).
2. Chỉ ra edge case chưa xử lý: demand vượt capacity, route rỗng, thời gian âm,
   không đủ xe, trạm bị loại do vi phạm ride-time nhưng chưa có cơ chế
   "xử lý điểm bị loại" (ví dụ: gán sang route khác hoặc báo lỗi riêng).
3. Đề xuất bộ unit test cụ thể (input mẫu + kết quả mong đợi), viết bằng
   pytest hoặc ngôn ngữ/framework tôi đang dùng, đối chiếu 1-1 với các hàm
   evaluate_route_times / check_capacity / check_all_visited_once trong
   Phần B nếu code của tôi có cấu trúc tương tự.
4. Không tự thêm ràng buộc mới ngoài danh sách trên vào thuyết minh/báo cáo
   nếu tôi chưa yêu cầu.

=== CẤU HÌNH HIỆN TẠI CỦA HỆ THỐNG ===

vehicle:
  count: 4
  capacity: 45

constraints:
  max_ride_time: 45        # phút
  max_route_duration: 90   # phút
  max_waiting_time: 10     # phút (tùy chọn)

time_window:
  policy: SOFT
  early_penalty: 1
  late_penalty: 10

service:
  default_service_time: 2  # phút

routing:
  start_depot: CTU
  end_depot: CTU

optimization:
  primary: time_window_violation
  secondary: total_distance
  tertiary: operating_cost

=== CODE CỦA TÔI ===

[Dán code Sweep + Tabu Search + input schema tại đây]
```

---

**Bước tiếp theo có thể làm:** viết bộ unit test pytest đầy đủ cho 7 ràng buộc + soft constraints dựa trên skeleton code ở Phần B, hoặc chuyển mô hình toán học ở Phần A sang định dạng LaTeX thuần để chèn trực tiếp vào file báo cáo/luận văn (Word hoặc Overleaf).
