import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.ticket import Ticket, TicketStatus

def create_ticket(db: Session, user_id: int, route_id: Optional[int] = None) -> Ticket:
    qr_code = f"CTUBUS-{uuid.uuid4().hex[:12].upper()}"
    db_ticket = Ticket(
        user_id=user_id,
        route_id=route_id,
        qr_code=qr_code,
        status=TicketStatus.ACTIVE
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

def get_user_tickets(db: Session, user_id: int) -> List[Ticket]:
    return db.query(Ticket).filter(Ticket.user_id == user_id).order_by(Ticket.created_at.desc()).all()

def verify_and_use_ticket(db: Session, qr_code: str) -> Optional[Ticket]:
    ticket = db.query(Ticket).filter(Ticket.qr_code == qr_code).first()
    if not ticket:
        return None
    if ticket.status == TicketStatus.ACTIVE:
        ticket.status = TicketStatus.USED
        db.commit()
        db.refresh(ticket)
    return ticket
