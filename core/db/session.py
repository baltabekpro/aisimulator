"""
Database session utilities
"""
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
    """
    Get a new database session
    
    Returns:
        Session: A new database session
    """
    db = SessionLocal()
    return db

def get_session():
    """Alias for get_db_session for backward compatibility"""
    return get_db_session()

def get_db():
    """
    Get a database session for FastAPI dependency injection.
    Usage in FastAPI:
    
    ```
    @app.get("/users/")
    def read_users(db: Session = Depends(get_db)):
        ...
    ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
