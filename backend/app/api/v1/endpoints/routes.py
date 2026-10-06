import hmac
import uuid
import datetime
import time
from typing import Any, List, Optional, Tuple
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import func

from app.api import deps
from app.core.config import settings
from app.models.profile import Profile, ProfileRole
from app.models.location import Location
from app.models.vehicle import Vehicle
from app.models.ticket import Ticket, TicketStatus
from app.models.route import Route, RouteStop, RouteStatus
from app.models.route_job import RouteJob, RouteJobStatus
from app.schemas.route import (
    PolylineResponse,
    RouteGenerateRequest,
    RouteApproveRequest,
    RouteDriverOption,
    RouteJobResponse,
    RouteRejectRequest,
    RouteResponse,
    RouteStopResponse,
)
from app.services.route_worker import run_route_job_worker
from app.services.student_routing.helpers.goong_direction import goong_direction_service
from app.core.timezone import VN_TZ

router = APIRouter()

# ── Centralized State Machine Matrix for Route Transitions ───────────────────
VALID_ROUTE_TRANSITIONS = {
    RouteStatus.PENDING: [RouteStatus.APPROVED, RouteStatus.REJECTED, RouteStatus.IN_PROGRESS],
    RouteStatus.APPROVED: [RouteStatus.IN_PROGRESS, RouteStatus.REJECTED],
    RouteStatus.IN_PROGRESS: [RouteStatus.COMPLETED],
    RouteStatus.REJECTED: [],
    RouteStatus.COMPLETED: [],
}


def _route_job_response(job: RouteJob) -> dict[str, Any]:
    """Serialize the ORM job using the public API field name ``job_id``."""
    return {
        "job_id": job.id,
        "service_date": job.service_date,
        "session_id": job.session_id,
        "trip_type": job.trip_type,
        "status": job.status,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def verify_cron_secret(x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret")) -> str:
    """Verifies X-Cron-Secret header against environment settings using constant-time comparison."""
    if not x_cron_secret or not settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu hoặc mã X-Cron-Secret không hợp lệ.",
        )
    if not hmac.compare_digest(x_cron_secret.encode("utf-8"), settings.CRON_SECRET.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã X-Cron-Secret không chính xác.",
        )
    return x_cron_secret


def _create_and_run_job(request_in: RouteGenerateRequest, db: Session) -> dict[str, Any]:
    # 1. Check cutoff deadline (Job only allowed after 22:00 cutoff on D-1)
    now_vn = datetime.datetime.now(VN_TZ)
    cutoff_dt = datetime.datetime.combine(
        request_in.service_date - datetime.timedelta(days=1),
        datetime.time(hour=22, minute=0, second=0),
        tzinfo=VN_TZ,
    )

    if now_vn < cutoff_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể chạy job sinh tuyến sau mốc deadline 22:00 (giờ Việt Nam) của ngày trước ngày chạy.",
        )

    # 2. Check Depot
    depot = db.query(Location).filter(Location.id == request_in.depot_location_id).first()
    if not depot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy trạm xuất phát (depot) đã chọn.",
        )

    # 3. Check existing active or succeeded job for this run
    active_job = (
        db.query(RouteJob)
        .filter(
            RouteJob.service_date == request_in.service_date,
            RouteJob.session_id == request_in.session_id,
            RouteJob.trip_type == request_in.trip_type,
            RouteJob.status.in_([RouteJobStatus.QUEUED, RouteJobStatus.RUNNING]),
        )
        .first()
    )

    if active_job:
        return _route_job_response(active_job)

    succeeded_job = (
        db.query(RouteJob)
        .filter(
            RouteJob.service_date == request_in.service_date,
            RouteJob.session_id == request_in.session_id,
            RouteJob.trip_type == request_in.trip_type,
            RouteJob.status == RouteJobStatus.SUCCEEDED,
        )
        .first()
    )

    if succeeded_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job sinh tuyến cho lượt chạy này đã hoàn tất thành công trước đó.",
        )

    # Check existing failed job to reuse/retry
    failed_job = (
        db.query(RouteJob)
        .filter(
            RouteJob.service_date == request_in.service_date,
            RouteJob.session_id == request_in.session_id,
            RouteJob.trip_type == request_in.trip_type,
            RouteJob.status == RouteJobStatus.FAILED,
        )
        .first()
    )

    if failed_job:
        job_to_run = failed_job
        job_to_run.depot_location_id = request_in.depot_location_id
        job_to_run.status = RouteJobStatus.QUEUED
        job_to_run.error_message = None
        db.commit()
        db.refresh(job_to_run)
    else:
        job_to_run = RouteJob(
            id=uuid.uuid4(),
            service_date=request_in.service_date,
            session_id=request_in.session_id,
            trip_type=request_in.trip_type,
            depot_location_id=request_in.depot_location_id,
            status=RouteJobStatus.QUEUED,
        )
        db.add(job_to_run)
        db.commit()
        db.refresh(job_to_run)

    # Run worker process for the job
    try:
        updated_job = run_route_job_worker(db=db, job_id=job_to_run.id)
        return _route_job_response(updated_job)
    except Exception:
        db.refresh(job_to_run)
        return _route_job_response(job_to_run)


