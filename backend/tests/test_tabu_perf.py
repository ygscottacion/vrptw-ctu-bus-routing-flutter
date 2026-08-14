import sys
import os
import time

# Thêm thư mục backend vào sys.path để ưu tiên app cục bộ thay vì app trong .venv site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tabu_service import TabuSearchOptimizer

def test_tabu_performance_and_optimality():
    # Khởi tạo thuật toán với cấu hình chuẩn
    optimizer = TabuSearchOptimizer(
        tabu_tenure=8,
        max_iterations=100,
        distance_weight=1.0,
        waiting_time_weight=0.5,
        lateness_weight=100.0,
        average_speed_km_h=30.0
    )
    
    depot = {"id": 0, "latitude": 10.0299, "longitude": 105.7684}
    
    # Tạo 12 trạm dừng mẫu với tọa độ và khung thời gian lộn xộn
    stops = [
        {"id": 1, "latitude": 10.0342, "longitude": 105.7876, "time_window_start": 10.0, "time_window_end": 20.0},
        {"id": 2, "latitude": 10.0031, "longitude": 105.7482, "time_window_start": 30.0, "time_window_end": 45.0},
        {"id": 3, "latitude": 10.0450, "longitude": 105.7620, "time_window_start": 15.0, "time_window_end": 25.0},
        {"id": 4, "latitude": 10.0210, "longitude": 105.7910, "time_window_start": 40.0, "time_window_end": 60.0},
        {"id": 5, "latitude": 10.0150, "longitude": 105.7720, "time_window_start": 50.0, "time_window_end": 70.0},
        {"id": 6, "latitude": 10.0510, "longitude": 105.7500, "time_window_start": 20.0, "time_window_end": 35.0},
        {"id": 7, "latitude": 10.0390, "longitude": 105.7300, "time_window_start": 60.0, "time_window_end": 80.0},
        {"id": 8, "latitude": 10.0250, "longitude": 105.7200, "time_window_start": 80.0, "time_window_end": 100.0},
        {"id": 9, "latitude": 10.0610, "longitude": 105.7800, "time_window_start": 70.0, "time_window_end": 90.0},
        {"id": 10, "latitude": 10.0480, "longitude": 105.7950, "time_window_start": 90.0, "time_window_end": 110.0},
        {"id": 11, "latitude": 10.0120, "longitude": 105.7350, "time_window_start": 110.0, "time_window_end": 130.0},
        {"id": 12, "latitude": 10.0550, "longitude": 105.7700, "time_window_start": 120.0, "time_window_end": 140.0},
    ]

    # Tính cost ban đầu của lộ trình chưa được tối ưu (theo thứ tự ban đầu)
    initial_eval = optimizer.evaluate_route(stops, depot)
    initial_cost = initial_eval.cost

    # Đo thời gian bắt đầu chạy Tabu Search
    start_time = time.perf_counter()
    optimized_stops, optimized_cost = optimizer.optimize_cluster_route(stops, depot)
    end_time = time.perf_counter()
    
    execution_time_ms = (end_time - start_time) * 1000.0

    print(f"\n--- Tabu Search Evaluation (N = {len(stops)} stops) ---")
    print(f"Initial Route Cost  : {initial_cost:.2f}")
    print(f"Optimized Route Cost: {optimized_cost:.2f}")
    print(f"Improvement Rate    : {((initial_cost - optimized_cost) / initial_cost) * 100:.2f}%")
    print(f"Execution Time      : {execution_time_ms:.2f} ms")
    
    # 1. Kiểm tra tính tối ưu: Cost sau khi chạy Tabu Search phải nhỏ hơn hoặc bằng Cost ban đầu
    assert optimized_cost <= initial_cost
    
    # 2. Kiểm tra mức độ cải thiện (tối thiểu 15%)
    improvement = (initial_cost - optimized_cost) / initial_cost
    assert improvement >= 0.15, f"Improvement only {improvement*100:.2f}%, expected >= 15%"
    
    # 3. Kiểm tra hiệu năng: Thời gian chạy phải nhanh (dưới 200ms cho 12 trạm)
    assert execution_time_ms < 200.0, f"Execution took too long: {execution_time_ms:.2f} ms"

if __name__ == "__main__":
    test_tabu_performance_and_optimality()
