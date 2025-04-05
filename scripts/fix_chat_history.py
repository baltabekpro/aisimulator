"""
Script to fix issues with the chat_history table.
This addresses any broken entries and improves UUID handling.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import logging
from uuid import uuid4

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_chat_history():
    """Fix issues in the chat_history table"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database: {db_url}")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        with conn.begin():
            try:
                # Check if chat_history table exists
                table_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_history')"
                )).scalar()
                
                if not table_exists:
                    logger.info("chat_history table doesn't exist, no fixes needed")
                    return True
                
                # Create index on character_id and user_id as text for faster queries
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_chat_history_character_id_text "
                    "ON chat_history ((character_id::text))"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_chat_history_user_id_text "
                    "ON chat_history ((user_id::text))"
                ))
                logger.info("Created text indexes on chat_history for better performance")
                
                # Check for invalid entries where user_id might be a Session object
                # Using text() cast to prevent type errors with UUID columns
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION is_user_id_session(user_id_val ANYELEMENT) 
                    RETURNS BOOLEAN AS $$
                    BEGIN
                        RETURN user_id_val::text LIKE '%Session%';
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # Find problematic records without using length()
                result = conn.execute(text("""
                    SELECT id, character_id, user_id::text as user_id_text 
                    FROM chat_history
                    WHERE is_user_id_session(user_id)
                    LIMIT 10
                """))
                
                bad_records = result.fetchall()
                if bad_records:
                    logger.warning(f"Found {len(bad_records)} bad records in chat_history")
                    
                    # Delete broken records to prevent errors
                    conn.execute(text("""
                        DELETE FROM chat_history
                        WHERE is_user_id_session(user_id)
                    """))
                    logger.info("Deleted broken chat_history records with Session objects as user_id")
                else:
                    logger.info("No problematic chat_history records found")
                
                # Create helper functions for safer UUID operations
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION is_valid_uuid(txt TEXT)
                    RETURNS BOOLEAN AS $$
                    BEGIN
                        IF txt ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
                            RETURN TRUE;
                        ELSE
                            RETURN FALSE;
                        END IF;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # Create an index to help with finding invalid UUIDs
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_history_is_active 
                    ON chat_history (is_active);
                """))
                
                logger.info("✅ Successfully applied fixes to the chat_history table")
                return True
            except Exception as e:
                logger.error(f"Error fixing chat_history table: {e}")
                return False

def fix_chat_history_table():
    """
    Main function to run chat history fixes
    (added to match the script import pattern)
    """
    return fix_chat_history()

if __name__ == "__main__":
    fix_chat_history()
