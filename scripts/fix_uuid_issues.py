"""
Script to diagnose and fix UUID comparison issues in PostgreSQL.

This script creates helper functions in the database to allow safer
UUID comparisons and fixes any tables that need explicit type casts.
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

def fix_uuid_issues():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    # Only proceed if it's PostgreSQL
    if 'postgresql' not in db_url.lower():
        logger.info("This script is only needed for PostgreSQL databases")
        return True
    
    logger.info(f"Using database: {db_url}")
    
    # Connect to the database
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        with conn.begin():
            try:
                # 1. Create a function to safely compare UUID and text
                logger.info("Creating UUID comparison helper function...")
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION uuid_eq_text(uuid UUID, txt TEXT)
                    RETURNS BOOLEAN AS $$
                    BEGIN
                        RETURN uuid::text = txt;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # 2. Create a function to safely convert text to UUID
                logger.info("Creating text to UUID conversion function...")
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION safe_text_to_uuid(txt TEXT)
                    RETURNS UUID AS $$
                    BEGIN
                        BEGIN
                            RETURN txt::uuid;
                        EXCEPTION WHEN others THEN
                            RETURN NULL;
                        END;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # 3. Create indexes to speed up string-UUID comparisons
                logger.info("Creating indexes for common ID fields...")
                
                # Check all tables with potential UUID columns
                for table, column in [
                    ('messages', 'sender_id'), 
                    ('messages', 'recipient_id'),
                    ('chat_history', 'character_id'),
                    ('chat_history', 'user_id'),
                ]:
                    try:
                        # Create a functional index using the text cast
                        conn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS idx_{table}_{column}_text 
                            ON {table} (({column}::text));
                        """))
                        logger.info(f"Created text-cast index on {table}.{column}")
                    except Exception as e:
                        logger.warning(f"Couldn't create index on {table}.{column}: {e}")
                
                logger.info("Successfully created UUID helpers and indexes")
                return True
                
            except Exception as e:
                logger.error(f"Error fixing UUID issues: {e}")
                return False

if __name__ == "__main__":
    fix_uuid_issues()
