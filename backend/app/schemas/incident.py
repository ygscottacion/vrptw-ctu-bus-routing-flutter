import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.incident import IncidentStatus


class IncidentBase(BaseModel):
    title: str
    description: Optional[str] = None
    vehicle_id: Optional[UUID] = None


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    status: IncidentStatus


class IncidentResponse(IncidentBase):
    id: UUID
    driver_id: UUID
    status: IncidentStatus
    reported_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
