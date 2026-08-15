from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.models.route import Route
from app.models.ticket import Ticket
from app.models.incident import Incident, IncidentStatus

router = APIRouter()

@router.get("/summary")
def get_admin_dashboard_summary(
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
) -> Any:
    """
    Get aggregated system analytics for Admin Web Dashboard.
    """
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
