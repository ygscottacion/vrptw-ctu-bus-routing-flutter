import datetime
import secrets
import string

from sqlalchemy.orm import Session

from app.models.ticket import Ticket


_SESSION_CODES = {
    "MORNING_1": "MOR1",
    "MORNING_2": "MOR2",
    "NOON_1": "NOO1",
    "NOON_2": "NOO2",
}
_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_ticket_code(db: Session, service_date: datetime.date, session_id: str) -> str:
    """Return a short human-readable code, retrying codes already in the database."""
    session_code = _SESSION_CODES.get(session_id)
    if session_code is None:
        raise ValueError(f"Unsupported ticket session: {session_id}")

    date_code = service_date.strftime("%d%m%y")
    for _ in range(100):
        suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(3))
        code = f"CT-{session_code}-{date_code}-{suffix}"
        if not db.query(Ticket.id).filter(Ticket.qr_code == code).first():
            return code

    raise RuntimeError("Unable to generate a unique ticket code after 100 attempts")
