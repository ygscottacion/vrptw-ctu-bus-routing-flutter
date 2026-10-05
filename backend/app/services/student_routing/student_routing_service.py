from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from app.services.student_routing import config
from app.services.student_routing.schemas import (
    SchoolConfig, Vehicle, Station, OptimizationOptions,
    OptimizationResponse, PartialResult, InfeasibleStation
)
from app.services.student_routing.helpers.distance_matrix import (
    GoongDistanceMatrixProvider, OSRMWithFallbackProvider, haversine_distance, DistanceMatrixProvider
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
      3. Distance / Travel Time Matrix Construction (Goong Maps API with 3s Timeout & Fallback)
      4. Sweep Algorithm (Khởi tạo Lời giải Ban đầu)
      5. Tabu Search Optimization (Tối ưu Lộ trình & VRPTW)
      6. Formatting Response JSON
    """

    def __init__(self, distance_provider: DistanceMatrixProvider = None):
        self.distance_provider = distance_provider or GoongDistanceMatrixProvider()

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

        # ── 1. Validate Basic Inputs & MVP Data Bounds ───────────────────────
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

        if len(stations) > config.MAX_STATIONS_PER_JOB:
            return self.response_formatter.format_error(
                options.session_id, options.trip_type, "MVP_DATA_LIMIT_EXCEEDED",
                f"Số trạm đón ({len(stations)}) vượt quá giới hạn MVP ({config.MAX_STATIONS_PER_JOB})"
            )

        if len(vehicles) > config.MAX_VEHICLES_PER_JOB:
            return self.response_formatter.format_error(
                options.session_id, options.trip_type, "MVP_DATA_LIMIT_EXCEEDED",
                f"Số lượng xe ({len(vehicles)}) vượt quá giới hạn MVP ({config.MAX_VEHICLES_PER_JOB})"
            )

        school_loc = {"lat": school_config.location.lat, "lng": school_config.location.lng}

        # Total requested students
        total_students_requested = sum(
            st.pickup_student_count if options.trip_type == "PICKUP" else st.dropoff_student_count
            for st in stations
        )

        if total_students_requested > config.MAX_BOOKINGS_PER_JOB:
            return self.response_formatter.format_error(
                options.session_id, options.trip_type, "MVP_DATA_LIMIT_EXCEEDED",
                f"Tổng số SV ({total_students_requested}) vượt quá giới hạn MVP ({config.MAX_BOOKINGS_PER_JOB})"
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

        session_info = config.PICKUP_SESSIONS.get(options.session_id.value, {})
        class_deadline_mins = None
        if options.trip_type.value == "PICKUP" and session_info.get("school_start"):
            class_hour, class_minute = map(int, session_info["school_start"].split(":"))
            class_deadline_mins = class_hour * 60 + class_minute - config.CLASS_ARRIVAL_BUFFER_MINUTES
            # Dynamic per-station pickup window: [latest - 45m, latest].
            # latest accounts for the direct road travel time from that station to school.
            school_index = point_index_map["SCHOOL"]
            for station in feasible_stations:
                station_index = point_index_map[station.id]
                return_drive_mins = float(ttime_matrix[station_index][school_index])
                latest_pickup = class_deadline_mins - return_drive_mins - config.PICKUP_SERVICE_MINUTES
                earliest_pickup = latest_pickup - config.STATION_TIME_WINDOW_MINUTES
                station.time_window_start = f"{int(earliest_pickup // 60) % 24:02d}:{int(earliest_pickup % 60):02d}"
                station.time_window_end = f"{int(latest_pickup // 60) % 24:02d}:{int(latest_pickup % 60):02d}"

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
        try:
            initial_routes = self.sweep_clusterer.create_initial_routes(
                depot=depot_dict,
                stations=station_dicts,
                vehicles=vehicle_dicts
            )
        except RuntimeError as exc:
            if "INSUFFICIENT_VEHICLES" in str(exc):
                return self.response_formatter.format_error(
                    options.session_id, options.trip_type, "INSUFFICIENT_VEHICLES",
                    f"Số lượng xe khả dụng ({len(vehicles)}) không đủ để phục vụ tất cả các trạm"
                )
            raise

        # Departure time calculation
        session_info = config.PICKUP_SESSIONS.get(options.session_id.value, {})
        depart_str = session_info.get("vehicle_depart_latest", "05:30")
        departure_mins = self._parse_time_to_minutes(depart_str)

        vehicle_capacities = [v.capacity for v in vehicles]

        # ── 5. Route Optimization via Tabu Search (With Fallback to Sweep) ───
        try:
            optimized_routes, best_eval = self.tabu_optimizer.optimize(
                initial_routes=initial_routes,
                depot=depot_dict,
                distance_matrix=dist_matrix,
                travel_time_matrix=ttime_matrix,
                point_index_map=point_index_map,
                vehicle_capacities=vehicle_capacities,
                departure_time_mins=departure_mins,
                arrival_deadline_mins=class_deadline_mins,
                trip_type=options.trip_type.value
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                f"Tabu Search optimization failed: {exc}. Falling back to Sweep initial routes."
            )
            optimized_routes = initial_routes
            best_eval = self.evaluator.evaluate_solution(
                optimized_routes,
                depot_dict,
                dist_matrix,
                ttime_matrix,
                point_index_map,
                vehicle_capacities,
                departure_mins,
                class_deadline_mins,
                options.trip_type.value,
            )

        if len(optimized_routes) > len(vehicles):
            return self.response_formatter.format_error(
                options.session_id,
                options.trip_type,
                "INSUFFICIENT_VEHICLES",
                f"Cần {len(optimized_routes)} xe để phục vụ các trạm nhưng hiện chỉ có {len(vehicles)} xe.",
            )

        if not best_eval.is_feasible():
            return self.response_formatter.format_error(
                options.session_id,
                options.trip_type,
                "INFEASIBLE_TIME_CONSTRAINTS",
                "Không tìm được phương án thỏa time window, giờ đến trường và giới hạn 90 phút di chuyển.",
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
