"""
Script to fix the missing category column in memory_entries table.
This script should be run via docker exec to apply the fix inside the container.
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

def fix_memory_category():
    """Fix memory_entries table by adding the category column"""
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
                    
                    # Check if category column exists
                    category_exists = conn.execute(text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'memory_entries' AND column_name = 'category')"
                    )).scalar()
                    
                    if not category_exists:
                        logger.info("Adding missing category column to memory_entries table")
                        
                        # Add category column with NOT NULL constraint and default value
                        conn.execute(text(
                            "ALTER TABLE memory_entries ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'general'"
                        ))
                        logger.info("✅ Added category column with default value 'general'")
                        
                        # Create index on category column
                        conn.execute(text(
                            "CREATE INDEX IF NOT EXISTS idx_memory_entries_category ON memory_entries(category)"
                        ))
                        logger.info("✅ Created index on category column")
                    else:
                        logger.info("✓ Category column already exists, checking for NULL values")
                        
                        # Update any NULL values
                        result = conn.execute(text(
                            "UPDATE memory_entries SET category = 'general' WHERE category IS NULL"
                        ))
                        logger.info(f"✅ Updated {result.rowcount} rows with NULL category values")
                        
                    logger.info("✅ Memory entries table schema fix completed")
                    return True
                else:
                    logger.error("❌ Memory entries table does not exist")
                    return False
            except Exception as e:
                logger.error(f"Error fixing memory schema: {e}")
                return False

if __name__ == "__main__":
    fix_memory_category()