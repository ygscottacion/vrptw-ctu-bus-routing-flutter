import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    event_key = Column(String(160), nullable=False)
    type = Column(String(32), nullable=False)
    title = Column(String(180), nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "event_key", name="uq_notifications_user_event"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )
