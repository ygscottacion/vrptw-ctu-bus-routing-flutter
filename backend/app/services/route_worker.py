import uuid
import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.services.vrptw_solver import VRPTWSolverService
from app.services.student_routing.schemas import SessionId, TripType

from app.core.timezone import VN_TZ


def run_route_job_worker(db: Session, job_id: uuid.UUID) -> RouteJob:
    """
    Executes a route generation job atomically inside PostgreSQL.
    Claims job (queued -> running), runs VRPTW solver, persists routes, stops, and ticket assignments.
    Updates job status to succeeded or failed safely.
    """
    job = (
        db.query(RouteJob)
        .filter(RouteJob.id == job_id)
        .with_for_update(skip_locked=True)
        .first()
    )

    if not job:
        job = db.query(RouteJob).filter(RouteJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")
        return job

    if job.status == RouteJobStatus.SUCCEEDED:
        return job

    job.status = RouteJobStatus.RUNNING
    job.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    try:
        # 1. Fetch Depot
        depot_loc = db.query(Location).filter(Location.id == job.depot_location_id).first()
        if not depot_loc:
            raise ValueError(f"Depot location {job.depot_location_id} not found.")

        depot_dict = {
            "id": str(depot_loc.id),
            "name": depot_loc.name,
            "latitude": depot_loc.latitude,
            "longitude": depot_loc.longitude,
        }

        # 2. Fetch Reserved Tickets for this run
        tickets = (
            db.query(Ticket)
            .filter(
                Ticket.service_date == job.service_date,
                Ticket.session_id == job.session_id,
                Ticket.trip_type == job.trip_type,
                Ticket.status == TicketStatus.RESERVED,
            )
            .all()
        )

        if not tickets:
            job.status = RouteJobStatus.FAILED
            job.error_message = "Không có vé ở trạng thái RESERVED nào cho chuyến chạy này."
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            return job

        # Group demand per pickup location
        location_demands: Dict[uuid.UUID, int] = {}
        tickets_by_location: Dict[uuid.UUID, List[Ticket]] = {}

        for t in tickets:
            location_demands[t.pickup_location_id] = location_demands.get(t.pickup_location_id, 0) + 1
            tickets_by_location.setdefault(t.pickup_location_id, []).append(t)

        loc_ids = list(location_demands.keys())
        locations = db.query(Location).filter(Location.id.in_(loc_ids)).all()

        location_dicts = []
        for loc in locations:
            location_dicts.append({
                "id": str(loc.id),
                "name": loc.name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "demand": location_demands.get(loc.id, 1),
                "time_window_start": loc.time_window_start.strftime("%H:%M") if loc.time_window_start else "06:00",
                "time_window_end": loc.time_window_end.strftime("%H:%M") if loc.time_window_end else "07:30",
            })

        # 3. Fetch Vehicles
        vehicles = db.query(Vehicle).all()
        if not vehicles:
            raise ValueError("Không tìm thấy xe buýt nào trong cơ sở dữ liệu.")

        vehicle_dicts = [
            {"id": str(v.id), "capacity": v.capacity, "license_plate": v.license_plate}
            for v in vehicles
        ]

        # 4. Run VRPTW Solver Pipeline
        session_enum = SessionId.MORNING_1
        try:
            session_enum = SessionId(job.session_id)
        except Exception:
            pass

        trip_enum = TripType.PICKUP
        try:
            trip_enum = TripType(job.trip_type)
        except Exception:
            pass

        solver = VRPTWSolverService()
        solved_routes = solver.solve(
            depot=depot_dict,
            locations=location_dicts,
            vehicles=vehicle_dicts,
            session_id=session_enum,
            trip_type=trip_enum,
        )

        if not solved_routes:
            raise ValueError("Thuật toán VRPTW không tìm thấy phương án phân bổ tuyến khả thi.")

        # 5. Persist Routes, Stops & Ticket Assignments in 1 Atomic DB Transaction
        db.begin_nested() if db.in_transaction() else None

        for route_info in solved_routes:
            v_id_str = route_info.get("vehicle_id")
            v_id = None
            if v_id_str:
                try:
                    v_id = uuid.UUID(v_id_str)
                except Exception:
                    pass

            new_route = Route(
                id=uuid.uuid4(),
                route_job_id=job.id,
                service_date=job.service_date,
                session_id=job.session_id,
                trip_type=job.trip_type,
                vehicle_id=v_id,
                status=RouteStatus.PENDING,
                total_distance=float(route_info.get("total_distance_km", 0.0)),
            )
            db.add(new_route)
            db.flush()

            ordered_stops = route_info.get("ordered_stops", [])
            stop_order = 1

            for stop_data in ordered_stops:
                stop_loc_id_str = stop_data.get("id")
                if not stop_loc_id_str:
                    continue

                stop_loc_id = uuid.UUID(stop_loc_id_str)

                # Parse arrival time ISO or string
                arr_time_str = stop_data.get("arrival_time")
                arr_dt = None
                if arr_time_str:
                    try:
                        # e.g., "06:15"
                        h, m = map(int, arr_time_str.split(":"))
                        arr_dt = datetime.datetime.combine(
                            job.service_date,
                            datetime.time(hour=h, minute=m),
                            tzinfo=VN_TZ,
                        ).astimezone(datetime.timezone.utc)
                    except Exception:
                        arr_dt = datetime.datetime.now(datetime.timezone.utc)

                route_stop = RouteStop(
                    id=uuid.uuid4(),
                    route_id=new_route.id,
                    location_id=stop_loc_id,
                    arrival_time=arr_dt,
                    stop_order=stop_order,
                )
                db.add(route_stop)

                # Assign tickets at this pickup location to this route
                matching_tickets = tickets_by_location.get(stop_loc_id, [])
                for t in matching_tickets:
                    t.route_id = new_route.id
                    t.status = TicketStatus.ASSIGNED

                stop_order += 1

        job.status = RouteJobStatus.SUCCEEDED
        job.error_message = None
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)

        db.commit()
        db.refresh(job)
        return job

    except Exception as exc:
        db.rollback()
        job = db.query(RouteJob).filter(RouteJob.id == job_id).first()
        if job:
            job.status = RouteJobStatus.FAILED
            job.error_message = str(exc)
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            db.refresh(job)
        raise exc
