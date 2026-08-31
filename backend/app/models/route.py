import enum
import uuid
from sqlalchemy import Column, Integer, Float, Date, DateTime, String, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class RouteStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Route(Base):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_job_id = Column(UUID(as_uuid=True), ForeignKey("route_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    service_date = Column(Date, nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    trip_type = Column(String(50), nullable=False, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(
        SQLEnum(
            RouteStatus,
            name="route_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=RouteStatus.PENDING,
        nullable=False,
    )
    total_distance = Column(Float, default=0.0)

    # Relationships
    vehicle = relationship("Vehicle")
    route_job = relationship("RouteJob")
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="route")

    @property
    def passenger_count(self) -> int:
        """Authoritative assigned-passenger count for validation and API payloads."""
        return sum(1 for ticket in self.tickets if ticket.status == "assigned")

    __table_args__ = (
        Index("ix_routes_run", "service_date", "session_id", "trip_type"),
    )


class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    arrival_time = Column(DateTime(timezone=True), nullable=True)
    stop_order = Column(Integer, nullable=False)

    # Relationships
    route = relationship("Route", back_populates="stops")
    location = relationship("Location")

    __table_args__ = (
        UniqueConstraint("route_id", "stop_order", name="uq_route_stops_order"),
    )
