from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.models.route import Route, RouteStop, RouteStatus
from datetime import datetime

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

def get_routes_by_driver(db: Session, driver_id: int) -> List[Route]:
    from app.models.vehicle import Vehicle
    return db.query(Route).join(Vehicle, Route.vehicle_id == Vehicle.id).filter(Vehicle.driver_id == driver_id).all()
