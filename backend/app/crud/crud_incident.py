from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.incident import Incident, IncidentStatus
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
    return incident
