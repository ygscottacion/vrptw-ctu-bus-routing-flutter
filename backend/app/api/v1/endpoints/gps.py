from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.gps_log import GpsLog
from app.models.profile import Profile, ProfileRole
from app.models.route import Route, RouteStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.vehicle import Vehicle
from app.schemas.gps import GpsLocationCreate, GpsLocationResponse

router = APIRouter()


def _get_route_for_view(route_id: UUID, profile: Profile, db: Session) -> Route:
    route = db.query(Route).filter(Route.id == route_id).first()
    if route is None or route.status != RouteStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chuyến đang chạy.")

    if profile.role == ProfileRole.ADMIN:
        return route

    if profile.role == ProfileRole.DRIVER:
        assigned = db.query(Vehicle.id).filter(
            Vehicle.id == route.vehicle_id,
            Vehicle.driver_id == profile.id,
        ).first()
        if assigned:
            return route
    elif profile.role == ProfileRole.PASSENGER:
        has_ticket = db.query(Ticket.id).filter(
            Ticket.route_id == route.id,
            Ticket.user_id == profile.id,
            Ticket.status.in_([TicketStatus.ASSIGNED, TicketStatus.USED]),
        ).first()
        if has_ticket:
            return route

    # Hide route existence from users who are not assigned to it.
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chuyến đang chạy.")


@router.post("/", response_model=GpsLocationResponse, status_code=status.HTTP_201_CREATED)
def create_gps_location(
    location_in: GpsLocationCreate,
    db: Session = Depends(deps.get_db),
    current_driver: Profile = Depends(deps.get_current_driver),
) -> Any:
    route = db.query(Route).filter(Route.id == location_in.route_id).first()
    if route is None or route.status != RouteStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Chỉ nhận vị trí của chuyến đang chạy.")

    if current_driver.role == ProfileRole.DRIVER:
        assigned = db.query(Vehicle.id).filter(
            Vehicle.id == route.vehicle_id,
            Vehicle.driver_id == current_driver.id,
        ).first()
        if not assigned:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chuyến được phân công.")

    log = GpsLog(**location_in.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/{route_id}/latest", response_model=GpsLocationResponse)
def read_latest_gps_location(
    route_id: UUID,
    db: Session = Depends(deps.get_db),
    current_profile: Profile = Depends(deps.get_current_profile),
) -> Any:
    route = _get_route_for_view(route_id, current_profile, db)
    latest = (
        db.query(GpsLog)
        .filter(GpsLog.route_id == route.id)
        .order_by(GpsLog.recorded_at.desc())
        .first()
    )
    if latest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chưa có vị trí GPS cho chuyến này.")
    return latest
