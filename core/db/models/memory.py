import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class MemoryEntry(Base):
    """
    Модель для хранения памяти персонажей AI
    """
    __tablename__ = "memory_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    memory_type = Column(String(50), nullable=False)  # Тип памяти: factual, emotional, etc.
    category = Column(String(100), nullable=True)  # Категория памяти
    content = Column(Text, nullable=False)  # Содержание памяти
    importance = Column(Integer, default=1)  # Важность памяти (1-10)
    is_active = Column(Boolean, default=True)  # Активна ли память
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    character = relationship("Character", backref="memories")
    user = relationship("User", backref="character_memories")
    
    def __repr__(self):
        return f"<MemoryEntry {self.memory_type}: {self.content[:30]}...>"
