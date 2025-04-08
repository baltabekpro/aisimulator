"""
Database connection utilities for admin panel.
Acts as a compatibility layer between routes and the db.session module.
"""
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Create engine based on DATABASE_URL
def get_engine():
    """Get SQLAlchemy engine using DATABASE_URL"""
    database_url = os.environ.get("DATABASE_URL", "postgresql://aibot:postgres@postgres:5432/aibot")
    logger.info(f"Creating database engine with URL: {database_url}")
    return create_engine(database_url)

# Create session factory
session_factory = sessionmaker(autocommit=False, autoflush=False)
Session = scoped_session(session_factory)

def init_db(app=None):
    """Initialize database connections"""
    engine = get_engine()
    session_factory.configure(bind=engine)
    logger.info("Database session initialized")
    return engine

def get_db():
    """Get a database session"""
    try:
        db = Session()
        return db
    except Exception as e:
        logger.error(f"Error getting database session: {e}")
        raise

@contextmanager
def db_session():
    """Context manager for database sessions"""
    session = get_db()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Error in database session: {e}")
        session.rollback()
        raise
    finally:
        session.close()