#!/usr/bin/env python3
"""
Script to create a system user for memory entries
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import logging
import uuid

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_system_user():
    """Create a system user for orphaned memory entries"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    # Connect to database
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Start transaction
        with conn.begin():
            try:
                # Check if system user already exists
                result = conn.execute(
                    text("SELECT COUNT(*) FROM users WHERE user_id = :user_id"),
                    {"user_id": "00000000-0000-0000-0000-000000000000"}
                )
                user_exists = result.scalar() > 0
                
                if user_exists:
                    logger.info("System user already exists")
                    return True
                
                # Create system user
                password_hash = generate_password_hash("system")
                
                conn.execute(
                    text("""
                        INSERT INTO users (user_id, username, email, name, password_hash, created_at, is_admin)
                        VALUES (:user_id, :username, :email, :name, :password_hash, NOW(), FALSE)
                    """),
                    {
                        "user_id": "00000000-0000-0000-0000-000000000000",
                        "username": "system",
                        "email": "system@example.com",
                        "name": "System",
                        "password_hash": password_hash
                    }
                )
                
                # Fix any existing NULL user_id values
                conn.execute(
                    text("UPDATE memory_entries SET user_id = :system_id WHERE user_id IS NULL"),
                    {"system_id": "00000000-0000-0000-0000-000000000000"}
                )
                
                logger.info("Created system user for memory entries")
                return True
                
            except Exception as e:
                logger.error(f"Error creating system user: {e}")
                return False

if __name__ == "__main__":
    create_system_user()