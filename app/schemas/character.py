from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid

class CharacterBase(BaseModel):
    name: str
    age: int
    gender: str
    personality_traits: List[str] = []
    interests: List[str] = []
    background: Optional[str] = None

class CharacterCreate(CharacterBase):
    pass

class CharacterInteractionRequest(BaseModel):
    character_id: str = Field(..., description="ID of the character to interact with")

class CharacterPhoto(BaseModel):
    id: str
    url: str
    is_primary: bool = False

class CharacterFeedResponse(CharacterBase):
    id: str
    avatar_url: Optional[str] = None
    photos: List[CharacterPhoto] = []  # Добавлено поле для списка фотографий
    bio_summary: Optional[str] = None
    match_percentage: Optional[float] = None
    
    class Config:
        from_attributes = True

class CharacterResponse(CharacterBase):
    id: str
    avatar_url: Optional[str] = None
    photos: List[CharacterPhoto] = []  # Добавлено поле для списка фотографий
    bio_summary: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MatchNotification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str
    character_name: str
    avatar_url: Optional[str] = None
    message: str = "You have a new match!"
    created_at: datetime = Field(default_factory=datetime.now)

class CharacterAvatarResponse(BaseModel):
    url: str
    message: str = "Avatar successfully updated"

    class Config:
        from_attributes = True
