from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BookingBase(BaseModel):
    route_id: int
    ticket_id: int
    pickup_location_id: int  # BỔ SUNG: Trạm sinh viên chọn
    note: Optional[str] = None

class BookingCreate(BookingBase):
    # Sinh viên chỉ cần gửi route_id, ticket_id và pickup_location_id
    pass

class BookingResponse(BookingBase):
    id: int
    user_id: int
    schedule_time: str       # DỊCH CHUYỂN: Chuyển xuống Response vì backend sẽ tự tạo ra dữ liệu này
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
    
class BookingUpdate(BaseModel):
    route_id: Optional[int] = None
    pickup_location_id: Optional[int] = None  # Bổ sung để có thể đổi trạm đón nếu cần
    schedule_time: Optional[str] = None
    note: Optional[str] = None