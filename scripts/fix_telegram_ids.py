"""
Script to fix Telegram user IDs in chat_history and messages tables.
This converts numeric Telegram IDs to proper UUIDs.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import uuid

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define a namespace UUID for consistent conversion
NAMESPACE_USER_ID = uuid.UUID('c7e7f1d0-5a5d-5a5e-a2b0-914b8c42a3d7')

def telegram_id_to_uuid(telegram_id):
    """Convert Telegram ID to UUID using UUID v5 algorithm"""
    return str(uuid.uuid5(NAMESPACE_USER_ID, str(telegram_id)))

def is_valid_uuid(value):
    """Check if a value is a valid UUID string"""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False

def fix_telegram_ids():
    """Fix numeric Telegram IDs by converting them to UUIDs"""
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
    
    with engine.connect() as conn:
        with conn.begin():
            try:
                # Create a helper function to check if a string is a UUID
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION is_uuid(txt TEXT)
                    RETURNS BOOLEAN AS $$
                    BEGIN
                        RETURN txt ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # Create a function to convert Telegram IDs to UUIDs
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION telegram_id_to_uuid(telegram_id TEXT)
                    RETURNS UUID AS $$
                    DECLARE
                        namespace UUID := 'c7e7f1d0-5a5d-5a5e-a2b0-914b8c42a3d7'::UUID;
                    BEGIN
                        RETURN uuid_generate_v5(namespace, telegram_id);
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # Ensure the uuid-ossp extension is available
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
                
                # Check for numeric user_ids in chat_history table
                result = conn.execute(text("""
                    SELECT id, user_id 
                    FROM chat_history
                    WHERE NOT is_uuid(user_id::text)
                """))
                
                rows = result.fetchall()
                if rows:
                    logger.info(f"Found {len(rows)} chat_history records with non-UUID user_ids")
                    
                    # Create a map of old IDs to new UUIDs for consistency
                    id_mapping = {}
                    
                    # Process each row
                    for row in rows:
                        old_id = row[1]
                        if old_id not in id_mapping:
                            # Generate a consistent UUID from the Telegram ID
                            new_uuid = telegram_id_to_uuid(old_id)
                            id_mapping[old_id] = new_uuid
                            
                    # Update all chat_history records with the new UUIDs        
                    for old_id, new_uuid in id_mapping.items():
                        conn.execute(text("""
                            UPDATE chat_history 
                            SET user_id = :new_uuid
                            WHERE user_id::text = :old_id
                        """), {"new_uuid": new_uuid, "old_id": str(old_id)})
                        
                    logger.info(f"Updated {len(id_mapping)} unique user_ids in chat_history table")
                    
                    # Do the same for messages table
                    for old_id, new_uuid in id_mapping.items():
                        # Update sender_id
                        sender_result = conn.execute(text("""
                            UPDATE messages 
                            SET sender_id = :new_uuid
                            WHERE sender_id::text = :old_id AND sender_type = 'user'
                        """), {"new_uuid": new_uuid, "old_id": str(old_id)})
                        
                        # Update recipient_id
                        recipient_result = conn.execute(text("""
                            UPDATE messages 
                            SET recipient_id = :new_uuid
                            WHERE recipient_id::text = :old_id AND recipient_type = 'user'
                        """), {"new_uuid": new_uuid, "old_id": str(old_id)})
                        
                    logger.info(f"Updated user_ids in messages table")
                else:
                    logger.info("No non-UUID user_ids found in chat_history table")
                
                # Create indexes for improved performance with UUID comparisons
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_history_user_id_uuid
                    ON chat_history USING btree (user_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_messages_sender_id_uuid
                    ON messages USING btree (sender_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_messages_recipient_id_uuid
                    ON messages USING btree (recipient_id);
                """))
                
                logger.info("✅ Created UUID indexes for improved query performance")
                
                logger.info("✅ Successfully fixed Telegram IDs in database")
                return True
            except Exception as e:
                logger.error(f"Error fixing Telegram IDs: {e}")
                return False

def fix_telegram_ids_main():
    """Main function to run Telegram ID fixes"""
    return fix_telegram_ids()

if __name__ == "__main__":
    fix_telegram_ids()
