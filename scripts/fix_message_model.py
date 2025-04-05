"""
Script to fix the Message model and database table alignment issues.
This script handles the timestamp/created_at column mismatch.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_message_model():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return
    
    logger.info(f"Using database: {db_url}")
    
    # Connect to the database
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    
    try:
        # Check if we're using PostgreSQL
        is_postgres = 'postgresql' in db_url.lower()
        
        # Get current columns in the messages table
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('messages')]
        
        logger.info(f"Current columns in messages table: {columns}")
        
        # Check for timestamp vs created_at issue
        needs_timestamp_fix = 'timestamp' in columns and 'created_at' not in columns
        needs_created_at_fix = 'created_at' in columns and 'timestamp' not in columns
        
        # Handle the timestamp to created_at conversion
        if needs_timestamp_fix:
            logger.info("Converting 'timestamp' to 'created_at'")
            
            with db_session.begin():
                if is_postgres:
                    # PostgreSQL version
                    db_session.execute(text("ALTER TABLE messages RENAME COLUMN timestamp TO created_at"))
                else:
                    # SQLite version (requires recreating the table)
                    logger.warning("SQLite does not support direct column renaming. Please use a more advanced migration tool.")
                    
                logger.info("Successfully renamed timestamp to created_at")
                
        # Add any missing columns
        missing_columns = []
        for required_col in ['is_read', 'is_gift', 'updated_at']:
            if required_col not in columns:
                missing_columns.append(required_col)
        
        if missing_columns:
            logger.info(f"Adding missing columns: {missing_columns}")
            
            with db_session.begin():
                for col in missing_columns:
                    if col == 'is_read' or col == 'is_gift':
                        if is_postgres:
                            db_session.execute(text(f"ALTER TABLE messages ADD COLUMN {col} BOOLEAN NOT NULL DEFAULT false"))
                        else:
                            db_session.execute(text(f"ALTER TABLE messages ADD COLUMN {col} BOOLEAN NOT NULL DEFAULT 0"))
                    elif col == 'updated_at':
                        db_session.execute(text(f"ALTER TABLE messages ADD COLUMN {col} TIMESTAMP"))
                        
                logger.info("Successfully added missing columns")
                
        # Get updated columns
        columns = [col['name'] for col in inspector.get_columns('messages')]
        logger.info(f"Updated columns in messages table: {columns}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing message model: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db_session.close()

if __name__ == "__main__":
    fix_message_model()
