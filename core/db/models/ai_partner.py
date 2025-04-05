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
    
    # Columns that may not exist in the actual database will be handled as properties
    # Only include what's definitely in the database
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Define properties for columns that might be accessed but don't exist in DB
    @property
    def partner_id(self):
        return self.id
        
    @property
    def personality_traits(self):
        return None
    
    @property
    def interests(self):
        return None
    
    @property
    def background(self):
        return None
    
    @property
    def current_emotion(self):
        return "neutral"
    
    @property
    def age(self):
        return None
        
    @property
    def gender(self):
        return "female"  # Default value
    
    @property
    def fetishes(self):
        return None
    
    def __repr__(self):
        return f"<AIPartner {self.name}>"
