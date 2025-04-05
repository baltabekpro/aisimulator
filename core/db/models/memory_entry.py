from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.db.base import Base
import uuid

class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    character_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Integer, default=1)  # 1-10 scale
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<MemoryEntry {self.id}: {self.character_id} -> {self.user_id}>"
