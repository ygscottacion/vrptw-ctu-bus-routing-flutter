from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_incident
from app.models.user import User
from app.models.incident import IncidentStatus
from app.schemas.incident import IncidentCreate, IncidentUpdate, IncidentResponse

router = APIRouter()

@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def report_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(deps.get_db),
    current_driver: User = Depends(deps.get_current_driver)
) -> Any:
    """
    Driver reports an emergency or breakdown incident.
    """
    return crud_incident.create_incident(db=db, driver_id=current_driver.id, incident_in=incident_in)

@router.get("/", response_model=List[IncidentResponse])
def read_incidents(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(deps.get_current_admin)
) -> Any:
    """
    Retrieve reported incidents. Admin only.
    """
    return crud_incident.get_incidents(db=db, skip=skip, limit=limit)

@router.put("/{incident_id}/status", response_model=IncidentResponse)
def update_incident(
    incident_id: int,
    status_in: IncidentUpdate,
    db: Session = Depends(deps.get_db),
    current_admin: User = Depends(deps.get_current_admin)
) -> Any:
    """
    Update incident resolution status. Admin only.
    """
    incident = crud_incident.update_incident_status(db=db, incident_id=incident_id, status=status_in.status)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
