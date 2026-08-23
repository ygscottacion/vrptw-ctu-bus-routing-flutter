from datetime import date as date_cls
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.route import Route, RouteStatus
from app.models.ticket import Ticket
from app.models.incident import Incident, IncidentStatus

router = APIRouter()


@router.get("/summary")
def get_admin_dashboard_summary(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
) -> Any:

    total_students = db.query(User).filter(User.role == UserRole.PASSENGER).count()
    total_drivers = db.query(User).filter(User.role == UserRole.DRIVER).count()
    total_vehicles = db.query(Vehicle).count()
    total_routes = db.query(Route).count()
    total_tickets = db.query(Ticket).count()
    pending_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.PENDING).count()

    return {
        "summary": {
            "total_students": total_students,
            "total_drivers": total_drivers,
            "total_vehicles": total_vehicles,
            "total_routes": total_routes,
            "total_tickets": total_tickets,
            "pending_incidents": pending_incidents,
        },
        "system_status": "OPERATIONAL"
    }


@router.get("/fleet-status")
def get_fleet_status(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
) -> Any:

    today = date_cls.today()

    vehicles = db.query(Vehicle).all()

    running_routes = (
        db.query(Route)
        .filter(Route.date == today, Route.status == RouteStatus.IN_PROGRESS)
        .all()
    )
    route_by_vehicle = {r.vehicle_id: r for r in running_routes}

    running, broken, idle = [], [], []

    for v in vehicles:
        if v.status == VehicleStatus.BROKEN:
            inc = (
                db.query(Incident)
                .filter(Incident.vehicle_id == v.id, Incident.status != IncidentStatus.RESOLVED)
                .order_by(Incident.reported_at.desc())
                .first()
            )
            broken.append({
                "vehicle_id": v.id,
                "license_plate": v.license_plate,
                "incident_id": inc.id if inc else None,
                "incident_title": inc.title if inc else None,
            })
        elif v.status == VehicleStatus.RUNNING:
            r = route_by_vehicle.get(v.id)
            running.append({
                "vehicle_id": v.id,
                "license_plate": v.license_plate,
                "route_id": r.id if r else None,
            })
        else:  # IDLE
            idle.append({
                "vehicle_id": v.id,
                "license_plate": v.license_plate,
            })

    return {
        "total_vehicles": len(vehicles),
        "running_count": len(running),
        "broken_count": len(broken),
        "idle_count": len(idle),
        "running": running,
        "broken": broken,
        "idle": idle,
    }


@router.get("/routes-today")
def get_routes_today(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
) -> Any:

    today = date_cls.today()

    rows = (
        db.query(Route, Vehicle.license_plate)
        .outerjoin(Vehicle, Vehicle.id == Route.vehicle_id)
        .filter(Route.date == today)
        .all()
    )

    by_status = {"pending": 0, "in_progress": 0, "completed": 0}
    items = []
    for route, plate in rows:
        status_key = route.status.value  # "pending" | "in_progress" | "completed"
        by_status[status_key] = by_status.get(status_key, 0) + 1
        items.append({
            "id": route.id,
            "vehicle_id": route.vehicle_id,
            "license_plate": plate,
            "status": status_key,
            "total_distance": route.total_distance,
        })

    return {
        "date": str(today),
        "total": len(items),
        "by_status": by_status,
        "routes": items,
    }
