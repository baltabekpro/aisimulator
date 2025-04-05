"""
Fix the messages table schema by adding missing columns.
This script adds both is_read and is_gift columns if they don't exist.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def fix_messages_table():
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
                # Get the list of existing columns
                if is_postgres:
                    result = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns " +
                        "WHERE table_name='messages'"
                    ))
                    existing_columns = [row[0] for row in result]
                else:
                    result = conn.execute(text("PRAGMA table_info(messages)"))
                    existing_columns = [row[1] for row in result]
                
                print(f"Existing columns in messages table: {existing_columns}")
                
                # Add is_read column if it doesn't exist
                if 'is_read' not in existing_columns:
                    print("Adding is_read column to messages table...")
                    
                    if is_postgres:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT false"))
                    else:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0"))
                    
                    print("✅ is_read column added successfully!")
                else:
                    print("is_read column already exists in messages table")
                
                # Add is_gift column if it doesn't exist
                if 'is_gift' not in existing_columns:
                    print("Adding is_gift column to messages table...")
                    
                    if is_postgres:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN is_gift BOOLEAN NOT NULL DEFAULT false"))
                    else:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN is_gift BOOLEAN NOT NULL DEFAULT 0"))
                    
                    print("✅ is_gift column added successfully!")
                else:
                    print("is_gift column already exists in messages table")
                
                # Add created_at column if it doesn't exist and timestamp doesn't exist
                if 'created_at' not in existing_columns:
                    print("Adding created_at column to messages table...")
                    
                    if is_postgres:
                        if 'timestamp' in existing_columns:
                            # If timestamp exists, rename it to created_at
                            conn.execute(text("ALTER TABLE messages RENAME COLUMN timestamp TO created_at"))
                            print("✅ Renamed timestamp column to created_at")
                        else:
                            # Otherwise add a new created_at column
                            conn.execute(text("ALTER TABLE messages ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT NOW()"))
                            print("✅ created_at column added successfully!")
                    else:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"))
                        print("✅ created_at column added successfully!")
                else:
                    print("created_at column already exists in messages table")
                
                # Add updated_at column if it doesn't exist
                if 'updated_at' not in existing_columns:
                    print("Adding updated_at column to messages table...")
                    
                    if is_postgres:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN updated_at TIMESTAMP"))
                        print("✅ updated_at column added successfully!")
                    else:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN updated_at TIMESTAMP"))
                        print("✅ updated_at column added successfully!")
                else:
                    print("updated_at column already exists in messages table")
                
                # Verify the changes
                if is_postgres:
                    result = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns " +
                        "WHERE table_name='messages'"
                    ))
                    updated_columns = [row[0] for row in result]
                else:
                    result = conn.execute(text("PRAGMA table_info(messages)"))
                    updated_columns = [row[1] for row in result]
                
                print(f"Updated columns in messages table: {updated_columns}")
                print("✅ Messages table schema updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating messages table: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_messages_table()
