"""
Script to create a test character in the database directly.
This ensures we have at least one character to work with.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import uuid
import json
from datetime import datetime

def create_character():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get database URL directly from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    print(f"Using database: {db_url}")
    
    # Connect to the database
    engine = create_engine(db_url)
    
    try:
        # Create a test character
        character_id = str(uuid.uuid4())
        name = "Мария"
        age = 25
        gender = "female"
        personality = "Дружелюбная, общительная, умная"
        background = "Программистка, любит путешествовать"
        interests = "Технологии, книги, спорт"
        
        with engine.connect() as conn:
            # Begin a transaction
            with conn.begin():
                # Check if the characters table exists
                if 'postgresql' in db_url.lower():
                    table_exists = conn.execute(text(
                        "SELECT 1 FROM information_schema.tables WHERE table_name = 'characters'"
                    )).fetchone() is not None
                else:
                    table_exists = conn.execute(text(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='characters'"
                    )).fetchone() is not None
                
                if not table_exists:
                    print("❌ Characters table doesn't exist - creating it...")
                    # Create the characters table
                    create_table_sql = """
                    CREATE TABLE characters (
                        id UUID PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        age INTEGER,
                        gender VARCHAR(50),
                        personality TEXT,
                        background TEXT,
                        interests TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                    """
                    conn.execute(text(create_table_sql))
                
                # Check if a character with this name already exists
                existing = conn.execute(
                    text("SELECT 1 FROM characters WHERE name = :name"),
                    {"name": name}
                ).fetchone()
                
                if not existing:
                    # Insert the character into the database
                    conn.execute(
                        text("""
                        INSERT INTO characters 
                        (id, name, age, gender, personality, background, interests, created_at)
                        VALUES (:id, :name, :age, :gender, :personality, :background, :interests, :created_at)
                        """),
                        {
                            "id": character_id,
                            "name": name,
                            "age": age,
                            "gender": gender,
                            "personality": personality,
                            "background": background,
                            "interests": interests,
                            "created_at": datetime.now()
                        }
                    )
                    print(f"✅ Created character: {name} (ID: {character_id})")
                else:
                    print(f"Character with name '{name}' already exists - skipping creation")
        
    except Exception as e:
        print(f"❌ Error creating character: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_character()
