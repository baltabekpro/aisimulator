"""
Memory schemas for API.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID

class MemoryBase(BaseModel):
    """Base memory schema"""
    memory_type: str = Field(default="unknown")
    category: str = Field(default="general")
    content: str
    importance: int = Field(default=5, ge=1, le=10)

class MemoryCreate(MemoryBase):
    """Schema for creating a memory"""
    pass

class MemoryUpdate(MemoryBase):
    """Schema for updating a memory"""
    memory_type: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    importance: Optional[int] = None
    is_active: Optional[bool] = None

class MemorySchema(MemoryBase):
    """Schema for returning a memory"""
    id: str
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True
