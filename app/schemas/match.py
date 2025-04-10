from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class MatchBase(BaseModel):
    user_id: str
    character_id: str
    match_strength: float = Field(ge=0.0, le=1.0, default=0.5)
    
class MatchCreate(MatchBase):
    pass

class MatchResponse(MatchBase):
    id: str
    character_name: str
    avatar_url: Optional[str] = None
    last_interaction: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class MatchList(BaseModel):
    matches: List[MatchResponse]
