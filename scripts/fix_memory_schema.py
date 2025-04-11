"""
Script to fix memory table schema issues by adding required columns.
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

def fix_memory_schema():
    """Fix memory_entries table schema by adding missing columns"""
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
                # Check if memory_entries table exists
                memory_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
                )).scalar()
                
                if memory_exists:
                    logger.info("✅ Memory entries table exists")
                    
                    # Get columns
                    columns = conn.execute(text(
                        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'memory_entries'"
                    )).fetchall()
                    
                    logger.info("Memory entries table columns:")
                    column_names = []
                    for col in columns:
                        logger.info(f"  - {col[0]} ({col[1]})")
                        column_names.append(col[0])
                    
                    # Check and add missing type column
                    if 'type' not in column_names and 'memory_type' not in column_names:
                        logger.info("Adding missing type column to memory_entries table")
                        conn.execute(text("ALTER TABLE memory_entries ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'unknown'"))
                        logger.info("✅ Added type column")
                    else:
                        logger.info("Type column already exists")
                    
                    # Check and add missing category column
                    if 'category' not in column_names:
                        logger.info("Adding missing category column to memory_entries table")
                        conn.execute(text("ALTER TABLE memory_entries ADD COLUMN category VARCHAR(50) DEFAULT 'general'"))
                        logger.info("✅ Added category column")
                    else:
                        logger.info("Category column already exists")
                    
                    # Create an index for better performance
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_character_user ON memory_entries(character_id, user_id)"))
                    logger.info("✅ Created or verified index on character_id and user_id")
                    
                    # Create column alias if needed - alternative approach using SQL VIEW
                    # Note that we're not using this now, but could be a future solution
                    """
                    conn.execute(text('''
                        CREATE OR REPLACE VIEW memory_entries_view AS
                        SELECT id, character_id, user_id, type as memory_type, category, content, importance, 
                              is_active, created_at, updated_at 
                        FROM memory_entries
                    '''))
                    """
                    
                    logger.info("✅ Memory entries table schema fix completed")
                    return True
                else:
                    logger.error("❌ Memory entries table does not exist")
                    return False
            except Exception as e:
                logger.error(f"Error fixing memory schema: {e}")
                return False

if __name__ == "__main__":
    success = fix_memory_schema()
    if success:
        logger.info("✅ Memory schema fix completed successfully!")
    else:
        logger.error("❌ Memory schema fix failed!")
