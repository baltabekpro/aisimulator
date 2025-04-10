from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

def get_user_matches(db: Session, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get all matches for a user
    """
    # Convert user_id to string if it's a UUID object
    if isinstance(user_id, uuid.UUID):
        user_id = str(user_id)
        
    query = text("""
        SELECT 
            m.id,
            m.user_id,
            m.character_id,
            c.name AS character_name,
            c.avatar_url,
            m.match_strength,
            m.created_at,
            (
                SELECT MAX(msg.created_at)
                FROM messages msg
                WHERE 
                    (msg.sender_id::text = m.user_id::text AND msg.recipient_id::text = m.character_id::text) OR
                    (msg.sender_id::text = m.character_id::text AND msg.recipient_id::text = m.user_id::text)
            ) AS last_interaction
        FROM 
            matches m
        JOIN 
            characters c ON m.character_id::text = c.id::text
        WHERE 
            m.user_id::text = :user_id::text
        ORDER BY 
            last_interaction DESC NULLS LAST,
            m.created_at DESC
        LIMIT :limit
        OFFSET :offset
    """)
    
    try:
        result = db.execute(query, {"user_id": user_id, "limit": limit, "offset": offset})
        return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error getting user matches: {e}")
        return []

def get_match_by_id(db: Session, match_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific match by ID
    """
    query = text("""
        SELECT 
            m.id,
            m.user_id,
            m.character_id,
            c.name AS character_name,
            c.avatar_url,
            m.match_strength,
            m.created_at
        FROM 
            matches m
        JOIN 
            characters c ON m.character_id::text = c.id::text
        WHERE 
            m.id::text = :match_id::text
    """)
    
    try:
        result = db.execute(query, {"match_id": match_id}).fetchone()
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error getting match by ID: {e}")
        return None

def create_match(db: Session, user_id: str, character_id: str, match_strength: float = 0.5) -> Optional[str]:
    """
    Create a new match between user and character
    """
    query = text("""
        INSERT INTO matches (
            id,
            user_id,
            character_id,
            match_strength,
            created_at
        ) VALUES (
            uuid_generate_v4(),
            :user_id::uuid,
            :character_id::uuid,
            :match_strength,
            NOW()
        )
        RETURNING id
    """)
    
    try:
        result = db.execute(query, {
            "user_id": user_id,
            "character_id": character_id,
            "match_strength": match_strength
        })
        db.commit()
        return result.scalar()
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating match: {e}")
        return None
