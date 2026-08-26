from typing import List, Dict, Any
from app.services.student_routing import config


class EvaluationResult:
    """
    Kết quả lượng giá chi tiết của một giải pháp hoặc một route đơn lẻ.
    """
    def __init__(
        self,
        total_distance: float,
        total_travel_time: float,
        total_early_arrival: float,
        total_late_arrival: float,
        capacity_violations: int,
        ride_time_violations: int,
        early_penalty: float,
        late_penalty: float,
        capacity_penalty: float,
        ride_time_penalty: float,
        total_penalty: float,
        objective_value: float
    ):
        self.total_distance = round(total_distance, 2)
        self.total_travel_time = round(total_travel_time, 2)
        self.total_early_arrival = round(total_early_arrival, 2)
        self.total_late_arrival = round(total_late_arrival, 2)
        self.capacity_violations = capacity_violations
        self.ride_time_violations = ride_time_violations
        self.early_penalty = round(early_penalty, 2)
        self.late_penalty = round(late_penalty, 2)
        self.capacity_penalty = round(capacity_penalty, 2)
        self.ride_time_penalty = round(ride_time_penalty, 2)
        self.total_penalty = round(total_penalty, 2)
        self.objective_value = round(objective_value, 2)

    def is_feasible(self) -> bool:
        """Kiểm tra giải pháp có hoàn toàn khả thi không (không vi phạm HARD constraints)"""
        return self.capacity_violations == 0 and self.ride_time_violations == 0

    def __repr__(self) -> str:
        return (f"EvaluationResult(dist={self.total_distance}km, "
                f"early={self.total_early_arrival}m, late={self.total_late_arrival}m, "
                f"cap_viol={self.capacity_violations}, ride_viol={self.ride_time_violations}, "
                f"penalty={self.total_penalty}, objective={self.objective_value})")


