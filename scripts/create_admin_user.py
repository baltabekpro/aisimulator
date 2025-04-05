"""
Script to create an admin user for the admin panel
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

def create_admin_user(username=None, password=None):
    """Create an admin user in the database"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    # Get admin credentials from environment or parameters
    admin_username = username or os.getenv("ADMIN_USERNAME", "admin")
    admin_password = password or os.getenv("ADMIN_PASSWORD", "admin_password")
    
    # Connect to database
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Start transaction
        with conn.begin():
            # Check if admin_users table exists
            try:
                result = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_users')"))
                table_exists = result.scalar()
                
                if not table_exists:
                    # Create admin_users table if it doesn't exist
                    logger.info("Creating admin_users table")
                    conn.execute(text("""
                        CREATE TABLE admin_users (
                            id VARCHAR(36) PRIMARY KEY,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            email VARCHAR(100) UNIQUE,
                            password_hash VARCHAR(200) NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            last_login TIMESTAMP,
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                    """))
                
                # Check if user already exists
                result = conn.execute(
                    text("SELECT COUNT(*) FROM admin_users WHERE username = :username"),
                    {"username": admin_username}
                )
                user_exists = result.scalar() > 0
                
                if user_exists:
                    logger.info(f"Admin user '{admin_username}' already exists")
                    return True
                
                # Create admin user
                admin_id = str(uuid.uuid4())
                password_hash = generate_password_hash(admin_password)
                
                conn.execute(
                    text("""
                        INSERT INTO admin_users (id, username, email, password_hash, is_active, created_at)
                        VALUES (:id, :username, :email, :password_hash, TRUE, NOW())
                    """),
                    {
                        "id": admin_id,
                        "username": admin_username,
                        "email": f"{admin_username}@example.com",
                        "password_hash": password_hash
                    }
                )
                
                logger.info(f"Created admin user '{admin_username}'")
                return True
                
            except Exception as e:
                logger.error(f"Error creating admin user: {e}")
                return False

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Create an admin user for the admin panel")
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--password", help="Admin password")
    args = parser.parse_args()
    
    # Create admin user
    create_admin_user(username=args.username, password=args.password)
