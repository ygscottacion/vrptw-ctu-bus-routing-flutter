import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.ticket import TicketStatus


class TicketReserveRequest(BaseModel):
    """Payload for reserving a ticket for a specific date, session, trip type, and pickup location."""
    service_date: datetime.date
    session_id: str = Field(pattern="^(MORNING_1|MORNING_2|NOON_1|NOON_2)$", description="Session ID (MORNING_1, MORNING_2, NOON_1, NOON_2)")
    trip_type: str = Field(pattern="^(pickup|dropoff)$", description="Trip type (pickup or dropoff)")
    pickup_location_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "service_date": "2026-09-01",
                "session_id": "MORNING_1",
                "trip_type": "pickup",
                "pickup_location_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
            }
        }
    )


class TicketResponse(BaseModel):
    id: UUID
    user_id: UUID
    route_id: Optional[UUID] = None
    service_date: datetime.date
    session_id: str
    trip_type: str
    pickup_location_id: UUID
    qr_code: str
    status: TicketStatus
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class QRVerifyRequest(BaseModel):
    qr_code: str
