"""
test_khanh_validation_day9.py
=============================
Bộ test kiểm thử toàn diện cho nhiệm vụ của Khánh:
Ngày 9 — Validation bắt buộc:
1. `đủ stop`: 100% trạm/khách được phân bổ, không bỏ sót.
2. `không lặp`: Không trùng lặp trạm trung gian trong lộ trình.
3. `≤ 45 khách`: Chặn quá tải trên từng xe buýt.
4. `≤ 90 phút`: Chặn quá thời gian hành trình toàn tuyến.
"""

import pytest
import datetime
from app.services.route_validator import (
    RouteValidator,
    RouteValidationError,
    calculate_stops_duration_minutes,
    parse_time_to_minutes,
)
import math
from app.services.vrptw_solver import VRPTWSolverService


# ══════════════════════════════════════════════════════════════════════════════
# 1. TEST BÀN GIAO: OUTPUT TỪ SOLVER CỦA DUY PASS 100% VALIDATION CỦA KHÁNH
# ══════════════════════════════════════════════════════════════════════════════

def test_day9_duy_solver_output_passes_khanh_validator():
    """
    Xác nhận lời giải 60 sinh viên quanh CTU từ Solver của Duy
    hoàn toàn thỏa mãn 4 tiêu chuẩn bắt buộc của Khánh (0 vi phạm).
    """
    solver = VRPTWSolverService(use_static_matrix=True)
    depot = {"id": 0, "name": "ĐH Cần Thơ", "latitude": 10.0302, "longitude": 105.7721}

    # 20 trạm, mỗi trạm 3 sinh viên = 60 SV
    locations = [
        {
            "id": f"location_{i}",
            "name": f"Trạm {i}",
            "latitude": 10.0302 + 0.02 * math.cos(i * 2 * math.pi / 20),
            "longitude": 105.7721 + 0.02 * math.sin(i * 2 * math.pi / 20),
            "demand": 3,
            "pickup_student_count": 3,
        }
        for i in range(20)
    ]
    vehicles = [{"id": "BUS-01", "capacity": 45}, {"id": "BUS-02", "capacity": 45}]

    solved_routes = solver.solve(
        depot=depot,
        locations=locations,
        vehicles=vehicles,
        tabu_max_iterations=10,
    )

    # Thẩm định bằng RouteValidator của Khánh
    res = RouteValidator.validate_solver_routes(
        routes=solved_routes,
        expected_station_ids={f"location_{i}" for i in range(20)},
        expected_total_demand=60,
        max_capacity=45,
        max_duration_minutes=90.0,
    )

    assert res["status"] == "VALID"
    assert res["total_served_demand"] == 60
    assert res["total_routes"] >= 2
    assert res["max_capacity_complied"] is True
    assert res["max_duration_complied"] is True
    assert res["no_duplicates"] is True
    assert res["completeness_verified"] is True


# ══════════════════════════════════════════════════════════════════════════════
# 2. TEST QUY TẮC 1: ĐỦ STOP (COMPLETENESS & NO MISSING STATIONS)
# ══════════════════════════════════════════════════════════════════════════════

def test_day9_validation_rejects_missing_stations():
    """Bắt lỗi khi có trạm có nhu cầu nhưng bị bỏ sót khỏi lộ trình."""
    routes = [
        {
            "vehicle_id": "BUS-01",
            "total_demand": 10,
            "ordered_stops": [
                {"id": "depot", "arrival_time": "06:00"},
                {"id": "ST_01", "arrival_time": "06:15", "demand": 5},
                {"id": "ST_02", "arrival_time": "06:30", "demand": 5},
            ]
        }
    ]
    expected_stations = {"ST_01", "ST_02", "ST_03"}  # ST_03 bị thiếu

    with pytest.raises(RouteValidationError) as exc_info:
        RouteValidator.validate_solver_routes(
            routes=routes,
            expected_station_ids=expected_stations,
            expected_total_demand=10,
        )

    assert exc_info.value.error_code == "MISSING_STOPS"
    assert "ST_03" in exc_info.value.message


def test_day9_validation_rejects_demand_mismatch():
    """Bắt lỗi khi tổng số sinh viên phục vụ không khớp nhu cầu."""
    routes = [
        {
            "vehicle_id": "BUS-01",
            "total_demand": 15,
            "ordered_stops": [
                {"id": "depot", "arrival_time": "06:00"},
                {"id": "ST_01", "arrival_time": "06:20", "demand": 15},
            ]
        }
    ]

    with pytest.raises(RouteValidationError) as exc_info:
        RouteValidator.validate_solver_routes(
            routes=routes,
            expected_total_demand=20,  # Kỳ vọng 20 nhưng chỉ phục vụ 15
        )

    assert exc_info.value.error_code == "DEMAND_MISMATCH"


