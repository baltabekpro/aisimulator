"""
Script to fix the column type issues in the events table.
This addresses the character_id and user_id columns type mismatches.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_events_columns():
    """Fix column type issues in the events table"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    # Only needed for PostgreSQL
    if 'postgresql' not in db_url.lower():
        logger.info("This fix is only needed for PostgreSQL databases")
        return True
    
    logger.info(f"Using database: {db_url}")
    engine = create_engine(db_url)
    
    # First check if the events table exists
    with engine.connect() as conn:
        with conn.begin():
            try:
                # Check if events table exists
                table_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events')"
                )).scalar()
                
                if not table_exists:
                    logger.info("Events table doesn't exist, no fixes needed")
                    return True
                
                # Check column types
                character_id_type = conn.execute(text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = 'events' AND column_name = 'character_id'"
                )).scalar()
                
                if character_id_type and character_id_type.lower() == 'character varying':
                    # Need to fix column type
                    logger.info("Found character_id with varchar type, fixing...")
                    
                    # Create index on character_id as text for faster queries
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_events_character_id_text "
                        "ON events ((character_id::text))"
                    ))
                    logger.info("Created text index on character_id for better performance")
                    
                    # Create helper function for safer comparison
                    conn.execute(text("""
                        CREATE OR REPLACE FUNCTION event_character_id_eq(uuid_val UUID, text_val TEXT)
                        RETURNS BOOLEAN AS $$
                        BEGIN
                            RETURN uuid_val::text = text_val;
                        END;
                        $$ LANGUAGE plpgsql;
                    """))
                    logger.info("Created helper function for UUID comparison")
                
                # Check if there are any UUID type issues in messages table too
                message_character_id_type = conn.execute(text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = 'messages' AND column_name = 'sender_id'"
                )).scalar()
                
                if message_character_id_type and message_character_id_type.lower() == 'character varying':
                    # Create indexes for safer string-UUID comparisons
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_messages_sender_id_text "
                        "ON messages ((sender_id::text))"
                    ))
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_messages_recipient_id_text "
                        "ON messages ((recipient_id::text))"
                    ))
                    logger.info("Created text indexes on messages table")
                
                logger.info("✅ Successfully applied fixes to the events table")
                return True
            except Exception as e:
                logger.error(f"Error fixing events table: {e}")
                return False

# Add this function to align with the import in fix_all_db_issues.py
def fix_event_columns():
    """
    Main function to fix events table column issues
    (added to match the script import pattern)
    """
    return fix_events_columns()

if __name__ == "__main__":
    fix_events_columns()
