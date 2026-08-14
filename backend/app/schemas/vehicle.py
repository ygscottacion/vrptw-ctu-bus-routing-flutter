from typing import Optional
from pydantic import BaseModel, Field

class VehicleBase(BaseModel):
    license_plate: str = Field(..., max_length=20)
    capacity: int = Field(default=30, gt=0)
    driver_id: Optional[int] = None
    
class VehicleCreate(VehicleBase):
    pass

class VehicleResponse(VehicleBase):
    id: int

    class Config:
        from_attributes = True
