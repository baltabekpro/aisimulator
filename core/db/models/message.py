import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from uuid import uuid4

from core.db.base import Base

class Message(Base):
    """
    Model for messages between users and AI partners
    """
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    sender_id = Column(String, nullable=False)
    sender_type = Column(String, nullable=False)  # 'user' or 'character'
    recipient_id = Column(String, nullable=False)
    recipient_type = Column(String, nullable=False)  # 'user' or 'character'
    content = Column(Text, nullable=False)
    emotion = Column(String, nullable=True)
    conversation_id = Column(String, nullable=True)
    
    # Use created_at instead of timestamp
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, nullable=True)
    
    # Additional columns
    is_read = Column(Boolean, default=False)
    is_gift = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Message {self.id}: from {self.sender_type}({self.sender_id}) to {self.recipient_type}({self.recipient_id})>"
