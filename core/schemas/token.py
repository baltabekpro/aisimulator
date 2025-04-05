from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for data contained in authentication token."""
    user_id: Optional[str] = None
