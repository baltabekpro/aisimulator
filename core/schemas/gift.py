from pydantic import BaseModel
from typing import Dict, Any, Optional

class GiftRequest(BaseModel):
    """Schema for gift request."""
    gift_id: str

class GiftResponse(BaseModel):
    """Schema for gift response."""
    success: bool
    gift: Dict[str, Any]
    reaction: str
    relationship_changes: Dict[str, float]
