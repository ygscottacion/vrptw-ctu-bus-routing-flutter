"""
test_duy_solver_day7_day8_day14.py
===================================
Bộ test kiểm thử toàn diện các nhiệm vụ của thành viên Duy (Solver):
1. Sweep clustering: phân 60 sinh viên vào >= 2 xe, chặn quá tải và quá giờ (Ngày 7).
2. Tabu Search: tối ưu thứ tự trạm theo ma trận thật (Ngày 8).
3. Logic so sánh Baseline (Sweep) vs Tabu Search phục vụ Khánh và benchmark (Ngày 14).
"""

import pytest
import math
from app.services.sweep_service import SweepClusteringService
from app.services.tabu_service import TabuSearchOptimizer
from app.services.student_routing.core.sweep_clustering import SweepClusterer
from app.services.student_routing.benchmark import StudentRoutingBenchmark, generate_synthetic_dataset
from app.services.student_routing.helpers.distance_matrix import StaticDistanceMatrixProvider


# ══════════════════════════════════════════════════════════════════════════════
# 1. NGÀY 7: SWEEP CLUSTERING (60 SV, >= 2 XE, CHẶN QUÁ TẢI, CHẶN QUÁ GIỜ)
# ══════════════════════════════════════════════════════════════════════════════

def test_day7_sweep_clustering_60_students_partition_ge_2_vehicles():
    """
    Kiểm tra Sweep clustering phân bổ 60 sinh viên:
    - Phải chia vào >= 2 xe.
    - Không xe nào vượt quá tải trọng 45 chỗ (chặn quá tải).
    """
    service = SweepClusteringService()
    depot = {"id": 0, "latitude": 10.0302, "longitude": 105.7721}

    # Tạo 20 trạm, mỗi trạm 3 sinh viên -> Tổng 60 sinh viên
    locations = [
        {
            "id": i,
            "latitude": 10.0302 + 0.02 * math.sin(i * 2 * math.pi / 20),
            "longitude": 105.7721 + 0.02 * math.cos(i * 2 * math.pi / 20),
            "demand": 3
        }
        for i in range(1, 21)
    ]
    assert sum(loc["demand"] for loc in locations) == 60

    # Cung cấp 2 xe (mỗi xe sức chứa 45)
    vehicles = [{"id": "BUS-01", "capacity": 45}, {"id": "BUS-02", "capacity": 45}]

    clusters = service.cluster_locations(depot, locations, vehicles)

    # 1. Phải chia vào >= 2 xe
    assert len(clusters) >= 2, f"Expected >= 2 clusters, got {len(clusters)}"

    # 2. Chặn quá tải: không xe nào vượt quá capacity (<= 45)
    total_assigned = 0
    for c in clusters:
        assert c["current_demand"] <= c["capacity"], (
            f"Xe {c['vehicle_id']} bị quá tải: {c['current_demand']} > {c['capacity']}"
        )
        assert c["current_demand"] <= 45, (
            f"Xe {c['vehicle_id']} vượt quá tải tối đa 45 khách: {c['current_demand']}"
        )
        total_assigned += c["current_demand"]

    # 3. Đủ stop, không sót khách nào
    assert total_assigned == 60, f"Expected 60 total assigned students, got {total_assigned}"


