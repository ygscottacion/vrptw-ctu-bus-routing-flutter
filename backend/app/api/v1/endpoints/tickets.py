from datetime import datetime, time, timedelta
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_ticket
from app.models.location import Location
from app.models.user import User
from app.schemas.ticket import TicketPurchase, TicketResponse, QRVerifyRequest

router = APIRouter()

@router.post("/buy", response_model=List[TicketResponse], status_code=status.HTTP_201_CREATED)
def buy_tickets(
    purchase_in: TicketPurchase,
    db: Session = Depends(deps.get_db),
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    """
    Buy exactly one daily, one-way ticket.  Routes are generated from all
    reservations after the 22:00 cutoff on the previous day.
    """
    deadline = datetime.combine(
        purchase_in.service_date - timedelta(days=1), time(hour=22)
    )
    if datetime.now() >= deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đã quá hạn đặt vé 22:00 của ngày trước ngày chạy.",
        )
    if purchase_in.trip_type == "pickup" and not purchase_in.session_id.startswith("MORNING"):
        raise HTTPException(status_code=422, detail="Chiều đi chỉ dùng ca MORNING_1 hoặc MORNING_2.")
    if purchase_in.trip_type == "dropoff" and not purchase_in.session_id.startswith("NOON"):
        raise HTTPException(status_code=422, detail="Chiều về chỉ dùng ca NOON_1 hoặc NOON_2.")
    if not db.query(Location).filter(Location.id == purchase_in.pickup_location_id).first():
        raise HTTPException(status_code=404, detail="Không tìm thấy trạm đã chọn.")
    return crud_ticket.create_tickets(
        db=db,
        user_id=current_student.id,
        quantity=1,
        service_date=purchase_in.service_date,
        session_id=purchase_in.session_id,
        trip_type=purchase_in.trip_type,
        pickup_location_id=purchase_in.pickup_location_id,
    )

@router.get("/me", response_model=List[TicketResponse])
def read_my_tickets(
    db: Session = Depends(deps.get_db),
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    """
    Retrieve all tickets owned by the current student.
    """
    return crud_ticket.get_user_tickets(db=db, user_id=current_student.id)

@router.post("/verify-qr", response_model=TicketResponse)
def verify_ticket_qr(
    request: QRVerifyRequest,
    db: Session = Depends(deps.get_db),
    current_driver: User = Depends(deps.get_current_driver)
) -> Any:
    """
    Driver scans student's QR code on the bus to verify and check-in ticket.
    """
    ticket = crud_ticket.verify_and_use_ticket(db=db, qr_code=request.qr_code)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vé không hợp lệ hoặc không tồn tại trong hệ thống"
        )
    return ticket
