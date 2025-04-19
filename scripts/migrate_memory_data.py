"""
Script to migrate memory data from events table to memory_entries table.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import json
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_character_exists(conn, character_id):
    """Check if a character exists in the database"""
    try:
        # Преобразуем character_id в строку, если это объект UUID
        character_id_str = str(character_id) if isinstance(character_id, uuid.UUID) else character_id
            
        # Используем безопасный формат запроса для PostgreSQL
        result = conn.execute(text("""
            SELECT COUNT(*) FROM characters
            WHERE id = CAST(:character_id AS UUID)
        """), {"character_id": character_id_str}).scalar()
        return result > 0
    except Exception as e:
        logger.warning(f"Error checking if character {character_id} exists: {e}")
        return False

def check_user_exists(conn, user_id):
    """Check if a user exists in the database"""
    if user_id is None:
        return False # None user_id doesn't exist, will be replaced by system user later
    try:
        user_id_str = str(user_id) if isinstance(user_id, uuid.UUID) else user_id
        result = conn.execute(text("""
            SELECT COUNT(*) FROM users
            WHERE user_id = CAST(:user_id AS UUID)
        """), {"user_id": user_id_str}).scalar()
        return result > 0
    except Exception as e:
        logger.warning(f"Error checking if user {user_id} exists: {e}")
        return False

def memory_exists(conn, character_id, content):
    """Check if a memory already exists"""
    try:
        # Преобразуем character_id в строку, если это объект UUID
        character_id_str = str(character_id) if isinstance(character_id, uuid.UUID) else character_id
            
        # Используем безопасный формат запроса для PostgreSQL
        result = conn.execute(text("""
            SELECT COUNT(*) FROM memory_entries
            WHERE character_id = CAST(:character_id AS UUID)
            AND content = :content
        """), {
            "character_id": character_id_str,
            "content": content
        }).scalar()
        return result > 0
    except Exception as e:
        logger.warning(f"Error checking memory existence: {e}")
        return False

def migrate_memory_data():
    """Migrate memory data from events table to memory_entries table"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database: {db_url}")
    engine = create_engine(db_url)
    
    # Get memory events - in its own connection to avoid transaction issues
    memory_events = []
    with engine.connect() as conn:
        try:
            memory_events = conn.execute(text("""
                SELECT id, character_id, user_id, data, created_at
                FROM events
                WHERE event_type = 'memory'
                ORDER BY created_at ASC
            """)).fetchall()
            
            logger.info(f"Found {len(memory_events)} memory events to migrate")
        except Exception as e:
            logger.error(f"Error fetching memory events: {e}")
            return False
    
    # Process events one by one - each in its own transaction
    total_memories = 0
    migrated_memories = 0
    skipped_memories = 0
    
    for event in memory_events:
        event_id = event[0]
        character_id = event[1]
        user_id = event[2]
        data = event[3]
        created_at = event[4]
        
        # Try to parse the data
        try:
            if isinstance(data, str):
                memory_data = json.loads(data)
            else:
                memory_data = data
            
            # It could be a list of memories or a single memory
            memories_to_process = []
            if isinstance(memory_data, list):
                memories_to_process.extend(memory_data)
            elif isinstance(memory_data, dict):
                memories_to_process.append(memory_data)
            
            if not memories_to_process:
                logger.warning(f"No memories found in event {event_id}")
                continue
                
            # For each memory in the event
            for memory in memories_to_process:
                total_memories += 1
                
                # Use a new connection for each memory to handle errors better
                with engine.connect() as conn:
                    with conn.begin():
                        try:
                            # Validate memory
                            if not isinstance(memory, dict):
                                logger.warning(f"Invalid memory format in event {event_id}")
                                skipped_memories += 1
                                continue
                                
                            memory_type = memory.get("type", "unknown")
                            category = memory.get("category", "general")
                            content = memory.get("content", "")
                            importance = memory.get("importance", 5)
                            
                            # Skip empty content
                            if not content:
                                logger.warning(f"Empty content in memory from event {event_id}")
                                skipped_memories += 1
                                continue
                            
                            # Check if the character exists
                            if not check_character_exists(conn, character_id):
                                logger.warning(f"Character {character_id} doesn't exist, skipping memory")
                                skipped_memories += 1
                                continue
                            
                            # Check if this memory already exists
                            if memory_exists(conn, character_id, content):
                                logger.info(f"Memory already exists, skipping: {content[:50]}...")
                                skipped_memories += 1
                                continue
                            
                            # Check if the user exists, otherwise use system user
                            if not check_user_exists(conn, user_id):
                                logger.warning(f"User {user_id} not found, assigning memory to system user.")
                                user_id_str = "00000000-0000-0000-0000-000000000000"
                            elif isinstance(user_id, uuid.UUID):
                                user_id_str = str(user_id)
                            else:
                                user_id_str = user_id

                            # Убедимся, что character_id тоже строка
                            if isinstance(character_id, uuid.UUID):
                                character_id_str = str(character_id)
                            else:
                                character_id_str = character_id

                            conn.execute(text("""
                                INSERT INTO memory_entries (
                                    id, character_id, user_id, type, memory_type, category, content,
                                    importance, is_active, created_at, updated_at
                                ) VALUES (
                                    :id, CAST(:character_id AS UUID), CAST(:user_id AS UUID), :type, :memory_type, :category, :content,
                                    :importance, :is_active, :created_at, :updated_at
                                )
                            """), {
                                "id": memory_id,
                                "character_id": character_id_str,
                                "user_id": user_id_str, # Используем проверенный или системный user_id
                                "type": memory_type,
                                "memory_type": memory_type,
                                "category": category,
                                "content": content,
                                "importance": importance,
                                "is_active": True,
                                "created_at": timestamp,
                                "updated_at": timestamp
                            })
                            
                            migrated_memories += 1
                            logger.debug(f"Migrated memory: [{memory_type}/{category}] {content[:50]}...")
                        except Exception as insert_err:
                            logger.error(f"Error inserting memory from event {event_id}: {insert_err}")
                            skipped_memories += 1
        except Exception as parse_err:
            logger.error(f"Error parsing memory data for event {event_id}: {parse_err}")
            skipped_memories += 1
    
    logger.info(f"Migration complete. Processed {total_memories} memories, migrated {migrated_memories} new memories, skipped {skipped_memories} memories.")
    return True

if __name__ == "__main__":
    migrate_memory_data()
