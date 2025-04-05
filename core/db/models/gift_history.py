import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from core.db.base_class import Base
from datetime import datetime

class GiftHistory(Base):
    """История отправки подарков."""
    
    __tablename__ = "gift_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Update foreign key references to plural table names
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("ai_partners.partner_id"), nullable=False)
    gift_id = Column(String, nullable=False)
    gift_name = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow)
