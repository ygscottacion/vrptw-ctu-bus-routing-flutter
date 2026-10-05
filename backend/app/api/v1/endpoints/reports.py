from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import deps
from app.models.profile import Profile
from app.models.vehicle import Vehicle
from app.models.route import Route
from app.models.ticket import Ticket
from app.models.incident import Incident, IncidentStatus

router = APIRouter()

@router.get("/summary")
def get_admin_dashboard_summary(
    db: Session = Depends(deps.get_db),
    current_admin: Profile = Depends(deps.get_current_admin)
) -> Any:
    """
    Get aggregated system analytics for Admin Web Dashboard.
    """
    user_counts = db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE COALESCE(profile.role::text, 'passenger') = 'passenger') AS total_students,
                COUNT(*) FILTER (WHERE profile.role::text = 'driver') AS total_drivers
            FROM auth.users AS auth_user
            LEFT JOIN public.profiles AS profile ON profile.id = auth_user.id
            """
        )
    ).mappings().one()
    total_students = user_counts["total_students"]
    total_drivers = user_counts["total_drivers"]
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
