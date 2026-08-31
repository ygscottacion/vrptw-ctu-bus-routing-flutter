import enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.profile import ProfileRole


class ProfileBase(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class ProfileCreate(ProfileBase):
    """Internal schema for profile creation. Role is assigned internally."""
    id: UUID
    role: ProfileRole = ProfileRole.PASSENGER


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: UUID
    role: ProfileRole
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
