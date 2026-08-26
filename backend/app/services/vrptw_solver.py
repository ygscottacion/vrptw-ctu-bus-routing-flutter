from typing import List, Dict, Any
from app.services.student_routing.schemas import (
    SchoolConfig, Vehicle, Station, OptimizationOptions, SessionId, TripType, LocationSchema
)
from app.services.student_routing.student_routing_service import StudentRoutingService


class VRPTWSolverService:
    """
    Adapter Service tổng hợp VRPTW Solver Pipeline:
    Kết nối API Backend v1 với StudentRoutingService (Sweep Algorithm + Tabu Search Optimization).
    """

    def __init__(self):
        self.routing_service = StudentRoutingService()

    def solve(
        self,
        depot: Dict[str, Any],
        locations: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        session_id: SessionId = SessionId.MORNING_1,
        trip_type: TripType = TripType.PICKUP,
    ) -> List[Dict[str, Any]]:
        school_lat = depot.get("latitude", depot.get("lat", 10.0302))
        school_lng = depot.get("longitude", depot.get("lng", 105.7721))

        school_cfg = SchoolConfig(
            school_id=str(depot.get("id", "SCHOOL")),
            school_name=depot.get("name", "Trường Đại học Cần Thơ"),
            location=LocationSchema(lat=school_lat, lng=school_lng)
        )

        vehicle_models = [
            Vehicle(
                id=str(v["id"]),
                capacity=v.get("capacity", 45)
            ) for v in vehicles
        ]

        station_models = []
        for loc in locations:
            st_lat = loc.get("latitude", loc.get("lat", 10.03))
            st_lng = loc.get("longitude", loc.get("lng", 105.77))
            demand = loc.get("demand", loc.get("pickup_student_count", 1))

            station_models.append(Station(
                id=str(loc["id"]),
                name=loc.get("name", f"Trạm #{loc['id']}"),
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
                    if s.station_id == "SCHOOL":
                        continue
                    ordered_stops.append({
                        "id": s.station_id,
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
