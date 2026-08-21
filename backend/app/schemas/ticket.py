import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.ticket import TicketStatus

class TicketBase(BaseModel):
    route_id: Optional[int] = None

# Thay thế TicketCreate bằng TicketPurchase để mua theo số lượng
class TicketPurchase(BaseModel):
    quantity: int = Field(default=1, ge=1, le=10, description="Số lượng vé muốn mua")

class TicketResponse(TicketBase):
    id: int
    user_id: int
    qr_code: str
    status: TicketStatus
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class QRVerifyRequest(BaseModel):
    qr_code: str