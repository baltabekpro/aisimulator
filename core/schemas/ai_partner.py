from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


class AIPartnerBase(BaseModel):
    """Base schema for AI Partner data."""
    name: str
    age: int
    biography: Optional[str] = None
    personality: Optional[Dict[str, Any]] = None
    avatar_url: Optional[str] = None


class AIPartnerCreate(AIPartnerBase):
    """Schema for creating a new AI Partner."""
    pass


class AIPartnerUpdate(BaseModel):
    """Schema for updating an AI Partner."""
    name: Optional[str] = None
    age: Optional[int] = None
    biography: Optional[str] = None
    personality: Optional[Dict[str, Any]] = None
    avatar_url: Optional[str] = None


class AIPartner(AIPartnerBase):
    """Schema for AI Partner response."""
    partner_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    personality_traits: Optional[List[str]] = []
    interests: Optional[List[str]] = []

    class Config:
        orm_mode = True
