import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class Message(Base):
    """
    Модель для хранения сообщений между пользователями и AI персонажами
    """
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(UUID(as_uuid=True), nullable=False)
    sender_type = Column(String(20), nullable=False)  # 'user' или 'character'
    recipient_id = Column(UUID(as_uuid=True), nullable=False)
    recipient_type = Column(String(20), nullable=False)  # 'user' или 'character'
    content = Column(Text, nullable=False)
    emotion = Column(String(50), nullable=True)  # Эмоциональный тон сообщения
    # Remove conversation_id field completely as it doesn't exist in the database
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_read = Column(Boolean, default=False)
    is_gift = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Message {self.id} from {self.sender_type}:{self.sender_id} to {self.recipient_type}:{self.recipient_id}>"