@router.post("/generate", response_model=RouteJobResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_routes(
    request_in: RouteGenerateRequest,
    x_cron_secret: str = Depends(verify_cron_secret),
    db: Session = Depends(deps.get_db),
) -> Any:
    return _create_and_run_job(request_in, db)


@router.post("/admin/generate", response_model=RouteJobResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_routes_admin(
    request_in: RouteGenerateRequest,
    current_admin: Profile = Depends(deps.get_current_admin),
    db: Session = Depends(deps.get_db),
) -> Any:
    return _create_and_run_job(request_in, db)


@router.get("/jobs/{job_id}", response_model=RouteJobResponse)
def read_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
) -> Any:
    job = db.query(RouteJob).filter(RouteJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin job.",
        )
    return _route_job_response(job)


@router.get("", response_model=List[RouteResponse])
def read_routes(
    service_date: Optional[datetime.date] = Query(None),
    session_id: Optional[str] = Query(None),
    trip_type: Optional[str] = Query(None),
    status: Optional[RouteStatus] = Query(None),
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
) -> Any:
    query = (
        db.query(Route)
        .options(
            selectinload(Route.stops).selectinload(RouteStop.location),
            joinedload(Route.vehicle).joinedload(Vehicle.driver),
        )
    )

    from fastapi.params import Param

    if service_date is not None and not isinstance(service_date, Param):
        query = query.filter(Route.service_date == service_date)
    if session_id is not None and not isinstance(session_id, Param):
        query = query.filter(Route.session_id == session_id)
    if trip_type is not None and not isinstance(trip_type, Param):
        query = query.filter(Route.trip_type == trip_type)
    if status is not None and not isinstance(status, Param):
        query = query.filter(Route.status == status)

    if current_profile.role == ProfileRole.PASSENGER:
        user_ticket_route_ids = (
            db.query(Ticket.route_id)
            .filter(
                Ticket.user_id == current_profile.id,
                Ticket.route_id.isnot(None),
                Ticket.status == TicketStatus.ASSIGNED,
            )
            .scalar_subquery()
        )
        query = query.filter(Route.id.in_(user_ticket_route_ids))

    elif current_profile.role == ProfileRole.DRIVER:
        driver_vehicle_ids = (
            db.query(Vehicle.id)
            .filter(Vehicle.driver_id == current_profile.id)
            .scalar_subquery()
        )
        query = query.filter(Route.vehicle_id.in_(driver_vehicle_ids))

    routes = query.order_by(Route.service_date.desc(), Route.session_id.asc()).all()
    return routes


# Polyline Rate Limiter
_rate_limit_store: dict[str, list[float]] = {}

def _check_rate_limit(client_ip: str, limit: int = 60, window_seconds: float = 60.0):
    now = time.time()
    timestamps = _rate_limit_store.get(client_ip, [])
    valid_timestamps = [t for t in timestamps if now - t < window_seconds]
    if len(valid_timestamps) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Bạn đã gửi quá nhiều yêu cầu định tuyến trong thời gian ngắn. Vui lòng thử lại sau 1 phút."
        )
    valid_timestamps.append(now)
    _rate_limit_store[client_ip] = valid_timestamps


