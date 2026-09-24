import hmac
import uuid
import datetime
from zoneinfo import ZoneInfo
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
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
    RouteJobResponse,
    RouteRejectRequest,
    RouteResponse,
    RouteStopResponse,
)
from app.services.route_worker import run_route_job_worker
from app.core.timezone import VN_TZ


router = APIRouter()


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
    """
    Endpoint nội bộ dành cho Cron Trigger tạo và chạy Job định tuyến VRPTW.
    Yêu cầu Header X-Cron-Secret chính xác.
    """
    return _create_and_run_job(request_in, db)


@router.post("/admin/generate", response_model=RouteJobResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_routes_admin(
    request_in: RouteGenerateRequest,
    current_admin: Profile = Depends(deps.get_current_admin),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Endpoint dành cho Admin sinh tuyến trực tiếp trên Admin Portal (Auth qua JWT Admin).
    """
    return _create_and_run_job(request_in, db)


@router.get("/jobs/{job_id}", response_model=RouteJobResponse)
def read_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
) -> Any:
    """Tra cứu trạng thái của tác vụ sinh tuyến theo job_id."""
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
    """
    Lấy danh sách các tuyến xe có phân quyền RBAC:
    - Sinh viên: Chỉ thấy các tuyến liên kết với vé đã gán của chính mình.
    - Tài xế: Chỉ thấy các tuyến được gán cho xe của mình phụ trách.
    - Admin: Xem đầy đủ theo các bộ lọc query.
    """
    query = (
        db.query(Route)
        .options(
            selectinload(Route.stops).selectinload(RouteStop.location),
            joinedload(Route.vehicle),
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

    # Apply RBAC filters
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


@router.get("/{route_id}", response_model=RouteResponse)
def read_route_detail(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
) -> Any:
    """
    Chi tiết tuyến xe theo ID với phân quyền RBAC và danh sách các trạm dừng theo stop_order.
    """
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

    # RBAC Validation
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


@router.post("/{route_id}/start", response_model=RouteResponse)
@router.patch("/{route_id}/start", response_model=RouteResponse)
def start_route(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_driver: Profile = Depends(deps.get_current_driver),
) -> Any:
    """
    Tài xế bắt đầu ca chạy: chuyển trạng thái tuyến sang IN_PROGRESS.
    Xác thực tài xế đang quản lý phương tiện được phân công cho tuyến xe.
    """
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
            detail="Không tìm thấy tuyến xe.",
        )

    if not route.vehicle_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tuyến xe chưa được gán cho phương tiện nào.",
        )

    vehicle = db.query(Vehicle).filter(Vehicle.id == route.vehicle_id).first()
    if not vehicle or vehicle.driver_id != current_driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tuyến xe này không thuộc xe do bạn quản lý.",
        )

    route.status = RouteStatus.IN_PROGRESS
    db.commit()
    db.refresh(route)
    return route


@router.post("/{route_id}/end", response_model=RouteResponse)
@router.patch("/{route_id}/end", response_model=RouteResponse)
def end_route(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_driver: Profile = Depends(deps.get_current_driver),
) -> Any:
    """
    Tài xế kết thúc ca chạy: chuyển trạng thái tuyến sang COMPLETED.
    """
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
            detail="Không tìm thấy tuyến xe.",
        )

    if not route.vehicle_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tuyến xe chưa được gán cho phương tiện nào.",
        )

    vehicle = db.query(Vehicle).filter(Vehicle.id == route.vehicle_id).first()
    if not vehicle or vehicle.driver_id != current_driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tuyến xe này không thuộc xe do bạn quản lý.",
        )

    route.status = RouteStatus.COMPLETED
    db.commit()
    db.refresh(route)
    return route


import time
from fastapi import Request
from typing import Tuple
from app.schemas.route import PolylineResponse
from app.services.student_routing.helpers.goong_direction import goong_direction_service

# Simple rate limiter for polyline requests (max 60 req/min per IP)
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
    """
    Endpoint nội bộ lấy đường dẫn uốn lượn (polyline), quãng đường (km) và thời gian di chuyển (phút).
    Đã qua mã hóa, xác thực và lưu Cache 24h.
    Không lộ Goong REST API Key cho mobile client.
    """
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


@router.patch("/{route_id}/start", response_model=RouteResponse)
def start_route(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_driver: Profile = Depends(deps.get_current_driver),
) -> Any:
    """Tài xế bắt đầu thực hiện chuyến xe (Chỉ chủ xe hoặc Admin mới có quyền)."""
    route = (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
        .filter(Route.id == route_id)
        .first()
    )
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    if current_driver.role == ProfileRole.DRIVER:
        if not route.vehicle_id or not route.vehicle or route.vehicle.driver_id != current_driver.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền bắt đầu tuyến xe này (chỉ tài xế phụ trách phương tiện mới có quyền).",
            )

    if route.status == RouteStatus.IN_PROGRESS:
        return route
    if route.status == RouteStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tuyến xe này đã hoàn tất chuyến trước đó.",
        )

    route.status = RouteStatus.IN_PROGRESS
    db.commit()
    db.refresh(route)
    return route


@router.patch("/{route_id}/end", response_model=RouteResponse)
def end_route(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_driver: Profile = Depends(deps.get_current_driver),
) -> Any:
    """Tài xế kết thúc chuyến xe (Chỉ chủ xe hoặc Admin mới có quyền)."""
    route = (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
        .filter(Route.id == route_id)
        .first()
    )
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    if current_driver.role == ProfileRole.DRIVER:
        if not route.vehicle_id or not route.vehicle or route.vehicle.driver_id != current_driver.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền kết thúc tuyến xe này.",
            )

    if route.status == RouteStatus.COMPLETED:
        return route
    if route.status in (RouteStatus.PENDING, RouteStatus.APPROVED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tuyến xe chưa được bắt đầu.",
        )

    route.status = RouteStatus.COMPLETED
    db.commit()
    db.refresh(route)
    return route


@router.post("/{route_id}/approve", response_model=RouteResponse)
def approve_route(
    route_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_admin: Profile = Depends(deps.get_current_admin),
) -> Any:
    """Admin duyệt lộ trình tuyến buýt."""
    route = (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
        .filter(Route.id == route_id)
        .first()
    )
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    route.status = RouteStatus.APPROVED
    route.approved_by = current_admin.id
    route.approved_at = datetime.datetime.now(VN_TZ)
    route.rejection_reason = None
    db.commit()
    db.refresh(route)
    return route


@router.post("/{route_id}/reject", response_model=RouteResponse)
def reject_route(
    route_id: uuid.UUID,
    reject_in: RouteRejectRequest,
    db: Session = Depends(deps.get_db),
    current_admin: Profile = Depends(deps.get_current_admin),
) -> Any:
    """Admin từ chối lộ trình tuyến buýt (ghi lý do)."""
    route = (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.location), joinedload(Route.vehicle))
        .filter(Route.id == route_id)
        .first()
    )
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tuyến xe.")

    route.status = RouteStatus.REJECTED
    route.approved_by = current_admin.id
    route.approved_at = datetime.datetime.now(VN_TZ)
    route.rejection_reason = reject_in.reason
    db.commit()
    db.refresh(route)
    return route


