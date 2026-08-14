import sys
import os

# Thêm thư mục backend vào sys.path để ưu tiên app cục bộ thay vì app trong .venv site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tabu_service import TabuSearchOptimizer

def test_early_stopping_behavior():
    # Khởi tạo thuật toán với tối đa 100 vòng lặp nhưng dừng sớm sau 5 vòng không cải thiện
    optimizer = TabuSearchOptimizer(
        tabu_tenure=3,
        max_iterations=100,
        early_stopping_rounds=5,
        diversify_rounds=20,  # lớn hơn early_stopping để không bị restart giữa chừng
        average_speed_km_h=30.0
    )
    
    depot = {"id": 0, "latitude": 10.0, "longitude": 105.0}
    # Chỉ có 3 trạm (tổng không gian hoán đổi cực kỳ nhỏ, hội tụ rất nhanh)
    stops = [
        {"id": 1, "latitude": 10.01, "longitude": 105.01, "time_window_start": 10.0, "time_window_end": 20.0},
        {"id": 2, "latitude": 10.02, "longitude": 105.02, "time_window_start": 20.0, "time_window_end": 30.0},
        {"id": 3, "latitude": 10.03, "longitude": 105.03, "time_window_start": 30.0, "time_window_end": 40.0},
    ]
    
    best_stops, cost = optimizer.optimize_cluster_route(stops, depot)
    assert len(best_stops) == 3
    assert cost > 0


def test_diversification_behavior():
    # Chúng ta đặt diversify_rounds = 3 và early_stopping_rounds = 10
    # Điều này đảm bảo thuật toán sẽ kích hoạt diversification trước khi dừng sớm
    optimizer = TabuSearchOptimizer(
        tabu_tenure=2,
        max_iterations=30,
        early_stopping_rounds=10,
        diversify_rounds=3,
        average_speed_km_h=30.0
    )
    
    depot = {"id": 0, "latitude": 10.0, "longitude": 105.0}
    stops = [
        {"id": 1, "latitude": 10.01, "longitude": 105.04, "time_window_start": 10.0, "time_window_end": 20.0},
        {"id": 2, "latitude": 10.04, "longitude": 105.01, "time_window_start": 40.0, "time_window_end": 50.0},
        {"id": 3, "latitude": 10.02, "longitude": 105.03, "time_window_start": 20.0, "time_window_end": 35.0},
        {"id": 4, "latitude": 10.05, "longitude": 105.02, "time_window_start": 5.0, "time_window_end": 15.0},
        {"id": 5, "latitude": 10.03, "longitude": 105.05, "time_window_start": 30.0, "time_window_end": 45.0},
    ]
    
    best_stops, cost = optimizer.optimize_cluster_route(stops, depot)
    assert len(best_stops) == 5
    assert cost > 0
