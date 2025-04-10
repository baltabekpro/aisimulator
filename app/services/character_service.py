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
