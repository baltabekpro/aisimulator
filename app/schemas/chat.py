from datetime import datetime
from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, UUID4
from uuid import UUID

# Emotion types
EmotionType = Literal["happy", "sad", "angry", "excited", "anxious", "neutral"]

# Relationship types
RelationType = Literal["friendship", "romance", "trust", "intimacy", "understanding"]

# Message types
MessageType = Literal["text", "image"]
SenderType = Literal["user", "bot"]

class Milestone(BaseModel):
    id: str
    name: str
    description: str
    threshold: int
    achieved: bool = False
    achieved_at: Optional[datetime] = None

class Relationship(BaseModel):
    type: RelationType = "friendship"
    level: float = Field(1, ge=0, le=1)
    milestones: List[Milestone] = []

class Emotion(BaseModel):
    name: EmotionType
    intensity: float = Field(..., ge=0, le=1)
    timestamp: datetime

class Event(BaseModel):
    id: str
    name: str
    description: str
    progress: float = Field(..., ge=0, le=1)
    requirements: Dict[str, Any] = {}
    rewards: Dict[str, Any] = {}
    completed: bool = False
    completed_at: Optional[datetime] = None
    milestones: List[Milestone] = []

class CharacterBase(BaseModel):
    id: str
    name: str
    age: int = Field(..., ge=0)
    gender: str
    personality_traits: List[str] = []
    interests: List[str] = []
    fetishes: List[str] = []
    background: str
    height: Optional[int] = None  # в сантиметрах
    weight: Optional[int] = None  # в килограммах
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    body_type: Optional[str] = None
    breast_size: Optional[str] = None
    hip_size: Optional[str] = None
    penis_size: Optional[int] = None  # в сантиметрах
    photos: List[str] = []
    
class CharacterResponse(CharacterBase):
    relationships: Dict[str, Relationship] = {}
    active_events: List[Event] = []
    completed_events: List[Event] = []
    current_emotion: Emotion
    emotional_history: List[Emotion] = []
    created_at: datetime
    updated_at: datetime
    conversation_id: Optional[str] = None
    conversation_context: Optional[str] = None

class Message(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    content: str
    message_type: MessageType = "text"
    image_url: Optional[str] = None
    image_caption: Optional[str] = None
    timestamp: datetime

class UserMessage(BaseModel):
    content: str
    image_url: Optional[Union[str, None]] = None
    image_caption: Optional[Union[str, None]] = None
    id: UUID
    user_id: UUID
    partner_id: UUID
    sender_type: SenderType
    emotion: Optional[EmotionType] = None
    created_at: datetime
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True

class ConversationResponse(BaseModel):
    character_id: str
    messages: List[Message] = []
    context: Optional[str] = ""
    relationship: Optional[Relationship] = None

class MessageItem(BaseModel):
    id: str
    text: str
    delay: int
    emotion: str
    typing_status: Optional[str] = "typing"
    timestamp: Optional[str] = None  # Add timestamp field for frontend processing

class MessageResponse(BaseModel):
    id: str
    text: str
    photo_url: Optional[str] = None
    timestamp: Any  # Accept multiple types for timestamp
    relationship_changes: Optional[Dict[str, float]] = None
    emotion: Any  # Accept object or string
    
    # New optional field for multi-messages
    multi_messages: Optional[List[MessageItem]] = None
    
    # Add a flag to help frontend identify multi-message responses
    is_multi_message: Optional[bool] = Field(default=None, description="Flag for multi-message responses")
    
    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic v2
        arbitrary_types_allowed = True  # Allow more flexible type handling
        
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-set the is_multi_message flag based on the presence of multi_messages
        if self.is_multi_message is None:
            self.is_multi_message = self.multi_messages is not None and len(self.multi_messages) > 0

class ChatResponse(BaseModel):
    message: Message
    relationship_changes: Dict[str, float] = {}
    emotion: EmotionType

# Request models
class SendPhotoRequest(BaseModel):
    file: bytes
