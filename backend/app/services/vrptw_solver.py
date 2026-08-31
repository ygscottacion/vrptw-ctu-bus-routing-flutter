from typing import List, Dict, Any, Optional
from app.services.student_routing.schemas import (
    SchoolConfig, Vehicle, Station, OptimizationOptions, SessionId, TripType, LocationSchema
)
from app.services.student_routing.student_routing_service import StudentRoutingService
from app.services.student_routing.helpers.distance_matrix import StaticDistanceMatrixProvider
from app.services.student_routing import config as routing_config


class VRPTWSolverService:
    """
    Adapter Service tổng hợp VRPTW Solver Pipeline:
    Kết nối API Backend v1 với StudentRoutingService (Sweep Algorithm + Tabu Search Optimization).

    Parameters
    ----------
    use_static_matrix : bool, default False
        Nếu True, bỏ qua OSRM và dùng StaticDistanceMatrixProvider (Haversine + tốc độ trung bình).
        Dùng trong môi trường test để tránh phụ thuộc network và đảm bảo tốc độ ổn định.
    """

    def __init__(self, use_static_matrix: bool = False):
        self.routing_service = StudentRoutingService()
        self._use_static_matrix = use_static_matrix
        if use_static_matrix:
            # Monkey-patch distance provider sang static để bypass OSRM
            self.routing_service.distance_provider = StaticDistanceMatrixProvider()

    def solve(
        self,
        depot: Dict[str, Any],
        locations: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        session_id: SessionId = SessionId.MORNING_1,
        trip_type: TripType = TripType.PICKUP,
        tabu_max_iterations: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        # Cho phép override Tabu iterations (dùng trong test để giảm thời gian)
        if tabu_max_iterations is not None:
            self.routing_service.tabu_optimizer.max_iterations = tabu_max_iterations
        school_lat = depot.get("latitude", depot.get("lat", 10.0302))
        school_lng = depot.get("longitude", depot.get("lng", 105.7721))

        school_cfg = SchoolConfig(
            school_id="depot",
            school_name=depot.get("name", "Trường Đại học Cần Thơ"),
            location=LocationSchema(lat=school_lat, lng=school_lng)
        )

        vehicle_models = [
            Vehicle(
                id=str(v["id"]),
                capacity=v.get("capacity", 45)
            ) for v in vehicles
        ]

        # The public solver contract intentionally contains no persistence IDs.
        # It always emits deterministic technical keys owned by this solve call.
        station_models = []
        for idx, loc in enumerate(locations):
            st_lat = loc.get("latitude", loc.get("lat", 10.03))
            st_lng = loc.get("longitude", loc.get("lng", 105.77))
            demand = loc.get("demand", loc.get("pickup_student_count", 1))

            node_key = f"location_{idx}"
            station_models.append(Station(
                id=node_key,
                name=loc.get("name", f"Trạm #{node_key}"),
                location=LocationSchema(lat=st_lat, lng=st_lng),
                time_window_start=loc.get("time_window_start", "06:00"),
                time_window_end=loc.get("time_window_end", "06:30"),
                pickup_student_count=demand,
                dropoff_student_count=demand
            ))

        options = OptimizationOptions(
            session_id=session_id,
            trip_type=trip_type
        )

        response = self.routing_service.optimize_routes(
            school_config=school_cfg,
            vehicles=vehicle_models,
            stations=station_models,
            options=options
        )

        final_routes = []
        if response.data and response.data.routes:
            for route_obj in response.data.routes:
                ordered_stops = []
                for s in route_obj.stops:
                    # Trả về node key kỹ thuật (depot, location_0, ...)
                    station_node_key = "depot" if s.station_id == "SCHOOL" or s.station_id == "depot" else s.station_id
                    ordered_stops.append({
                        "id": station_node_key,
                        "name": s.station_name,
                        "arrival_time": s.arrival_time,
                        "departure_time": s.departure_time,
                        "demand": s.students_picked
                    })

                final_routes.append({
                    "vehicle_id": route_obj.vehicle_id,
                    "total_demand": route_obj.total_students,
                    "total_distance_km": route_obj.total_distance_km,
                    "ordered_stops": ordered_stops
                })

        return final_routes
