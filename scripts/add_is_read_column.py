"""
Quick script to add the is_read column to the messages table directly,
bypassing Alembic migrations which might be having issues.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def add_is_read_column():
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
        # Check if we're using PostgreSQL or SQLite
        is_postgres = 'postgresql' in db_url.lower()
        
        with engine.connect() as conn:
            # Begin a transaction
            with conn.begin():
                # Check if column exists (different syntax for PostgreSQL vs SQLite)
                if is_postgres:
                    # PostgreSQL syntax
                    result = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns " +
                        "WHERE table_name='messages' AND column_name='is_read'"
                    ))
                else:
                    # SQLite syntax
                    result = conn.execute(text(
                        "SELECT 1 FROM pragma_table_info('messages') WHERE name='is_read'"
                    ))
                
                column_exists = result.fetchone() is not None
                
                if not column_exists:
                    print("Adding is_read column to messages table...")
                    
                    # Add the column with appropriate syntax for the database type
                    if is_postgres:
                        # PostgreSQL syntax
                        conn.execute(text("ALTER TABLE messages ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT false"))
                    else:
                        # SQLite syntax
                        conn.execute(text("ALTER TABLE messages ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0"))
                    
                    print("✅ Column added successfully!")
                else:
                    print("Column is_read already exists in messages table.")
        
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_is_read_column()
