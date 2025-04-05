from sqlalchemy import Column, ForeignKey, Integer, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.db.base_class import Base
import uuid

class LoveRating(Base):
    __tablename__ = "love_rating"
    rating_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.user_id"))
    partner_id = Column(UUID, ForeignKey("ai_partners.partner_id"))
    score = Column(Integer, default=50)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Add check constraint to ensure score is between 0 and 100
    __table_args__ = (
        CheckConstraint('score >= 0 AND score <= 100', name='check_score_range'),
    )
