import pytest
import uuid
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.db.base import Base
from core.db.models import User, AIPartner

# Use SQLite for testing (in-memory database)
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    """Create a clean in-memory database session for tests."""
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_create_user(db_session):
    """Test creating a user record."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashedpassword123",
        name="Test User",
        external_id="ext123"
    )
    db_session.add(user)
    db_session.commit()
    
    # Retrieve the user from the database
    db_user = db_session.query(User).filter_by(username="testuser").first()
    assert db_user is not None
    assert db_user.email == "test@example.com"
    assert db_user.name == "Test User"

def test_create_ai_partner(db_session):
    """Test creating an AI partner record."""
    # First create a user
    user = User(
        username="aiowner",
        email="owner@example.com",
        password_hash="hashedpassword456",
        name="Partner Owner"
    )
    db_session.add(user)
    db_session.commit()
    
    # Create AI partner for this user
    ai_partner = AIPartner(
        user_id=user.user_id,
        name="AI Helper",
        biography="I'm an AI assistant designed to help with various tasks.",
        age=25
    )
    db_session.add(ai_partner)
    db_session.commit()
    
    # Retrieve the AI partner from the database
    db_ai = db_session.query(AIPartner).filter_by(name="AI Helper").first()
    assert db_ai is not None
    assert db_ai.biography == "I'm an AI assistant designed to help with various tasks."
    assert db_ai.user_id == user.user_id
    assert db_ai.age == 25

# Add this code to run tests when file is executed directly
if __name__ == "__main__":
    print("Running tests...")
    # Run the create user test
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("Testing user creation...")
        test_create_user(session)
        print("User creation test passed!")
        
        print("Testing AI partner creation...")
        test_create_ai_partner(session)
        print("AI partner creation test passed!")
        
        print("All tests passed successfully!")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        session.close()
        Base.metadata.drop_all(engine)
