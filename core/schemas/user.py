from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    """Base schema for User data."""
    email: EmailStr
    username: str


class UserCreate(UserBase):
    """Schema for creating new users."""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user data."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """Schema for User response."""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserInDB(User):
    """Schema with hashed password field for internal use."""
    hashed_password: str


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str
