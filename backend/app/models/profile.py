import enum
from sqlalchemy import Column, String, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ProfileRole(str, enum.Enum):
    ADMIN = "admin"
    DRIVER = "driver"
    PASSENGER = "passenger"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role = Column(
        SQLEnum(ProfileRole, name="profile_role"),
        default=ProfileRole.PASSENGER,
        nullable=False,
    )
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)