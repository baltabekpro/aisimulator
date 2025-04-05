"""
Tool to fix the messages table schema issues by dropping and recreating it.

Usage:
    python -m tools.fix_messages_table
"""

import sys
import os
import logging
import sqlite3
import json
from pathlib import Path
import datetime
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

def fix_messages_table():
    """Completely recreate the messages table with the correct schema."""
    try:
        # Get database path from settings
        from core.config import settings
        db_path = settings.DATABASE_URL
        
        if db_path.startswith('sqlite:///'):
            db_path = db_path.replace('sqlite:///', '')
        else:
            logger.error(f"Unsupported database type: {db_path}")
            return False
            
        # Ensure database file exists
        if not os.path.exists(db_path):
            logger.error(f"Database file does not exist: {db_path}")
            return False
            
        # Create a backup of the database first
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"
        
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            logger.info(f"Created database backup at: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            return False
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if messages table exists and drop it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if cursor.fetchone() is not None:
            cursor.execute("DROP TABLE messages")
            logger.info("Dropped existing messages table")
        
        # Create new messages table with correct schema
        cursor.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            sender_id TEXT,
            sender_type TEXT,
            recipient_id TEXT,
            recipient_type TEXT,
            content TEXT,
            emotion TEXT,
            is_read BOOLEAN DEFAULT 0,
            is_gift BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """)
        
        conn.commit()
        logger.info("Successfully created messages table with correct schema")
        
        # Test the table
        test_id = str(uuid.uuid4())
        try:
            cursor.execute(
                "INSERT INTO messages (id, content) VALUES (?, ?)",
                (test_id, "Test message")
            )
            conn.commit()
            logger.info("Successfully inserted test message")
            
            cursor.execute("SELECT * FROM messages WHERE id = ?", (test_id,))
            result = cursor.fetchone()
            if result:
                logger.info("Successfully retrieved test message")
                cursor.execute("DELETE FROM messages WHERE id = ?", (test_id,))
                conn.commit()
            else:
                logger.warning("Could not retrieve test message")
        except Exception as e:
            logger.error(f"Error testing messages table: {e}")
            conn.rollback()
        
        conn.close()
        return True
        
    except Exception as e:
        logger.exception(f"Error fixing messages table: {e}")
        return False

def main():
    """Main entry point"""
    logger.info("Starting messages table fix...")
    
    print("WARNING: This tool will recreate the messages table, which will remove all existing messages.")
    print("A backup of your database will be created, but any existing message data will be lost.")
    choice = input("Do you want to continue? (y/n): ").strip().lower()
    
    if choice != 'y':
        logger.info("Operation cancelled by user")
        return 1
    
    if fix_messages_table():
        logger.info("✅ Messages table fixed successfully")
        return 0
    else:
        logger.error("❌ Failed to fix messages table")
        return 1

if __name__ == "__main__":
    sys.exit(main())
