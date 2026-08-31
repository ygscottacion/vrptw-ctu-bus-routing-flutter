import pytest
import time
from app.services.sweep_service import SweepClusteringService
from app.services.tabu_service import TabuSearchOptimizer
from app.services.vrptw_solver import VRPTWSolverService


def test_sweep_clustering():
    service = SweepClusteringService()
    depot = {"id": 0, "latitude": 10.0299, "longitude": 105.7684}
    locations = [
        {"id": 1, "latitude": 10.0342, "longitude": 105.7876, "demand": 10},
        {"id": 2, "latitude": 10.0031, "longitude": 105.7482, "demand": 15},
    ]
    vehicles = [{"id": 1, "capacity": 20}, {"id": 2, "capacity": 20}]
    clusters = service.cluster_locations(depot, locations, vehicles)
    assert len(clusters) > 0
    assert clusters[0]["current_demand"] <= 20


def test_tabu_optimizer():
    optimizer = TabuSearchOptimizer(max_iterations=10)
    depot = {"id": 0, "latitude": 10.0299, "longitude": 105.7684}
    stops = [
        {"id": 1, "latitude": 10.0342, "longitude": 105.7876},
        {"id": 2, "latitude": 10.0031, "longitude": 105.7482},
    ]
    best_stops, cost = optimizer.optimize_cluster_route(stops, depot)
    assert len(best_stops) == 2
    assert cost > 0


def test_vrptw_solver_pipeline():
    """Smoke test: solver tìm được ít nhất 1 route với static matrix."""
    solver = VRPTWSolverService(use_static_matrix=True)
    depot = {"id": 0, "name": "CTU Depot", "latitude": 10.0299, "longitude": 105.7684}
    locations = [
        {"id": 1, "latitude": 10.0342, "longitude": 105.7876, "demand": 5},
        {"id": 2, "latitude": 10.0031, "longitude": 105.7482, "demand": 8},
    ]
    vehicles = [{"id": 1, "capacity": 20}]
    results = solver.solve(depot, locations, vehicles)
    assert len(results) == 1
    assert "ordered_stops" in results[0]


def test_scaling_10_20_50_stops():
    """
    Scaling test VRPTW solver: 10, 20, 50 stops.

    Sử dụng:
    - use_static_matrix=True : bypass OSRM, không cần network.
    - tabu_max_iterations được điều chỉnh theo kích thước (O(n²) complexity).

    Ngưỡng thời gian:
    - 10 stops × 50 iter < 5s
    - 20 stops × 30 iter < 12s
    - 50 stops × 10 iter < 30s
    """
    solver = VRPTWSolverService(use_static_matrix=True)
    depot = {"id": 0, "name": "CTU Depot", "latitude": 10.0299, "longitude": 105.7684}
    vehicles = [
        {"id": 1, "capacity": 30},
        {"id": 2, "capacity": 30},
        {"id": 3, "capacity": 30},
    ]
    # (count, tabu_iterations, time_limit_s)
    test_cases = [(10, 50, 5.0), (20, 30, 12.0), (50, 10, 30.0)]

    for count, iters, limit in test_cases:
        # Offset 0.0001° ≈ 11m/stop → 50 stops ≈ 550m từ depot, trong 10km radius.
        locations = [
            {
                "id": i,
                "name": f"Trạm {i}",
                "latitude": 10.0299 + (i * 0.0001),
                "longitude": 105.7684 + (i * 0.0001),
                "demand": 1,
            }
            for i in range(1, count + 1)
        ]

        start_time = time.time()
        results = solver.solve(
            depot, locations, vehicles,
            tabu_max_iterations=iters,
        )
        elapsed = time.time() - start_time

        assert len(results) > 0, (
            f"Solver không tìm được route nào cho {count} stops. "
            f"Kiểm tra radius filter hoặc ride time constraints."
        )
        assert elapsed < limit, (
            f"Solver quá chậm cho {count} stops ({iters} iter): "
            f"{elapsed:.2f}s (limit: {limit}s)."
        )
        print(f"SUCCESS: VRPTW Solver {count} stops ({iters} iter): {elapsed:.3f}s < {limit}s")
