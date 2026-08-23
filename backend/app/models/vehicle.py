import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base


class VehicleStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    BROKEN = "broken"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, default=30)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    status = Column(SQLEnum(VehicleStatus), default=VehicleStatus.IDLE, nullable=False)

    driver = relationship("User")
