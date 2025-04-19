#!/usr/bin/env python
"""
Fix memory schema issues by ensuring both 'type' and 'memory_type' columns are populated.
This script addresses issues with the memory_entries table schema where some columns
may be missing values, causing null constraint violations.
"""

import os
import sys
import logging
import sqlalchemy
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

def get_db_connection_string():
    """Get database connection string from environment variables"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable is not set!")
        sys.exit(1)
    return db_url

def fix_memory_schema():
    """Fix memory_entries table schema issues"""
    try:
        # Connect to the database
        db_url = get_db_connection_string()
        engine = create_engine(db_url)
        conn = engine.connect()
        
        # Check if the memory_entries table exists
        logger.info("Checking if memory_entries table exists...")
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'memory_entries')"
        ))
        
        table_exists = result.scalar()
        if not table_exists:
            logger.error("memory_entries table does not exist!")
            return False

        # Check the columns in the memory_entries table
        logger.info("Getting memory_entries table columns...")
        columns = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'memory_entries'"
        )).fetchall()
        
        column_names = [col[0] for col in columns]
        logger.info(f"Found columns: {column_names}")
        
        has_type = 'type' in column_names
        has_memory_type = 'memory_type' in column_names
        
        # Check for NULL values in the required columns
        if has_type:
            null_type_count = conn.execute(text(
                "SELECT COUNT(*) FROM memory_entries WHERE type IS NULL"
            )).scalar()
            logger.info(f"Found {null_type_count} NULL values in 'type' column")
        else:
            null_type_count = 0
            
        if has_memory_type:
            null_memory_type_count = conn.execute(text(
                "SELECT COUNT(*) FROM memory_entries WHERE memory_type IS NULL"
            )).scalar()
            logger.info(f"Found {null_memory_type_count} NULL values in 'memory_type' column")
        else:
            null_memory_type_count = 0
        
        # Add missing columns if needed
        if not has_type:
            logger.info("Adding 'type' column to memory_entries table...")
            conn.execute(text(
                "ALTER TABLE memory_entries ADD COLUMN type TEXT"
            ))
            
        if not has_memory_type:
            logger.info("Adding 'memory_type' column to memory_entries table...")
            conn.execute(text(
                "ALTER TABLE memory_entries ADD COLUMN memory_type TEXT"
            ))
        
        # Update NULL values in type column using memory_type values
        if has_type and has_memory_type and null_type_count > 0:
            logger.info("Updating NULL 'type' values with 'memory_type' values...")
            conn.execute(text(
                "UPDATE memory_entries SET type = memory_type WHERE type IS NULL AND memory_type IS NOT NULL"
            ))
        
        # Update NULL values in memory_type column using type values
        if has_type and has_memory_type and null_memory_type_count > 0:
            logger.info("Updating NULL 'memory_type' values with 'type' values...")
            conn.execute(text(
                "UPDATE memory_entries SET memory_type = type WHERE memory_type IS NULL AND type IS NOT NULL"
            ))
        
        # Set default values for any remaining NULL values
        if has_type:
            logger.info("Setting default values for any remaining NULL 'type' values...")
            conn.execute(text(
                "UPDATE memory_entries SET type = 'personal_info' WHERE type IS NULL"
            ))
            
        if has_memory_type:
            logger.info("Setting default values for any remaining NULL 'memory_type' values...")
            conn.execute(text(
                "UPDATE memory_entries SET memory_type = 'personal_info' WHERE memory_type IS NULL"
            ))
        
        # Create an index on each column to improve query performance
        if has_type:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(type)"
            ))
        
        if has_memory_type:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type ON memory_entries(memory_type)"
            ))
            
        # Set NOT NULL constraints if needed
        if has_type:
            logger.info("Setting NOT NULL constraint on 'type' column...")
            conn.execute(text(
                "ALTER TABLE memory_entries ALTER COLUMN type SET NOT NULL"
            ))
            
        if has_memory_type:
            logger.info("Setting NOT NULL constraint on 'memory_type' column...")
            conn.execute(text(
                "ALTER TABLE memory_entries ALTER COLUMN memory_type SET NOT NULL"
            ))
        
        # Create a view to make memory queries easier
        logger.info("Creating or replacing memory_view...")
        conn.execute(text("""
            DROP VIEW IF EXISTS memory_view;
            CREATE VIEW memory_view AS
            SELECT 
                id,
                character_id,
                user_id,
                COALESCE(memory_type, type) AS memory_type,
                type,
                category,
                content,
                importance,
                is_active,
                created_at,
                updated_at
            FROM memory_entries
            WHERE is_active = TRUE
            ORDER BY importance DESC, created_at DESC
        """))
        
        logger.info("Memory schema fix completed successfully!")
        return True
    
    except Exception as e:
        logger.exception(f"Error fixing memory schema: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("Starting memory schema fix...")
    success = fix_memory_schema()
    if success:
        logger.info("Memory schema fix completed successfully!")
    else:
        logger.error("Memory schema fix failed!")
        sys.exit(1)
