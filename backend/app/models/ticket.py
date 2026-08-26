import enum
import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base

class TicketStatus(str, enum.Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    # A ticket is a reservation for exactly one direction on one service day.
    # These fields are filled when the student checks out, before routes exist.
    service_date = Column(Date, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    trip_type = Column(String, nullable=True)
    pickup_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    qr_code = Column(String, unique=True, nullable=False, index=True)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User")
    route = relationship("Route")
    pickup_location = relationship("Location")
