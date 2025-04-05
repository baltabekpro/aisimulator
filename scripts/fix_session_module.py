"""
Script to ensure the database session module is properly configured.
This fixes issues with SessionLocal imports and session handling.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_session_module():
    # Generate fixed session.py
    session_py_path = os.path.join("core", "db", "session.py")
    session_content = """\"\"\"
Database session utilities
\"\"\"
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aibot.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={} if "postgresql" in DATABASE_URL else {"check_same_thread": False}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
declarative_base = declarative_base

def get_db_session():
    \"\"\"
    Get a new database session
    
    Returns:
        Session: A new database session
    \"\"\"
    db = SessionLocal()
    return db

def get_session():
    \"\"\"Alias for get_db_session for backward compatibility\"\"\"
    return get_db_session()

def get_db():
    \"\"\"
    Get a database session for FastAPI dependency injection.
    Usage in FastAPI:
    
    ```
    @app.get("/users/")
    def read_users(db: Session = Depends(get_db)):
        ...
    ```
    \"\"\"
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""

    with open(session_py_path, 'w', encoding='utf-8') as f:
        f.write(session_content)
    logger.info(f"✅ Fixed session module written to {session_py_path}")
    
    # Update base.py to avoid circular imports and fix model imports
    base_py_path = os.path.join("core", "db", "base.py")
    base_content = """from sqlalchemy.ext.declarative import declarative_base

# Create Base class for models
Base = declarative_base()

# Note: Models are imported in other modules when needed
# The imports are commented out here to avoid circular imports
# These were causing "Import could not be resolved" errors
#
# from core.db.models.user import User
# from core.db.models.message import Message
# from core.db.models.character import Character
# from core.db.models.chat_history import ChatHistory
# from core.db.models.memory_entry import MemoryEntry
"""

    with open(base_py_path, 'w', encoding='utf-8') as f:
        f.write(base_content)
    logger.info(f"✅ Fixed base module written to {base_py_path}")
    
    # Create __init__.py files if they don't exist
    init_paths = [
        os.path.join("core", "db", "__init__.py"),
        os.path.join("core", "db", "models", "__init__.py")
    ]
    
    for init_path in init_paths:
        os.makedirs(os.path.dirname(init_path), exist_ok=True)
        if not os.path.exists(init_path):
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write("# Database module\n")
            logger.info(f"✅ Created {init_path}")
    
    # Create a models/__init__.py file that imports all models
    models_init_path = os.path.join("core", "db", "models", "__init__.py")
    models_init_content = """# Import all models here for convenience
# This allows imports like: from core.db.models import User, Message, etc.

try:
    from core.db.models.user import User
except ImportError:
    pass

try:
    from core.db.models.message import Message
except ImportError:
    pass

try:
    from core.db.models.character import Character
except ImportError:
    pass

try:
    from core.db.models.chat_history import ChatHistory
except ImportError:
    pass

try:
    from core.db.models.memory_entry import MemoryEntry
except ImportError:
    pass
"""
    
    with open(models_init_path, 'w', encoding='utf-8') as f:
        f.write(models_init_content)
    logger.info(f"✅ Created models __init__.py at {models_init_path}")
    
    logger.info("Database session module fixed successfully!")
    return True

if __name__ == "__main__":
    fix_session_module()
