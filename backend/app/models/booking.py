import enum
import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base

class BookingStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, unique=True)
    
    # BỔ SUNG: Trạm sinh viên đứng chờ
    pickup_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    
    # CẬP NHẬT: Cho phép nullable=True để linh hoạt lưu chuỗi "Đang chờ cập nhật" hoặc rỗng
    schedule_time = Column(String, nullable=True)
    
    note = Column(String, nullable=True)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.CONFIRMED, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User")
    route = relationship("Route")
    ticket = relationship("Ticket")
    pickup_location = relationship("Location") # Thêm liên kết bảng để dễ dàng truy vấn tên trạm sau này