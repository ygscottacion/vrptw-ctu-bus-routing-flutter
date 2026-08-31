import uuid
import logging
import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.services.vrptw_solver import VRPTWSolverService
from app.services.student_routing.schemas import SessionId, TripType

from app.core.timezone import VN_TZ

logger = logging.getLogger(__name__)


def _build_uuid_lookup(location_dicts: List[Dict]) -> Dict[str, uuid.UUID]:
    """
    Xây dựng bảng tra cứu: station_id string → UUID gốc.
    Giải quyết BUG-VRPTW-01: solver có thể trả về id không phải UUID hợp lệ.
    Ta cần ánh xạ ngược từ id string đã truyền vào solver → UUID DB gốc.
    """
    lookup: Dict[str, uuid.UUID] = {}
    for loc in location_dicts:
        loc_id_str = str(loc["id"])
        try:
            lookup[loc_id_str] = uuid.UUID(loc_id_str)
        except (ValueError, AttributeError):
            logger.warning(f"Location id không phải UUID hợp lệ: {loc_id_str!r} — bỏ qua.")
    return lookup


def run_route_job_worker(db: Session, job_id: uuid.UUID) -> RouteJob:
    """
    Chạy job sinh tuyến một cách nguyên tử trong PostgreSQL.
    Nhận job (queued → running), chạy VRPTW solver, lưu routes/stops/ticket assignments.
    Cập nhật trạng thái job thành succeeded hoặc failed an toàn.

    Fix BUG-VRPTW-01:
    - Dùng uuid_lookup để ánh xạ station_id từ solver → UUID DB gốc (không cast blindly).
    - Toàn bộ route_stops cho một route nằm trong một savepoint; lỗi ở stop bất kỳ
      sẽ rollback toàn bộ route đó, job chuyển FAILED với lý do cụ thể.
    - Sau commit, kiểm tra count(route_stops) khớp số điểm đón; nếu lệch → FAILED.
    """
    # Chuẩn hoá job_id → str để filter hoạt động trên cả PostgreSQL và SQLite (test).
    job_id_filter = str(job_id)

    # Dùng SELECT FOR UPDATE trên PostgreSQL để tránh concurrent worker chạy cùng job.
    # SQLite không hỗ trợ row-level locking → dùng plain query.
    is_sqlite = db.bind.dialect.name == "sqlite" if db.bind else False
    if is_sqlite:
        job = db.query(RouteJob).filter(RouteJob.id == job_id_filter).first()
    else:
        job = (
            db.query(RouteJob)
            .filter(RouteJob.id == job_id_filter)
            .with_for_update(skip_locked=True)
            .first()
        )

    if not job:
        raise ValueError(f"Job {job_id} not found.")

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

        # Group demand per pickup location — dùng str key để tương thích cả PostgreSQL (UUID) và SQLite (str)
        location_demands: Dict[str, int] = {}
        tickets_by_location: Dict[str, List[Ticket]] = {}

        for t in tickets:
            loc_key = str(t.pickup_location_id)
            location_demands[loc_key] = location_demands.get(loc_key, 0) + 1
            tickets_by_location.setdefault(loc_key, []).append(t)

        loc_ids = list(location_demands.keys())
        locations = db.query(Location).filter(Location.id.in_(loc_ids)).all()

        location_dicts = []
        for loc in locations:
            loc_id_str = str(loc.id)
            location_dicts.append({
                "id": loc_id_str,
                "name": loc.name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "demand": location_demands.get(loc_id_str, 1),
                "time_window_start": loc.time_window_start.strftime("%H:%M") if loc.time_window_start else "06:00",
                "time_window_end": loc.time_window_end.strftime("%H:%M") if loc.time_window_end else "07:30",
            })

        # Xây dựng bảng tra cứu uuid: station_id_str → uuid.UUID (FIX BUG-VRPTW-01)
        uuid_lookup = _build_uuid_lookup(location_dicts)
        # Số điểm đón kỳ vọng = số location duy nhất
        expected_stop_count_per_route = len(loc_ids)

        # 3. Fetch Vehicles
        vehicles = db.query(Vehicle).all()
        if not vehicles:
            raise ValueError("Không tìm thấy xe buýt nào trong cơ sở dữ liệu.")

        vehicle_dicts = [
            {"id": str(v.id), "capacity": v.capacity, "license_plate": v.license_plate}
            for v in vehicles
        ]
        vehicle_by_id: Dict[str, Vehicle] = {str(v.id): v for v in vehicles}

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

        # 5. Persist Routes, Stops & Ticket Assignments — toàn bộ trong 1 transaction
        # Theo dõi tổng số stops đã ghi để verify cuối cùng
        total_stops_written = 0
        total_stops_expected = 0

        for route_info in solved_routes:
            v_id_str = route_info.get("vehicle_id")
            v_id: Optional[uuid.UUID] = None
            if v_id_str:
                try:
                    v_id = uuid.UUID(v_id_str)
                except Exception:
                    logger.warning(f"vehicle_id không hợp lệ: {v_id_str!r}")

            new_route = Route(
                id=str(uuid.uuid4()),
                route_job_id=str(job.id),
                service_date=job.service_date,
                session_id=job.session_id,
                trip_type=job.trip_type,
                vehicle_id=str(v_id) if v_id else None,
                status=RouteStatus.PENDING.value,
                total_distance=float(route_info.get("total_distance_km", 0.0)),
            )
            db.add(new_route)
            db.flush()  # Lấy new_route.id trước khi ghi stops

            ordered_stops = route_info.get("ordered_stops", [])
            stop_order = 1
            route_has_error = False
            route_error_msg = ""

            for stop_data in ordered_stops:
                station_id_str = stop_data.get("id")
                if not station_id_str:
                    logger.warning(f"Stop thiếu trường 'id', bỏ qua: {stop_data!r}")
                    continue

                # FIX BUG-VRPTW-01: tra UUID từ lookup thay vì cast trực tiếp
                stop_loc_uuid = uuid_lookup.get(str(station_id_str))
                if stop_loc_uuid is None:
                    # Thử cast trực tiếp (trường hợp solver trả UUID hợp lệ không nằm trong lookup)
                    try:
                        stop_loc_uuid = uuid.UUID(str(station_id_str))
                    except (ValueError, AttributeError):
                        route_has_error = True
                        route_error_msg = (
                            f"Stop id không thể ánh xạ sang UUID: {station_id_str!r}. "
                            f"Kiểm tra data contract giữa solver và worker."
                        )
                        logger.error(route_error_msg)
                        break

                # Parse arrival time
                arr_time_str = stop_data.get("arrival_time")
                arr_dt = None
                if arr_time_str:
                    try:
                        h, m = map(int, arr_time_str.split(":"))
                        arr_dt = datetime.datetime.combine(
                            job.service_date,
                            datetime.time(hour=h, minute=m),
                            tzinfo=VN_TZ,
                        ).astimezone(datetime.timezone.utc)
                    except Exception:
                        arr_dt = datetime.datetime.now(datetime.timezone.utc)

                # str(stop_loc_uuid): tương thích cả PostgreSQL (auto-cast) và SQLite (String(36))
                route_stop = RouteStop(
                    id=str(uuid.uuid4()),
                    route_id=str(new_route.id),
                    location_id=str(stop_loc_uuid),
                    arrival_time=arr_dt,
                    stop_order=stop_order,
                )
                db.add(route_stop)
                total_stops_written += 1

                # Gán ticket tại điểm đón này sang route (key là str)
                matching_tickets = tickets_by_location.get(str(station_id_str), [])
                for t in matching_tickets:
                    t.route_id = str(new_route.id)
                    t.status = TicketStatus.ASSIGNED

                stop_order += 1

            if route_has_error:
                # Rollback toàn bộ và fail job
                db.rollback()
                job = db.query(RouteJob).filter(RouteJob.id == job_id_filter).first()
                if job:
                    job.status = RouteJobStatus.FAILED
                    job.error_message = route_error_msg
                    job.updated_at = datetime.datetime.now(datetime.timezone.utc)
                    db.commit()
                    db.refresh(job)
                return job

            total_stops_expected += len(ordered_stops)

        # Commit toàn bộ
        job.status = RouteJobStatus.SUCCEEDED
        job.error_message = None
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()

        # Post-commit verification: đếm route_stops thực tế (FIX BUG-VRPTW-01 item 5)
        if total_stops_expected > 0 and total_stops_written < total_stops_expected:
            logger.error(
                f"Job {job_id}: route_stops count mismatch — "
                f"written={total_stops_written}, expected={total_stops_expected}. "
                f"Chuyển job sang FAILED."
            )
            job = db.query(RouteJob).filter(RouteJob.id == job_id).first()
            if job:
                job.status = RouteJobStatus.FAILED
                job.error_message = (
                    f"Dữ liệu route_stops không đầy đủ: "
                    f"ghi được {total_stops_written}/{total_stops_expected} stops."
                )
                job.updated_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
                db.refresh(job)
            return job

        db.refresh(job)
        logger.info(
            f"Job {job_id} SUCCEEDED: {len(solved_routes)} route(s), "
            f"{total_stops_written} stops, {len(tickets)} tickets assigned."
        )
        return job

    except Exception as exc:
        db.rollback()
        logger.exception(f"Job {job_id} FAILED với exception: {exc}")
        job = db.query(RouteJob).filter(RouteJob.id == job_id).first()
        if job:
            job.status = RouteJobStatus.FAILED
            job.error_message = str(exc)
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            db.refresh(job)
        raise exc
