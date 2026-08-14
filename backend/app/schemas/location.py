from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class LocationBase(BaseModel):
    name: str = Field(..., max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    demand: int = Field(default=1, ge=0)
    
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
    id: int
    
    class Config:
        from_attributes = True