# ══════════════════════════════════════════════════════════════════════════════
# 3. TEST QUY TẮC 2: KHÔNG LẶP TRẠM (NO DUPLICATE STOPS)
# ══════════════════════════════════════════════════════════════════════════════

def test_day9_validation_rejects_duplicate_stops_in_route():
    """Bắt lỗi khi trong cùng một lộ trình, một trạm đón xuất hiện 2 lần."""
    routes = [
        {
            "vehicle_id": "BUS-01",
            "total_demand": 10,
            "ordered_stops": [
                {"id": "depot", "arrival_time": "06:00"},
                {"id": "ST_01", "arrival_time": "06:15", "demand": 5},
                {"id": "ST_02", "arrival_time": "06:25", "demand": 3},
                {"id": "ST_01", "arrival_time": "06:40", "demand": 2},  # Lặp ST_01
            ]
        }
    ]

    with pytest.raises(RouteValidationError) as exc_info:
        RouteValidator.validate_solver_routes(routes=routes)

    assert exc_info.value.error_code == "DUPLICATE_STOPS"
    assert "ST_01" in exc_info.value.message


# ══════════════════════════════════════════════════════════════════════════════
# 4. TEST QUY TẮC 3: <= 45 KHÁCH (CHẶN QUÁ TẢI CAPACITY)
# ══════════════════════════════════════════════════════════════════════════════

def test_day9_validation_rejects_overload_capacity():
    """Bắt lỗi khi tải trọng xe vượt quá 45 khách."""
    routes = [
        {
            "vehicle_id": "BUS-01",
            "total_demand": 46,  # Quá 45
            "ordered_stops": [
                {"id": "depot", "arrival_time": "06:00"},
                {"id": "ST_01", "arrival_time": "06:20", "demand": 46},
            ]
        }
    ]

    with pytest.raises(RouteValidationError) as exc_info:
        RouteValidator.validate_solver_routes(routes=routes, max_capacity=45)

    assert exc_info.value.error_code == "OVERLOAD_VIOLATION"
    assert "46" in exc_info.value.message


# ══════════════════════════════════════════════════════════════════════════════
# 5. TEST QUY TẮC 4: <= 90 PHÚT (CHẶN QUÁ THỜI LƯỢNG HÀNH TRÌNH)
# ══════════════════════════════════════════════════════════════════════════════

def test_day9_validation_rejects_overtime_duration():
    """Bắt lỗi khi thời lượng toàn tuyến vượt quá 90 phút."""
    # Điểm đầu 05:30 -> Điểm cuối 07:15 (105 phút > 90 phút)
    routes = [
        {
            "vehicle_id": "BUS-01",
            "total_demand": 20,
            "ordered_stops": [
                {"id": "depot", "arrival_time": "05:30", "departure_time": "05:30"},
                {"id": "ST_01", "arrival_time": "06:00", "departure_time": "06:05"},
                {"id": "ST_02", "arrival_time": "06:45", "departure_time": "06:50"},
                {"id": "depot", "arrival_time": "07:15", "departure_time": "07:15"},
            ]
        }
    ]

    with pytest.raises(RouteValidationError) as exc_info:
        RouteValidator.validate_solver_routes(routes=routes, max_duration_minutes=90.0)

    assert exc_info.value.error_code == "OVERTIME_VIOLATION"
    assert "105.0" in exc_info.value.message or "vượt quá" in exc_info.value.message


# ══════════════════════════════════════════════════════════════════════════════
# 6. TEST TIỆN ÍCH TÍNH THỜI LƯỢNG
# ══════════════════════════════════════════════════════════════════════════════

def test_time_calculation_utilities():
    assert parse_time_to_minutes("06:30") == 390.0
    assert parse_time_to_minutes("00:00") == 0.0
    assert parse_time_to_minutes(datetime.time(7, 15)) == 435.0

    stops = [
        {"arrival_time": "06:00"},
        {"arrival_time": "06:30"},
        {"arrival_time": "07:15"},
    ]
    duration = calculate_stops_duration_minutes(stops)
    assert duration == 75.0  # 07:15 - 06:00 = 75 phút
