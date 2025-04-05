import uuid
import logging
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.sql import func
from core.db.base import Base

logger = logging.getLogger(__name__)

class ChatHistory(Base):
    """
    Model for storing conversation history between users and AI partners
    Used to replace JSON-based storage in the 'events' table
    """
    __tablename__ = "chat_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    character_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    role = Column(String)
    content = Column(Text)
    message_metadata = Column(Text)
    position = Column(Integer)
    is_active = Column(Boolean, default=True, index=True)
    compressed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __init__(self, **kwargs):
        """
        Initialize a ChatHistory instance with type validation
        """
        # Ensure character_id and user_id are strings
        if 'character_id' in kwargs:
            kwargs['character_id'] = str(kwargs['character_id'])
        
        if 'user_id' in kwargs:
            kwargs['user_id'] = str(kwargs['user_id'])
            
        # Call parent constructor
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<ChatHistory {self.id}: {self.character_id} - {self.user_id}>"
