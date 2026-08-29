import enum
from sqlalchemy import Column, String, Enum as SQLEnum, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

# Register stub auth.users table in SQLAlchemy metadata so ORM FK resolution works in all environments
if "auth.users" not in Base.metadata.tables:
    Table(
        "users",
        Base.metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        schema="auth",
    )


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
        SQLEnum(
            ProfileRole,
            name="profile_role",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ProfileRole.PASSENGER,
        nullable=False,
    )
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)