from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel
from app.models.route import RouteStatus

class RouteStopResponse(BaseModel):
    id: int
    location_id: int
    stop_order: int
    arrival_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class RouteResponse(BaseModel):
    id: int
    vehicle_id: Optional[int] = None
    date: date
    status: RouteStatus
    total_distance: float
    stops: List[RouteStopResponse] = []

    class Config:
        from_attributes = True

class RouteGenerateRequest(BaseModel):
    date: date
    depot_location_id: int
