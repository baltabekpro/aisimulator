from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db, get_current_user
from app.schemas.user import User
from app.schemas.match import MatchResponse
from app.services.match_service import get_user_matches

router = APIRouter()

@router.get("/", response_model=List[MatchResponse])
def get_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get all matches for the current user.
    """
    matches = get_user_matches(db, current_user.id, limit, offset)
    return matches
