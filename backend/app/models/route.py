import enum
from sqlalchemy import Column, Integer, Float, Date, DateTime, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base

class RouteStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    date = Column(Date, nullable=False)
    status = Column(SQLEnum(RouteStatus), default=RouteStatus.PENDING, nullable=False)
    total_distance = Column(Float, default=0.0)

    # Relationships
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan")

class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    arrival_time = Column(DateTime, nullable=True)
    stop_order = Column(Integer, nullable=False)

    # Relationships
    route = relationship("Route", back_populates="stops")
    location = relationship("Location")

