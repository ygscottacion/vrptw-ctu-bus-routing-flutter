import enum
import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class BookingStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL"), nullable=True, index=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    pickup_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_time = Column(String, nullable=True)
    note = Column(String, nullable=True)
    status = Column(
        SQLEnum(
            BookingStatus,
            name="bookingstatus",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=BookingStatus.CONFIRMED,
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
    ticket = relationship("Ticket")
    pickup_location = relationship("Location")