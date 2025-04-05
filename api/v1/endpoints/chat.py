from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from typing import Dict, Any, List

# Fix import - import directly from the models module
from core.models import User
from core import schemas
from core.services.gift import GiftService
from core.services.ai_partner import AIPartnerService
from core.services.message import MessageService
from core.services.love_rating import LoveRatingService
from api.v1.dependencies import get_db, get_current_user

# Set up logger
logger = logging.getLogger(__name__)

# Make sure the router is properly defined with the right prefix
# Remove the prefix if it's causing route registration issues
router = APIRouter()

# Add a debug route to test if the router is properly registered
@router.get("/debug", response_model=Dict[str, str])
def debug_router():
    """
    Debug endpoint to check if router is registered correctly.
    """
    return {"status": "Router working", "routes": "Available endpoints: /characters/{id}/gift, /characters/{id}/clear-history"}

# Now all endpoints will be under /chat/characters

@router.post("/characters/{character_id}/gift", response_model=schemas.GiftResponse)  # Fix the path here
def send_gift_to_character(
    character_id: str,
    gift_data: schemas.GiftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отправить подарок персонажу.
    """
    # Проверяем, существует ли персонаж
    partner_service = AIPartnerService(db)
    try:
        partner_id = UUID(character_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Invalid character ID format"
        )
    
    character = partner_service.get(partner_id)
    if not character:
        raise HTTPException(
            status_code=404,
            detail="Character not found"
        )
    
    # Отправляем подарок
    try:
        gift_service = GiftService(db)
        result = gift_service.send_gift(
            user_id=current_user.id,
            partner_id=partner_id,
            gift_id=gift_data.gift_id
        )
        
        return {
            "success": True,
            "gift": result["gift"],
            "reaction": result["reaction"],
            "relationship_changes": result["relationship_changes"]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error sending gift: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send gift"
        )

@router.post("/characters/{character_id}/clear-history", response_model=schemas.SuccessResponse)  # Fix the path here
def clear_chat_history(
    character_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Очистить историю чата с персонажем.
    """
    # Проверяем, существует ли персонаж
    partner_service = AIPartnerService(db)
    try:
        partner_id = UUID(character_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Invalid character ID format"
        )
    
    character = partner_service.get(partner_id)
    if not character:
        raise HTTPException(
            status_code=404,
            detail="Character not found"
        )
    
    # Очищаем историю сообщений
    try:
        message_service = MessageService(db)
        # Удаляем все сообщения между пользователем и персонажем
        messages = message_service.get_conversation(current_user.id, partner_id)
        
        for message in messages:
            db.delete(message)
        
        db.commit()
        
        return {"success": True, "message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to clear chat history"
        )

@router.get("/characters/{character_id}/relationship", response_model=Dict[str, Any])  # Fix the path here
def get_character_relationship(
    character_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить информацию об отношениях с персонажем.
    """
    # Проверяем, существует ли персонаж
    partner_service = AIPartnerService(db)
    try:
        partner_id = UUID(character_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Invalid character ID format"
        )
    
    character = partner_service.get(partner_id)
    if not character:
        raise HTTPException(
            status_code=404,
            detail="Character not found"
        )
    
    # Получаем информацию об отношениях
    try:
        love_rating_service = LoveRatingService(db)
        relationship_info = love_rating_service.analyze_recent_changes(current_user.id, partner_id)
        
        # Преобразуем информацию в более полный формат для отображения
        current_rating = relationship_info.get("current_rating", 50)
        
        return {
            "rating": {
                "value": current_rating,
                "display": f"{current_rating}%",
                "max": 100
            },
            "emotions": {
                "friendship": {
                    "value": min(1.0, current_rating / 80.0),
                    "percentage": int(min(1.0, current_rating / 80.0) * 100),
                    "display": f"{int(min(1.0, current_rating / 80.0) * 100)}%"
                },
                "romance": {
                    "value": min(1.0, max(0, current_rating - 40) / 60.0),
                    "percentage": int(min(1.0, max(0, current_rating - 40) / 60.0) * 100),
                    "display": f"{int(min(1.0, max(0, current_rating - 40) / 60.0) * 100)}%"
                },
                "trust": {
                    "value": min(1.0, current_rating / 90.0),
                    "percentage": int(min(1.0, current_rating / 90.0) * 100),
                    "display": f"{int(min(1.0, current_rating / 90.0) * 100)}%"
                }
            },
            "status": {
                "level": _calculate_relationship_level(current_rating),
                "label": _get_relationship_status(current_rating),
                "emoji": _get_status_emoji(current_rating),
                "description": _get_status_description(current_rating)
            },
            "recent_changes": relationship_info.get("recent_changes", [])
        }
    except Exception as e:
        logger.error(f"Error getting relationship info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve relationship information"
        )

# Helper functions for relationship status
def _calculate_relationship_level(rating: int) -> int:
    if rating < 20:
        return 1
    elif rating < 40:
        return 2
    elif rating < 60:
        return 3
    elif rating < 80:
        return 4
    else:
        return 5

def _get_relationship_status(rating: int) -> str:
    if rating < 20:
        return "Холодные"
    elif rating < 40:
        return "Знакомые"
    elif rating < 60:
        return "Друзья"
    elif rating < 80:
        return "Близкие друзья"
    elif rating < 95:
        return "Романтические отношения"
    else:
        return "Глубокая привязанность"

def _get_status_emoji(rating: int) -> str:
    if rating < 20:
        return "🧊"  # Cold
    elif rating < 40:
        return "👤"  # Acquaintance
    elif rating < 60:
        return "👭"  # Friends
    elif rating < 80:
        return "💫"  # Close friends
    elif rating < 95:
        return "💘"  # Romance
    else:
        return "💞"  # Deep love

def _get_status_description(rating: int) -> str:
    if rating < 20:
        return "Отношения в самом начале или напряженные"
    elif rating < 40:
        return "Знакомые, общение на формальном уровне"
    elif rating < 60:
        return "Дружеские отношения, общие интересы"
    elif rating < 80:
        return "Близкая дружба, доверительные отношения"
    elif rating < 95:
        return "Романтические чувства, сильная привязанность"
    else:
        return "Глубокая эмоциональная связь и привязанность"