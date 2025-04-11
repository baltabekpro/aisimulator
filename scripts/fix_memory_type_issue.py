#!/usr/bin/env python3
"""
Fix the memory entries table by adding memory_type column and creating a view for compatibility.
This resolves the issue where the application code uses 'memory_type' but the database has 'type'.
"""

import os
import sys
import logging
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Add parent directory to path so we can import from project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

try:
    from core.db.session import SessionLocal, engine
    from core.config import settings
except ImportError:
    logger.error("Failed to import required modules. Make sure you're running this from the project root.")
    sys.exit(1)

def read_sql_file(filename):
    """Read SQL commands from a file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"SQL file {filename} not found")
        return None

def execute_sql_script(sql_script):
    """Execute a SQL script using SQLAlchemy."""
    if not sql_script:
        return False
        
    db = SessionLocal()
    try:
        # Split the script into separate commands by semicolon
        commands = sql_script.split(';')
        
        for cmd in commands:
            cmd = cmd.strip()
            if cmd:  # Skip empty commands
                logger.info(f"Executing SQL: {cmd[:80]}...")  # Log only start of command for brevity
                db.execute(text(cmd))
        
        db.commit()
        logger.info("SQL script executed successfully")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error executing SQL script: {e}")
        return False
    finally:
        db.close()

def check_memory_entries_table():
    """Check if memory_entries table exists and if memory_type column exists."""
    db = SessionLocal()
    try:
        # Check if table exists
        result = db.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memory_entries')"))
        table_exists = result.scalar()
        
        if not table_exists:
            logger.warning("memory_entries table does not exist yet")
            return False
            
        # Check if memory_type column exists
        result = db.execute(text("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'memory_entries' AND column_name = 'memory_type')"))
        column_exists = result.scalar()
        
        if column_exists:
            logger.info("memory_type column already exists in memory_entries table")
            return True
        else:
            logger.info("memory_type column does not exist in memory_entries table, will add it")
            return False
    except SQLAlchemyError as e:
        logger.error(f"Error checking memory_entries table: {e}")
        return False
    finally:
        db.close()

def main():
    logger.info("Starting memory_type column fix script")
    
    # Check if the memory_type column already exists
    if check_memory_entries_table():
        logger.info("Table already has memory_type column. No action needed.")
        return
    
    # Read SQL script from file
    sql_script = read_sql_file("fix_memory_type_column.sql")
    if not sql_script:
        logger.error("Failed to read SQL script")
        return
    
    # Execute the script
    if execute_sql_script(sql_script):
        logger.info("Successfully fixed memory_type column issue")
    else:
        logger.error("Failed to fix memory_type column issue")

if __name__ == "__main__":
    main()