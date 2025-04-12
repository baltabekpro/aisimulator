#!/usr/bin/env python3
"""
Auto-fix script for memory database issues.
This script automatically fixes common problems with the memory_entries table:
1. Missing columns (category, type, memory_type)
2. Foreign key constraint issues
3. NULL values in required fields
"""
import os
import sys
import logging
import time
import uuid
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def wait_for_db(max_retries=30, retry_interval=2):
    """Wait for database to be ready"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Waiting for database to be available at {db_url}")
    engine = create_engine(db_url)
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                logger.info("✅ Database is ready!")
                return True
        except Exception as e:
            logger.info(f"Database not ready yet ({attempt+1}/{max_retries}): {str(e)}")
            time.sleep(retry_interval)
    
    logger.error("❌ Database connection timed out")
    return False

def fix_memory_columns():
    """Fix memory_entries table schema by adding missing columns"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Fixing memory columns using database: {db_url}")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        with conn.begin():
            try:
                # Check if memory_entries table exists
                memory_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
                )).scalar()
                
                if not memory_exists:
                    logger.info("Memory entries table doesn't exist yet, will be created by normal initialization")
                    return True
                
                # Get columns
                columns = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
                )).fetchall()
                
                column_names = [col[0] for col in columns]
                
                # Check and add missing type column
                if 'type' not in column_names:
                    logger.info("Adding missing type column to memory_entries table")
                    conn.execute(text("ALTER TABLE memory_entries ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'general'"))
                    logger.info("✅ Added type column")
                    
                # Check and add missing memory_type column
                if 'memory_type' not in column_names:
                    logger.info("Adding missing memory_type column to memory_entries table")
                    conn.execute(text("ALTER TABLE memory_entries ADD COLUMN memory_type VARCHAR(50) NOT NULL DEFAULT 'general'"))
                    logger.info("✅ Added memory_type column")
                
                # Check and add missing category column
                if 'category' not in column_names:
                    logger.info("Adding missing category column to memory_entries table")
                    conn.execute(text("ALTER TABLE memory_entries ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'general'"))
                    logger.info("✅ Added category column")

                # Synchronize values between type and memory_type if both exist
                if 'type' in column_names and 'memory_type' in column_names:
                    logger.info("Synchronizing data between type and memory_type columns")
                    
                    # Update memory_type from type where memory_type is null but type has value
                    conn.execute(text("""
                        UPDATE memory_entries 
                        SET memory_type = type 
                        WHERE memory_type IS NULL AND type IS NOT NULL
                    """))
                    
                    # Update type from memory_type where type is null but memory_type has value
                    conn.execute(text("""
                        UPDATE memory_entries 
                        SET type = memory_type 
                        WHERE type IS NULL AND memory_type IS NOT NULL
                    """))
                    
                    # Set default value for both if both are null
                    conn.execute(text("""
                        UPDATE memory_entries 
                        SET type = 'general', memory_type = 'general' 
                        WHERE type IS NULL AND memory_type IS NULL
                    """))
                    
                    logger.info("✅ Synchronized type and memory_type data")
                
                # Create indexes for better performance
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_category ON memory_entries(category)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type ON memory_entries(memory_type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_character_user ON memory_entries(character_id, user_id)"))
                logger.info("✅ Created indexes")
                
                # Create view for admin panel
                logger.info("Creating admin memory view with proper column handling")
                conn.execute(text("""
                    CREATE OR REPLACE VIEW admin_memories_view AS
                    SELECT m.id, m.character_id, c.name as character_name, 
                           COALESCE(m.type, 'unknown') as type, 
                           COALESCE(m.memory_type, 'unknown') as memory_type, 
                           COALESCE(m.category, 'general') as category, 
                           m.content, m.importance,
                           m.user_id, m.created_at
                    FROM memory_entries m
                    LEFT JOIN characters c ON c.id::text = m.character_id::text
                    ORDER BY m.created_at DESC
                """))
                logger.info("✅ Created admin memory view")
                
                return True
            except Exception as e:
                logger.error(f"Error fixing memory columns: {e}")
                return False

def fix_memory_constraints():
    """Fix foreign key constraints in memory_entries table"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Fixing memory constraints using database: {db_url}")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        with conn.begin():
            try:
                # First check if tables exist
                memory_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
                )).scalar()
                
                users_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
                )).scalar()
                
                if not memory_exists or not users_exists:
                    logger.info("Required tables don't exist yet, skipping constraint fix")
                    return True
                
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
                    AND kcu.column_name = 'user_id'
                """)).fetchall()
                
                if constraints:
                    # Drop user_id foreign key constraints
                    for constraint in constraints:
                        constraint_name = constraint[0]
                        logger.info(f"Dropping constraint: {constraint_name}")
                        conn.execute(text(f"""
                            ALTER TABLE memory_entries
                            DROP CONSTRAINT IF EXISTS {constraint_name}
                        """))
                    logger.info("✅ Removed problematic foreign key constraints")
                
                # Create system user if not exists
                system_user_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM users WHERE user_id = '00000000-0000-0000-0000-000000000000')"
                )).scalar()
                
                if not system_user_exists:
                    logger.info("Creating system user for orphaned memories")
                    # Check what columns exist in users table
                    user_columns = conn.execute(text("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'users'
                    """)).fetchall()
                    user_column_names = [col[0] for col in user_columns]
                    
                    # Build dynamic SQL based on existing columns
                    columns = ['user_id', 'username', 'email']
                    values = ["'00000000-0000-0000-0000-000000000000'", "'system'", "'system@example.com'"]
                    
                    if 'name' in user_column_names:
                        columns.append('name')
                        values.append("'System'")
                        
                    if 'password_hash' in user_column_names:
                        columns.append('password_hash')
                        values.append("'$2b$12$K8uw2YYdIzp2XvRWMs9vpO6STRyI53aUEym.Oi4XwqVgRvG/f7kUC'")
                        
                    if 'created_at' in user_column_names:
                        columns.append('created_at')
                        values.append("NOW()")
                        
                    if 'is_admin' in user_column_names:
                        columns.append('is_admin')
                        values.append("false")
                        
                    columns_str = ", ".join(columns)
                    values_str = ", ".join(values)
                    
                    insert_sql = f"""
                        INSERT INTO users ({columns_str})
                        VALUES ({values_str})
                    """
                    
                    conn.execute(text(insert_sql))
                    logger.info("✅ Created system user")
                
                # Create indexes
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id_text
                    ON memory_entries ((user_id::text))
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id_text
                    ON memory_entries ((character_id::text))
                """))
                
                logger.info("✅ Created text-based indexes")
                
                # Update any null user_ids to use system user
                result = conn.execute(text("""
                    UPDATE memory_entries 
                    SET user_id = '00000000-0000-0000-0000-000000000000'
                    WHERE user_id IS NULL
                """))
                if result.rowcount > 0:
                    logger.info(f"✅ Fixed {result.rowcount} rows with NULL user_id")
                
                return True
            except Exception as e:
                logger.error(f"Error fixing memory constraints: {e}")
                return False

def main():
    """Main script execution - fix all memory issues"""
    load_dotenv()
    
    if not wait_for_db():
        logger.error("Database is not available, cannot proceed")
        return False
    
    success = True
    
    # Fix memory columns
    if not fix_memory_columns():
        success = False
        logger.error("Failed to fix memory columns")
    
    # Fix memory constraints
    if not fix_memory_constraints():
        success = False
        logger.error("Failed to fix memory constraints")
    
    if success:
        logger.info("✅ Successfully fixed all memory issues")
    else:
        logger.error("❌ Some fixes failed, check logs for details")
    
    return success

if __name__ == "__main__":
    main()