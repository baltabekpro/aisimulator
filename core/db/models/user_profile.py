import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class UserProfile(Base):
    """
    Модель профиля пользователя с расширенной информацией
    """
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, unique=True)
    
    # Основная информация
    name = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    location = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Поля для социальных взаимодействий
    interests = Column(JSON, default=list)  # Хранение интересов как JSON массив
    matching_preferences = Column(JSON, default=dict)  # Настройки предпочтений для алгоритма сватовства
    
    # Информация о создании и обновлении
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связь с основной моделью пользователя
    user = relationship("User", backref="profile", lazy="joined")
    
    def __repr__(self):
        return f"<UserProfile {self.id}: user={self.user_id}>"