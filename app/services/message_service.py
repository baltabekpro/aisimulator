from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import List, Dict, Any, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

def get_messages(db: Session, limit: int = 100, offset: int = 0):
    """
    Retrieve messages with proper sender and recipient names.
    Fixed the type mismatch by explicitly casting UUIDs to text.
    """
    query = text("""
        SELECT 
            m.id, 
            m.sender_id, 
            m.sender_type, 
            m.recipient_id, 
            m.recipient_type, 
            m.content, 
            m.emotion, 
            m.created_at,
            CASE 
                WHEN m.sender_type = 'user' AND u1.username IS NOT NULL THEN u1.username
                WHEN m.sender_type = 'character' AND c1.name IS NOT NULL THEN c1.name
                ELSE m.sender_id::text
            END as sender_name,
            CASE 
                WHEN m.recipient_type = 'user' AND u2.username IS NOT NULL THEN u2.username
                WHEN m.recipient_type = 'character' AND c2.name IS NOT NULL THEN c2.name
                ELSE m.recipient_id::text
            END as recipient_name
        FROM messages m
        LEFT JOIN users u1 ON m.sender_id::text = u1.user_id::text AND m.sender_type = 'user'
        LEFT JOIN characters c1 ON m.sender_id::text = c1.id::text AND m.sender_type = 'character'
        LEFT JOIN users u2 ON m.recipient_id::text = u2.user_id::text AND m.recipient_type = 'user'
        LEFT JOIN characters c2 ON m.recipient_id::text = c2.id::text AND m.recipient_type = 'character'
        ORDER BY m.created_at DESC
        LIMIT :limit
        OFFSET :offset
    """)
    
    try:
        result = db.execute(query, {"limit": limit, "offset": offset})
        return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error retrieving messages: {e}")
        return []

def get_message_by_id(db: Session, message_id: str) -> Optional[Dict[str, Any]]:
    """
    Get specific message by ID
    """
    query = text("""
        SELECT 
            m.id, 
            m.sender_id, 
            m.sender_type, 
            m.recipient_id, 
            m.recipient_type, 
            m.content, 
            m.emotion, 
            m.created_at,
            m.is_read,
            m.is_gift,
            CASE 
                WHEN m.sender_type = 'user' AND u1.username IS NOT NULL THEN u1.username
                WHEN m.sender_type = 'character' AND c1.name IS NOT NULL THEN c1.name
                ELSE m.sender_id::text
            END as sender_name,
            CASE 
                WHEN m.recipient_type = 'user' AND u2.username IS NOT NULL THEN u2.username
                WHEN m.recipient_type = 'character' AND c2.name IS NOT NULL THEN c2.name
                ELSE m.recipient_id::text
            END as recipient_name
        FROM messages m
        LEFT JOIN users u1 ON m.sender_id::text = u1.user_id::text AND m.sender_type = 'user'
        LEFT JOIN characters c1 ON m.sender_id::text = c1.id::text AND m.sender_type = 'character'
        LEFT JOIN users u2 ON m.recipient_id::text = u2.user_id::text AND m.recipient_type = 'user'
        LEFT JOIN characters c2 ON m.recipient_id::text = c2.id::text AND m.recipient_type = 'character'
        WHERE m.id = :message_id::uuid
    """)
    
    try:
        result = db.execute(query, {"message_id": message_id}).fetchone()
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error retrieving message by ID: {e}")
        return None

def save_message(
    db: Session, 
    sender_id: str, 
    sender_type: str, 
    recipient_id: str, 
    recipient_type: str, 
    content: str, 
    emotion: str = "neutral", 
    is_read: bool = False, 
    is_gift: bool = False
) -> Optional[str]:
    """
    Save a message to the database with explicit UUID conversion
    """
    if isinstance(sender_id, uuid.UUID):
        sender_id = str(sender_id)
        
    if isinstance(recipient_id, uuid.UUID):
        recipient_id = str(recipient_id)
    
    query = text("""
        INSERT INTO messages (
            id, 
            sender_id, 
            sender_type, 
            recipient_id, 
            recipient_type, 
            content, 
            emotion, 
            is_read, 
            is_gift,
            created_at
        ) VALUES (
            uuid_generate_v4(), 
            :sender_id::uuid, 
            :sender_type, 
            :recipient_id::uuid, 
            :recipient_type, 
            :content, 
            :emotion, 
            :is_read, 
            :is_gift,
            NOW()
        )
        RETURNING id
    """)
    
    try:
        result = db.execute(query, {
            "sender_id": sender_id,
            "sender_type": sender_type,
            "recipient_id": recipient_id,
            "recipient_type": recipient_type,
            "content": content,
            "emotion": emotion,
            "is_read": is_read,
            "is_gift": is_gift
        })
        db.commit()
        return result.scalar()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving message: {e}")
        return None

def mark_message_as_read(db: Session, message_id: str) -> bool:
    """
    Mark a message as read
    """
    query = text("""
        UPDATE messages
        SET is_read = TRUE
        WHERE id = :message_id::uuid
        RETURNING id
    """)
    
    try:
        result = db.execute(query, {"message_id": message_id})
        db.commit()
        return result.rowcount > 0
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking message as read: {e}")
        return False