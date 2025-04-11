from sqlalchemy.orm import Session
import uuid
import logging
from typing import List, Dict, Any, Optional

from core.db.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

def get_user_profile(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Получить профиль пользователя
    """
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if not profile:
            return None
        
        return {
            "id": str(profile.id),
            "user_id": str(profile.user_id),
            "name": profile.name,
            "age": profile.age,
            "gender": profile.gender,
            "location": profile.location,
            "bio": profile.bio,
            "interests": profile.interests or [],
            "matching_preferences": profile.matching_preferences or {},
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
        }
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return None

def create_or_update_profile(db: Session, user_id: str, 
                           profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Создать или обновить профиль пользователя
    """
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if not profile:
            # Создаем новый профиль
            profile = UserProfile(
                id=uuid.uuid4(),
                user_id=user_id,
                name=profile_data.get("name"),
                age=profile_data.get("age"),
                gender=profile_data.get("gender"),
                location=profile_data.get("location"),
                bio=profile_data.get("bio"),
                interests=profile_data.get("interests", []),
                matching_preferences=profile_data.get("matching_preferences", {})
            )
            db.add(profile)
        else:
            # Обновляем существующий профиль
            for key, value in profile_data.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)
        
        db.commit()
        db.refresh(profile)
        
        return {
            "id": str(profile.id),
            "user_id": str(profile.user_id),
            "name": profile.name,
            "age": profile.age,
            "gender": profile.gender,
            "location": profile.location,
            "bio": profile.bio,
            "interests": profile.interests or [],
            "matching_preferences": profile.matching_preferences or {},
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating user profile: {e}")
        return None

def get_all_interests(db: Session) -> List[str]:
    """
    Получить список всех доступных интересов
    """
    # Список предопределенных интересов
    DEFAULT_INTERESTS = [
        "Путешествия", "Кино", "Музыка", "Литература", "Спорт",
        "Кулинария", "Фотография", "Искусство", "Танцы", "Йога",
        "Технологии", "Наука", "История", "Мода", "Животные",
        "Игры", "Саморазвитие", "Рукоделие", "Природа", "Автомобили"
    ]
    
    try:
        # Можно также добавить логику для получения интересов из базы данных,
        # если они хранятся в отдельной таблице
        return DEFAULT_INTERESTS
    except Exception as e:
        logger.error(f"Error getting interests: {e}")
        return DEFAULT_INTERESTS  # Возвращаем предопределенный список в случае ошибки