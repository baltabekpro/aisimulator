import uuid
from sqlalchemy import Column, String, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from core.db.base_class import Base

class Gift(Base):
    """Model for gift catalog items."""
    
    # Change table name to plural form
    __tablename__ = "gifts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gift_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    emoji = Column(String, nullable=True)
    price = Column(Integer, nullable=False, default=0)
    effect = Column(JSON, nullable=True)  # Stores effect data as JSON
