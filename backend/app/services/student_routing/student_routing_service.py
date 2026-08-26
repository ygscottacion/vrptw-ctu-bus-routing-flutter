from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from app.services.student_routing import config
from app.services.student_routing.schemas import (
    SchoolConfig, Vehicle, Station, OptimizationOptions,
    OptimizationResponse, PartialResult, InfeasibleStation
)
from app.services.student_routing.helpers.distance_matrix import (
    OSRMWithFallbackProvider, haversine_distance
)
from app.services.student_routing.core.evaluator import SolutionEvaluator
from app.services.student_routing.core.sweep_clustering import SweepClusterer
from app.services.student_routing.core.tabu_optimizer import TabuSearchOptimizer
from app.services.student_routing.helpers.response_formatter import ResponseFormatter


class StudentRoutingService:
    """
    Orchestrator chính cho Service Tối ưu Lộ trình Xe buýt Sinh viên (CTU Student Routing).
    Pipeline thực thi:
      1. Validation & Service Radius Check (<= 10km)
      2. Ride Time Feasibility Preprocessing (Reject individual station if > 45 mins)
      3. Distance / Travel Time Matrix Construction (OSRM with 3s Timeout & Fallback)
      4. Sweep Algorithm (Khởi tạo Lời giải Ban đầu)
      5. Tabu Search Optimization (Tối ưu Lộ trình & VRPTW)
      6. Formatting Response JSON
    """

    def __init__(self):
        self.distance_provider = OSRMWithFallbackProvider()
        self.evaluator = SolutionEvaluator()
        self.sweep_clusterer = SweepClusterer()
        self.tabu_optimizer = TabuSearchOptimizer(evaluator=self.evaluator)
        self.response_formatter = ResponseFormatter()

    @staticmethod
    def _parse_time_to_minutes(time_str: str) -> float:
        try:
            h, m = map(int, time_str.split(":"))
            return float(h * 60 + m)
        except Exception:
            return 330.0  # Default 05:30

    def optimize_routes(
        self,
        school_config: SchoolConfig,
        vehicles: List[Vehicle],
        stations: List[Station],
        options: OptimizationOptions
    ) -> OptimizationResponse:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # ── 1. Validate Basic Inputs ──────────────────────────────────────────
        if not vehicles:
            return self.response_formatter.format_error(
                options.session_id, options.trip_type, "NO_VEHICLE_AVAILABLE",
                "Không có xe khả dụng cho ca này"
            )

        if not stations:
            return self.response_formatter.format_error(
                options.session_id, options.trip_type, "INVALID_INPUT",
                "Danh sách trạm đón không được để trống"
            )

        school_loc = {"lat": school_config.location.lat, "lng": school_config.location.lng}

        # Total requested students
        total_students_requested = sum(
            st.pickup_student_count if options.trip_type == "PICKUP" else st.dropoff_student_count
            for st in stations
        )

        total_capacity = sum(v.capacity for v in vehicles)
        if total_students_requested > total_capacity:
            return self.response_formatter.format_error(
                options.session_id, options.trip_type, "CAPACITY_EXCEEDED",
                f"Tổng số SV ({total_students_requested}) vượt quá tổng sức chứa của xe ({total_capacity})"
            )

        # ── 2. Preprocessing: Service Radius & Ride Time Feasibility Check ───
        feasible_stations: List[Station] = []
        infeasible_list: List[InfeasibleStation] = []

        speed_kmh = config.SPEED_NORMAL_KMH
        max_radius = school_config.service_radius_km or config.MAX_SERVICE_RADIUS_KM
        max_ride_time = school_config.max_ride_time_minutes or config.MAX_RIDE_TIME_MINUTES

        for st in stations:
            # Check 1: Radius <= 10 km
            dist_to_school = haversine_distance(
                school_loc["lat"], school_loc["lng"],
                st.location.lat, st.location.lng
            )
            if dist_to_school > max_radius:
                infeasible_list.append(InfeasibleStation(
                    station_id=st.id,
                    reason="STATION_OUT_OF_RADIUS",
                    detail=f"Trạm nằm ngoài bán kính {max_radius}km (Khoảng cách: {round(dist_to_school, 2)}km)"
                ))
                continue

            # Check 2: Direct Ride Time Check (Hard Constraint <= 45 mins)
            direct_travel_time_min = (dist_to_school / speed_kmh) * 60.0
            if direct_travel_time_min > max_ride_time:
                infeasible_list.append(InfeasibleStation(
                    station_id=st.id,
                    reason="MAX_RIDE_TIME_EXCEEDED",
                    detail=f"Thời gian ngồi xe ước tính {round(direct_travel_time_min, 1)} phút, vượt giới hạn {max_ride_time} phút"
                ))
                continue

            feasible_stations.append(st)

        if not feasible_stations:
            return self.response_formatter.format_error(
                options.session_id, options.trip_type, "INFEASIBLE_ROUTE",
                "Tất cả các trạm đều vi phạm bán kính hoặc Max Ride Time",
                partial_result=PartialResult(
                    feasible_stations=[],
                    infeasible_stations=infeasible_list
                )
            )

        # ── 3. Distance & Travel Time Matrix Construction ─────────────────────
        all_points = [{"lat": school_loc["lat"], "lng": school_loc["lng"]}]
        point_index_map = {"SCHOOL": 0}

        for idx, st in enumerate(feasible_stations, start=1):
            all_points.append({"lat": st.location.lat, "lng": st.location.lng})
            point_index_map[st.id] = idx

        dist_matrix, ttime_matrix, source_used = self.distance_provider.get_matrix(
            all_points, time_str_or_session=options.session_id.value
        )

        depot_dict = {"id": "SCHOOL", "lat": school_loc["lat"], "lng": school_loc["lng"]}
        station_dicts = []
        for st in feasible_stations:
            count = st.pickup_student_count if options.trip_type == "PICKUP" else st.dropoff_student_count
            station_dicts.append({
                "id": st.id,
                "name": st.name,
                "lat": st.location.lat,
                "lng": st.location.lng,
                "demand": count,
                "pickup_student_count": st.pickup_student_count,
                "dropoff_student_count": st.dropoff_student_count,
                "time_window_start": st.time_window_start,
                "time_window_end": st.time_window_end
            })

        vehicle_dicts = [{"id": v.id, "capacity": v.capacity} for v in vehicles]

        # ── 4. Initial Solution via Sweep Algorithm ───────────────────────────
        initial_routes = self.sweep_clusterer.create_initial_routes(
            depot=depot_dict,
            stations=station_dicts,
            vehicles=vehicle_dicts
        )

        # Departure time calculation
        session_info = config.PICKUP_SESSIONS.get(options.session_id.value, {})
        depart_str = session_info.get("vehicle_depart_latest", "05:30")
        departure_mins = self._parse_time_to_minutes(depart_str)

        vehicle_capacities = [v.capacity for v in vehicles]

        # ── 5. Route Optimization via Tabu Search ──────────────────────────────
        optimized_routes, best_eval = self.tabu_optimizer.optimize(
            initial_routes=initial_routes,
            depot=depot_dict,
            distance_matrix=dist_matrix,
            travel_time_matrix=ttime_matrix,
            point_index_map=point_index_map,
            vehicle_capacities=vehicle_capacities,
            departure_time_mins=departure_mins
        )

        # ── 6. Response Formatting ─────────────────────────────────────────────
        return self.response_formatter.format_success(
            session_id=options.session_id,
            trip_type=options.trip_type,
            routes_raw=optimized_routes,
            vehicles=vehicles,
            depot=depot_dict,
            dist_matrix=dist_matrix,
            ttime_matrix=ttime_matrix,
            point_index_map=point_index_map,
            departure_mins=departure_mins,
            total_students_requested=total_students_requested,
            infeasible_stations=infeasible_list,
            optimized_at=now_str
        )
