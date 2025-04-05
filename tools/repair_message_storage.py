"""
Tool to repair message storage issues by migrating messages from the 
events table JSON to proper message records in the messages table.

Usage:
    python -m tools.repair_message_storage
"""

import sys
import os
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
import datetime
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

def repair_message_storage():
    """Repairs message storage by migrating from JSON events to proper message records."""
    from app.db.session import SessionLocal
    from core.models import Event, Message, AIPartner, User
    from sqlalchemy import func
    
    db = SessionLocal()
    try:
        # 1. Get all conversation events
        conversation_events = db.query(Event).filter(Event.event_type == 'conversation').all()
        logger.info(f"Found {len(conversation_events)} conversation events to process")
        
        # 2. Process each event
        total_messages_migrated = 0
        events_processed = 0
        
        for event in conversation_events:
            character_id = event.character_id
            
            # Skip if no data
            if not event.data:
                logger.warning(f"Event {event.id} has no data, skipping")
                continue
            
            try:
                # Parse the conversation messages
                messages = json.loads(event.data)
                if not isinstance(messages, list):
                    logger.warning(f"Event {event.id} data is not a list, skipping")
                    continue
                
                logger.info(f"Processing {len(messages)} messages for character {character_id}")
                
                # Find a user who has communicated with this character
                user_query = (
                    db.query(Message.sender_id)
                    .filter(Message.recipient_id == character_id, Message.sender_type == "user")
                    .order_by(func.random())
                    .limit(1)
                )
                
                user_id = user_query.scalar()
                
                if not user_id:
                    # Try looking in the other direction
                    user_query = (
                        db.query(Message.recipient_id)
                        .filter(Message.sender_id == character_id, Message.recipient_type == "user")
                        .order_by(func.random())
                        .limit(1)
                    )
                    user_id = user_query.scalar()
                
                if not user_id:
                    # If still no user found, look for any user
                    user_query = db.query(User.user_id).order_by(func.random()).limit(1)
                    user_id = user_query.scalar()
                
                if not user_id:
                    logger.warning(f"No user found to associate with character {character_id}, skipping")
                    continue
                
                # Process each message in the conversation
                messages_added = 0
                for msg in messages:
                    role = msg.get("role")
                    content = msg.get("content", "")
                    
                    # Skip empty or invalid messages
                    if not content or not role:
                        continue
                    
                    # Determine sender and recipient
                    if role == "user":
                        sender_id = user_id
                        sender_type = "user"
                        recipient_id = character_id
                        recipient_type = "character"
                    elif role == "assistant":
                        sender_id = character_id
                        sender_type = "character"
                        recipient_id = user_id
                        recipient_type = "user"
                    else:
                        # Skip system messages
                        continue
                    
                    # Check if message already exists
                    existing_message = db.query(Message).filter(
                        Message.sender_id == sender_id,
                        Message.recipient_id == recipient_id,
                        Message.content == content
                    ).first()
                    
                    if existing_message:
                        continue
                    
                    # Get emotion from metadata if available
                    emotion = "neutral"
                    if "metadata" in msg and isinstance(msg["metadata"], dict):
                        emotion = msg["metadata"].get("emotion", "neutral")
                    
                    # Create new message
                    new_message = Message(
                        id=uuid.uuid4(),
                        sender_id=sender_id,
                        sender_type=sender_type,
                        recipient_id=recipient_id,
                        recipient_type=recipient_type,
                        content=content,
                        emotion=emotion,
                        created_at=datetime.datetime.now() - datetime.timedelta(minutes=messages_added)
                    )
                    
                    db.add(new_message)
                    messages_added += 1
                
                if messages_added > 0:
                    db.commit()
                    logger.info(f"✅ Added {messages_added} messages for character {character_id}")
                    total_messages_migrated += messages_added
                else:
                    logger.info(f"No new messages to add for character {character_id}")
                
                events_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing event {event.id}: {e}")
                db.rollback()
        
        logger.info(f"✅ Processing complete! Processed {events_processed} events, migrated {total_messages_migrated} messages")
        return True
    
    except Exception as e:
        logger.exception(f"Error in repair_message_storage: {e}")
        return False
    finally:
        db.close()

def verify_message_storage():
    """Verify that messages are properly stored in the messages table."""
    from app.db.session import SessionLocal
    from core.models import Event, Message, AIPartner
    
    db = SessionLocal()
    try:
        # Count messages in the database
        message_count = db.query(Message).count()
        logger.info(f"Total messages in messages table: {message_count}")
        
        # Count conversation events
        event_count = db.query(Event).filter(Event.event_type == 'conversation').count()
        logger.info(f"Total conversation events: {event_count}")
        
        # Count characters
        character_count = db.query(AIPartner).count()
        logger.info(f"Total characters: {character_count}")
        
        # Display some recent messages
        recent_messages = db.query(Message).order_by(Message.created_at.desc()).limit(5).all()
        
        logger.info("Recent messages:")
        for msg in recent_messages:
            content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            logger.info(f"  ID: {msg.id}, From: {msg.sender_id} ({msg.sender_type}), " 
                       f"To: {msg.recipient_id} ({msg.recipient_type}), "
                       f"Content: {content_preview}")
        
        return True
        
    except Exception as e:
        logger.exception(f"Error in verify_message_storage: {e}")
        return False
    finally:
        db.close()

def main():
    """Main entry point for the repair tool."""
    logger.info("Starting message storage repair")
    
    # First verify current state
    logger.info("Verifying current message storage state:")
    verify_message_storage()
    
    # Ask for confirmation
    print("\nThis tool will migrate messages from the events table to the messages table.")
    choice = input("Do you want to proceed? (y/n): ").strip().lower()
    
    if choice != 'y':
        logger.info("Operation cancelled by user")
        return 1
    
    # Proceed with repair
    if repair_message_storage():
        logger.info("✅ Message storage repair completed successfully")
        
        # Verify the results
        logger.info("\nVerifying repaired message storage:")
        verify_message_storage()
        
        return 0
    else:
        logger.error("❌ Message storage repair failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
