"""
Script to add a new memory to the database.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import uuid
import argparse
from datetime import datetime

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_character_list(conn):
    """Get a list of available characters"""
    try:
        return conn.execute(text("""
            SELECT id, name FROM characters
            ORDER BY name
        """)).fetchall()
    except Exception as e:
        logger.error(f"Error fetching characters: {e}")
        return []

def get_user_list(conn):
    """Get a list of available users"""
    try:
        return conn.execute(text("""
            SELECT id, username FROM users
            ORDER BY username
        """)).fetchall()
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []

def add_memory(character_id=None, user_id=None, memory_type=None, category=None, content=None, importance=None):
    """Add a new memory to the database"""
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
                # If no character_id provided, list characters and ask user to select one
                if not character_id:
                    characters = get_character_list(conn)
                    if not characters:
                        logger.error("No characters found in database")
                        return False
                    
                    print("\nAvailable characters:")
                    for i, (char_id, char_name) in enumerate(characters, 1):
                        print(f"{i}. {char_name} (ID: {char_id})")
                    
                    choice = input("\nSelect character number (or paste ID): ")
                    
                    if choice.isdigit() and 1 <= int(choice) <= len(characters):
                        character_id = characters[int(choice)-1][0]
                    elif uuid.UUID(choice, version=4):  # Try to parse as UUID
                        character_id = choice
                    else:
                        logger.error("Invalid character selection")
                        return False
                
                # If no user_id provided, list users or create a placeholder
                if not user_id:
                    users = get_user_list(conn)
                    if users:
                        print("\nAvailable users:")
                        for i, (usr_id, username) in enumerate(users, 1):
                            print(f"{i}. {username} (ID: {usr_id})")
                        
                        print(f"{len(users)+1}. Create a new placeholder user ID")
                        
                        choice = input("\nSelect user number (or paste ID): ")
                        
                        if choice.isdigit() and 1 <= int(choice) <= len(users):
                            user_id = users[int(choice)-1][0]
                        elif choice.isdigit() and int(choice) == len(users)+1:
                            user_id = str(uuid.uuid4())
                            logger.info(f"Created placeholder user ID: {user_id}")
                        elif uuid.UUID(choice, version=4):  # Try to parse as UUID
                            user_id = choice
                        else:
                            logger.error("Invalid user selection")
                            return False
                    else:
                        user_id = str(uuid.uuid4())
                        logger.info(f"No users found, created placeholder user ID: {user_id}")
                
                # Get memory type
                if not memory_type:
                    memory_types = ["personal_info", "preference", "fact", "date", "relationship", "other"]
                    print("\nMemory types:")
                    for i, t in enumerate(memory_types, 1):
                        print(f"{i}. {t}")
                    
                    choice = input("\nSelect memory type (or enter custom): ")
                    
                    if choice.isdigit() and 1 <= int(choice) <= len(memory_types):
                        memory_type = memory_types[int(choice)-1]
                    else:
                        memory_type = choice
                
                # Get category
                if not category:
                    categories = ["general", "job", "age", "name", "hobby", "like", "dislike", 
                                 "location", "family", "appearance", "personality", "other"]
                    print("\nCategories:")
                    for i, c in enumerate(categories, 1):
                        print(f"{i}. {c}")
                    
                    choice = input("\nSelect category (or enter custom): ")
                    
                    if choice.isdigit() and 1 <= int(choice) <= len(categories):
                        category = categories[int(choice)-1]
                    else:
                        category = choice
                
                # Get content
                if not content:
                    content = input("\nEnter memory content: ")
                    if not content:
                        logger.error("Memory content cannot be empty")
                        return False
                
                # Get importance (1-10)
                if not importance:
                    importance_input = input("\nEnter importance (1-10, default is 5): ")
                    if importance_input.strip() and importance_input.isdigit():
                        importance = max(1, min(10, int(importance_input)))
                    else:
                        importance = 5
                
                # Insert the memory
                memory_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                
                conn.execute(text("""
                    INSERT INTO memory_entries (
                        id, character_id, user_id, memory_type, category, content,
                        importance, is_active, created_at, updated_at
                    ) VALUES (
                        :id, :character_id, :user_id, :memory_type, :category, :content,
                        :importance, :is_active, :created_at, :updated_at
                    )
                """), {
                    "id": memory_id,
                    "character_id": character_id,
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "category": category,
                    "content": content,
                    "importance": importance,
                    "is_active": True,
                    "created_at": timestamp,
                    "updated_at": timestamp
                })
                
                logger.info(f"✅ Memory added successfully:")
                logger.info(f"  Type: {memory_type}")
                logger.info(f"  Category: {category}")
                logger.info(f"  Content: {content}")
                logger.info(f"  Importance: {importance}")
                logger.info(f"  Character ID: {character_id}")
                logger.info(f"  User ID: {user_id}")
                
                return True
            except Exception as e:
                logger.error(f"Error adding memory: {e}")
                return False

def main():
    parser = argparse.ArgumentParser(description="Add a memory to the database")
    parser.add_argument("--character", "-c", help="Character ID")
    parser.add_argument("--user", "-u", help="User ID")
    parser.add_argument("--type", "-t", help="Memory type")
    parser.add_argument("--category", "-g", help="Memory category")
    parser.add_argument("--content", "-m", help="Memory content")
    parser.add_argument("--importance", "-i", type=int, help="Importance (1-10)")
    
    args = parser.parse_args()
    
    add_memory(
        character_id=args.character,
        user_id=args.user,
        memory_type=args.type,
        category=args.category,
        content=args.content,
        importance=args.importance
    )

if __name__ == "__main__":
    main()
