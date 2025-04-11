import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class DeviceToken(Base):
    """
    Модель для хранения токенов устройств для отправки push-уведомлений
    """
    __tablename__ = "device_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    device_token = Column(String(255), nullable=False, index=True)
    device_type = Column(String(20), nullable=False)  # ios, android, web
    app_version = Column(String(20), nullable=True)
    os_version = Column(String(20), nullable=True)
    device_model = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связь с моделью пользователя
    user = relationship("User", backref="device_tokens")
    
    def __repr__(self):
        return f"<DeviceToken {self.device_token[:10]}... for user {self.user_id}>"