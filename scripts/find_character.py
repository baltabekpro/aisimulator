"""
Script to find a character in the database.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import argparse

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_character(character_id=None):
    """Find a character in the database by ID"""
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
            if not character_id:
                # List all characters
                logger.info("Listing all characters:")
                
                # Check ai_partners table
                try:
                    ai_partners = conn.execute(text("""
                        SELECT id, name FROM ai_partners ORDER BY name
                    """)).fetchall()
                    
                    if ai_partners:
                        logger.info("Characters found in ai_partners table:")
                        for char in ai_partners:
                            logger.info(f"  - {char[1]} (ID: {char[0]})")
                    else:
                        logger.info("No characters found in ai_partners table")
                except Exception as e:
                    logger.error(f"Error querying ai_partners table: {e}")
                
                # Check characters table
                try:
                    characters = conn.execute(text("""
                        SELECT id, name FROM characters ORDER BY name
                    """)).fetchall()
                    
                    if characters:
                        logger.info("Characters found in characters table:")
                        for char in characters:
                            logger.info(f"  - {char[1]} (ID: {char[0]})")
                    else:
                        logger.info("No characters found in characters table")
                except Exception as e:
                    logger.error(f"Error querying characters table: {e}")
                
                return True
            
            # Find specific character
            logger.info(f"Looking for character with ID: {character_id}")
            
            # Try ai_partners table first
            try:
                ai_partner = conn.execute(text("""
                    SELECT id, name FROM ai_partners WHERE id::text = :character_id
                """), {"character_id": character_id}).fetchone()
                
                if ai_partner:
                    logger.info(f"✅ Found in ai_partners: {ai_partner[1]} (ID: {ai_partner[0]})")
                else:
                    logger.info("❌ Not found in ai_partners table")
            except Exception as e:
                logger.error(f"Error querying ai_partners table: {e}")
            
            # Try characters table
            try:
                character = conn.execute(text("""
                    SELECT id, name FROM characters WHERE id::text = :character_id
                """), {"character_id": character_id}).fetchone()
                
                if character:
                    logger.info(f"✅ Found in characters: {character[1]} (ID: {character[0]})")
                else:
                    logger.info("❌ Not found in characters table")
            except Exception as e:
                logger.error(f"Error querying characters table: {e}")
            
            # Check if there are any memories for this character
            try:
                memory_count = conn.execute(text("""
                    SELECT COUNT(*) FROM memory_entries WHERE character_id::text = :character_id
                """), {"character_id": character_id}).scalar()
                
                logger.info(f"Memory entries for this character: {memory_count}")
            except Exception as e:
                logger.error(f"Error checking memory_entries: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error finding character: {e}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find a character in the database")
    parser.add_argument("--id", help="Character ID to search for (optional)")
    
    args = parser.parse_args()
    find_character(args.id)
