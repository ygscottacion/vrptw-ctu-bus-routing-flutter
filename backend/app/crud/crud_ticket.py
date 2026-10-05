import uuid
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.models.ticket import Ticket, TicketStatus
from app.services.ticket_code import generate_ticket_code


def create_tickets(db: Session, user_id: uuid.UUID, quantity: int = 1, **ticket_fields) -> List[Ticket]:
    tickets = []
    for _ in range(quantity):
        ticket_id = uuid.uuid4()
        qr_code = generate_ticket_code(db, ticket_fields["service_date"], ticket_fields["session_id"])
        db_ticket = Ticket(
            id=ticket_id,
            user_id=user_id,
            route_id=None,
            qr_code=qr_code,
            status=TicketStatus.RESERVED,
            **ticket_fields,
        )
        db.add(db_ticket)
        db.flush()
        tickets.append(db_ticket)

    db.commit()
    for ticket in tickets:
        db.refresh(ticket)
    return tickets


def get_user_tickets(db: Session, user_id: uuid.UUID) -> List[Ticket]:
    return (
        db.query(Ticket)
        .filter(
            Ticket.user_id == user_id,
            Ticket.status.in_([TicketStatus.RESERVED, TicketStatus.ASSIGNED, TicketStatus.USED]),
        )
        .order_by(Ticket.created_at.desc())
        .all()
    )


def get_unassigned_tickets_for_run(
    db: Session, service_date: date, session_id: str, trip_type: str
) -> List[Ticket]:
    return (
        db.query(Ticket)
        .filter(
            Ticket.status == TicketStatus.RESERVED,
            Ticket.route_id.is_(None),
            Ticket.service_date == service_date,
            Ticket.session_id == session_id,
            Ticket.trip_type == trip_type,
        )
        .all()
    )


def verify_and_use_ticket(db: Session, qr_code: str) -> Optional[Ticket]:
    ticket = db.query(Ticket).filter(Ticket.qr_code == qr_code).first()
    if not ticket:
        return None
    if ticket.status in (TicketStatus.ASSIGNED, TicketStatus.RESERVED):
        ticket.status = TicketStatus.USED
        db.commit()
        db.refresh(ticket)
    return ticket
