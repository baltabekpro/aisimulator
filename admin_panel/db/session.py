"""
Database session management for admin panel.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/aibot")

# Configure PostgreSQL engine with appropriate parameters
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Help detect and handle connection drops
    pool_size=5,         # Default connection pool size
    max_overflow=10,     # Allow 10 connections beyond pool_size
    pool_timeout=30,     # Seconds to wait before timeout
    pool_recycle=1800,   # Recycle connections after 30 minutes
    connect_args={'client_encoding': 'utf8'}  # Set client encoding for PostgreSQL
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

def get_engine():
    """Get SQLAlchemy engine"""
    return engine

def get_session():
    """Get a new database session"""
    return SessionLocal()
