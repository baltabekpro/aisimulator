from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from app.api.deps import get_current_user
from app.config import settings

router = APIRouter()

# --- Models ---
class LikeRequest(BaseModel):
    character_id: str = Field(..., description="ID of the character to like/dislike")

class InteractionResponse(BaseModel):
    success: bool
    message: str
    match: bool = False
    match_id: Optional[str] = None

class ProfileFeedItem(BaseModel):
    id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    personality_traits: List[str] = []
    interests: List[str] = []
    background: Optional[str] = None
    photos: List[str] = []
    
class MatchProfile(BaseModel):
    id: str
    name: str
    age: Optional[int] = None
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    photo_url: Optional[str] = None
    unread_count: int = 0

# --- Endpoints ---
@router.post("/characters/{character_id}/like", response_model=InteractionResponse)
async def like_character(
    character_id: str = Path(..., description="Character ID to like"),
    current_user = Depends(get_current_user)
):
    """Like a character - user shows interest in this character"""
    # Here would be the actual implementation to record the like in the database
    # For demo purposes, let's just return a successful response
    # In a real implementation, you would check if this creates a match
    
    is_match = False  # Random logic for demo - in reality check db for mutual like
    match_id = None
    
    # Simulate random match (5% chance)
    import random
    if random.random() < 0.05:
        is_match = True
        match_id = str(uuid.uuid4())
    
    return InteractionResponse(
        success=True,
        message=f"Successfully liked character {character_id}",
        match=is_match,
        match_id=match_id if is_match else None
    )

@router.post("/characters/{character_id}/dislike", response_model=InteractionResponse)
async def dislike_character(
    character_id: str = Path(..., description="Character ID to dislike/pass"),
    current_user = Depends(get_current_user)
):
    """Dislike/pass a character - user is not interested in this character"""
    # Record the dislike/pass in the database
    return InteractionResponse(
        success=True,
        message=f"Successfully passed on character {character_id}",
        match=False
    )

@router.post("/characters/{character_id}/superlike", response_model=InteractionResponse)
async def superlike_character(
    character_id: str = Path(..., description="Character ID to superlike"),
    current_user = Depends(get_current_user)
):
    """Superlike a character - shows special interest in this character"""
    # Record the superlike in the database
    # Superlike might have special behavior like immediate notification
    
    # 20% chance of match for superlikes
    import random
    is_match = random.random() < 0.2
    match_id = str(uuid.uuid4()) if is_match else None
    
    return InteractionResponse(
        success=True,
        message=f"Successfully superliked character {character_id}",
        match=is_match,
        match_id=match_id
    )

@router.get("/discover/characters", response_model=List[ProfileFeedItem])
async def get_character_feed(
    limit: int = Query(10, description="Number of profiles to return"),
    current_user = Depends(get_current_user)
):
    """Get a feed of character profiles for the discovery/swiping interface"""
    # In a real implementation, you would:
    # 1. Fetch profiles from DB that the user hasn't seen/swiped
    # 2. Apply any filters/preferences the user has set
    # 3. Return the next batch of profiles
    
    # For demo purposes, return sample data
    profiles = [
        ProfileFeedItem(
            id=str(uuid.uuid4()),
            name="Алиса",
            age=25,
            gender="female",
            personality_traits=["friendly", "creative", "outgoing"],
            interests=["art", "music", "travel"],
            background="Художница из Москвы. Люблю путешествовать и рисовать новые места.",
            photos=["https://example.com/photos/1.jpg", "https://example.com/photos/2.jpg"]
        )
    ]
    
    # Add more sample profiles
    names = ["София", "Мария", "Виктория", "Ева", "Анна"]
    for name in names:
        profiles.append(
            ProfileFeedItem(
                id=str(uuid.uuid4()),
                name=name,
                age=20 + len(name),  # Just for variety
                gender="female",
                personality_traits=["intelligent", "caring", "funny"],
                interests=["books", "movies", "cooking"],
                background=f"{name} любит проводить время в хорошей компании.",
                photos=[f"https://example.com/photos/{name.lower()}.jpg"]
            )
        )
    
    return profiles[:limit]

@router.get("/matches", response_model=List[MatchProfile])
async def get_matches(
    current_user = Depends(get_current_user)
):
    """Get the list of matches (mutual likes) for the current user"""
    # In a real implementation, fetch matches from database
    # For demo purposes, return sample data
    return [
        MatchProfile(
            id=str(uuid.uuid4()),
            name="Алиса",
            age=25,
            last_message="Привет! Как твой день?",
            last_message_time=datetime.now(),
            photo_url="https://example.com/photos/alice.jpg",
            unread_count=2
        ),
        MatchProfile(
            id=str(uuid.uuid4()),
            name="София",
            age=23,
            last_message="Было приятно пообщаться!",
            last_message_time=datetime.now(),
            photo_url="https://example.com/photos/sofia.jpg",
            unread_count=0
        )
    ]

@router.get("/notifications", response_model=dict)
async def get_notifications(
    current_user = Depends(get_current_user)
):
    """Get notifications for the current user (likes, matches, messages)"""
    # In a real implementation, fetch notifications from database
    return {
        "total_unread": 5,
        "notifications": [
            {
                "id": str(uuid.uuid4()),
                "type": "match",
                "message": "Новый мэтч с Алиса!",
                "created_at": datetime.now(),
                "is_read": False,
                "data": {
                    "character_id": str(uuid.uuid4()),
                    "character_name": "Алиса"
                }
            },
            {
                "id": str(uuid.uuid4()),
                "type": "message",
                "message": "Новое сообщение от София",
                "created_at": datetime.now(),
                "is_read": False,
                "data": {
                    "character_id": str(uuid.uuid4()),
                    "character_name": "София",
                    "message_preview": "Привет! Как дела?"
                }
            },
            {
                "id": str(uuid.uuid4()),
                "type": "like",
                "message": "Вас лайкнули!",
                "created_at": datetime.now(),
                "is_read": False,
                "data": {
                    "character_id": str(uuid.uuid4())
                }
            }
        ]
    }

# Alternative API endpoints with consistent naming
@router.post("/interactions/like", response_model=InteractionResponse)
async def like_character_alt(like_request: LikeRequest, current_user = Depends(get_current_user)):
    """Alternative endpoint for liking a character"""
    return await like_character(like_request.character_id, current_user)

@router.post("/interactions/dislike", response_model=InteractionResponse)
async def dislike_character_alt(like_request: LikeRequest, current_user = Depends(get_current_user)):
    """Alternative endpoint for disliking a character"""
    return await dislike_character(like_request.character_id, current_user)

@router.post("/interactions/superlike", response_model=InteractionResponse)
async def superlike_character_alt(like_request: LikeRequest, current_user = Depends(get_current_user)):
    """Alternative endpoint for superliking a character"""
    return await superlike_character(like_request.character_id, current_user)