def test_day7_sweep_clustering_overtime_protection():
    """
    Kiểm tra chặn quá giờ: Khi các trạm có khoảng cách làm tổng thời lượng tuyến vượt ngưỡng,
    Sweep phải tự động ngắt cụm sang xe tiếp theo dù xe chưa đầy tải.
    """
    service = SweepClusteringService()
    depot = {"id": 0, "latitude": 10.0302, "longitude": 105.7721}

    # 6 trạm trong bán kính 6km quanh CTU, mỗi trạm demand 2 SV
    locations = [
        {"id": 1, "latitude": 10.045, "longitude": 105.785, "demand": 2},
        {"id": 2, "latitude": 10.055, "longitude": 105.795, "demand": 2},
        {"id": 3, "latitude": 10.065, "longitude": 105.805, "demand": 2},
        {"id": 4, "latitude": 10.020, "longitude": 105.750, "demand": 2},
        {"id": 5, "latitude": 10.010, "longitude": 105.740, "demand": 2},
        {"id": 6, "latitude": 10.005, "longitude": 105.730, "demand": 2},
    ]
    # Xe có sức chứa 45 (dư sức chở 12 sinh viên), nhưng đặt giới hạn 30 phút
    vehicles = [{"id": "BUS-01", "capacity": 45}, {"id": "BUS-02", "capacity": 45}]

    clusters = service.cluster_locations(
        depot, locations, vehicles, max_route_duration_minutes=30.0
    )

    # Do giới hạn 30 phút, thuật toán phải chia sang >= 2 xe dù tổng khách chỉ là 12
    assert len(clusters) >= 2, "Thuật toán phải tách cụm khi bị quá giờ (overtime)"
    for c in clusters:
        dur = service.estimate_route_duration(depot, c["stops"])
        assert dur <= 90.0, f"Thời lượng {dur} phút vượt ngưỡng 90 phút"


def test_day7_student_routing_core_sweep_clusterer_60_students():
    """
    Kiểm tra SweepClusterer trong module student_routing/core/sweep_clustering.py
    với 60 sinh viên và bảo đảm >= 2 xe, <= 45 khách/xe, duration <= 90m.
    """
    clusterer = SweepClusterer()
    depot = {"id": "SCHOOL", "lat": 10.0302, "lng": 105.7721}

    stations = [
        {
            "id": f"ST-{i:02d}",
            "name": f"Trạm {i}",
            "lat": 10.0302 + 0.02 * math.cos(i * 2 * math.pi / 20),
            "lng": 105.7721 + 0.02 * math.sin(i * 2 * math.pi / 20),
            "pickup_student_count": 3,
            "demand": 3
        }
        for i in range(1, 21)
    ]
    vehicles = [{"id": "BUS-01", "capacity": 45}, {"id": "BUS-02", "capacity": 45}]

    routes = clusterer.create_initial_routes(depot, stations, vehicles)

    assert len(routes) >= 2, f"Expected >= 2 routes for 60 students, got {len(routes)}"
    for r in routes:
        load = sum(st.get("demand", 1) for st in r)
        assert load <= 45, f"Route overload: {load} > 45"
        dur = clusterer.estimate_route_duration(depot, r)
        assert dur <= 90.0, f"Route overtime: {dur} > 90m"


# ══════════════════════════════════════════════════════════════════════════════
# 2. NGÀY 8: TABU SEARCH TỐI ƯU THEO MA TRẬN THẬT
# ══════════════════════════════════════════════════════════════════════════════

