import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GpsLocationCreate(BaseModel):
    route_id: UUID
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    heading: float = Field(default=0, ge=0, lt=360)
    speed: float = Field(default=0, ge=0, description="Tốc độ km/h")
    accuracy: float = Field(default=0, ge=0)


class GpsLocationResponse(BaseModel):
    route_id: UUID
    latitude: float
    longitude: float
    heading: float
    speed: float
    accuracy: float
    recorded_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
