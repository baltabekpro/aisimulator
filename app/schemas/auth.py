from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, EmailStr, Field

class AppleAuthRequest(BaseModel):
    identity_token: str
    email: EmailStr
    name: Optional[str] = None
    apple_user_id: Optional[str] = None  # Уникальный идентификатор пользователя от Apple
    given_name: Optional[str] = None     # Имя пользователя из Apple
    family_name: Optional[str] = None    # Фамилия пользователя из Apple
    profile_photo: Optional[str] = None  # URL фотографии профиля

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    name: Optional[str] = None
    external_id: Optional[str] = None
    preferences: Optional[dict] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True

class OAuth2Form(BaseModel):
    grant_type: Optional[str] = None
    username: str
    password: str
    scope: str = ""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
