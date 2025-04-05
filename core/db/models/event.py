import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.db.base import Base

class Event(Base):
    """
    Model for storing various events like memories, relationship milestones, etc.
    """
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Optional, if specific to a user
    event_type = Column(String(50), nullable=False)  # 'memory', 'milestone', etc.
    data = Column(Text, nullable=True)  # JSON data stored as text
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Event {self.event_type}: {self.id}>"
