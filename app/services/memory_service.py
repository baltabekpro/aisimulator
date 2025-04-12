"""
Memory service - handles operations with character memories
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

def get_memories(db: Session, character_id: str, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve memories for a character
    
    If user_id is provided, retrieves only memories for the specific user
    Otherwise, retrieves general character memories
    """
    try:
        # Проверяем наличие представления memory_entries_view
        view_exists = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.views 
                WHERE table_name = 'memory_entries_view'
            )
        """)).scalar()
        
        if view_exists:
            # Используем представление, если оно существует
            if user_id:
                query = text("""
                    SELECT id, memory_type, category, content, importance, created_at
                    FROM memory_entries_view
                    WHERE character_id::text = :character_id 
                    AND user_id::text = :user_id
                    AND (is_active IS NULL OR is_active = TRUE)
                    ORDER BY importance DESC, created_at DESC
                    LIMIT :limit
                """)
                result = db.execute(query, {
                    "character_id": character_id,
                    "user_id": user_id,
                    "limit": limit
                })
            else:
                query = text("""
                    SELECT id, memory_type, category, content, importance, created_at
                    FROM memory_entries_view
                    WHERE character_id::text = :character_id
                    AND (is_active IS NULL OR is_active = TRUE)
                    ORDER BY importance DESC, created_at DESC
                    LIMIT :limit
                """)
                result = db.execute(query, {
                    "character_id": character_id,
                    "limit": limit
                })
        else:
            # Используем прямой запрос к таблице с учетом обоих полей
            if user_id:
                query = text("""
                    SELECT id, 
                           COALESCE(memory_type, type, 'unknown') as memory_type, 
                           COALESCE(category, 'general') as category, 
                           content, 
                           importance, 
                           created_at
                    FROM memory_entries
                    WHERE character_id::text = :character_id 
                    AND user_id::text = :user_id
                    AND (is_active IS NULL OR is_active = TRUE)
                    ORDER BY importance DESC, created_at DESC
                    LIMIT :limit
                """)
                result = db.execute(query, {
                    "character_id": character_id,
                    "user_id": user_id,
                    "limit": limit
                })
            else:
                query = text("""
                    SELECT id, 
                           COALESCE(memory_type, type, 'unknown') as memory_type, 
                           COALESCE(category, 'general') as category, 
                           content, 
                           importance, 
                           created_at
                    FROM memory_entries
                    WHERE character_id::text = :character_id
                    AND (is_active IS NULL OR is_active = TRUE)
                    ORDER BY importance DESC, created_at DESC
                    LIMIT :limit
                """)
                result = db.execute(query, {
                    "character_id": character_id,
                    "limit": limit
                })

        memories = []
        for row in result:
            memories.append({
                "id": str(row[0]),
                "type": row[1],  # Используем memory_type, но клиентам предоставляем как type для обратной совместимости
                "category": row[2],
                "content": row[3],
                "importance": row[4] if row[4] is not None else 5,
                "created_at": row[5].isoformat() if row[5] else None
            })
        
        return memories
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        db.rollback()
        return []

def create_memory(
    db: Session, 
    character_id: str, 
    user_id: str, 
    memory_type: str,
    content: str, 
    importance: int = 5,
    category: str = "general"
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
            memory_type,
            category,
            content,
            importance,
            created_at,
            updated_at,
            is_active
        ) VALUES (
            uuid_generate_v4(),
            :character_id::uuid,
            :user_id::uuid,
            :memory_type,
            :memory_type,
            :category,
            :content,
            :importance,
            NOW(),
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
            "category": category,
            "content": content,
            "importance": importance
        })
        db.commit()
        return result.scalar()
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating memory: {e}")
        return None

def check_duplicate_memory(
    db: Session,
    character_id: str,
    content: str
) -> bool:
    """
    Check if a similar memory already exists
    """
    query = text("""
        SELECT EXISTS (
            SELECT 1 FROM memory_entries
            WHERE character_id::text = :character_id
            AND content = :content
        )
    """)
    
    try:
        result = db.execute(query, {
            "character_id": character_id,
            "content": content
        })
        return result.scalar()
    except Exception as e:
        logger.error(f"Error checking duplicate memory: {e}")
        return False

def delete_memory(db: Session, memory_id: str) -> bool:
    """
    Delete a memory entry
    """
    query = text("""
        DELETE FROM memory_entries
        WHERE id::text = :memory_id
    """)
    
    try:
        db.execute(query, {"memory_id": memory_id})
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting memory: {e}")
        return False

def mark_memory_inactive(db: Session, memory_id: str) -> bool:
    """
    Mark a memory as inactive instead of deleting it
    """
    query = text("""
        UPDATE memory_entries
        SET is_active = FALSE, updated_at = NOW()
        WHERE id::text = :memory_id
    """)
    
    try:
        db.execute(query, {"memory_id": memory_id})
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking memory as inactive: {e}")
        return False

def get_memory_counts(db: Session, character_id: str) -> Dict[str, int]:
    """
    Get counts of memories by type for a character
    """
    query = text("""
        SELECT 
            COALESCE(memory_type, type, 'unknown') as memory_type,
            COUNT(*) as count
        FROM memory_entries
        WHERE character_id::text = :character_id
        AND (is_active IS NULL OR is_active = TRUE)
        GROUP BY memory_type
    """)
    
    try:
        result = db.execute(query, {"character_id": character_id})
        counts = {}
        for row in result:
            counts[row[0]] = row[1]
        return counts
    except Exception as e:
        logger.error(f"Error getting memory counts: {e}")
        return {}
