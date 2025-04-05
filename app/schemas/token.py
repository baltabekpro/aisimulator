"""
Token schemas for authentication.
"""
from pydantic import BaseModel
from typing import Optional

class TokenPayload(BaseModel):
    """Token payload schema"""
    sub: str
    exp: Optional[int] = None
    token_type: str = "access"

class Token(BaseModel):
    """Token schema for API responses"""
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

class RefreshToken(BaseModel):
    """Refresh token schema."""
    refresh_token: str
