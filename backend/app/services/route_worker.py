"""Persist VRPTW solver output safely using technical solver node keys."""
import datetime
import logging
import traceback
import uuid
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

from app.core.timezone import VN_TZ
from app.models.location import Location
from app.models.route import Route, RouteStatus, RouteStop
from app.models.route_job import RouteJob, RouteJobStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.vehicle import Vehicle
from app.services.student_routing.schemas import SessionId, TripType
from app.services.vrptw_solver import VRPTWSolverService

logger = logging.getLogger(__name__)


def _db_id(db: Session, value: uuid.UUID | str) -> uuid.UUID | str:
    """Bind UUIDs correctly for PostgreSQL and SQLite test schemas.

    Supabase/PostgreSQL receives UUID instances. SQLite tests may compile UUID
    columns to either VARCHAR or native UUID depending on their fixture.
    """
    parsed = uuid.UUID(str(value))
    # Some legacy SQLite tests replace the column type with String globally;
    # inspect the actual mapped column instead of treating every SQLite UUID as
    # text. Supabase/PostgreSQL always keeps PostgreSQLUUID.
    return parsed if isinstance(RouteJob.__table__.c.id.type, PostgreSQLUUID) else str(parsed)


class UnmappedSolverNodeError(Exception):
    """A solver key was not present in the worker-created UUID mapping."""
    error_code = "UNMAPPED_SOLVER_NODE"

    def __init__(self, node_key: str, route_job_id: str):
        self.node_key, self.route_job_id = node_key, route_job_id
        super().__init__(f"Solver node key {node_key!r} is not mapped for route job {route_job_id}.")


class RouteStopValidationError(Exception):
    def __init__(self, route_job_id: str, message: str, error_code: str = "ROUTE_STOP_VALIDATION_ERROR"):
        self.route_job_id, self.error_code = route_job_id, error_code
        super().__init__(message)


def _build_uuid_lookup(depot_loc_id: uuid.UUID, locations: Sequence[Location], location_dicts: Sequence[Mapping[str, Any]]) -> Mapping[str, uuid.UUID]:
    """Return immutable technical node-key -> database UUID mapping.

    ``location_N`` is canonical. Numeric node indexes are accepted only for
    backward-compatible solver responses; neither is parsed as a UUID.
    """
    if len(locations) != len(location_dicts):
        raise ValueError("locations and location_dicts must have the same length")
    lookup: Dict[str, uuid.UUID] = {"depot": uuid.UUID(str(depot_loc_id)), "SCHOOL": uuid.UUID(str(depot_loc_id))}
    for index, (location, data) in enumerate(zip(locations, location_dicts)):
        location_id = uuid.UUID(str(location.id))
        lookup[str(data.get("id", f"location_{index}"))] = location_id
        lookup[f"location_{index}"] = location_id
        lookup[str(index)] = location_id
    return MappingProxyType(lookup)


def _lookup_solver_node(uuid_lookup: Mapping[str, uuid.UUID], node_key: object, route_job_id: str) -> uuid.UUID:
    key = str(node_key)
    try:
        return uuid_lookup[key]
    except KeyError as exc:
        raise UnmappedSolverNodeError(key, route_job_id) from exc


