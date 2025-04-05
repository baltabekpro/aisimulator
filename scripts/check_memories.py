"""
Script to check and display existing memories in the database.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import json
from tabulate import tabulate

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_memories():
    """Check and display existing memories in the database"""
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
            # Count total memories
            memory_count = conn.execute(text("SELECT COUNT(*) FROM memory_entries")).scalar()
            logger.info(f"Total memories in database: {memory_count}")
            
            # Count by type
            type_counts = conn.execute(text("""
                SELECT memory_type, COUNT(*) 
                FROM memory_entries 
                GROUP BY memory_type
                ORDER BY COUNT(*) DESC
            """)).fetchall()
            
            if type_counts:
                logger.info("Memory counts by type:")
                for memory_type, count in type_counts:
                    logger.info(f"  - {memory_type}: {count}")
            
            # Count by category
            category_counts = conn.execute(text("""
                SELECT category, COUNT(*) 
                FROM memory_entries 
                GROUP BY category
                ORDER BY COUNT(*) DESC
            """)).fetchall()
            
            if category_counts:
                logger.info("Memory counts by category:")
                for category, count in category_counts:
                    logger.info(f"  - {category}: {count}")
            
            # Get memories by character
            character_memories = conn.execute(text("""
                SELECT c.name AS character_name, COUNT(m.id) AS memory_count
                FROM memory_entries m
                LEFT JOIN characters c ON m.character_id::text = c.id::text
                GROUP BY c.name
                ORDER BY COUNT(m.id) DESC
            """)).fetchall()
            
            if character_memories:
                logger.info("Memories by character:")
                for char_name, count in character_memories:
                    char_display = char_name if char_name else "Unknown Character"
                    logger.info(f"  - {char_display}: {count}")
            
            # Get recent memories
            recent_memories = conn.execute(text("""
                SELECT 
                    m.id, 
                    c.name AS character_name,
                    m.memory_type,
                    m.category,
                    m.content,
                    m.importance,
                    m.created_at
                FROM memory_entries m
                LEFT JOIN characters c ON m.character_id::text = c.id::text
                ORDER BY m.created_at DESC
                LIMIT 10
            """)).fetchall()
            
            if recent_memories:
                logger.info("\nRecent memories:")
                
                # Format as a table
                headers = ["Character", "Type", "Category", "Importance", "Content"]
                table_data = []
                
                for memory in recent_memories:
                    char_name = memory[1] if memory[1] else "Unknown"
                    mem_type = memory[2] if memory[2] else "unknown"
                    category = memory[3] if memory[3] else "general"
                    content = memory[4]
                    importance = memory[5] if memory[5] is not None else 5
                    
                    # Truncate content if too long
                    if content and len(content) > 50:
                        content = content[:47] + "..."
                    
                    table_data.append([char_name, mem_type, category, importance, content])
                
                # Print table
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
            else:
                logger.info("No memories found in the database")
            
            return True
        except Exception as e:
            logger.error(f"Error checking memories: {e}")
            return False

if __name__ == "__main__":
    check_memories()
