from typing import List, Optional
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.route import RouteStatus
from app.models.route_job import RouteJobStatus
from app.schemas.location import LocationResponse


class RouteStopResponse(BaseModel):
    id: UUID
    route_id: UUID
    location_id: UUID
    stop_order: int
    arrival_time: Optional[datetime] = None
    location: Optional[LocationResponse] = None

    model_config = ConfigDict(from_attributes=True)


class RouteResponse(BaseModel):
    id: UUID
    route_job_id: Optional[UUID] = None
    service_date: date
    session_id: str
    trip_type: str
    vehicle_id: Optional[UUID] = None
    status: RouteStatus
    total_distance: float
    stops: List[RouteStopResponse] = []
    passenger_count: Optional[int] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RouteRejectRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=255, description="Lý do từ chối tuyến")



class RouteGenerateRequest(BaseModel):
    service_date: date
    session_id: str = Field(pattern="^(MORNING_1|MORNING_2|NOON_1|NOON_2)$", description="Session ID (MORNING_1, MORNING_2, NOON_1, NOON_2)")
    trip_type: str = Field(pattern="^(pickup|dropoff)$", description="Trip type (pickup or dropoff)")
    depot_location_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "service_date": "2026-09-01",
                "session_id": "MORNING_1",
                "trip_type": "pickup",
                "depot_location_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
            }
        }
    )


class RouteJobResponse(BaseModel):
    job_id: UUID
    service_date: date
    session_id: str
    trip_type: str
    status: RouteJobStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolylineResponse(BaseModel):
    encoded_polyline: str = Field("", description="Google/Goong Encoded Polyline string")
    distance_km: float = Field(..., description="Tổng quãng đường tính bằng km")
    duration_minutes: float = Field(..., description="Tổng thời gian di chuyển tính bằng phút")
    points: List[List[float]] = Field(default_factory=list, description="Danh sách các cặp tọa độ [[lat, lng], ...]")
    cached: bool = Field(False, description="Xác định kết quả có được trả về từ cache 24h hay không")
    cached_at: Optional[str] = Field(None, description="Thời gian lưu cache (ISO 8601 UTC)")

    model_config = ConfigDict(from_attributes=True)

