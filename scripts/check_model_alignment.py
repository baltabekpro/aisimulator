"""
Script to check if the SQLAlchemy models are aligned with the database structure.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, MetaData
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_table_columns(engine, table_name):
    """Check columns in a specific database table"""
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        column_names = [col['name'] for col in columns]
        logger.info(f"Table '{table_name}' columns: {', '.join(column_names)}")
        return column_names
    except Exception as e:
        logger.error(f"Error inspecting table '{table_name}': {e}")
        return []

def check_all_tables():
    """Check all tables in the database"""
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
    
    try:
        # Get all tables in the database
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Tables in database: {', '.join(tables)}")
        
        # Check important tables
        important_tables = ['messages', 'users', 'characters', 'memory_entries', 'admin_users']
        for table in important_tables:
            if table in tables:
                check_table_columns(engine, table)
            else:
                logger.warning(f"Table '{table}' not found in database")
        
        # Check for timestamp/created_at issue in messages table
        if 'messages' in tables:
            message_columns = check_table_columns(engine, 'messages')
            if 'timestamp' in message_columns and 'created_at' not in message_columns:
                logger.warning("⚠️ Found 'timestamp' but not 'created_at' in messages table - needs fixing")
            elif 'created_at' in message_columns and 'timestamp' not in message_columns:
                logger.info("✅ Messages table is using 'created_at' instead of 'timestamp' - good!")
            elif 'timestamp' in message_columns and 'created_at' in message_columns:
                logger.warning("⚠️ Both 'timestamp' and 'created_at' exist in messages table - possible duplication")
            else:
                logger.warning("⚠️ Neither 'timestamp' nor 'created_at' found in messages table")
                
    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_tables()
