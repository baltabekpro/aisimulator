import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class AIPartner(Base):
    """
    AI Partner model
    """
    __tablename__ = "ai_partners"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True, default="female")
    personality_traits = Column(Text, nullable=True)  # JSON as text
    interests = Column(Text, nullable=True)  # JSON as text
    background = Column(Text, nullable=True)
    current_emotion = Column(String(50), nullable=True, default="neutral")
    
    # Columns that may not exist in the actual database will be handled as properties
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Define a property for compatibility with character_id in other places
    @property
    def character_id(self):
        return self.id
    
    # Keep partner_id property for backward compatibility
    @property
    def partner_id(self):
        return self.id
    
    # Fetishes may still be accessed but isn't in our schema    
    @property
    def fetishes(self):
        return None
    
    def __repr__(self):
        return f"<AIPartner {self.name}>"