class SolutionEvaluator:
    """
    Tách biệt logic lượng giá giải pháp độc lập khỏi Sweep & Tabu Search.
    Nhiệm vụ: Tính toán chính xác các chỉ số: Total Distance, Travel Time, Early/Late Arrival,
    Capacity feasibility, Ride Time feasibility, Total Penalty và Objective Value.
    """

    def __init__(
        self,
        distance_weight: float = config.DISTANCE_WEIGHT,
        early_weight: float = config.EARLY_PENALTY_WEIGHT,
        late_weight: float = config.LATE_PENALTY_WEIGHT,
        capacity_penalty_weight: float = config.CAPACITY_PENALTY_WEIGHT,
        ride_time_penalty_weight: float = config.RIDE_TIME_PENALTY_WEIGHT,
        max_ride_time_minutes: float = config.MAX_RIDE_TIME_MINUTES
    ):
        self.distance_weight = distance_weight
        self.early_weight = early_weight
        self.late_weight = late_weight
        self.capacity_penalty_weight = capacity_penalty_weight
        self.ride_time_penalty_weight = ride_time_penalty_weight
        self.max_ride_time_minutes = max_ride_time_minutes

    @staticmethod
    def _parse_time_to_minutes(time_str: str) -> float:
        """Chuyển chuỗi HH:MM sang tổng số phút trong ngày"""
        try:
            h, m = map(int, time_str.split(":"))
            return float(h * 60 + m)
        except Exception:
            return 0.0

    def evaluate_route(
        self,
        stops: List[Dict[str, Any]],
        depot: Dict[str, Any],
        distance_matrix: List[List[float]],
        travel_time_matrix: List[List[float]],
        point_index_map: Dict[str, int],
        vehicle_capacity: int = config.VEHICLE_CAPACITY,
        departure_time_mins: float = 330.0  # Mặc định 05:30 (330 phút)
    ) -> EvaluationResult:
        """
        Lượng giá 1 route đơn lẻ (danh sách trạm + depot).
        Ride Time của trạm i = ArrivalTime_i - departure_time_mins.
        """
        if not stops:
            return EvaluationResult(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        total_distance = 0.0
        total_travel_time = 0.0
        total_early = 0.0
        total_late = 0.0
        capacity_violations = 0
        ride_time_violations = 0

        curr_load = 0
        current_time = departure_time_mins
        prev_idx = point_index_map[depot["id"]]

        for stop in stops:
            curr_idx = point_index_map[stop["id"]]

            # 1. Khoảng cách & thời gian di chuyển
            dist = distance_matrix[prev_idx][curr_idx]
            ttime = travel_time_matrix[prev_idx][curr_idx]

            total_distance += dist
            total_travel_time += ttime
            current_time += ttime

            # 2. Capacity Check
            demand = stop.get("demand", stop.get("pickup_student_count", 1))
            curr_load += demand
            if curr_load > vehicle_capacity:
                capacity_violations += 1

            # 3. Ride Time Check (Hard Constraint = 45 mins)
            # RideTime_i = ArrivalTime_i - RouteDepartureTime
            ride_time = current_time - departure_time_mins
            if ride_time > self.max_ride_time_minutes:
                ride_time_violations += 1

            # 4. Soft Time Window Check
            tw_start_str = stop.get("time_window_start")
            tw_end_str = stop.get("time_window_end")

            if tw_start_str and tw_end_str:
                tw_start = self._parse_time_to_minutes(tw_start_str)
                tw_end = self._parse_time_to_minutes(tw_end_str)

                if current_time < tw_start:
                    early = tw_start - current_time
                    total_early += early
                    # Đợi cho đến giờ tw_start trước khi rời trạm
                    current_time = tw_start
                elif current_time > tw_end:
                    late = current_time - tw_end
                    total_late += late

            prev_idx = curr_idx

        # Trở về Depot/Trường
        depot_idx = point_index_map[depot["id"]]
        total_distance += distance_matrix[prev_idx][depot_idx]
        total_travel_time += travel_time_matrix[prev_idx][depot_idx]

        # Tính toán Penalties
        early_penalty = total_early * self.early_weight
        late_penalty = total_late * self.late_weight
        cap_penalty = capacity_violations * self.capacity_penalty_weight
        ride_penalty = ride_time_violations * self.ride_time_penalty_weight

        total_penalty = early_penalty + late_penalty + cap_penalty + ride_penalty
        objective_value = (total_distance * self.distance_weight) + total_penalty

        return EvaluationResult(
            total_distance=total_distance,
            total_travel_time=total_travel_time,
            total_early_arrival=total_early,
            total_late_arrival=total_late,
            capacity_violations=capacity_violations,
            ride_time_violations=ride_time_violations,
            early_penalty=early_penalty,
            late_penalty=late_penalty,
            capacity_penalty=cap_penalty,
            ride_time_penalty=ride_penalty,
            total_penalty=total_penalty,
            objective_value=objective_value
        )

    def evaluate_solution(
        self,
        routes: List[List[Dict[str, Any]]],
        depot: Dict[str, Any],
        distance_matrix: List[List[float]],
        travel_time_matrix: List[List[float]],
        point_index_map: Dict[str, int],
        vehicle_capacities: List[int] = None,
        departure_time_mins: float = 330.0
    ) -> EvaluationResult:
        """
        Lượng giá toàn bộ giải pháp (tập hợp nhiều routes của các xe).
        """
        if not routes:
            return EvaluationResult(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        tot_dist = 0.0
        tot_ttime = 0.0
        tot_early = 0.0
        tot_late = 0.0
        tot_cap_viol = 0
        tot_ride_viol = 0

        for r_idx, route_stops in enumerate(routes):
            cap = vehicle_capacities[r_idx] if vehicle_capacities and r_idx < len(vehicle_capacities) else config.VEHICLE_CAPACITY
            res = self.evaluate_route(
                stops=route_stops,
                depot=depot,
                distance_matrix=distance_matrix,
                travel_time_matrix=travel_time_matrix,
                point_index_map=point_index_map,
                vehicle_capacity=cap,
                departure_time_mins=departure_time_mins
            )
            tot_dist += res.total_distance
            tot_ttime += res.total_travel_time
            tot_early += res.total_early_arrival
            tot_late += res.total_late_arrival
            tot_cap_viol += res.capacity_violations
            tot_ride_viol += res.ride_time_violations

        early_penalty = tot_early * self.early_weight
        late_penalty = tot_late * self.late_weight
        cap_penalty = tot_cap_viol * self.capacity_penalty_weight
        ride_penalty = tot_ride_viol * self.ride_time_penalty_weight

        total_penalty = early_penalty + late_penalty + cap_penalty + ride_penalty
        objective_value = (tot_dist * self.distance_weight) + total_penalty

        return EvaluationResult(
            total_distance=tot_dist,
            total_travel_time=tot_ttime,
            total_early_arrival=tot_early,
            total_late_arrival=tot_late,
            capacity_violations=tot_cap_viol,
            ride_time_violations=tot_ride_viol,
            early_penalty=early_penalty,
            late_penalty=late_penalty,
            capacity_penalty=cap_penalty,
            ride_time_penalty=ride_penalty,
            total_penalty=total_penalty,
            objective_value=objective_value
        )
