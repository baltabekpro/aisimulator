"""
Script to fix the chat_history table schema by making nullable columns that don't need to be required.
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

def fix_chat_history_schema():
    """Fix schema issues in the chat_history table"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database: {db_url}")
    
    # Check if we're using PostgreSQL
    if 'postgresql' not in db_url.lower():
        logger.info("This fix is only needed for PostgreSQL databases")
        return True
    
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
                
                # Get the column constraints
                columns_info = conn.execute(text("""
                    SELECT column_name, is_nullable, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'chat_history'
                    ORDER BY ordinal_position
                """)).fetchall()
                
                # Columns that should be made nullable
                nullable_columns = ['role', 'content', 'message_metadata', 'position']
                
                for col_info in columns_info:
                    col_name = col_info[0]
                    is_nullable = col_info[1].upper() == 'YES'
                    data_type = col_info[2]
                    
                    if col_name in nullable_columns and not is_nullable:
                        logger.info(f"Making {col_name} column nullable")
                        conn.execute(text(f"""
                            ALTER TABLE chat_history
                            ALTER COLUMN {col_name} DROP NOT NULL
                        """))
                        logger.info(f"✅ Made {col_name} column nullable")
                
                # Create default values for existing records that have NULL values
                # This is needed to avoid errors with existing records
                for col_name in nullable_columns:
                    # Handle each column type differently
                    if col_name == 'role':
                        conn.execute(text("""
                            UPDATE chat_history
                            SET role = 'system'
                            WHERE role IS NULL
                        """))
                    elif col_name == 'content':
                        conn.execute(text("""
                            UPDATE chat_history
                            SET content = ''
                            WHERE content IS NULL
                        """))
                    elif col_name == 'message_metadata':
                        conn.execute(text("""
                            UPDATE chat_history
                            SET message_metadata = '{}'
                            WHERE message_metadata IS NULL
                        """))
                    elif col_name == 'position':
                        conn.execute(text("""
                            UPDATE chat_history
                            SET position = 0
                            WHERE position IS NULL
                        """))
                
                logger.info("✅ Successfully fixed chat_history table schema")
                return True
            except Exception as e:
                logger.error(f"Error fixing chat_history schema: {e}")
                return False

def fix_chat_history_schema_main():
    """Main function"""
    return fix_chat_history_schema()

if __name__ == "__main__":
    fix_chat_history_schema()
