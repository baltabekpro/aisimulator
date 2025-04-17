from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

def get_character_feed(db: Session, user_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get a feed of characters for the current user to interact with.
    Excludes characters that the user has already liked/disliked.
    """
    query = text("""
        SELECT 
            c.id, 
            c.name, 
            c.age, 
            c.gender, 
            c.personality as personality_traits, 
            c.interests, 
            c.background,
            c.avatar_url
        FROM 
            characters c
        WHERE 
            c.id NOT IN (
                -- Get characters user has interacted with
                SELECT DISTINCT i.character_id 
                FROM interactions i 
                WHERE i.user_id = :user_id
            )
            AND c.is_active = TRUE
        ORDER BY 
            -- Randomize to get different suggestions each time
            random()
        LIMIT :limit
        OFFSET :offset
    """)
    
    try:
        result = db.execute(query, {"user_id": user_id, "limit": limit, "offset": offset})
        characters = []
        
        for row in result:
            character = dict(row)
            
            # Parse JSON from strings if needed
            for field in ['personality_traits', 'interests']:
                if isinstance(character.get(field), str):
                    import json
                    try:
                        character[field] = json.loads(character[field])
                    except Exception:
                        character[field] = []
            
            characters.append(character)
        
        return characters
    except Exception as e:
        logger.error(f"Error getting character feed: {e}")
        return []

def get_character_by_id(db: Session, character_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a character by ID
    """
    query = text("""
        SELECT 
            c.id, 
            c.name, 
            c.age, 
            c.gender, 
            c.personality as personality_traits, 
            c.interests, 
            c.background,
            c.avatar_url,
            c.created_at,
            c.updated_at
        FROM 
            characters c
        WHERE 
            c.id = :character_id
    """)
    
    try:
        result = db.execute(query, {"character_id": character_id}).fetchone()
        if result:
            character = dict(result)
            
            # Parse JSON from strings if needed
            for field in ['personality_traits', 'interests']:
                if isinstance(character.get(field), str):
                    import json
                    try:
                        character[field] = json.loads(character[field])
                    except Exception:
                        character[field] = []
                        
            return character
        return None
    except Exception as e:
        logger.error(f"Error getting character by ID: {e}")
        return None

def like_character(db: Session, user_id: str, character_id: str) -> Dict[str, Any]:
    """
    Like a character and check if it's a match
    """
    try:
        # Create a like interaction
        query = text("""
            INSERT INTO interactions (id, user_id, character_id, interaction_type, created_at)
            VALUES (:id, :user_id, :character_id, 'like', NOW())
            RETURNING id
        """)
        
        interaction_id = str(uuid.uuid4())
        db.execute(query, {
            "id": interaction_id,
            "user_id": user_id,
            "character_id": character_id
        })
        
        # For demo purposes, all likes are matches with a small random delay
        is_match = True
        
        # If it's a match, create a match record
        if is_match:
            match_query = text("""
                INSERT INTO matches (id, user_id, character_id, match_strength, created_at)
                VALUES (:id, :user_id, :character_id, :match_strength, NOW())
                RETURNING id
            """)
            
            import random
            match_strength = round(random.uniform(0.7, 1.0), 2)
            
            match_id = str(uuid.uuid4())
            db.execute(match_query, {
                "id": match_id,
                "user_id": user_id,
                "character_id": character_id,
                "match_strength": match_strength
            })
            
            db.commit()
            return {"is_match": True, "match_id": match_id, "match_strength": match_strength}
        
        db.commit()
        return {"is_match": False}
    except Exception as e:
        db.rollback()
        logger.error(f"Error liking character: {e}")
        return {"is_match": False, "error": str(e)}

def dislike_character(db: Session, user_id: str, character_id: str) -> Dict[str, Any]:
    """
    Dislike/pass on a character
    """
    try:
        # Create a dislike interaction
        query = text("""
            INSERT INTO interactions (id, user_id, character_id, interaction_type, created_at)
            VALUES (:id, :user_id, :character_id, 'dislike', NOW())
            RETURNING id
        """)
        
        interaction_id = str(uuid.uuid4())
        db.execute(query, {
            "id": interaction_id,
            "user_id": user_id,
            "character_id": character_id
        })
        
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        logger.error(f"Error disliking character: {e}")
        return {"success": False, "error": str(e)}

def superlike_character(db: Session, user_id: str, character_id: str) -> Dict[str, Any]:
    """
    Superlike a character - higher priority match
    """
    try:
        # Create a superlike interaction
        query = text("""
            INSERT INTO interactions (id, user_id, character_id, interaction_type, created_at)
            VALUES (:id, :user_id, :character_id, 'superlike', NOW())
            RETURNING id
        """)
        
        interaction_id = str(uuid.uuid4())
        db.execute(query, {
            "id": interaction_id,
            "user_id": user_id,
            "character_id": character_id
        })
        
        # For demo purposes, all superlikes are matches
        is_match = True
        
        # If it's a match, create a match record with high match strength
        if is_match:
            match_query = text("""
                INSERT INTO matches (id, user_id, character_id, match_strength, created_at)
                VALUES (:id, :user_id, :character_id, :match_strength, NOW())
                RETURNING id
            """)
            
            import random
            match_strength = round(random.uniform(0.9, 1.0), 2)  # Higher match strength for superlike
            
            match_id = str(uuid.uuid4())
            db.execute(match_query, {
                "id": match_id,
                "user_id": user_id,
                "character_id": character_id,
                "match_strength": match_strength
            })
            
            db.commit()
            return {"is_match": True, "match_id": match_id, "match_strength": match_strength}
        
        db.commit()
        return {"is_match": False}
    except Exception as e:
        db.rollback()
        logger.error(f"Error superliking character: {e}")
        return {"is_match": False, "error": str(e)}

def generate_character_photo_url(character_id: str, photo_number: int = 1) -> str:
    """
    Генерирует URL для фотографии персонажа.
    Использует MinIO для хранения файлов.
    
    Args:
        character_id: ID персонажа
        photo_number: Номер фотографии
        
    Returns:
        URL фотографии
    """
    from app.config import settings
    import os
    
    # Базовый URL для доступа к MinIO
    # В production это будет https://storage.yourdomain.com или похожий URL
    base_url = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")
    bucket = os.getenv("MINIO_BUCKET", "default")
    
    # Формируем путь к фотографии в формате characters/{character_id}/{photo_number}.jpg
    photo_path = f"characters/{character_id}/{photo_number}.jpg"
    
    # Полный URL
    url = f"{base_url}/{bucket}/{photo_path}"
    
    return url

def get_character_photos(character_id: str, count: int = 3) -> List[Dict[str, Any]]:
    """
    Получает список фотографий персонажа.
    
    Args:
        character_id: ID персонажа
        count: Количество фотографий
        
    Returns:
        Список фотографий в формате [{"id": "...", "url": "...", "is_primary": True/False}]
    """
    photos = []
    
    for i in range(1, count + 1):
        photo_id = f"{character_id}_photo_{i}"
        url = generate_character_photo_url(character_id, i)
        is_primary = (i == 1)  # Первая фотография считается основной
        
        photos.append({
            "id": photo_id,
            "url": url,
            "is_primary": is_primary
        })
    
    return photos
