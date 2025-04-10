from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    name: Optional[str] = None
    
class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None

class User(UserBase):
    id: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True
