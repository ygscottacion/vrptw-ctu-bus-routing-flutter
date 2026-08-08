import pytest
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
    vehicles = [
        {"id": 1, "capacity": 20},
        {"id": 2, "capacity": 20}
    ]

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
    solver = VRPTWSolverService()
    depot = {"id": 0, "name": "CTU Depot", "latitude": 10.0299, "longitude": 105.7684}
    locations = [
        {"id": 1, "latitude": 10.0342, "longitude": 105.7876, "demand": 5},
        {"id": 2, "latitude": 10.0031, "longitude": 105.7482, "demand": 8},
    ]
    vehicles = [{"id": 1, "capacity": 20}]

    results = solver.solve(depot, locations, vehicles)
    assert len(results) == 1
    assert "ordered_stops" in results[0]
