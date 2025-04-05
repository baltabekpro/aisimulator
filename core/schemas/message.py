from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class MessageBase(BaseModel):
    """Base schema for message data."""
    content: str
    sender_type: str  # "user" or "bot"
    emotion: Optional[str] = None


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    user_id: UUID
    partner_id: UUID


class Message(MessageBase):
    """Schema for message response."""
    message_id: UUID
    user_id: UUID
    partner_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class MessageResponse(BaseModel):
    """Schema for bot message response with additional metadata."""
    id: str
    text: str
    photo_url: Optional[str] = None
    timestamp: datetime
    emotion: Dict[str, Any]
    relationship_changes: Dict[str, float]
    relationship: Dict[str, Any]
