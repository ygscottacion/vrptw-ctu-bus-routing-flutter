import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.ticket import TicketStatus

class TicketBase(BaseModel):
    route_id: Optional[int] = None

# Thay thế TicketCreate bằng TicketPurchase để mua theo số lượng
class TicketPurchase(BaseModel):
    """One daily ticket, booked for a stop and a fixed operating session."""
    service_date: datetime.date
    session_id: str = Field(pattern="^(MORNING_1|MORNING_2|NOON_1|NOON_2)$")
    trip_type: str = Field(pattern="^(pickup|dropoff)$")
    pickup_location_id: int

class TicketResponse(TicketBase):
    id: int
    user_id: int
    qr_code: str
    status: TicketStatus
    created_at: datetime.datetime
    service_date: Optional[datetime.date] = None
    session_id: Optional[str] = None
    trip_type: Optional[str] = None
    pickup_location_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class QRVerifyRequest(BaseModel):
    qr_code: str
