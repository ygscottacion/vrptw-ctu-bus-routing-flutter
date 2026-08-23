from typing import List, Optional
from datetime import date as date_cls
from sqlalchemy.orm import Session
from app.models.incident import Incident, IncidentStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.route import Route, RouteStatus
from app.schemas.incident import IncidentCreate


def create_incident(db: Session, driver_id: int, incident_in: IncidentCreate) -> Incident:
    db_incident = Incident(
        driver_id=driver_id,
        vehicle_id=incident_in.vehicle_id,
        title=incident_in.title,
        description=incident_in.description,
        status=IncidentStatus.PENDING
    )
    db.add(db_incident)

    if incident_in.vehicle_id:
        vehicle = db.query(Vehicle).filter(Vehicle.id == incident_in.vehicle_id).first()
        if vehicle:
            vehicle.status = VehicleStatus.BROKEN

    db.commit()
    db.refresh(db_incident)
    return db_incident


def get_incidents(db: Session, skip: int = 0, limit: int = 100) -> List[Incident]:
    return db.query(Incident).order_by(Incident.reported_at.desc()).offset(skip).limit(limit).all()


def update_incident_status(db: Session, incident_id: int, status: IncidentStatus) -> Optional[Incident]:
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident:
        incident.status = status
        db.commit()
        db.refresh(incident)

        if status == IncidentStatus.RESOLVED and incident.vehicle_id:
            remaining = (
                db.query(Incident)
                .filter(
                    Incident.vehicle_id == incident.vehicle_id,
                    Incident.status != IncidentStatus.RESOLVED,
                    Incident.id != incident.id,
                )
                .count()
            )
            if remaining == 0:
                vehicle = db.query(Vehicle).filter(Vehicle.id == incident.vehicle_id).first()
                if vehicle:
                    still_running = (
                        db.query(Route)
                        .filter(
                            Route.vehicle_id == vehicle.id,
                            Route.date == date_cls.today(),
                            Route.status == RouteStatus.IN_PROGRESS,
                        )
                        .first()
                    )
                    vehicle.status = VehicleStatus.RUNNING if still_running else VehicleStatus.IDLE
                    db.commit()

    return incident
