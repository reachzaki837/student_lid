from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.user import UserRole

# Shared properties
class UserBase(BaseModel):
    email: EmailStr

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8)
    role: UserRole = UserRole.STUDENT

# Properties to return to client (never return password!)
class UserResponse(UserBase):
    id: int
    role: UserRole
    is_google_user: bool

    class Config:
        from_attributes = True