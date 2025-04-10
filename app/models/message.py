import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base_class import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), nullable=False)
    sender_type = Column(String(50), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), nullable=False)
    recipient_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    emotion = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)
    is_gift = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    def __repr__(self):
        return f"<Message {self.id}: {self.sender_type}:{self.sender_id} → {self.recipient_type}:{self.recipient_id}>"
