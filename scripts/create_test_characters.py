import os
import sys
import uuid
import logging
import argparse
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test character data
TEST_CHARACTERS = [
    {
        "name": "Алиса",
        "age": 21,
        "gender": "female",
        "personality_traits": ["friendly", "curious", "creative"],
        "interests": ["art", "music", "reading"],
        "background": "Студентка художественного колледжа, мечтает стать известной художницей",
    },
    {
        "name": "Виктория",
        "age": 25,
        "gender": "female",
        "personality_traits": ["confident", "ambitious", "witty"],
        "interests": ["business", "fashion", "travel"],
        "background": "Успешный предприниматель, владеет небольшим бутиком",
    },
    {
        "name": "София",
        "age": 23,
        "gender": "female",
        "personality_traits": ["caring", "empathetic", "gentle"],
        "interests": ["psychology", "yoga", "cooking"],
        "background": "Начинающий психолог, работает в центре поддержки",
    },
    {
        "name": "Мария",
        "age": 24,
        "gender": "female",
        "personality_traits": ["adventurous", "energetic", "spontaneous"],
        "interests": ["sports", "hiking", "photography"],
        "background": "Профессиональный фотограф и любитель приключений",
    }
]

def parse_db_url(url, override_host=None, override_port=None):
    """Parse and potentially modify a database URL with custom host/port"""
    if not url:
        return url
        
    parts = urlparse(url)
    
    # If we need to override the hostname or port
    if (override_host or override_port) and parts.netloc:
        # Split netloc into components (host:port)
        netloc_parts = parts.netloc.split('@')
        if len(netloc_parts) > 1:
            # Handle credentials in URL
            auth, host_port = netloc_parts[0], netloc_parts[1]
        else:
            # No credentials
            auth, host_port = '', netloc_parts[0]
            
        # Split host and port if present
        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host, port = host_port, None
            
        # Apply overrides
        if override_host:
            host = override_host
        if override_port:
            port = override_port
            
        # Reconstruct netloc
        if port:
            new_host_port = f"{host}:{port}"
        else:
            new_host_port = host
            
        if auth:
            new_netloc = f"{auth}@{new_host_port}"
        else:
            new_netloc = new_host_port
            
        # Rebuild URL with new netloc
        new_parts = parts._replace(netloc=new_netloc)
        return urlunparse(new_parts)
    
    return url

def create_test_characters(db_host=None, db_port=None):
    """Create test characters in the database"""
    session = None
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL", "postgresql://aibot:postgres@postgres:5432/aibot")
        
        # If db_host is provided, modify the database URL
        if db_host or db_port:
            logger.info(f"Overriding database connection: host={db_host}, port={db_port}")
            database_url = parse_db_url(database_url, db_host, db_port)
            logger.info(f"Using database URL: {database_url}")
        
        # Create database engine
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        
        try:
            # Test connection before proceeding
            connection = engine.connect()
            connection.close()
            logger.info("Database connection successful")
        except OperationalError as e:
            if "could not translate host name" in str(e):
                logger.error(f"Hostname resolution error: {e}")
                logger.error("Try running with --db-host localhost or the correct hostname")
            else:
                logger.error(f"Database connection error: {e}")
            return False
            
        session = Session()
        
        # Create characters table if it doesn't exist - using text()
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS characters (
                id UUID PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                age INTEGER,
                gender VARCHAR(50),
                personality_traits TEXT[],
                interests TEXT[],
                background TEXT,
                creator_id UUID,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        session.commit()
        
        # Insert test characters
        for char_data in TEST_CHARACTERS:
            # Check if character already exists - using text()
            existing = session.execute(
                text("SELECT id FROM characters WHERE name = :name"),
                {"name": char_data["name"]}
            ).fetchone()
            
            if not existing:
                char_id = uuid.uuid4()
                session.execute(text("""
                    INSERT INTO characters (
                        id, name, age, gender, personality_traits, 
                        interests, background, created_at
                    ) VALUES (
                        :id, :name, :age, :gender, :personality_traits,
                        :interests, :background, :created_at
                    )
                """), {
                    "id": char_id,
                    "name": char_data["name"],
                    "age": char_data["age"],
                    "gender": char_data["gender"],
                    "personality_traits": char_data["personality_traits"],
                    "interests": char_data["interests"],
                    "background": char_data["background"],
                    "created_at": datetime.utcnow()
                })
                logger.info(f"Created character: {char_data['name']}")
        
        session.commit()
        logger.info("Test characters created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error creating test characters: {e}")
        if session:
            session.rollback()
        return False
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    # Add command line arguments for database connection
    parser = argparse.ArgumentParser(description='Create test characters in the database')
    parser.add_argument('--db-host', help='Database hostname (overrides the one in DATABASE_URL)')
    parser.add_argument('--db-port', help='Database port (overrides the one in DATABASE_URL)')
    args = parser.parse_args()
    
    print("Creating test characters...")
    success = create_test_characters(db_host=args.db_host, db_port=args.db_port)
    if success:
        print("Done!")
    else:
        print("Failed to create test characters. Check the logs for details.")
        print("\nTry running with database host override:")
        print("  python scripts/create_test_characters.py --db-host localhost")
        sys.exit(1)
