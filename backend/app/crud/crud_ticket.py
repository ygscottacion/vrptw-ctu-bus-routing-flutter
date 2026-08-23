import uuid
import datetime
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.ticket import Ticket, TicketStatus
from app.crud import crud_settings


def create_ticket(db: Session, user_id: int, route_id: Optional[int] = None) -> Ticket:
    qr_code = f"CTUBUS-{uuid.uuid4().hex[:12].upper()}"

    current_price = crud_settings.get_settings(db).ticket_price

    db_ticket = Ticket(
        user_id=user_id,
        route_id=route_id,
        qr_code=qr_code,
        status=TicketStatus.ACTIVE,
        price=current_price,
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


def get_user_tickets(db: Session, user_id: int) -> List[Ticket]:
    return (
        db.query(Ticket)
        .filter(Ticket.user_id == user_id)
        .order_by(Ticket.created_at.desc())
        .all()
    )


def verify_and_use_ticket(db: Session, qr_code: str) -> Optional[Ticket]:
    ticket = db.query(Ticket).filter(Ticket.qr_code == qr_code).first()
    if not ticket:
        return None
    if ticket.status == TicketStatus.ACTIVE:
        ticket.status = TicketStatus.USED
        db.commit()
        db.refresh(ticket)
    return ticket

def get_all_tickets(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    route_id: Optional[int] = None,
) -> List[Ticket]:

    query = db.query(Ticket)
    if route_id is not None:
        query = query.filter(Ticket.route_id == route_id)
    return (
        query.order_by(Ticket.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_revenue_trend(db: Session, days: int = 7) -> List[dict]:

    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    rows = (
        db.query(
            func.date(Ticket.created_at).label("date"),
            func.sum(Ticket.price).label("revenue"),
            func.count(Ticket.id).label("ticket_count"),
        )
        .filter(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
        .all()
    )

    return [
        {
            "date": str(row.date),
            "revenue": float(row.revenue or 0),
            "ticket_count": row.ticket_count,
        }
        for row in rows
    ]