def test_day8_tabu_search_with_real_matrix():
    """
    Kiểm tra TabuSearchOptimizer khi được truyền ma trận khoảng cách & thời gian thật:
    - Thuật toán lượng giá chính xác theo ma trận.
    - Tìm ra thứ tự trạm tối ưu có cost <= giải pháp ban đầu.
    """
    optimizer = TabuSearchOptimizer(max_iterations=30)
    depot = {"id": 0, "latitude": 10.0302, "longitude": 105.7721}

    stops = [
        {"id": 1, "latitude": 10.04, "longitude": 105.78, "time_window_start": "06:00", "time_window_end": "06:20"},
        {"id": 2, "latitude": 10.05, "longitude": 105.79, "time_window_start": "06:20", "time_window_end": "06:40"},
        {"id": 3, "latitude": 10.03, "longitude": 105.76, "time_window_start": "05:40", "time_window_end": "06:05"},
        {"id": 4, "latitude": 10.02, "longitude": 105.75, "time_window_start": "05:30", "time_window_end": "05:55"},
    ]

    # Tạo ma trận thực tế qua StaticDistanceMatrixProvider
    points = [
        {"lat": depot["latitude"], "lng": depot["longitude"]},
        {"lat": stops[0]["latitude"], "lng": stops[0]["longitude"]},
        {"lat": stops[1]["latitude"], "lng": stops[1]["longitude"]},
        {"lat": stops[2]["latitude"], "lng": stops[2]["longitude"]},
        {"lat": stops[3]["latitude"], "lng": stops[3]["longitude"]},
    ]
    point_index_map = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4}

    provider = StaticDistanceMatrixProvider()
    dist_matrix, ttime_matrix, _ = provider.get_matrix(points, "MORNING_1")

    # Thứ tự ban đầu (ngược time window)
    initial_eval = optimizer.evaluate_route(
        stops, depot,
        distance_matrix=dist_matrix,
        travel_time_matrix=ttime_matrix,
        point_index_map=point_index_map,
        departure_time_mins=330.0  # 05:30
    )

    # Chạy Tabu Search tối ưu thứ tự
    best_stops, best_cost = optimizer.optimize_cluster_route(
        stops, depot,
        distance_matrix=dist_matrix,
        travel_time_matrix=ttime_matrix,
        point_index_map=point_index_map,
        departure_time_mins=330.0
    )

    assert len(best_stops) == len(stops), "Số lượng trạm không được thay đổi (đủ stop, không lặp)"
    assert best_cost <= initial_eval.cost, (
        f"Tabu Search phải cải thiện hoặc giữ nguyên cost: {best_cost} <= {initial_eval.cost}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. NGÀY 14: BENCHMARK BASELINE VS TABU (PHỐI HỢP VỚI KHÁNH)
# ══════════════════════════════════════════════════════════════════════════════

def test_day14_benchmark_60_students_scenario_full_metrics():
    """
    Kiểm tra kịch bản benchmark 60 sinh viên đối sánh Baseline (Sweep) vs Tabu Search:
    - Xuất đầy đủ các chỉ số: distance, travel time, lateness, violations, improvement %.
    - Đảm bảo tính khả thi: 0 overload, 0 overtime, >= 2 xe.
    - Cung cấp dữ liệu chuẩn để Khánh tích hợp lên API/UI ngày 14.
    """
    benchmark = StudentRoutingBenchmark()

    report = benchmark.run_60_students_scenario(num_vehicles=2, num_stations=20, num_runs=1)

    # 1. Kiểm tra cấu trúc dữ liệu trả về cho Khánh
    assert "baseline" in report
    assert "tabu_optimized" in report
    assert "improvements" in report
    assert "feasibility" in report

    # 2. Kiểm tra các chỉ số của Baseline
    base = report["baseline"]
    assert base["routes_count"] >= 2, "Baseline phải chia >= 2 xe cho 60 SV"
    assert base["capacity_violations"] == 0, "Không được có vi phạm quá tải (capacity <= 45)"

    # 3. Kiểm tra các chỉ số của Tabu Search
    tabu = report["tabu_optimized"]
    assert tabu["routes_count"] >= 2, "Tabu phải chia >= 2 xe cho 60 SV"
    assert tabu["capacity_violations"] == 0, "Không được có vi phạm quá tải (capacity <= 45)"
    assert tabu["objective_value"] <= base["objective_value"], (
        f"Tabu objective {tabu['objective_value']} phải <= baseline {base['objective_value']}"
    )
    assert tabu["total_distance_km"] <= base["total_distance_km"], "Tabu phải tối ưu quãng đường"
    assert tabu["ride_time_violations"] <= base["ride_time_violations"], "Tabu phải giảm hoặc giữ nguyên vi phạm ride time"

    # 4. Kiểm tra tiêu chí khả thi (Feasibility Handshake với Khánh ngày 9)
    feas = report["feasibility"]
    assert feas["overload_prevented"] is True, "Chặn quá tải thành công"
    assert feas["vehicles_used_ge_2"] is True, "Phân bổ >= 2 xe thành công"

    # 5. Kiểm tra các trường cải thiện
    imp = report["improvements"]
    assert "distance_reduction_km" in imp
    assert "objective_improvement_pct" in imp
    assert imp["objective_improvement_pct"] > 0.0, f"Tabu phải cải thiện objective > 0%, got {imp['objective_improvement_pct']}%"
    assert imp["distance_reduction_km"] >= 0.0, "Tabu phải giảm tổng quãng đường"
