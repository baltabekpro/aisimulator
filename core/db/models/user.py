import uuid
from datetime import datetime
import bcrypt
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class User(Base):
    """
    User model
    """
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)  # Changed from hashed_password to match the database schema
    name = Column(String(100), nullable=True)  # This is the column that was missing
    external_id = Column(String(100), nullable=True, index=True)  # Для хранения идентификатора из внешних систем (OAuth)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Добавляем property для совместимости с другими моделями
    @property
    def id(self):
        """Для совместимости с общепринятым именованием id"""
        return self.user_id
    
    # Для совместимости с методами API, которые ожидают строковое представление
    @property
    def user_id_str(self):
        """Возвращает строковое представление user_id"""
        return str(self.user_id) if self.user_id else None
    
    def set_password(self, password: str):
        """Set the user's password hash"""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Verify provided password against stored hash"""
        if not self.password_hash:
            return False
        password_bytes = password.encode('utf-8')
        stored_hash = self.password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, stored_hash)
    
    def __repr__(self):
        return f"<User {self.username}>"
