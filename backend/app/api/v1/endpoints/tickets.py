from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketResponse, QRVerifyRequest

router = APIRouter()

@router.post("/book", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def book_ticket(
    ticket_in: TicketCreate,
    db: Session = Depends(deps.get_db),
    current_student: User = Depends(deps.get_current_student)
) -> Any:
    """
    Student books a bus ticket and gets a unique QR Code for check-in.
    """
    return crud_ticket.create_ticket(db=db, user_id=current_student.id, route_id=ticket_in.route_id)

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
