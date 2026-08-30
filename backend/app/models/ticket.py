import enum
import datetime
import uuid
from sqlalchemy import Column, String, Date, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class TicketStatus(str, enum.Enum):
    RESERVED = "reserved"
    ASSIGNED = "assigned"
    USED = "used"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL"), nullable=True, index=True)
    service_date = Column(Date, nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    trip_type = Column(String(50), nullable=False, index=True)
    pickup_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    qr_code = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(
        SQLEnum(
            TicketStatus,
            name="ticket_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=TicketStatus.RESERVED,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("Profile")
    route = relationship("Route")
    pickup_location = relationship("Location")

    __table_args__ = (
        UniqueConstraint("user_id", "service_date", "session_id", "trip_type", name="uq_tickets_user_run"),
        Index("ix_tickets_run_status", "service_date", "session_id", "trip_type", "status"),
    )
