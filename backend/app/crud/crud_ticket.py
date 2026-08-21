import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.ticket import Ticket, TicketStatus

def create_tickets(db: Session, user_id: int, quantity: int = 1) -> List[Ticket]:
    tickets = []
    for _ in range(quantity):
        qr_code = f"CTUBUS-{uuid.uuid4().hex[:12].upper()}"
        db_ticket = Ticket(
            user_id=user_id,
            route_id=None,  # Không gán tuyến khi mua
            qr_code=qr_code,
            status=TicketStatus.ACTIVE
        )
        db.add(db_ticket)
        tickets.append(db_ticket)
        
    db.commit()
    for ticket in tickets:
        db.refresh(ticket)
    return tickets

def get_user_tickets(db: Session, user_id: int) -> List[Ticket]:
    # Chỉ lấy vé ACTIVE (chưa dùng) VÀ route_id == None (chưa gán tuyến)
    return db.query(Ticket).filter(
        Ticket.user_id == user_id,
        Ticket.status == TicketStatus.ACTIVE,
        Ticket.route_id == None
    ).order_by(Ticket.created_at.desc()).all()

def verify_and_use_ticket(db: Session, qr_code: str) -> Optional[Ticket]:
    ticket = db.query(Ticket).filter(Ticket.qr_code == qr_code).first()
    if not ticket:
        return None
    if ticket.status == TicketStatus.ACTIVE:
        ticket.status = TicketStatus.USED
        db.commit()
        db.refresh(ticket)
    return ticket