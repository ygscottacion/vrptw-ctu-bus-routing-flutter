from typing import Optional
from pydantic import BaseModel
from app.models.user import UserRole

class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = UserRole.PASSENGER

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str
