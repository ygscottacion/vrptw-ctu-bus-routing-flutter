import enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DRIVER = "driver"
    PASSENGER = "passenger"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.PASSENGER, nullable=False)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
