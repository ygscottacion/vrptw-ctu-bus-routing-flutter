import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.sweep_service import SweepClusteringService

def test_polar_angle_calculation():
    """Kiểm tra tính toán góc cực từ Depot"""
    depot_lat, depot_lng = 10.0, 10.0
    
    # Điểm ở hướng Đông (0 rad)
    east_angle = SweepClusteringService.calculate_polar_angle(depot_lat, depot_lng, 10.0, 11.0)
    assert math.isclose(east_angle, 0.0, abs_tol=1e-5)
    
    # Điểm ở hướng Bắc (pi/2 rad)
    north_angle = SweepClusteringService.calculate_polar_angle(depot_lat, depot_lng, 11.0, 10.0)
    assert math.isclose(north_angle, math.pi / 2, abs_tol=1e-5)
    
    # Điểm ở hướng Tây (pi rad)
    west_angle = SweepClusteringService.calculate_polar_angle(depot_lat, depot_lng, 10.0, 9.0)
    assert math.isclose(west_angle, math.pi, abs_tol=1e-5)

    print("[PASS] test_polar_angle_calculation PASSED")

def test_sweep_clustering_capacity():
    """Kiểm tra gom cụm Sweep tôn trọng ràng buộc sức chứa (capacity) xe"""
    service = SweepClusteringService()
    depot = {"id": 0, "latitude": 10.0, "longitude": 10.0}
    
    # 4 trạm xung quanh Depot với demand = 10
    locations = [
        {"id": 1, "latitude": 10.0, "longitude": 11.0, "demand": 10}, # 0 rad
        {"id": 2, "latitude": 11.0, "longitude": 10.0, "demand": 10}, # pi/2 rad
        {"id": 3, "latitude": 10.0, "longitude": 9.0, "demand": 10},  # pi rad
        {"id": 4, "latitude": 9.0, "longitude": 10.0, "demand": 10},  # 3pi/2 rad
    ]
    
    # 2 xe, mỗi xe capacity = 20
    vehicles = [
        {"id": 101, "capacity": 20},
        {"id": 102, "capacity": 20},
    ]

    clusters = service.cluster_locations(depot, locations, vehicles)
    
    assert len(clusters) == 2, f"Kỳ vọng 2 cụm xe nhưng nhận được {len(clusters)}"
    
    # Cụm 1
    assert clusters[0]["vehicle_id"] == 101
    assert clusters[0]["current_demand"] == 20
    assert len(clusters[0]["stops"]) == 2
    
    # Cụm 2
    assert clusters[1]["vehicle_id"] == 102
    assert clusters[1]["current_demand"] == 20
    assert len(clusters[1]["stops"]) == 2

    print("[PASS] test_sweep_clustering_capacity PASSED")

def test_sweep_sorting_order():
    """Kiểm tra trạm được sắp xếp chuẩn theo thứ tự góc quét tăng dần"""
    service = SweepClusteringService()
    depot = {"id": 0, "latitude": 10.0, "longitude": 10.0}
    
    locations = [
        {"id": 1, "name": "Nam", "latitude": 9.0, "longitude": 10.0, "demand": 5},   # 270 deg (3pi/2)
        {"id": 2, "name": "Bắc", "latitude": 11.0, "longitude": 10.0, "demand": 5},  # 90 deg (pi/2)
        {"id": 3, "name": "Đông", "latitude": 10.0, "longitude": 11.0, "demand": 5}, # 0 deg
    ]
    
    vehicles = [{"id": 1, "capacity": 30}]
    
    clusters = service.cluster_locations(depot, locations, vehicles)
    stops = clusters[0]["stops"]
    
    stop_names = [s["name"] for s in stops]
    assert stop_names == ["Đông", "Bắc", "Nam"], f"Thứ tự trạm sai: {stop_names}"

    print("[PASS] test_sweep_sorting_order PASSED")

if __name__ == "__main__":
    test_polar_angle_calculation()
    test_sweep_clustering_capacity()
    test_sweep_sorting_order()
    print("\n--- Tat ca Unit Tests cho Sweep Service (Tuan 2) da THANH CONG! ---")

