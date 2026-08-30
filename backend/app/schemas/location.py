from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class LocationBase(BaseModel):
    name: str = Field(..., description="Tên trạm hoặc điểm đón")
    latitude: float = Field(..., description="Vĩ độ (Latitude)")
    longitude: float = Field(..., description="Kinh độ (Longitude)")
    time_window_start: Optional[datetime] = Field(None, description="Khung giờ đón bắt đầu")
    time_window_end: Optional[datetime] = Field(None, description="Khung giờ đón kết thúc")
    demand: int = Field(1, ge=0, description="Nhu cầu / số lượng hành khách tại điểm")


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    demand: Optional[int] = None


class LocationResponse(LocationBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
