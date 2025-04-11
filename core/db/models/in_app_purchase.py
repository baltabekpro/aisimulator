import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Float, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.db.base import Base

class InAppPurchase(Base):
    """
    Модель для хранения информации о покупках внутри приложения
    """
    __tablename__ = "in_app_purchases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    product_id = Column(String(100), nullable=False, index=True)
    transaction_id = Column(String(100), nullable=False, unique=True)
    receipt_data = Column(Text, nullable=False)  # Данные чека в формате base64
    purchase_date = Column(DateTime(timezone=True), nullable=False)
    expiration_date = Column(DateTime(timezone=True), nullable=True)  # Для подписок
    status = Column(String(20), nullable=False, default="completed")  # completed, refunded, expired
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    environment = Column(String(20), nullable=False, default="production")  # production, sandbox
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связь с моделью пользователя
    user = relationship("User", backref="purchases")
    
    def __repr__(self):
        return f"<InAppPurchase {self.product_id} for user {self.user_id}>"


class PurchaseProduct(Base):
    """
    Модель для хранения информации о доступных для покупки товарах
    """
    __tablename__ = "purchase_products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), nullable=False)  # consumable, non-consumable, subscription
    price_tier = Column(String(20), nullable=False)
    price_usd = Column(Float, nullable=False)  # Базовая цена в USD
    stars_amount = Column(Integer, nullable=True)  # Для товаров с виртуальной валютой
    duration_days = Column(Integer, nullable=True)  # Для подписок
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<PurchaseProduct {self.product_id} - {self.name}>"