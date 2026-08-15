import sys
import os

# Thêm thư mục backend vào sys.path để ưu tiên app cục bộ thay vì app trong .venv site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tabu_service import TabuSearchOptimizer, RouteEvaluation

def test_fitness_perfect_timing():
    # Trường hợp lý tưởng: xe chạy từ depot -> stop 1 -> quay về depot.
    # Khoảng cách được bố trí để đến đúng lúc tw_start hoặc không có time window.
    optimizer = TabuSearchOptimizer(
        average_speed_km_h=30.0,
        distance_weight=1.0,
        waiting_time_weight=0.5,
        lateness_weight=100.0
    )
    
    depot = {"latitude": 10.0, "longitude": 105.0}
    # Điểm đón cách 5 km (dist = 5.0)
    # Thời gian di chuyển = (5 / 30) * 60 = 10 phút.
    # Ta đặt tw_start = 10.0, tw_end = 15.0 để xe đến đúng lúc tw_start, không bị trễ, không bị chờ.
    stop = {
        "latitude": 10.0,
        "longitude": 105.0 + (5.0 / 111.0),  # Khoảng cách xấp xỉ 5km
        "time_window_start": 10.0,
        "time_window_end": 15.0
    }
    
    route = [stop]
    eval_res = optimizer.evaluate_route(route, depot)
    
    # 5km đi + 5km về = 10km
    assert abs(eval_res.distance - 10.0) < 0.1
    # Không phải chờ vì đến đúng lúc tw_start (10 phút)
    assert abs(eval_res.waiting_time - 0.0) < 0.1
    # Không bị trễ
    assert abs(eval_res.lateness - 0.0) < 0.1
    # Chi phí = 10.0 * 1.0 = 10.0
    assert abs(eval_res.cost - 10.0) < 0.1


def test_fitness_waiting_time():
    # Trường hợp xe đến sớm: xe di chuyển mất 10 phút nhưng tw_start = 25.0 -> phải chờ 15 phút.
    optimizer = TabuSearchOptimizer(
        average_speed_km_h=30.0,
        distance_weight=1.0,
        waiting_time_weight=2.0,  # weight phạt chờ là 2.0
        lateness_weight=100.0
    )
    
    depot = {"latitude": 10.0, "longitude": 105.0}
    stop = {
        "latitude": 10.0,
        "longitude": 105.0 + (5.0 / 111.0),
        "time_window_start": 25.0,  # đến phút thứ 10 nhưng bắt đầu từ 25 -> chờ 15 phút
        "time_window_end": 30.0
    }
    
    route = [stop]
    eval_res = optimizer.evaluate_route(route, depot)
    
    # Chờ 15 phút
    assert abs(eval_res.waiting_time - 15.0) < 0.1
    # Không bị trễ
    assert abs(eval_res.lateness - 0.0) < 0.1
    # Chi phí = distance (10.0) * 1.0 + waiting_time (15.0) * 2.0 = 10.0 + 30.0 = 40.0
    assert abs(eval_res.cost - 40.0) < 0.5


def test_fitness_lateness_penalty():
    # Trường hợp xe đến trễ: xe di chuyển mất 10 phút nhưng tw_end = 5.0 -> trễ 5 phút.
    optimizer = TabuSearchOptimizer(
        average_speed_km_h=30.0,
        distance_weight=1.0,
        waiting_time_weight=0.5,
        lateness_weight=50.0  # weight phạt trễ là 50.0
    )
    
    depot = {"latitude": 10.0, "longitude": 105.0}
    stop = {
        "latitude": 10.0,
        "longitude": 105.0 + (5.0 / 111.0),
        "time_window_start": 0.0,
        "time_window_end": 5.0  # đến phút thứ 10 nhưng phải xong trước 5 -> trễ 5 phút
    }
    
    route = [stop]
    eval_res = optimizer.evaluate_route(route, depot)
    
    # Không phải chờ
    assert abs(eval_res.waiting_time - 0.0) < 0.1
    # Trễ 5 phút
    assert abs(eval_res.lateness - 5.0) < 0.1
    # Chi phí = distance (10.0) * 1.0 + lateness (5.0) * 50.0 = 10.0 + 250.0 = 260.0
    assert abs(eval_res.cost - 260.0) < 0.5