@router.get("/polyline", response_model=PolylineResponse, status_code=status.HTTP_200_OK)
def get_route_polyline(
    request: Request,
    origin: Optional[str] = Query(None, description="Tọa độ điểm đầu 'lat,lng'"),
    destination: Optional[str] = Query(None, description="Tọa độ điểm cuối 'lat,lng'"),
    waypoints: Optional[str] = Query(None, description="Chuỗi tọa độ phân cách bởi dấu chấm phẩy ';' hoặc '|'"),
    current_profile: Profile = Depends(deps.get_current_profile),
) -> Any:
    client_ip = request.client.host if request.client else "127.0.0.1"
    _check_rate_limit(client_ip)

    parsed_pts: List[Tuple[float, float]] = []

    if waypoints:
        raw_list = waypoints.replace("|", ";").split(";")
        for item in raw_list:
            item = item.strip()
            if not item:
                continue
            parts = item.split(",")
            if len(parts) != 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tọa độ waypoint '{item}' không hợp lệ. Định dạng chuẩn: 'lat,lng'",
                )
            try:
                lat, lng = float(parts[0]), float(parts[1])
                parsed_pts.append((lat, lng))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tọa độ waypoint '{item}' phải là số thực hợp lệ.",
                )
    elif origin and destination:
        for name, str_val in [("origin", origin), ("destination", destination)]:
            parts = str_val.strip().split(",")
            if len(parts) != 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tọa độ {name} '{str_val}' không hợp lệ. Định dạng chuẩn: 'lat,lng'",
                )
            try:
                lat, lng = float(parts[0]), float(parts[1])
                parsed_pts.append((lat, lng))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tọa độ {name} '{str_val}' phải là số thực hợp lệ.",
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần truyền tham số 'waypoints' (ví dụ: 'lat1,lng1;lat2,lng2') hoặc cặp 'origin' và 'destination'.",
        )

    if len(parsed_pts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần tối thiểu 2 điểm tọa độ để tính toán lộ trình.",
        )

    return goong_direction_service.get_route_polyline(parsed_pts)


@router.get("/{route_id}", response_model=RouteResponse)
def read_route_detail(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
) -> Any:
    route = (
        db.query(Route)
        .options(
            selectinload(Route.stops).selectinload(RouteStop.location),
            joinedload(Route.vehicle),
        )
        .filter(Route.id == route_id)
        .first()
    )

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin tuyến xe.",
        )

    if current_profile.role == ProfileRole.PASSENGER:
        user_has_ticket = (
            db.query(Ticket)
            .filter(
                Ticket.route_id == route.id,
                Ticket.user_id == current_profile.id,
            )
            .first()
        )
        if not user_has_ticket:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập thông tin tuyến xe này.",
            )
    elif current_profile.role == ProfileRole.DRIVER:
        if not route.vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tuyến xe chưa được phân công cho phương tiện nào.",
            )
        vehicle = db.query(Vehicle).filter(Vehicle.id == route.vehicle_id).first()
        if not vehicle or vehicle.driver_id != current_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tuyến xe này không thuộc xe do bạn quản lý.",
            )

    return route


# ── Single Set of Driver Route State Handlers (Atomic & Strict State Machine) ──

