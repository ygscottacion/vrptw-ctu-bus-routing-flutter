from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.profile import ProfileResponse


class VehicleBase(BaseModel):
    license_plate: str = Field(..., description="Biển số xe")
    capacity: int = Field(30, gt=0, description="Sức chứa tối đa của xe buýt")
    driver_id: Optional[UUID] = Field(None, description="ID tài xế được gán cho xe (profiles.id)")


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    license_plate: Optional[str] = None
    capacity: Optional[int] = None
    driver_id: Optional[UUID] = None


class VehicleResponse(VehicleBase):
    id: UUID
    driver: Optional[ProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)
