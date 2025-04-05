"""
Tool to create the chat_history table and migrate existing conversation data.

Usage:
    python -m tools.create_chat_history_table
"""

import sys
import os
import logging
import json
from typing import List, Dict, Any
import datetime
import uuid
from pathlib import Path
from sqlalchemy import create_engine, inspect, Column, String, Boolean, DateTime, Text, Integer, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

def create_chat_history_table():
    """Create the chat_history table if it doesn't exist."""
    from core.config import settings
    from core.db.base import Base
    from core.db.session import engine
    
    try:
        # Create a table definition
        metadata = MetaData()
        Base = declarative_base(metadata=metadata)
        
        class ChatHistory(Base):
            __tablename__ = "chat_history"
            
            id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            character_id = Column(UUID(as_uuid=True), nullable=False, index=True)
            user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
            role = Column(String, nullable=False)  # "system", "user", "assistant"
            content = Column(Text, nullable=False)
            message_metadata = Column(Text, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
            position = Column(Integer, nullable=False)  # Order in the conversation
            is_active = Column(Boolean, default=True)  # For soft deletion
            compressed = Column(Boolean, default=False)  # Part of compression
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), onupdate=func.now())
        
        # Check if table already exists
        inspector = inspect(engine)
        if "chat_history" in inspector.get_table_names():
            logger.info("chat_history table already exists")
            return True
            
        # Create the table
        Base.metadata.create_all(engine)
        logger.info("Successfully created chat_history table")
        return True
        
    except Exception as e:
        logger.exception(f"Error creating chat_history table: {e}")
        return False

def migrate_data_to_chat_history():
    """Migrate existing conversation data from events table to chat_history."""
    from app.db.session import SessionLocal
    from core.models import Event, AIPartner, User
    # Import ChatHistory directly from its module instead of from core.models
    from core.db.models.chat_history import ChatHistory
    
    db = SessionLocal()
    try:
        # Get all conversation events
        events = db.query(Event).filter(Event.event_type == 'conversation').all()
        logger.info(f"Found {len(events)} conversation events to migrate")
        
        # Process each event
        for event in events:
            character_id = event.character_id
            
            if not event.data:
                logger.warning(f"Event {event.id} has no data, skipping")
                continue
                
            try:
                # Parse the messages
                messages = json.loads(event.data)
                if not isinstance(messages, list):
                    logger.warning(f"Event {event.id} data is not a list, skipping")
                    continue
                    
                # Find a user associated with this character
                user_query = db.query(User).first()
                if not user_query:
                    logger.warning(f"No users found in database, skipping event {event.id}")
                    continue
                    
                user_id = user_query.user_id
                
                # Process each message
                position = 0
                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    
                    if not role or not content:
                        continue
                        
                    # Prepare metadata string
                    metadata_str = None
                    if "metadata" in msg and isinstance(msg["metadata"], dict):
                        metadata_str = json.dumps(msg["metadata"])
                    
                    # Create chat history entry
                    position += 1
                    new_entry = ChatHistory(
                        id=uuid.uuid4(),
                        character_id=character_id,
                        user_id=user_id,
                        role=role,
                        content=content,
                        message_metadata=metadata_str,  # Updated column name
                        position=position,
                        is_active=True,
                        compressed=False,
                        created_at=datetime.datetime.now()
                    )
                    db.add(new_entry)
                
                db.commit()
                logger.info(f"Migrated {len(messages)} messages for character {character_id}")
                
            except Exception as e:
                logger.error(f"Error migrating data for event {event.id}: {e}")
                db.rollback()
        
        return True
    
    except Exception as e:
        logger.exception(f"Error in migrate_data_to_chat_history: {e}")
        return False
    finally:
        db.close()

def main():
    """Main entry point."""
    logger.info("Starting chat_history table creation and data migration")
    
    # Create the table
    if not create_chat_history_table():
        logger.error("Failed to create chat_history table")
        return 1
    
    # Migrate data
    print("\nDo you want to migrate existing conversation data from events table to chat_history?")
    choice = input("This may take a while for large datasets. Proceed? (y/n): ").strip().lower()
    
    if choice == 'y':
        if migrate_data_to_chat_history():
            logger.info("✅ Successfully migrated conversation data to chat_history table")
        else:
            logger.error("❌ Failed to migrate conversation data")
            return 1
    else:
        logger.info("Data migration skipped")
    
    logger.info("✅ chat_history table creation completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