def _parse_solver_time(value: object, service_date: datetime.date) -> datetime.datetime | None:
    if value in (None, ""):
        return None
    try:
        hour, minute = map(int, str(value).split(":"))
        return datetime.datetime.combine(service_date, datetime.time(hour=hour, minute=minute), tzinfo=VN_TZ).astimezone(datetime.timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid solver arrival_time {value!r}") from exc


def _validate_route_and_stops(job_id: str, created_routes: Sequence[Tuple[Route, Sequence[RouteStop], Sequence[Ticket]]], expected_tickets_count: int, depot_location_id: str) -> None:
    """Validate stops, assignments and passenger counts before SUCCEEDED."""
    if not created_routes:
        raise RouteStopValidationError(job_id, "Solver returned no routes.")
    assigned_ids: set[str] = set()
    actual_stops = 0
    for route, stops, tickets in created_routes:
        if len(stops) != len(tickets) + 1:
            raise RouteStopValidationError(job_id, f"Route {route.id} has {len(stops)} stops for {len(tickets)} tickets.", "ROUTE_STOP_COUNT_MISMATCH")
        if not stops or str(stops[0].location_id) != str(depot_location_id) or stops[0].stop_order != 1:
            raise RouteStopValidationError(job_id, f"Route {route.id} has no valid depot at stop 1.")
        if any(stop.stop_order != index + 1 for index, stop in enumerate(stops)):
            raise RouteStopValidationError(job_id, f"Route {route.id} has non-contiguous stop_order values.")
        pickup_ids = [str(stop.location_id) for stop in stops[1:]]
        ticket_location_ids = [str(ticket.pickup_location_id) for ticket in tickets]
        if len(pickup_ids) != len(set(pickup_ids)):
            raise RouteStopValidationError(job_id, f"Route {route.id} has duplicate pickup UUIDs.")
        if set(pickup_ids) != set(ticket_location_ids) or len(ticket_location_ids) != len(set(ticket_location_ids)):
            raise RouteStopValidationError(job_id, f"Route {route.id} stops and tickets are not one-to-one.", "ROUTE_STOP_COUNT_MISMATCH")
        if any(ticket.status != TicketStatus.ASSIGNED or ticket.route is not route for ticket in tickets):
            raise RouteStopValidationError(job_id, f"Route {route.id} contains an unassigned ticket.")
        if route.passenger_count != len(tickets):
            raise RouteStopValidationError(job_id, f"Route {route.id} passenger_count mismatch.")
        actual_stops += len(stops)
        assigned_ids.update(str(ticket.id) for ticket in tickets)
    if len(assigned_ids) != expected_tickets_count:
        raise RouteStopValidationError(job_id, f"Assigned {len(assigned_ids)} of {expected_tickets_count} tickets.", "ROUTE_STOP_COUNT_MISMATCH")
    if actual_stops != expected_tickets_count + len(created_routes):
        raise RouteStopValidationError(job_id, "Total stop count does not equal depot + assigned tickets.", "ROUTE_STOP_COUNT_MISMATCH")


def _record_failed_job(db: Session, job_id: uuid.UUID, error_code: str, message: str, stack_trace: str) -> None:
    """Persist failure in a new transaction after the write transaction rolls back."""
    with db.begin():
        job = db.query(RouteJob).filter(RouteJob.id == job_id).first()
        if job:
            job.status = RouteJobStatus.FAILED
            job.error_message = f"[{error_code}] {message}\n{stack_trace}"
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)


