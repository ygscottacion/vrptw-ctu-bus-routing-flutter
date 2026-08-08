from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, default=30)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    driver = relationship("User")
