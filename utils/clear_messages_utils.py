"""
Utility functions for clearing message history from the database.
These are separated from the command-line script to allow importing from API endpoints.
"""

import logging
from typing import Optional
from uuid import UUID

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def clear_messages(character_id: Optional[str] = None, clear_all: bool = False) -> int:
    """
    Clear message history from the database.
    
    Args:
        character_id: ID of character (if clearing messages for a specific character)
        clear_all: Flag to clear all messages
        
    Returns:
        Number of deleted messages
    """
    try:
        # Import database models and session here to avoid circular imports
        from core.db.session import SessionLocal
        from core.db.models.message import Message
        from core.db.models.event import Event
        
        db = SessionLocal()
        try:
            # Define deletion query
            delete_count = 0
            
            # Clear messages
            if clear_all:
                # Delete all messages
                delete_count = db.query(Message).delete()
                logger.info(f"Deleted {delete_count} messages from database")
                
                # Also delete memory events
                memory_count = db.query(Event).filter(Event.event_type == 'memory').delete()
                logger.info(f"Deleted {memory_count} memory records")
            elif character_id:
                # Try to convert to UUID (for validation)
                try:
                    char_uuid = UUID(character_id)
                    
                    # Delete messages where the character is sender or recipient
                    delete_count = db.query(Message).filter(
                        (Message.sender_id == char_uuid) | 
                        (Message.recipient_id == char_uuid)
                    ).delete()
                    logger.info(f"Deleted {delete_count} messages for character {character_id}")
                    
                    # Delete related memory events
                    memory_count = db.query(Event).filter(
                        (Event.character_id == char_uuid) & 
                        (Event.event_type == 'memory')
                    ).delete()
                    logger.info(f"Deleted {memory_count} memory records for character {character_id}")
                except ValueError:
                    logger.error(f"Invalid UUID format for character_id: {character_id}")
                    return 0
            else:
                logger.error("No deletion parameters specified. Use character_id or clear_all=True")
                return 0
                
            # Commit changes
            db.commit()
            return delete_count
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error clearing messages: {e}")
        return 0
