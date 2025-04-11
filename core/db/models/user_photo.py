import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class UserPhoto(Base):
    """
    Модель для хранения фотографий пользователя
    """
    __tablename__ = "user_photos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Информация о фотографии
    url = Column(String(500), nullable=False)  # URL фотографии в хранилище
    filename = Column(String(200), nullable=False)  # Оригинальное имя файла
    content_type = Column(String(100), nullable=True)  # Тип контента (image/jpeg, image/png, ...)
    size = Column(Integer, nullable=True)  # Размер файла в байтах
    
    # Метаданные
    is_primary = Column(Boolean, default=False)  # Основная фотография профиля
    is_moderated = Column(Boolean, default=False)  # Флаг прохождения модерации
    order = Column(Integer, default=0)  # Порядок отображения
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связь с моделью пользователя
    user = relationship("User", backref="photos")
    
    def __repr__(self):
        return f"<UserPhoto {self.id}: user={self.user_id}, url={self.url}>"