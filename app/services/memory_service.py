from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

def get_character_memories(db: Session, character_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve memories for a character, optionally filtered by user
    Handles missing type column by using the actual column name
    """
    query_params = {"character_id": character_id}
    
    if user_id:
        user_filter = "AND user_id::text = :user_id::text"
        query_params["user_id"] = user_id
    else:
        user_filter = ""
    
    query = text(f"""
        SELECT 
            id, 
            character_id, 
            user_id, 
            type, 
            content, 
            importance, 
            created_at
        FROM memory_entries
        WHERE character_id::text = :character_id::text
        {user_filter}
        AND (is_active IS NULL OR is_active = TRUE)
        ORDER BY importance DESC, created_at DESC
    """)
    
    try:
        result = db.execute(query, query_params)
        return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error retrieving character memories: {str(e)}")
        return []

def create_memory(
    db: Session, 
    character_id: str, 
    user_id: str, 
    memory_type: str,
    content: str, 
    importance: int = 5
) -> Optional[str]:
    """
    Create a new memory entry
    """
    query = text("""
        INSERT INTO memory_entries (
            id,
            character_id,
            user_id,
            type,
            content,
            importance,
            created_at,
            is_active
        ) VALUES (
            uuid_generate_v4(),
            :character_id::uuid,
            :user_id::uuid,
            :memory_type,
            :content,
            :importance,
            NOW(),
            TRUE
        )
        RETURNING id
    """)
    
    try:
        result = db.execute(query, {
            "character_id": character_id,
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
            "importance": importance
        })
        db.commit()
        return result.scalar()
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating memory: {e}")
        return None
