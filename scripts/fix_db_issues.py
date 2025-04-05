"""
Comprehensive script to fix database issues including:
1. UUID comparison issues
2. Transaction failures
3. Type casting problems
4. Adding missing indexes
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import logging
import uuid

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_database_issues():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database: {db_url}")
    
    # Connect to the database
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Start transaction
        with conn.begin():
            try:
                # 1. Fix UUID comparison issues
                if 'postgresql' in db_url.lower():
                    logger.info("Creating UUID comparison helper functions...")
                    
                    # Create helper function for UUID-to-text comparison
                    conn.execute(text("""
                        CREATE OR REPLACE FUNCTION uuid_eq_text(uuid UUID, txt TEXT)
                        RETURNS BOOLEAN AS $$
                        BEGIN
                            RETURN uuid::text = txt;
                        END;
                        $$ LANGUAGE plpgsql;
                    """))
                    
                    # Create function to safely convert text to UUID
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
                
                # 2. Create indexes for better performance
                logger.info("Creating performance indexes...")
                
                # Check all tables with potential UUID columns
                for table, column in [
                    ('messages', 'sender_id'), 
                    ('messages', 'recipient_id'),
                    ('chat_history', 'character_id'),
                    ('chat_history', 'user_id'),
                    ('messages', 'conversation_id'),
                    ('users', 'id'),
                    ('characters', 'id')
                ]:
                    try:
                        # First check if table exists
                        inspector = inspect(engine)
                        if table not in inspector.get_table_names():
                            logger.warning(f"Table {table} does not exist, skipping")
                            continue
                            
                        # Check if column exists
                        columns = [c['name'] for c in inspector.get_columns(table)]
                        if column not in columns:
                            logger.warning(f"Column {column} does not exist in table {table}, skipping")
                            continue
                        
                        # Create a functional index using the text cast for PostgreSQL
                        if 'postgresql' in db_url.lower():
                            conn.execute(text(f"""
                                CREATE INDEX IF NOT EXISTS idx_{table}_{column}_text 
                                ON {table} (({column}::text));
                            """))
                            
                            # Also create normal index if not exists
                            conn.execute(text(f"""
                                CREATE INDEX IF NOT EXISTS idx_{table}_{column}
                                ON {table} ({column});
                            """))
                        else:
                            # For SQLite, just create a regular index
                            conn.execute(text(f"""
                                CREATE INDEX IF NOT EXISTS idx_{table}_{column}
                                ON {table} ({column});
                            """))
                            
                        logger.info(f"Created indexes on {table}.{column}")
                    except Exception as e:
                        logger.warning(f"Couldn't create index on {table}.{column}: {e}")
                
                # 3. Add index on created_at for common tables
                for table in ['messages', 'users', 'characters', 'memory_entries']:
                    try:
                        # Check if table exists
                        inspector = inspect(engine)
                        if table not in inspector.get_table_names():
                            continue
                            
                        # Check if column exists
                        columns = [c['name'] for c in inspector.get_columns(table)]
                        if 'created_at' not in columns:
                            continue
                            
                        # Create index
                        conn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS idx_{table}_created_at
                            ON {table} (created_at DESC);
                        """))
                        logger.info(f"Created index on {table}.created_at")
                    except Exception as e:
                        logger.warning(f"Couldn't create index on {table}.created_at: {e}")
                
                logger.info("Database fixes applied successfully")
                return True
                
            except Exception as e:
                logger.error(f"Error fixing database issues: {e}")
                conn.rollback()
                return False

# Add this function to align with the import in fix_all_db_issues.py
def fix_db_issues():
    """
    Main function to run all database fixes
    (added to match the script import pattern)
    """
    return fix_database_issues()

if __name__ == "__main__":
    fix_database_issues()