def run_route_job_worker(db: Session, job_id: uuid.UUID) -> RouteJob:
    """Create routes/stops, assign tickets and set SUCCEEDED in one transaction."""
    job_id_uuid = uuid.UUID(str(job_id))
    job_id_str = str(job_id_uuid)
    job_db_id = _db_id(db, job_id_uuid)
    job = db.query(RouteJob).filter(RouteJob.id == job_db_id).first()
    if not job:
        raise ValueError(f"Route job {job_id} does not exist.")
    if job.status == RouteJobStatus.SUCCEEDED:
        return job

    # A separate lifecycle commit is safe: no route, stop, ticket, or SUCCEEDED data exists yet.
    job.status = RouteJobStatus.RUNNING
    job.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    try:
        with db.begin():
            job = db.query(RouteJob).filter(RouteJob.id == job_db_id).with_for_update().one()
            depot_id = uuid.UUID(str(job.depot_location_id))
            depot = db.query(Location).filter(Location.id == _db_id(db, depot_id)).one_or_none()
            if not depot:
                raise ValueError(f"Depot {job.depot_location_id} does not exist.")
            tickets = db.query(Ticket).filter(Ticket.service_date == job.service_date, Ticket.session_id == job.session_id, Ticket.trip_type == job.trip_type, Ticket.status == TicketStatus.RESERVED).with_for_update().all()
            if not tickets:
                raise RouteStopValidationError(job_id_str, "No RESERVED tickets found.", "DATABASE_WRITE_FAILED")

            tickets_by_location: Dict[str, List[Ticket]] = {}
            for ticket in tickets:
                tickets_by_location.setdefault(str(ticket.pickup_location_id), []).append(ticket)
            location_ids = [_db_id(db, location_id) for location_id in tickets_by_location]
            locations = db.query(Location).filter(Location.id.in_(location_ids)).order_by(Location.id).all()
            if len(locations) != len(location_ids):
                raise ValueError("One or more pickup locations no longer exist.")
            location_dicts: List[Dict[str, Any]] = []
            for index, location in enumerate(locations):
                demand = len(tickets_by_location[str(location.id)])
                if demand != 1:
                    raise RouteStopValidationError(job_id_str, f"Pickup {location.id} has {demand} tickets but RouteStop is one-to-one.", "ROUTE_STOP_COUNT_MISMATCH")
                location_dicts.append({"id": f"location_{index}", "name": location.name, "latitude": location.latitude, "longitude": location.longitude, "demand": demand, "time_window_start": location.time_window_start.strftime("%H:%M") if location.time_window_start else "06:00", "time_window_end": location.time_window_end.strftime("%H:%M") if location.time_window_end else "07:30"})
            uuid_lookup = _build_uuid_lookup(depot_id, locations, location_dicts)

            vehicles = db.query(Vehicle).all()
            if not vehicles:
                raise ValueError("No vehicles available for route generation.")
            try:
                session_id, trip_type = SessionId(job.session_id), TripType(job.trip_type.upper())
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid job session/trip type: {job.session_id}/{job.trip_type}") from exc
            solved_routes = VRPTWSolverService().solve(
                depot={"id": "depot", "name": depot.name, "latitude": depot.latitude, "longitude": depot.longitude},
                locations=location_dicts,
                vehicles=[{"id": str(vehicle.id), "capacity": vehicle.capacity, "license_plate": vehicle.license_plate} for vehicle in vehicles],
                session_id=session_id, trip_type=trip_type,
            )
            if not solved_routes:
                raise RouteStopValidationError(job_id_str, "Solver found no feasible route.")

            created_routes: List[Tuple[Route, List[RouteStop], List[Ticket]]] = []
            assigned_ids: set[str] = set()
            for route_info in solved_routes:
                vehicle_id = route_info.get("vehicle_id")
                try:
                    vehicle_id = uuid.UUID(str(vehicle_id)) if vehicle_id else None
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Solver returned invalid vehicle UUID {vehicle_id!r}") from exc
                route_id = uuid.uuid4()
                route = Route(id=_db_id(db, route_id), route_job_id=job_db_id, service_date=job.service_date, session_id=job.session_id, trip_type=job.trip_type, vehicle_id=_db_id(db, vehicle_id) if vehicle_id else None, status=RouteStatus.PENDING, total_distance=float(route_info.get("total_distance_km", 0.0)))
                db.add(route)
                raw_stops = list(route_info.get("ordered_stops") or [])
                if not raw_stops or str(raw_stops[0].get("id")) not in {"depot", "SCHOOL"}:
                    raw_stops.insert(0, {"id": "depot", "arrival_time": "06:00"})
                # Solver may include SCHOOL again as a return leg. RouteStop is
                # the passenger pickup manifest, so persist exactly one depot.
                raw_stops = [stop for index, stop in enumerate(raw_stops) if index == 0 or str(stop.get("id")) not in {"depot", "SCHOOL"}]
                route_stops: List[RouteStop] = []
                route_tickets: List[Ticket] = []
                for stop_order, stop_data in enumerate(raw_stops, 1):
                    if "id" not in stop_data or stop_data["id"] in (None, ""):
                        raise RouteStopValidationError(job_id_str, f"Solver stop is missing id: {stop_data!r}")
                    node_key = str(stop_data["id"])
                    location_id = _lookup_solver_node(uuid_lookup, node_key, job_id_str)
                    route_stop = RouteStop(id=_db_id(db, uuid.uuid4()), route_id=route.id, location_id=_db_id(db, location_id), stop_order=stop_order, arrival_time=_parse_solver_time(stop_data.get("arrival_time"), job.service_date))
                    db.add(route_stop)
                    route_stops.append(route_stop)
                    if node_key not in {"depot", "SCHOOL"}:
                        matching = tickets_by_location.get(str(location_id), [])
                        if len(matching) != 1 or str(matching[0].id) in assigned_ids:
                            raise RouteStopValidationError(job_id_str, f"Node {node_key!r} maps to an invalid or duplicate ticket.")
                        ticket = matching[0]
                        ticket.route, ticket.status = route, TicketStatus.ASSIGNED
                        route_tickets.append(ticket)
                        assigned_ids.add(str(ticket.id))
                created_routes.append((route, route_stops, route_tickets))
            _validate_route_and_stops(job_id_str, created_routes, len(tickets), str(depot.id))
            job.status, job.error_message = RouteJobStatus.SUCCEEDED, None
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)
        logger.info("Route job %s succeeded with %s routes and %s tickets.", job_id, len(created_routes), len(tickets))
        return db.query(RouteJob).filter(RouteJob.id == job_db_id).one()
    except Exception as exc:
        db.rollback()
        stack_trace = traceback.format_exc()
        error_code = getattr(exc, "error_code", "DATABASE_WRITE_FAILED")
        logger.exception("Route job %s failed [%s]: %s", job_id, error_code, exc)
        try:
            _record_failed_job(db, job_db_id, error_code, str(exc), stack_trace)
        except Exception:
            db.rollback()
            logger.exception("Could not persist FAILED status for route job %s", job_id)
        raise
