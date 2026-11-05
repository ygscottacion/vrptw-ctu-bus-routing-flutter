import datetime
import uuid

from sqlalchemy import Column, DateTime, Float, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class GpsLog(Base):
    __tablename__ = "gps_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(
        UUID(as_uuid=True),
        ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False,
    )
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    heading = Column(Float, nullable=False, default=0.0)
    speed = Column(Float, nullable=False, default=0.0)
    accuracy = Column(Float, nullable=False, default=0.0)
    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    __table_args__ = (
        Index("ix_gps_logs_route_recorded_at", "route_id", recorded_at.desc()),
        Index("ix_gps_logs_recorded_at", "recorded_at"),
    )
