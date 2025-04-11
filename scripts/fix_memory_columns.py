"""
Script to fix memory entries column names to ensure consistency between 'type' and 'memory_type'.
This allows memories to be properly retrieved across the application.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import time

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_memory_columns():
    """Fix memory_entries table column names to ensure proper retrieval"""
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
        try:
            # Check if memory_entries table exists
            memory_exists = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
            )).scalar()
            
            if not memory_exists:
                logger.error("Memory entries table doesn't exist")
                return False
            
            # Get existing columns
            columns = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
            )).fetchall()
            
            column_names = [col[0] for col in columns]
            logger.info(f"Found columns in memory_entries table: {', '.join(column_names)}")
            
            has_type = 'type' in column_names
            has_memory_type = 'memory_type' in column_names
            
            # Begin transaction
            with conn.begin():
                # Case 1: Has both columns, need to merge data
                if has_type and has_memory_type:
                    logger.info("Found both 'type' and 'memory_type' columns, merging data...")
                    
                    # Update any NULL values in memory_type from type column
                    conn.execute(text("""
                        UPDATE memory_entries 
                        SET memory_type = type 
                        WHERE memory_type IS NULL AND type IS NOT NULL
                    """))
                    
                    # Update any NULL values in type from memory_type column
                    conn.execute(text("""
                        UPDATE memory_entries 
                        SET type = memory_type 
                        WHERE type IS NULL AND memory_type IS NOT NULL
                    """))
                    
                    logger.info("Data merged between columns")
                    
                # Case 2: Has only type column, need to add memory_type
                elif has_type and not has_memory_type:
                    logger.info("Only 'type' column exists, adding 'memory_type'...")
                    
                    # Add memory_type column
                    conn.execute(text("ALTER TABLE memory_entries ADD COLUMN memory_type VARCHAR(50)"))
                    
                    # Copy data from type to memory_type
                    conn.execute(text("UPDATE memory_entries SET memory_type = type"))
                    
                    # Set not null constraint after data is populated
                    conn.execute(text("ALTER TABLE memory_entries ALTER COLUMN memory_type SET NOT NULL"))
                    
                    logger.info("Added and populated memory_type column")
                    
                # Case 3: Has only memory_type column, need to add type
                elif not has_type and has_memory_type:
                    logger.info("Only 'memory_type' column exists, adding 'type'...")
                    
                    # Add type column
                    conn.execute(text("ALTER TABLE memory_entries ADD COLUMN type VARCHAR(50)"))
                    
                    # Copy data from memory_type to type
                    conn.execute(text("UPDATE memory_entries SET type = memory_type"))
                    
                    # Set not null constraint after data is populated
                    conn.execute(text("ALTER TABLE memory_entries ALTER COLUMN type SET NOT NULL"))
                    
                    logger.info("Added and populated type column")
                    
                # Case 4: Neither column exists, need to add both
                elif not has_type and not has_memory_type:
                    logger.error("Neither 'type' nor 'memory_type' columns exist - major schema issue!")
                    return False
                
                # Create views to always provide consistent access regardless of column names
                logger.info("Creating view for consistent memory access...")
                conn.execute(text("""
                    CREATE OR REPLACE VIEW memory_entries_view AS
                    SELECT id, character_id, user_id, 
                           COALESCE(type, memory_type, 'unknown') as memory_type,
                           COALESCE(type, memory_type, 'unknown') as type,
                           category, content, importance, 
                           is_active, created_at, updated_at 
                    FROM memory_entries
                """))
                
                # Add appropriate indexes for better performance
                logger.info("Creating indexes for improved performance...")
                
                # For memory_type column
                if has_memory_type:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type 
                        ON memory_entries(memory_type)
                    """))
                
                # For type column
                if has_type:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_memory_entries_type 
                        ON memory_entries(type)
                    """))
                
                # For character_id + user_id combination
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_memory_entries_char_user 
                    ON memory_entries(character_id, user_id)
                """))
                
                # Text based index for UUID format conversion
                if 'postgresql' in db_url.lower():
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id_text 
                        ON memory_entries ((character_id::text))
                    """))
            
            # Test retrieval after fixes
            logger.info("Testing memory retrieval after fixes...")
            
            # Count total memories
            memory_count = conn.execute(text("SELECT COUNT(*) FROM memory_entries")).scalar()
            logger.info(f"Total memories in database: {memory_count}")
            
            # Count memories with proper type values
            type_count = 0
            if has_type:
                type_count = conn.execute(text("SELECT COUNT(*) FROM memory_entries WHERE type IS NOT NULL")).scalar()
                logger.info(f"Memories with 'type' value: {type_count}")
            
            memory_type_count = 0
            if has_memory_type:
                memory_type_count = conn.execute(text(
                    "SELECT COUNT(*) FROM memory_entries WHERE memory_type IS NOT NULL"
                )).scalar()
                logger.info(f"Memories with 'memory_type' value: {memory_type_count}")
            
            # View count (should match total memories)
            view_count = conn.execute(text("SELECT COUNT(*) FROM memory_entries_view")).scalar()
            logger.info(f"Memories accessible through view: {view_count}")
            
            logger.info("✅ Memory entries column fixes applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error fixing memory columns: {e}")
            return False

if __name__ == "__main__":
    start_time = time.time()
    success = fix_memory_columns()
    end_time = time.time()
    
    if success:
        logger.info(f"Script completed successfully in {end_time - start_time:.2f} seconds")
        sys.exit(0)
    else:
        logger.error(f"Script failed after {end_time - start_time:.2f} seconds")
        sys.exit(1)