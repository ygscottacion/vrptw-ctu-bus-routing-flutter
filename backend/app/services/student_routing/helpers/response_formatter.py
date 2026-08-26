from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.services.student_routing.schemas import (
    SessionId, TripType, OptimizationResponse, RouteDataPayload,
    RouteSummary, Route, Stop, PartialResult, InfeasibleStation, Vehicle
)


class ResponseFormatter:
    """
    Format kết quả đầu ra JSON API chuẩn hóa cho Student Routing Service.
    """

    @staticmethod
    def _minutes_to_time_str(minutes_float: float) -> str:
        mins = int(round(minutes_float)) % (24 * 60)
        h = mins // 60
        m = mins % 60
        return f"{h:02d}:{m:02d}"

    def format_success(
        self,
        session_id: SessionId,
        trip_type: TripType,
        routes_raw: List[List[Dict[str, Any]]],
        vehicles: List[Vehicle],
        depot: Dict[str, Any],
        dist_matrix: List[List[float]],
        ttime_matrix: List[List[float]],
        point_index_map: Dict[str, int],
        departure_mins: float,
        total_students_requested: int,
        infeasible_stations: List[InfeasibleStation],
        optimized_at: str
    ) -> OptimizationResponse:

        formatted_routes: List[Route] = []
        total_students_served = 0
        total_distance_sum = 0.0
        max_arrival_mins = departure_mins

        for r_idx, route_stops in enumerate(routes_raw):
            if not route_stops:
                continue

            vehicle = vehicles[r_idx] if r_idx < len(vehicles) else vehicles[0]
            route_id = f"ROUTE-{trip_type.value[:2]}-{vehicle.id}-{session_id.value}"

            stops_payload: List[Stop] = []
            curr_load = 0
            curr_time = departure_mins
            prev_idx = point_index_map[depot["id"]]
            route_dist = 0.0

            for seq, stop_dict in enumerate(route_stops, start=1):
                curr_idx = point_index_map[stop_dict["id"]]

                dist = dist_matrix[prev_idx][curr_idx]
                ttime = ttime_matrix[prev_idx][curr_idx]

                route_dist += dist
                curr_time += ttime
                arr_time_str = self._minutes_to_time_str(curr_time)

                picked = stop_dict.get("pickup_student_count", stop_dict.get("demand", 0))
                dropped = stop_dict.get("dropoff_student_count", 0)

                if trip_type == TripType.PICKUP:
                    curr_load += picked
                else:
                    curr_load -= dropped

                # Soft TW check for stop payload
                within_tw = True
                tw_start = stop_dict.get("time_window_start")
                tw_end = stop_dict.get("time_window_end")
                if tw_start and tw_end:
                    h1, m1 = map(int, tw_start.split(":"))
                    h2, m2 = map(int, tw_end.split(":"))
                    t1 = h1 * 60 + m1
                    t2 = h2 * 60 + m2
                    if curr_time < t1:
                        curr_time = float(t1)
                    elif curr_time > t2:
                        within_tw = False

                dep_time_str = self._minutes_to_time_str(curr_time)

                stops_payload.append(Stop(
                    sequence=seq,
                    station_id=stop_dict["id"],
                    station_name=stop_dict.get("name", stop_dict["id"]),
                    arrival_time=arr_time_str,
                    departure_time=dep_time_str,
                    students_picked=picked if trip_type == TripType.PICKUP else 0,
                    students_dropped=dropped if trip_type == TripType.DROPOFF else 0,
                    current_load=curr_load,
                    within_time_window=within_tw
                ))

                prev_idx = curr_idx

            # Arrive at school / depot
            depot_idx = point_index_map[depot["id"]]
            route_dist += dist_matrix[prev_idx][depot_idx]
            curr_time += ttime_matrix[prev_idx][depot_idx]
            school_arrival_str = self._minutes_to_time_str(curr_time)

            if curr_time > max_arrival_mins:
                max_arrival_mins = curr_time

            # Final stop at school
            stops_payload.append(Stop(
                sequence=len(stops_payload) + 1,
                station_id="SCHOOL",
                station_name="Trường Đại học Cần Thơ",
                arrival_time=school_arrival_str,
                departure_time=None,
                students_picked=0,
                students_dropped=0,
                current_load=0,
                within_time_window=True
            ))

            route_students = sum(s.students_picked if trip_type == TripType.PICKUP else s.students_dropped for s in stops_payload)
            total_students_served += route_students
            total_distance_sum += route_dist

            formatted_routes.append(Route(
                route_id=route_id,
                trip_type=trip_type,
                session_id=session_id,
                vehicle_id=vehicle.id,
                departure_time=self._minutes_to_time_str(departure_mins),
                arrival_at_school=school_arrival_str,
                total_students=route_students,
                total_distance_km=round(route_dist, 2),
                stops=stops_payload
            ))

        status_str = "PARTIAL_SUCCESS" if infeasible_stations else "SUCCESS"

        partial_res = PartialResult(
            feasible_stations=[st["id"] for r in routes_raw for st in r],
            infeasible_stations=infeasible_stations
        ) if infeasible_stations else None

        summary = RouteSummary(
            total_routes=len(formatted_routes),
            total_vehicles_used=len(formatted_routes),
            total_students_served=total_students_served,
            total_students_requested=total_students_requested,
            total_distance_km=round(total_distance_sum, 2),
            school_arrival_time=self._minutes_to_time_str(max_arrival_mins)
        )

        return OptimizationResponse(
            status=status_str,
            session_id=session_id,
            trip_type=trip_type,
            optimized_at=optimized_at,
            data=RouteDataPayload(summary=summary, routes=formatted_routes),
            partial_result=partial_res
        )

    def format_error(
        self,
        session_id: SessionId,
        trip_type: TripType,
        error_code: str,
        error_message: str,
        partial_result: Optional[PartialResult] = None
    ) -> OptimizationResponse:
        return OptimizationResponse(
            status="ERROR",
            session_id=session_id,
            trip_type=trip_type,
            optimized_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            error_code=error_code,
            error_message=error_message,
            partial_result=partial_result
        )
