import enum
import datetime
import uuid
from sqlalchemy import Column, String, Date, DateTime, Text, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class RouteJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RouteJob(Base):
    __tablename__ = "route_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_date = Column(Date, nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    trip_type = Column(String(50), nullable=False)
    depot_location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    status = Column(
        SQLEnum(
            RouteJobStatus,
            name="route_job_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=RouteJobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    depot_location = relationship("Location")

    __table_args__ = (
        Index(
            "ix_route_jobs_active_run",
            "service_date",
            "session_id",
            "trip_type",
            unique=True,
            postgresql_where=(status.in_(["queued", "running"])),
        ),
    )
