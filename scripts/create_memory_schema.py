"""
Script to create or update the memory tables schema.
This creates fresh tables with the correct structure if needed.
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

def create_memory_schema():
    """Create or update memory tables schema"""
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
        # Transaction for initial table check
        with conn.begin():
            # Check if tables exist
            memory_exists = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
            )).scalar()
            
            events_exists = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events')"
            )).scalar()
            
            logger.info(f"Existing tables check: memory_entries={memory_exists}, events={events_exists}")
        
        # First transaction: Create memory_entries table if it doesn't exist
        with conn.begin():
            try:
                if not memory_exists:
                    logger.info("Creating memory_entries table")
                    conn.execute(text("""
                        CREATE TABLE memory_entries (
                            id VARCHAR(36) PRIMARY KEY,
                            character_id VARCHAR(36) NOT NULL,
                            user_id VARCHAR(36) NOT NULL,
                            memory_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
                            category VARCHAR(50) NOT NULL DEFAULT 'general',
                            content TEXT NOT NULL,
                            importance INTEGER DEFAULT 5,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """))
                    logger.info("✅ Created memory_entries table")
                else:
                    # Table exists, check for missing columns
                    logger.info("memory_entries table exists, checking columns")
                    columns = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
                    )).fetchall()
                    
                    column_names = [col[0] for col in columns]
                    logger.info(f"Existing columns: {column_names}")
                    
                    # Check for missing columns
                    required_columns = {
                        'memory_type': 'VARCHAR(50) DEFAULT \'unknown\'',
                        'category': 'VARCHAR(50) DEFAULT \'general\'',
                        'content': 'TEXT NOT NULL',
                        'importance': 'INTEGER DEFAULT 5',
                        'is_active': 'BOOLEAN DEFAULT TRUE'
                    }
                    
                    for col_name, col_def in required_columns.items():
                        if col_name.lower() not in [c.lower() for c in column_names]:
                            logger.info(f"Adding missing column '{col_name}' to memory_entries table")
                            conn.execute(text(f"ALTER TABLE memory_entries ADD COLUMN {col_name} {col_def}"))
            except Exception as e:
                logger.error(f"Error creating memory_entries table: {e}")
        
        # Second transaction: Create events table if it doesn't exist
        with conn.begin():
            try:
                if not events_exists:
                    logger.info("Creating events table")
                    conn.execute(text("""
                        CREATE TABLE events (
                            id VARCHAR(36) PRIMARY KEY,
                            character_id VARCHAR(36) NOT NULL,
                            user_id VARCHAR(36),
                            event_type VARCHAR(50) NOT NULL,
                            data TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """))
                    logger.info("✅ Created events table")
            except Exception as e:
                logger.error(f"Error creating events table: {e}")
        
        # Third transaction: Create indexes
        with conn.begin():
            try:
                # Create indexes for memory_entries
                logger.info("Creating indexes for memory_entries table")
                
                # Basic indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id ON memory_entries(character_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id ON memory_entries(user_id)"))
                
                # Create memory_type column if it exists
                if 'memory_type' in [col[0].lower() for col in conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
                )).fetchall()]:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(memory_type)"))
                
                # Create category column if it exists
                if 'category' in [col[0].lower() for col in conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
                )).fetchall()]:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_category ON memory_entries(category)"))
                
                logger.info("✅ Created indexes for memory_entries table")
            except Exception as e:
                logger.error(f"Error creating memory_entries indexes: {e}")
        
        # Fourth transaction: Create indexes for events table
        with conn.begin():
            try:
                if events_exists:
                    logger.info("Creating indexes for events table")
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_character_id ON events(character_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type)"))
                    logger.info("✅ Created indexes for events table")
            except Exception as e:
                logger.error(f"Error creating events indexes: {e}")
        
        # Fifth transaction: Create text indexes for PostgreSQL
        if 'postgresql' in db_url.lower():
            with conn.begin():
                try:
                    logger.info("Creating text-based indexes for UUID fields")
                    
                    # For memory_entries
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id_text 
                        ON memory_entries ((character_id::text))
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id_text
                        ON memory_entries ((user_id::text))
                    """))
                    
                    # For events
                    if events_exists:
                        conn.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_events_character_id_text
                            ON events ((character_id::text))
                        """))
                        conn.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_events_user_id_text
                            ON events ((user_id::text)) 
                            WHERE user_id IS NOT NULL
                        """))
                    
                    logger.info("✅ Created text-based indexes for UUID fields")
                except Exception as e:
                    logger.error(f"Error creating text-based indexes: {e}")
    
    logger.info("✅ Memory schema creation/update completed")
    return True

if __name__ == "__main__":
    create_memory_schema()
