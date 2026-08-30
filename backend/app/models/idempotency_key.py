import datetime
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    key = Column(String(255), nullable=False)
    request_hash = Column(String(255), nullable=False)
    response_code = Column(Integer, nullable=False)
    response_body = Column(JSONType, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    user = relationship("Profile")

    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", "key", name="uq_idempotency_user_endpoint_key"),
    )
