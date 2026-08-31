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
    RouteGenerateRequest,
    RouteJobResponse,
    RouteResponse,
    RouteStopResponse,
)
from app.services.route_worker import run_route_job_worker

router = APIRouter()
from app.core.timezone import VN_TZ


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
        return active_job

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

    # Create new RouteJob
    new_job = RouteJob(
        id=uuid.uuid4(),
        service_date=request_in.service_date,
        session_id=request_in.session_id,
        trip_type=request_in.trip_type,
        depot_location_id=request_in.depot_location_id,
        status=RouteJobStatus.QUEUED,
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

# Run worker process for the job
    try:
        updated_job = run_route_job_worker(db=db, job_id=new_job.id)
        return _route_job_response(updated_job)
    except Exception:
        db.refresh(new_job)
        return _route_job_response(new_job)


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

    if service_date:
        query = query.filter(Route.service_date == service_date)
    if session_id:
        query = query.filter(Route.session_id == session_id)
    if trip_type:
        query = query.filter(Route.trip_type == trip_type)
    if status:
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
