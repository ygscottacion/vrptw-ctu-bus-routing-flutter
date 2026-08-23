import datetime
from sqlalchemy import Column, Integer, Float, DateTime
from app.core.database import Base


class SystemSetting(Base):
    """
    Singleton table - chỉ nên có duy nhất 1 dòng, luôn query bằng .first().
    Lưu các cấu hình toàn hệ thống mà admin có thể chỉnh qua UI.
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    ticket_price = Column(Float, nullable=False, default=0)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
