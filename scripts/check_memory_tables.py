"""
Script to check memory tables structure and data.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import json

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_memory_tables():
    """Check memory tables structure and data"""
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
            # Check memory_entries table
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
                for col in columns:
                    logger.info(f"  - {col[0]} ({col[1]})")
                
                # Count records
                count = conn.execute(text("SELECT COUNT(*) FROM memory_entries")).scalar()
                logger.info(f"Memory entries count: {count}")
                
                if count > 0:
                    # Show some sample data
                    samples = conn.execute(text(
                        "SELECT id, character_id, user_id, memory_type, category, content, created_at FROM memory_entries LIMIT 5"
                    )).fetchall()
                    
                    logger.info("Sample memory entries:")
                    for sample in samples:
                        logger.info(f"  - ID: {sample[0]}")
                        logger.info(f"    Character: {sample[1]}")
                        logger.info(f"    User: {sample[2]}")
                        logger.info(f"    Type: {sample[3]}")
                        logger.info(f"    Category: {sample[4]}")
                        logger.info(f"    Content: {sample[5]}")
                        logger.info(f"    Created: {sample[6]}")
                        logger.info(f"    -----")
            else:
                logger.warning("❌ Memory entries table does not exist")
            
            # Check events table
            events_exists = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events')"
            )).scalar()
            
            if events_exists:
                logger.info("✅ Events table exists")
                
                # Get columns
                columns = conn.execute(text(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'events'"
                )).fetchall()
                
                logger.info("Events table columns:")
                for col in columns:
                    logger.info(f"  - {col[0]} ({col[1]})")
                
                # Count records
                count = conn.execute(text("SELECT COUNT(*) FROM events WHERE event_type = 'memory'")).scalar()
                logger.info(f"Memory-related events count: {count}")
                
                if count > 0:
                    # Show some sample data
                    samples = conn.execute(text(
                        "SELECT id, character_id, user_id, event_type, data, created_at FROM events WHERE event_type = 'memory' LIMIT 5"
                    )).fetchall()
                    
                    logger.info("Sample memory events:")
                    for sample in samples:
                        logger.info(f"  - ID: {sample[0]}")
                        logger.info(f"    Character: {sample[1]}")
                        logger.info(f"    User: {sample[2]}")
                        logger.info(f"    Type: {sample[3]}")
                        try:
                            data = json.loads(sample[4]) if isinstance(sample[4], str) else sample[4]
                            logger.info(f"    Data: {data}")
                        except:
                            logger.info(f"    Data: {sample[4]}")
                        logger.info(f"    Created: {sample[5]}")
                        logger.info(f"    -----")
            else:
                logger.warning("❌ Events table does not exist")
            
            # Look for memory data in messages table
            logger.info("Checking for memory data in messages table...")
            
            # Function to extract memory JSON from message content
            def extract_memory_json(content):
                try:
                    if content and isinstance(content, str) and '"memory":' in content:
                        # Simple check for JSON-like content
                        if content.strip().startswith('{') and content.strip().endswith('}'):
                            data = json.loads(content)
                            if isinstance(data, dict) and 'memory' in data:
                                return data['memory']
                except:
                    pass
                return None
            
            # Count messages that might contain memory data
            messages_with_memory = 0
            memory_items_found = 0
            
            # Query for messages that might contain memory data
            result = conn.execute(text("""
                SELECT id, content FROM messages
                WHERE content LIKE '%"memory":%'
                LIMIT 100
            """))
            
            messages = result.fetchall()
            for msg in messages:
                memory_data = extract_memory_json(msg[1])
                if memory_data:
                    messages_with_memory += 1
                    if isinstance(memory_data, list):
                        memory_items_found += len(memory_data)
                        logger.info(f"Found memory data in message {msg[0]}:")
                        for item in memory_data[:3]:  # Show up to 3 items
                            logger.info(f"  - Type: {item.get('type', 'unknown')}")
                            logger.info(f"    Category: {item.get('category', 'unknown')}")
                            logger.info(f"    Content: {item.get('content', '')}")
            
            logger.info(f"Found {messages_with_memory} messages containing memory data")
            logger.info(f"Found {memory_items_found} memory items in messages")
            
            return True
        except Exception as e:
            logger.error(f"Error checking memory tables: {e}")
            return False

if __name__ == "__main__":
    check_memory_tables()
