import re
from typing import Any, Dict, List, Optional, Tuple, Union


class RoutingValidationError(Exception):
    """Base exception for routing input validation errors."""
    pass


class NoDemandError(RoutingValidationError):
    """Raised when there are no tickets/bookings to schedule."""
    pass


class NoVehicleAvailableError(RoutingValidationError):
    """Raised when no active vehicles are available."""
    pass


class InsufficientCapacityError(RoutingValidationError):
    """Raised when total student demand exceeds total fleet capacity."""
    pass


class InvalidStationError(RoutingValidationError):
    """Raised when station coordinates or time windows are invalid."""
    pass


class DemandAdapter:
    """
    Adapter and validator that transforms raw Ticket/Booking records, Locations,
    and Vehicles into structured demand inputs conforming to the VRPTW contract.
    """

    TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

    @classmethod
    def aggregate_tickets_to_station_demands(
        cls, tickets: List[Any]
    ) -> Dict[Union[int, str], int]:
        """
        Aggregates unassigned tickets by their pickup_location_id (or station_id).
        Supports both ORM Ticket models and dictionary structures.
        """
        demands: Dict[Union[int, str], int] = {}
        for ticket in tickets:
            if isinstance(ticket, dict):
                loc_id = ticket.get("pickup_location_id") or ticket.get("station_id") or ticket.get("location_id")
            else:
                loc_id = getattr(ticket, "pickup_location_id", None) or getattr(ticket, "station_id", None)

            if loc_id is not None:
                demands[loc_id] = demands.get(loc_id, 0) + 1

        return demands

    @classmethod
    def validate_time_window(cls, start: Optional[str], end: Optional[str]) -> bool:
        """
        Validates that time windows follow HH:MM format and start <= end.
        """
        if not start or not end:
            return True  # Optional / defaults apply
        if not cls.TIME_REGEX.match(start) or not cls.TIME_REGEX.match(end):
            return False
        return start <= end

    @classmethod
    def validate_inputs(
        cls,
        depot: Any,
        stations: List[Any],
        vehicles: List[Any],
        station_demands: Dict[Union[int, str], int],
    ) -> None:
        """
        Validates depot, stations, vehicles, and capacity requirements.
        Raises specific RoutingValidationError subclasses on invalid state.
        """
        # 1. Validate Depot
        if not depot:
            raise RoutingValidationError("Depot location not found or not provided.")

        depot_lat = depot.get("latitude") if isinstance(depot, dict) else getattr(depot, "latitude", None)
        depot_lng = depot.get("longitude") if isinstance(depot, dict) else getattr(depot, "longitude", None)

        if depot_lat is None or depot_lng is None or not (-90 <= depot_lat <= 90 and -180 <= depot_lng <= 180):
            raise RoutingValidationError(f"Invalid depot coordinates: lat={depot_lat}, lng={depot_lng}")

        # 2. Validate Demands
        total_demand = sum(station_demands.values())
        if total_demand <= 0:
            raise NoDemandError("Không có vé lượt đã chốt cho ca này (Total demand = 0).")

        # 3. Validate Vehicles
        if not vehicles:
            raise NoVehicleAvailableError("No vehicles available in system.")

        total_capacity = 0
        for v in vehicles:
            cap = v.get("capacity", 0) if isinstance(v, dict) else getattr(v, "capacity", 0)
            if cap <= 0:
                v_id = v.get("id") if isinstance(v, dict) else getattr(v, "id", "unknown")
                raise RoutingValidationError(f"Vehicle {v_id} has invalid non-positive capacity: {cap}")
            total_capacity += cap

        if total_demand > total_capacity:
            raise InsufficientCapacityError(
                f"Tổng số sinh viên đăng ký ({total_demand}) vượt quá tổng sức chứa của xe ({total_capacity})."
            )

        # 4. Validate Stations
        if not stations:
            raise InvalidStationError("No stations matching demand locations were found.")

        for st in stations:
            st_id = st.get("id") if isinstance(st, dict) else getattr(st, "id", None)
            st_lat = st.get("latitude") if isinstance(st, dict) else getattr(st, "latitude", None)
            st_lng = st.get("longitude") if isinstance(st, dict) else getattr(st, "longitude", None)

            if st_lat is None or st_lng is None or not (-90 <= st_lat <= 90 and -180 <= st_lng <= 180):
                raise InvalidStationError(f"Trạm {st_id} có tọa độ không hợp lệ: lat={st_lat}, lng={st_lng}")

            tw_start = st.get("time_window_start") if isinstance(st, dict) else getattr(st, "time_window_start", None)
            tw_end = st.get("time_window_end") if isinstance(st, dict) else getattr(st, "time_window_end", None)

            if isinstance(tw_start, str) and isinstance(tw_end, str):
                if not cls.validate_time_window(tw_start, tw_end):
                    raise InvalidStationError(
                        f"Trạm {st_id} có khung giờ không hợp lệ: start={tw_start}, end={tw_end}"
                    )

    @classmethod
    def build_solver_inputs(
        cls,
        depot: Any,
        stations: List[Any],
        vehicles: List[Any],
        station_demands: Dict[Union[int, str], int],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validates and constructs the clean dictionaries expected by VRPTWSolverService.solve.
        """
        cls.validate_inputs(depot, stations, vehicles, station_demands)

        depot_dict = {
            "id": depot.get("id") if isinstance(depot, dict) else getattr(depot, "id"),
            "name": depot.get("name", "Depot") if isinstance(depot, dict) else getattr(depot, "name", "Depot"),
            "latitude": depot.get("latitude") if isinstance(depot, dict) else getattr(depot, "latitude"),
            "longitude": depot.get("longitude") if isinstance(depot, dict) else getattr(depot, "longitude"),
        }

        locations_dict = []
        for loc in stations:
            loc_id = loc.get("id") if isinstance(loc, dict) else getattr(loc, "id")
            demand = station_demands.get(loc_id, 0)
            if demand > 0:
                tw_start = loc.get("time_window_start") if isinstance(loc, dict) else getattr(loc, "time_window_start", None)
                tw_end = loc.get("time_window_end") if isinstance(loc, dict) else getattr(loc, "time_window_end", None)

                locations_dict.append({
                    "id": loc_id,
                    "name": loc.get("name", f"Trạm {loc_id}") if isinstance(loc, dict) else getattr(loc, "name", f"Trạm {loc_id}"),
                    "latitude": loc.get("latitude") if isinstance(loc, dict) else getattr(loc, "latitude"),
                    "longitude": loc.get("longitude") if isinstance(loc, dict) else getattr(loc, "longitude"),
                    "demand": demand,
                    "pickup_student_count": demand,
                    "time_window_start": str(tw_start) if tw_start else "06:00",
                    "time_window_end": str(tw_end) if tw_end else "06:30",
                })

        vehicles_dict = []
        for v in vehicles:
            v_id = v.get("id") if isinstance(v, dict) else getattr(v, "id")
            plate = v.get("license_plate", f"BUS-{v_id}") if isinstance(v, dict) else getattr(v, "license_plate", f"BUS-{v_id}")
            cap = v.get("capacity", 20) if isinstance(v, dict) else getattr(v, "capacity", 20)
            vehicles_dict.append({
                "id": v_id,
                "license_plate": plate,
                "capacity": cap,
            })

        return depot_dict, locations_dict, vehicles_dict
