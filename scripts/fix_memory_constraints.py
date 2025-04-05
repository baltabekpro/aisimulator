"""
Script to fix memory_entries table foreign key constraints.
This allows memories to be stored without strict FK requirements.
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

def fix_memory_constraints():
    """Fix memory_entries table foreign key constraints"""
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
                # First check if memory_entries table exists
                table_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
                )).scalar()
                
                if not table_exists:
                    logger.warning("memory_entries table doesn't exist")
                    return False
                
                # Check for foreign key constraints
                constraints = conn.execute(text("""
                    SELECT tc.constraint_name, tc.table_name, kcu.column_name, 
                           ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY' 
                    AND tc.table_name = 'memory_entries'
                """)).fetchall()
                
                if not constraints:
                    logger.info("No foreign key constraints found on memory_entries table")
                    return True
                
                # Display found constraints
                logger.info(f"Found {len(constraints)} foreign key constraints on memory_entries table:")
                for constraint in constraints:
                    logger.info(f"  - {constraint[0]}: {constraint[1]}.{constraint[2]} -> {constraint[3]}.{constraint[4]}")
                
                # Drop all foreign key constraints
                for constraint in constraints:
                    constraint_name = constraint[0]
                    logger.info(f"Dropping constraint: {constraint_name}")
                    
                    conn.execute(text(f"""
                        ALTER TABLE memory_entries
                        DROP CONSTRAINT IF EXISTS {constraint_name}
                    """))
                
                logger.info("✅ Successfully removed foreign key constraints from memory_entries table")
                
                # Add text-based indexes for better performance
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id_text
                    ON memory_entries ((character_id::text))
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id_text
                    ON memory_entries ((user_id::text))
                """))
                
                logger.info("✅ Created text-based indexes for ID fields")
                
                return True
            except Exception as e:
                logger.error(f"Error fixing memory constraints: {e}")
                return False

if __name__ == "__main__":
    fix_memory_constraints()
