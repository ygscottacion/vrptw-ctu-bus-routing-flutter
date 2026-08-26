import uuid
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.models.ticket import Ticket, TicketStatus

def create_tickets(db: Session, user_id: int, quantity: int = 1, **ticket_fields) -> List[Ticket]:
    tickets = []
    for _ in range(quantity):
        qr_code = f"CTUBUS-{uuid.uuid4().hex[:12].upper()}"
        db_ticket = Ticket(
            user_id=user_id,
            route_id=None,  # Không gán tuyến khi mua
            qr_code=qr_code,
            status=TicketStatus.ACTIVE,
            **ticket_fields,
        )
        db.add(db_ticket)
        tickets.append(db_ticket)
        
    db.commit()
    for ticket in tickets:
        db.refresh(ticket)
    return tickets

def create_ticket(db: Session, user_id: int) -> Ticket:
    return create_tickets(db=db, user_id=user_id, quantity=1)[0]


def get_user_tickets(db: Session, user_id: int) -> List[Ticket]:
    # Keep assigned tickets visible as well: students need their QR after routing.
    return db.query(Ticket).filter(
        Ticket.user_id == user_id,
        Ticket.status == TicketStatus.ACTIVE
    ).order_by(Ticket.created_at.desc()).all()


def get_unassigned_tickets_for_run(
    db: Session, service_date: date, session_id: str, trip_type: str
) -> List[Ticket]:
    return db.query(Ticket).filter(
        Ticket.status == TicketStatus.ACTIVE,
        Ticket.route_id.is_(None),
        Ticket.service_date == service_date,
        Ticket.session_id == session_id,
        Ticket.trip_type == trip_type,
    ).all()

def verify_and_use_ticket(db: Session, qr_code: str) -> Optional[Ticket]:
    ticket = db.query(Ticket).filter(Ticket.qr_code == qr_code).first()
    if not ticket:
        return None
    if ticket.status == TicketStatus.ACTIVE:
        ticket.status = TicketStatus.USED
        db.commit()
        db.refresh(ticket)
    return ticket
