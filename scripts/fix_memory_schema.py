"""
Script to fix memory_entries table schema by adding missing columns.

This script adds memory_type and category columns to the memory_entries table
to ensure compatibility with the AI core.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import getpass

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
    
    # Check if there's a hostname "postgres" in the URL that might cause connection issues
    if "postgres" in db_url and "localhost" not in db_url:
        logger.warning("Your DATABASE_URL contains 'postgres' hostname which might not resolve on your local machine")
        
        use_custom_url = input("Would you like to enter a local database URL instead? (y/n): ")
        if use_custom_url.lower() == 'y':
            db_host = input("Enter database host (default: localhost): ") or "localhost"
            db_port = input("Enter database port (default: 5432): ") or "5432"
            db_name = input("Enter database name (default: ai_simulator): ") or "ai_simulator"
            db_user = input("Enter database username (default: postgres): ") or "postgres"
            db_pass = getpass.getpass("Enter database password: ")
            
            db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
            logger.info(f"Using custom database URL: postgresql://{db_user}:****@{db_host}:{db_port}/{db_name}")
    
    logger.info(f"Connecting to database...")
    try:
        engine = create_engine(db_url)
        
        # Test connection
        connection_test = False
        try:
            with engine.connect() as conn:
                connection_test = True
        except Exception as e:
            logger.error(f"Could not connect to database: {e}")
            return False
            
        if not connection_test:
            logger.error("Failed to connect to database")
            return False
            
        logger.info("Successfully connected to database")
        
        with engine.connect() as conn:
            # Check if memory_entries table exists
            with conn.begin():
                table_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
                )).scalar()
                
                if not table_exists:
                    logger.error("memory_entries table doesn't exist, cannot fix schema")
                    return False
                
                logger.info("memory_entries table exists, checking columns")
                
                # Get current columns
                columns = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
                )).fetchall()
                
                column_names = [col[0] for col in columns]
                logger.info(f"Existing columns: {column_names}")
                
                # Check for missing columns
                required_columns = {
                    'memory_type': 'VARCHAR(50) DEFAULT \'unknown\'',
                    'category': 'VARCHAR(50) DEFAULT \'general\''
                }
                
                # Add missing columns
                added_columns = False
                for col_name, col_def in required_columns.items():
                    if col_name.lower() not in [c.lower() for c in column_names]:
                        logger.info(f"Adding missing column '{col_name}' to memory_entries table")
                        conn.execute(text(f"ALTER TABLE memory_entries ADD COLUMN {col_name} {col_def}"))
                        added_columns = True
                    else:
                        logger.info(f"Column '{col_name}' already exists")
                
                if added_columns:
                    # Create indexes for added columns if they don't exist
                    logger.info("Creating indexes for memory_entries table")
                    
                    if 'memory_type' in required_columns and 'memory_type' not in column_names:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(memory_type)"))
                        logger.info("Created index on memory_entries.memory_type")
                    
                    if 'category' in required_columns and 'category' not in column_names:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_category ON memory_entries(category)"))
                        logger.info("Created index on memory_entries.category")
                    
                    logger.info("✅ Schema update completed successfully")
                else:
                    logger.info("✅ No columns needed to be added, schema is already correct")
                
                return True
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False

if __name__ == "__main__":
    print("Memory Schema Fixer")
    print("===================")
    print("This script will add missing columns to memory_entries table.")
    print("Make sure your database is accessible before continuing.")
    print()
    
    proceed = input("Do you want to proceed? (y/n): ")
    if proceed.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
        
    fixed = fix_memory_schema()
    if fixed:
        print("Memory schema fixed successfully!")
    else:
        print("Failed to fix memory schema. Check the logs for details.")
        sys.exit(1)
