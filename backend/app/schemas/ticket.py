import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.ticket import TicketStatus


class TicketBase(BaseModel):
    route_id: Optional[int] = None


class TicketCreate(TicketBase):
    pass


class TicketResponse(TicketBase):
    id: int
    user_id: int
    qr_code: str
    status: TicketStatus
    price: float
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class QRVerifyRequest(BaseModel):
    qr_code: str


class RevenueTrendPoint(BaseModel):
    date: str
    revenue: float
    ticket_count: int


class RevenueTrendResponse(BaseModel):
    data: list[RevenueTrendPoint]
