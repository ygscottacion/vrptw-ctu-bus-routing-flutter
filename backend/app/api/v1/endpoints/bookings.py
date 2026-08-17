from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User

router = APIRouter()

class BookingCreate(BaseModel):
    route_id: int
    schedule_time: str
    note: Optional[str] = None

class BookingResponse(BaseModel):
    id: int
    user_id: int
    route_id: int
    schedule_time: str
    status: str
    note: Optional[str] = None

_mock_bookings = []
_booking_id_counter = 1

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(deps.get_db),
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    global _booking_id_counter
    booking = {
        "id": _booking_id_counter,
        "user_id": current_student.id,
        "route_id": booking_in.route_id,
        "schedule_time": booking_in.schedule_time,
        "status": "confirmed",
        "note": booking_in.note
    }
    _booking_id_counter += 1
    _mock_bookings.append(booking)
    return booking

@router.get("/me", response_model=List[BookingResponse])
def read_my_bookings(
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    return [b for b in _mock_bookings if b["user_id"] == current_student.id]
