from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.api.deps import get_db, get_current_user
from app.schemas.character import CharacterResponse, CharacterFeedResponse, CharacterInteractionRequest, CharacterAvatarResponse
from app.services.character_service import (
    get_character_feed, 
    get_character_by_id,
    like_character,
    dislike_character,
    superlike_character,
    get_character_photos,
    update_character_avatar
)
from app.schemas.user import User
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/feed", response_model=List[CharacterFeedResponse])
def get_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """
    Get a feed of characters for the current user to interact with.
    """
    try:
        characters = get_character_feed(db, current_user.id, limit, offset)
        
        # Добавляем фотографии к каждому персонажу
        for character in characters:
            character_id = character.get("id")
            if character_id:
                photos = get_character_photos(character_id)
                character["photos"] = photos
                
                # Устанавливаем avatar_url как первую фотографию, если она не задана
                if not character.get("avatar_url") and photos:
                    character["avatar_url"] = photos[0]["url"]
        
        return characters
    except Exception as e:
        logger.error(f"Error retrieving character feed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve character feed")

@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(
    character_id: str = Path(..., description="Character ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific character.
    """
    character = get_character_by_id(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Добавляем фотографии персонажа
    photos = get_character_photos(character_id)
    character["photos"] = photos
    
    # Устанавливаем avatar_url как первую фотографию, если она не задана
    if not character.get("avatar_url") and photos:
        character["avatar_url"] = photos[0]["url"]
    
    return character

@router.get("/me", response_model=CharacterResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's own character/profile.
    """
    # In this implementation, we assume the user's profile info is in the same User model
    # For a more complex system, you might have a separate Character model linked to the User
    character = get_character_by_id(db, current_user.character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character profile not found")
    return character

@router.post("/{character_id}/like", status_code=200)
def like_character_endpoint(
    character_id: str = Path(..., description="Character ID to like"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Like a character (Green heart).
    """
    result = like_character(db, current_user.id, character_id)
    return {"success": True, "is_match": result.get("is_match", False)}

@router.post("/{character_id}/pass", status_code=200)
def dislike_character_endpoint(
    character_id: str = Path(..., description="Character ID to pass/dislike"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pass/Dislike a character (Red X).
    """
    dislike_character(db, current_user.id, character_id)
    return {"success": True}

@router.post("/{character_id}/superlike", status_code=200)
def superlike_character_endpoint(
    character_id: str = Path(..., description="Character ID to superlike"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Superlike a character (Blue star).
    """
    result = superlike_character(db, current_user.id, character_id)
    return {"success": True, "is_match": result.get("is_match", False)}

# Alternative endpoints for the same actions using request body
@router.post("/interactions/like", status_code=200)
def like_character_body(
    interaction: CharacterInteractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Like a character using request body.
    """
    result = like_character(db, current_user.id, interaction.character_id)
    return {"success": True, "is_match": result.get("is_match", False)}

@router.post("/interactions/dislike", status_code=200)
def dislike_character_body(
    interaction: CharacterInteractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pass/Dislike a character using request body.
    """
    dislike_character(db, current_user.id, interaction.character_id)
    return {"success": True}

@router.post("/interactions/superlike", status_code=200)
def superlike_character_body(
    interaction: CharacterInteractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Superlike a character using request body.
    """
    result = superlike_character(db, current_user.id, interaction.character_id)
    return {"success": True, "is_match": result.get("is_match", False)}

# Настройки загрузки фотографий персонажей
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/jpg"]

@router.post("/{character_id}/avatar", response_model=CharacterAvatarResponse)
async def upload_character_avatar(
    character_id: str = Path(..., description="Character ID"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CharacterAvatarResponse:
    """
    Upload and update character avatar
    """
    # Проверка типа файла
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
    # Проверка размера
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_PHOTO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowable ({MAX_PHOTO_SIZE / 1024 / 1024} MB)"
        )
    # Upload and update avatar
    url = update_character_avatar(db, character_id, file.file, file.filename, content_type=file.content_type)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found or failed to update avatar"
        )
    return CharacterAvatarResponse(url=url)