@router.post("/{route_id}/start", response_model=RouteResponse)
@router.patch("/{route_id}/start", response_model=RouteResponse)
def start_route(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_driver: Profile = Depends(deps.get_current_driver),
) -> Any:
    """
    Tài xế bắt đầu ca chạy: PENDING / APPROVED -> IN_PROGRESS.
    Xác thực order: Auth (401) -> Ownership (403) -> State Machine (409).
    """
    # 1. Lock route row for update without outer join
    route = (
        db.query(Route)
        .filter(Route.id == route_id)
        .with_for_update()
        .first()
    )
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    # 2. Ownership check (403)
    if current_driver.role == ProfileRole.DRIVER:
        if not route.vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tuyến xe này không thuộc xe do bạn quản lý.",
            )
        vehicle = db.query(Vehicle).filter(Vehicle.id == route.vehicle_id).first()
        if not vehicle or vehicle.driver_id != current_driver.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tuyến xe này không thuộc xe do bạn quản lý.",
            )

    # 3. State Machine Check (409)
    if route.status == RouteStatus.IN_PROGRESS:
        # Load relationships for response
        return (
            db.query(Route)
            .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
            .filter(Route.id == route_id)
            .first()
        )

    valid_from = [RouteStatus.PENDING, RouteStatus.APPROVED]
    if route.status not in valid_from:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể chuyển tuyến từ trạng thái '{route.status.value}' sang 'in_progress'.",
        )

    route.status = RouteStatus.IN_PROGRESS
    db.commit()
    
    return (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
        .filter(Route.id == route_id)
        .first()
    )


@router.post("/{route_id}/end", response_model=RouteResponse)
@router.patch("/{route_id}/end", response_model=RouteResponse)
def end_route(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_driver: Profile = Depends(deps.get_current_driver),
) -> Any:
    """
    Tài xế kết thúc ca chạy: IN_PROGRESS -> COMPLETED.
    Xác thực order: Auth (401) -> Ownership (403) -> State Machine (409).
    """
    # 1. Lock route row for update without outer join
    route = (
        db.query(Route)
        .filter(Route.id == route_id)
        .with_for_update()
        .first()
    )
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    # 2. Ownership check (403)
    if current_driver.role == ProfileRole.DRIVER:
        if not route.vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tuyến xe này không thuộc xe do bạn quản lý.",
            )
        vehicle = db.query(Vehicle).filter(Vehicle.id == route.vehicle_id).first()
        if not vehicle or vehicle.driver_id != current_driver.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tuyến xe này không thuộc xe do bạn quản lý.",
            )

    # 3. State Machine Check (409)
    if route.status == RouteStatus.COMPLETED:
        return (
            db.query(Route)
            .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
            .filter(Route.id == route_id)
            .first()
        )

    if route.status != RouteStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể chuyển tuyến từ trạng thái '{route.status.value}' sang 'completed'.",
        )

    route.status = RouteStatus.COMPLETED
    db.commit()

    return (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
        .filter(Route.id == route_id)
        .first()
    )


