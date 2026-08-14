from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse

class VehicleBase(BaseModel):
    license_plate: str = Field(..., description="Biển số xe")
    capacity: int = Field(30, gt=0, description="Sức chứa tối đa của xe buýt")
    driver_id: Optional[int] = Field(None, description="ID tài xế được gán cho xe")

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    license_plate: Optional[str] = None
    capacity: Optional[int] = None
    driver_id: Optional[int] = None

class VehicleResponse(VehicleBase):
    id: int
    driver: Optional[UserResponse] = None

    class Config:
        from_attributes = True
