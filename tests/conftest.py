import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to Python path for all tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db.base import Base

# Use SQLite for testing (in-memory database)
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_engine():
    """Create a SQLAlchemy engine for testing."""
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    """Create a clean in-memory database session for tests."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()
