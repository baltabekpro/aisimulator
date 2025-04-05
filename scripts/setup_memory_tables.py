"""
Script to set up memory tables and ensure memory data is correctly stored and accessible.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import logging
import uuid
import json

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_memory_tables():
    """Create and set up memory tables"""
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
                table_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
                )).scalar()
                
                if table_exists:
                    # Table exists, check its columns
                    columns = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
                    )).fetchall()
                    
                    column_names = [col[0] for col in columns]
                    logger.info(f"Found memory_entries table with columns: {', '.join(column_names)}")
                    
                    # Check for missing columns and add them if needed
                    required_columns = {
                        'memory_type': 'VARCHAR(50)',
                        'category': 'VARCHAR(50)',
                        'content': 'TEXT',
                        'is_active': 'BOOLEAN'
                    }
                    
                    for col_name, col_type in required_columns.items():
                        if col_name.lower() not in [c.lower() for c in column_names]:
                            logger.info(f"Adding missing column '{col_name}' to memory_entries table")
                            conn.execute(text(f"ALTER TABLE memory_entries ADD COLUMN {col_name} {col_type}"))
                            
                            # For required columns, set a default value
                            if col_name == 'memory_type':
                                conn.execute(text("UPDATE memory_entries SET memory_type = 'unknown' WHERE memory_type IS NULL"))
                            elif col_name == 'category':
                                conn.execute(text("UPDATE memory_entries SET category = 'general' WHERE category IS NULL"))
                            elif col_name == 'is_active':
                                conn.execute(text("UPDATE memory_entries SET is_active = TRUE WHERE is_active IS NULL"))
                else:
                    # Create memory_entries table if it doesn't exist
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS memory_entries (
                            id UUID PRIMARY KEY,
                            character_id UUID NOT NULL,
                            user_id UUID NOT NULL,
                            memory_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
                            category VARCHAR(50) NOT NULL DEFAULT 'general',
                            content TEXT NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    """))
                    logger.info("✅ Created memory_entries table")
                
                # Check if events table exists
                events_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events')"
                )).scalar()
                
                if not events_exists:
                    # Create events table if it doesn't exist
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS events (
                            id UUID PRIMARY KEY,
                            character_id UUID NOT NULL,
                            user_id UUID,
                            event_type VARCHAR(50) NOT NULL,
                            data JSONB NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    """))
                    logger.info("✅ Created events table")
                
                # Check for each column before creating indexes
                # For memory_entries table
                memory_columns = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
                )).fetchall()
                memory_column_names = [col[0] for col in memory_columns]
                
                # Create indexes only for columns that exist
                if 'character_id' in memory_column_names:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id ON memory_entries(character_id)"))
                    logger.info("Created index on memory_entries.character_id")
                
                if 'user_id' in memory_column_names:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id ON memory_entries(user_id)"))
                    logger.info("Created index on memory_entries.user_id")
                
                if 'memory_type' in memory_column_names:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(memory_type)"))
                    logger.info("Created index on memory_entries.memory_type")
                
                if 'category' in memory_column_names:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_category ON memory_entries(category)"))
                    logger.info("Created index on memory_entries.category")
                
                # For events table
                events_columns = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'events'"
                )).fetchall() if events_exists else []
                events_column_names = [col[0] for col in events_columns]
                
                # Create indexes for events table if it exists
                if events_exists:
                    if 'character_id' in events_column_names:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_character_id ON events(character_id)"))
                        logger.info("Created index on events.character_id")
                    
                    if 'event_type' in events_column_names:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)"))
                        logger.info("Created index on events.event_type")
                
                # Create text-based indexes for UUID columns to help with type casting
                if 'character_id' in memory_column_names:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id_text ON memory_entries ((character_id::text))"))
                    logger.info("Created text-based index on memory_entries.character_id")
                
                if 'user_id' in memory_column_names:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id_text ON memory_entries ((user_id::text))"))
                    logger.info("Created text-based index on memory_entries.user_id")
                
                if events_exists and 'character_id' in events_column_names:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_character_id_text ON events ((character_id::text))"))
                    logger.info("Created text-based index on events.character_id")
                
                logger.info("✅ Memory tables setup completed successfully")
                return True
            except Exception as e:
                logger.error(f"Error setting up memory tables: {e}")
                return False

def import_existing_memories():
    """Import memories from messages history into memory tables"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database for memory import: {db_url}")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        with conn.begin():
            try:
                # Check if we're using PostgreSQL
                is_postgresql = 'postgresql' in db_url.lower()
                
                # Find messages that contain memory data in the content
                logger.info("Looking for AI messages with memory data...")
                
                # Helper function to check for memory data in messages
                def extract_memory_json(content):
                    try:
                        # Try to find JSON content with memory field
                        if content and isinstance(content, str):
                            # Check if it looks like JSON
                            if content.strip().startswith('{') and content.strip().endswith('}'):
                                # Try to parse as JSON
                                data = json.loads(content)
                                if isinstance(data, dict) and 'memory' in data:
                                    return data['memory']
                    except:
                        pass
                    return None
                
                # Query for all assistant messages
                result = conn.execute(text("""
                    SELECT id, sender_id, recipient_id, content 
                    FROM messages 
                    WHERE sender_type = 'character'
                    ORDER BY created_at DESC
                    LIMIT 1000
                """))
                
                messages = result.fetchall()
                logger.info(f"Found {len(messages)} assistant messages to scan for memory data")
                
                # Variables to track import results
                memories_imported = 0
                messages_with_memory = 0
                
                # Process each message
                for msg in messages:
                    msg_id = msg[0]
                    character_id = msg[1] 
                    user_id = msg[2]
                    content = msg[3]
                    
                    # Extract memory data
                    memory_data = extract_memory_json(content)
                    
                    if memory_data:
                        messages_with_memory += 1
                        
                        # Process each memory item
                        if isinstance(memory_data, list):
                            for memory_item in memory_data:
                                if isinstance(memory_item, dict):
                                    memory_type = memory_item.get('type', 'unknown')
                                    category = memory_item.get('category', 'unknown')
                                    memory_content = memory_item.get('content', '')
                                    
                                    if memory_content:
                                        # Check if this memory already exists
                                        exists = conn.execute(text("""
                                            SELECT COUNT(*) FROM memory_entries
                                            WHERE character_id = :character_id 
                                            AND user_id = :user_id
                                            AND content = :content
                                        """), {
                                            "character_id": character_id,
                                            "user_id": user_id,
                                            "content": memory_content
                                        }).scalar()
                                        
                                        if not exists:
                                            # Insert into memory_entries
                                            new_id = str(uuid.uuid4())
                                            conn.execute(text("""
                                                INSERT INTO memory_entries (
                                                    id, character_id, user_id, memory_type, category, content
                                                ) VALUES (
                                                    :id, :character_id, :user_id, :memory_type, :category, :content
                                                )
                                            """), {
                                                "id": new_id,
                                                "character_id": character_id,
                                                "user_id": user_id,
                                                "memory_type": memory_type,
                                                "category": category,
                                                "content": memory_content
                                            })
                                            memories_imported += 1
                
                logger.info(f"Found {messages_with_memory} messages containing memory data")
                logger.info(f"Imported {memories_imported} unique memories into memory_entries table")
                
                # Test retrieving memories
                test_result = conn.execute(text("""
                    SELECT COUNT(*) FROM memory_entries
                """)).scalar()
                
                logger.info(f"Total memories in database: {test_result}")
                
                return True
            except Exception as e:
                logger.error(f"Error importing memories: {e}")
                return False

def fix_memory_management():
    """Main function to run memory management fixes"""
    setup_success = setup_memory_tables()
    
    if setup_success:
        import_success = import_existing_memories()
        return import_success
    
    return False

if __name__ == "__main__":
    fix_memory_management()
