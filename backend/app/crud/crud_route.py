from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.models.route import Route, RouteStop, RouteStatus
from app.models.vehicle import Vehicle, VehicleStatus  # THÊM


def create_route(db: Session, vehicle_id: int, route_date: date, total_distance: float, stops_data: List[dict]) -> Route:
    db_route = Route(
        vehicle_id=vehicle_id,
        date=route_date,
        status=RouteStatus.PENDING,
        total_distance=total_distance
    )
    db.add(db_route)
    db.commit()
    db.refresh(db_route)

    for idx, stop_info in enumerate(stops_data, start=1):
        db_stop = RouteStop(
            route_id=db_route.id,
            location_id=stop_info["id"],
            stop_order=idx
        )
        db.add(db_stop)

    db.commit()
    db.refresh(db_route)
    return db_route


def get_route_by_id(db: Session, route_id: int) -> Optional[Route]:
    return db.query(Route).filter(Route.id == route_id).first()


def get_routes_by_ids(db: Session, route_ids: List[int]) -> List[Route]:
    if not route_ids:
        return []
    return db.query(Route).filter(Route.id.in_(route_ids)).all()


def get_routes_by_driver(db: Session, driver_id: int) -> List[Route]:
    from app.models.vehicle import Vehicle
    return db.query(Route).join(Vehicle, Route.vehicle_id == Vehicle.id).filter(Vehicle.driver_id == driver_id).all()


def update_route_status(db: Session, route: Route, status: RouteStatus) -> Route:
    """Persist a driver transition for a route that was already assigned."""
    route.status = status

    if route.vehicle_id:
        vehicle = db.query(Vehicle).filter(Vehicle.id == route.vehicle_id).first()
        if vehicle and vehicle.status != VehicleStatus.BROKEN:
            if status == RouteStatus.IN_PROGRESS:
                vehicle.status = VehicleStatus.RUNNING
            elif status == RouteStatus.COMPLETED:
                vehicle.status = VehicleStatus.IDLE
            db.add(vehicle)

    db.add(route)
    db.commit()
    db.refresh(route)
    return route
