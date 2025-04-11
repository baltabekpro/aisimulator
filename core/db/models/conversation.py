import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class Conversation(Base):
    """
    Модель для хранения бесед между пользователями и AI персонажами
    """
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False)
    status = Column(String(20), default="active")  # active, archived, deleted
    metadata = Column(JSON, nullable=True)  # Дополнительные данные о беседе
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Связи
    user = relationship("User", backref="conversations")
    character = relationship("Character", backref="conversations")
    
    def __repr__(self):
        return f"<Conversation {self.id} between user:{self.user_id} and character:{self.character_id}>"
