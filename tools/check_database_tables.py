"""
Utility to check database tables and their structure.
This helps verify that the required tables exist with the correct columns.

Usage:
    python -m tools.check_database_tables
"""

import sys
import os
import logging
import sqlite3
from pathlib import Path
from sqlalchemy import inspect, create_engine
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

def get_database_path():
    """Get the database path from environment or use default."""
    try:
        from core.config import settings
        database_url = settings.DATABASE_URL
        
        if database_url.startswith('sqlite:///'):
            return database_url.replace('sqlite:///', '')
        return None  # Not SQLite
    except Exception as e:
        logger.error(f"Error getting database path from settings: {e}")
        return "app.db"  # Default fallback

def check_database_tables():
    """Check the structure of database tables."""
    try:
        db_path = get_database_path()
        if not db_path:
            logger.error("Could not determine database path or not using SQLite")
            return False
            
        logger.info(f"Checking database at: {db_path}")
        
        if not os.path.exists(db_path):
            logger.error(f"Database file does not exist: {db_path}")
            return False
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Found {len(tables)} tables in the database: {', '.join(tables)}")
        
        # Check important tables
        important_tables = ['events', 'messages', 'ai_partners', 'users']
        missing_tables = [table for table in important_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"Missing important tables: {', '.join(missing_tables)}")
            return False
        
        # Check the events table structure
        if 'events' in tables:
            cursor.execute("PRAGMA table_info(events)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            logger.info(f"Events table columns: {', '.join(columns.keys())}")
            
            required_columns = ['id', 'character_id', 'event_type', 'data', 'created_at']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                logger.error(f"Missing columns in events table: {', '.join(missing_columns)}")
                return False
                
            # Display events table contents
            cursor.execute("SELECT id, character_id, event_type, created_at FROM events LIMIT 10")
            events = cursor.fetchall()
            
            logger.info(f"Found {len(events)} events in the database (showing up to 10):")
            for event in events:
                logger.info(f"  ID: {event[0]}, Character: {event[1]}, Type: {event[2]}, Created: {event[3]}")
                
                # Display data sample for the first few events
                if event[2] in ('memory', 'conversation'):
                    cursor.execute("SELECT data FROM events WHERE id = ?", (event[0],))
                    data_row = cursor.fetchone()
                    
                    if data_row and data_row[0]:
                        try:
                            data = json.loads(data_row[0])
                            if isinstance(data, list) and len(data) > 0:
                                logger.info(f"  Data sample: {json.dumps(data[0], ensure_ascii=False)}")
                            else:
                                logger.info(f"  Data not in expected format")
                        except json.JSONDecodeError:
                            logger.warning(f"  Data is not valid JSON")
        
        # Check messages table structure
        if 'messages' in tables:
            cursor.execute("PRAGMA table_info(messages)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            logger.info(f"Messages table columns: {', '.join(columns.keys())}")
            
            required_columns = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                logger.error(f"Missing columns in messages table: {', '.join(missing_columns)}")
                return False
                
            # Display message count
            cursor.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            logger.info(f"Total message count in database: {count}")
            
            # Display most recent messages
            cursor.execute("SELECT id, sender_id, recipient_id, content, created_at FROM messages ORDER BY created_at DESC LIMIT 5")
            messages = cursor.fetchall()
            
            logger.info(f"Recent messages (up to 5):")
            for msg in messages:
                content_preview = msg[3][:50] + "..." if len(msg[3]) > 50 else msg[3]
                logger.info(f"  ID: {msg[0]}, From: {msg[1]}, To: {msg[2]}, Date: {msg[4]}")
                logger.info(f"  Content: {content_preview}")
        
        conn.close()
        return True
    
    except Exception as e:
        logger.exception(f"Error checking database tables: {e}")
        return False

def main():
    """Main entry point"""
    logger.info("Checking database tables...")
    if check_database_tables():
        logger.info("✅ Database check completed successfully")
        return 0
    else:
        logger.error("❌ Database check failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
