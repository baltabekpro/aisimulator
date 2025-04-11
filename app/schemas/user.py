from typing import Optional, List, Dict, Any
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

class UserProfileBase(BaseModel):
    """Базовая модель пользовательского профиля"""
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    photos: List[str] = Field(default_factory=list)
    
    # Настройки предпочтений для алгоритма сватовства
    matching_preferences: Dict[str, Any] = Field(default_factory=dict)

class UserProfileUpdate(UserProfileBase):
    """Модель для обновления пользовательского профиля"""
    pass

class UserProfileResponse(UserProfileBase):
    """Модель ответа с данными пользовательского профиля"""
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
