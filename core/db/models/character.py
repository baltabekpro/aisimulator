from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.db.base import Base
import uuid

class Character(Base):
    __tablename__ = "characters"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    age = Column(Integer)
    gender = Column(String(20))
    personality = Column(Text)
    background = Column(Text)
    interests = Column(Text)
    appearance = Column(Text)
    system_prompt = Column(Text)
    greeting_message = Column(Text)
    avatar_url = Column(String(500))
    creator_id = Column(String)
    is_active = Column(Boolean, default=True)
    character_metadata = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<Character {self.name}>"