@router.get("/{route_id}/drivers", response_model=List[RouteDriverOption])
def list_route_driver_options(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_admin: Profile = Depends(deps.get_current_admin),
) -> Any:
    """List drivers with a suitable vehicle and indicate same-shift assignments."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    assigned_driver_ids = {
        driver_id
        for (driver_id,) in (
            db.query(Vehicle.driver_id)
            .join(Route, Route.vehicle_id == Vehicle.id)
            .filter(
                Route.service_date == route.service_date,
                Route.session_id == route.session_id,
                Route.id != route.id,
                Route.status.in_([RouteStatus.APPROVED, RouteStatus.IN_PROGRESS, RouteStatus.COMPLETED]),
                Vehicle.driver_id.isnot(None),
            )
            .all()
        )
    }
    options = (
        db.query(Profile, Vehicle)
        .join(Vehicle, Vehicle.driver_id == Profile.id)
        .filter(Profile.role == ProfileRole.DRIVER, Vehicle.capacity >= (route.passenger_count or 0))
        .order_by(Profile.full_name.asc(), Vehicle.capacity.asc())
        .all()
    )
    # A driver can have more than one vehicle record; present the smallest suitable bus.
    unique_options: dict[uuid.UUID, tuple[Profile, Vehicle]] = {}
    for driver, vehicle in options:
        unique_options.setdefault(driver.id, (driver, vehicle))
    return [
        {
            "id": driver.id,
            "full_name": driver.full_name,
            "phone": driver.phone,
            "vehicle_id": vehicle.id,
            "license_plate": vehicle.license_plate,
            "capacity": vehicle.capacity,
            "busy": driver.id in assigned_driver_ids,
        }
        for driver, vehicle in unique_options.values()
    ]


@router.post("/{route_id}/approve", response_model=RouteResponse)
def approve_route(
    route_id: uuid.UUID,
    approve_in: Optional[RouteApproveRequest] = Body(None),
    db: Session = Depends(deps.get_db),
    current_admin: Profile = Depends(deps.get_current_admin),
) -> Any:
    """Admin duyệt lộ trình tuyến buýt: PENDING -> APPROVED."""
    route = (
        db.query(Route)
        .filter(Route.id == route_id)
        .with_for_update()
        .first()
    )
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    if route.status == RouteStatus.APPROVED:
        return (
            db.query(Route)
            .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle).joinedload(Vehicle.driver))
            .filter(Route.id == route_id)
            .first()
        )

    if route.status != RouteStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể duyệt tuyến đang ở trạng thái '{route.status.value}'.",
        )

    if approve_in is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vui lòng chọn tài xế trước khi duyệt tuyến.")

    # Lock the profile row so concurrent approvals for different routes serialize
    # while checking the driver's same-day, same-session availability.
    driver = (
        db.query(Profile)
        .filter(Profile.id == approve_in.driver_id, Profile.role == ProfileRole.DRIVER)
        .with_for_update()
        .first()
    )
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài xế.")

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.driver_id == driver.id, Vehicle.capacity >= (route.passenger_count or 0))
        .order_by(Vehicle.capacity.asc())
        .first()
    )
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tài xế chưa được gán xe đủ chỗ cho tuyến này.")

    driver_busy = (
        db.query(Route.id)
        .join(Vehicle, Route.vehicle_id == Vehicle.id)
        .filter(
            Vehicle.driver_id == driver.id,
            Route.service_date == route.service_date,
            Route.session_id == route.session_id,
            Route.id != route.id,
            Route.status.in_([RouteStatus.APPROVED, RouteStatus.IN_PROGRESS, RouteStatus.COMPLETED]),
        )
        .first()
    )
    if driver_busy:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tài xế đang bận trong ca này.")

    route.vehicle_id = vehicle.id
    route.status = RouteStatus.APPROVED
    route.approved_by = current_admin.id
    route.approved_at = datetime.datetime.now(VN_TZ)
    route.rejection_reason = None
    db.commit()

    return (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle).joinedload(Vehicle.driver))
        .filter(Route.id == route_id)
        .first()
    )


@router.post("/{route_id}/reject", response_model=RouteResponse)
def reject_route(
    route_id: uuid.UUID,
    reject_in: RouteRejectRequest,
    db: Session = Depends(deps.get_db),
    current_admin: Profile = Depends(deps.get_current_admin),
) -> Any:
    """Admin từ chối lộ trình tuyến buýt: PENDING / APPROVED -> REJECTED."""
    route = (
        db.query(Route)
        .filter(Route.id == route_id)
        .with_for_update()
        .first()
    )
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    if route.status == RouteStatus.REJECTED:
        return (
            db.query(Route)
            .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
            .filter(Route.id == route_id)
            .first()
        )

    valid_from = [RouteStatus.PENDING, RouteStatus.APPROVED]
    if route.status not in valid_from:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể từ chối tuyến đang ở trạng thái '{route.status.value}'.",
        )

    route.status = RouteStatus.REJECTED
    route.approved_by = current_admin.id
    route.approved_at = datetime.datetime.now(VN_TZ)
    route.rejection_reason = reject_in.reason
    db.commit()

    return (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
        .filter(Route.id == route_id)
        .first()
    )
