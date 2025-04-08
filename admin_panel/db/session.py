"""
Database session management for the admin panel.
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Base for models to use
Base = declarative_base()

def get_engine():
    """
    Create and return a SQLAlchemy engine instance using the database URL
    from environment variables.
    """
    # Get database URL from environment
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://aibot:postgres@postgres:5432/aibot"
        logger.warning(f"DATABASE_URL not found in environment, using default: {db_url}")
    
    # Create and return engine
    try:
        engine = create_engine(db_url)
        logger.info("Database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Error creating database engine: {e}")
        raise

# Create a configured "Session" class
engine = get_engine()
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = scoped_session(session_factory)

def get_session():
    """
    Get a database session for use in application code.
    """
    session = SessionLocal()
    try:
        return session
    except Exception as e:
        session.close()
        logger.error(f"Error getting database session: {e}")
        raise
