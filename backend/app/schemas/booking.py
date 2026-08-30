import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.booking import BookingStatus


class BookingBase(BaseModel):
    route_id: Optional[UUID] = None
    ticket_id: UUID
    pickup_location_id: UUID
    note: Optional[str] = None


class BookingCreate(BookingBase):
    pass


class BookingResponse(BookingBase):
    id: UUID
    user_id: UUID
    schedule_time: Optional[str] = None
    status: BookingStatus
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BookingUpdate(BaseModel):
    route_id: Optional[UUID] = None
    pickup_location_id: Optional[UUID] = None
    schedule_time: Optional[str] = None
    note: Optional[str] = None