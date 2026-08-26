from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel
from app.models.route import RouteStatus
from app.services.job_store import JobStatus

from app.schemas.location import LocationResponse

class RouteStopResponse(BaseModel):
    id: int
    location_id: int
    stop_order: int
    arrival_time: Optional[datetime] = None
    location: Optional[LocationResponse] = None

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
    session_id: str = "MORNING_1"
    trip_type: str = "pickup"

class RouteGenerationAcceptedResponse(BaseModel):
    """Phản hồi tức thì khi job sinh lộ trình được nhận và chạy nền (202 Accepted)."""
    job_id: str
    status: JobStatus
    message: str

class RouteGenerationJobStatusResponse(BaseModel):
    """Dùng để Flutter poll tiến trình/kết quả của job sinh lộ trình."""
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    routes: List[RouteResponse] = []

    class Config:
        from_attributes = True
