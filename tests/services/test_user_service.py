import pytest
from uuid import UUID
from sqlalchemy.orm import Session

from core.services.user import UserService
from core.db.models.user import User

@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

def test_create_user(user_service):
    user = user_service.create_user(
        username="testuser",
        email="test@example.com",
        password_hash="hashedpassword123",
        name="Test User"
    )
    
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert isinstance(user.user_id, UUID)

def test_get_user(user_service):
    # Create a user
    user = user_service.create_user(
        username="getuser",
        email="get@example.com",
        password_hash="hashedpassword"
    )
    
    # Get the user by ID
    retrieved_user = user_service.get(user.user_id)
    assert retrieved_user is not None
    assert retrieved_user.username == "getuser"

def test_get_by_username(user_service):
    # Create a user
    user_service.create_user(
        username="uniqueuser",
        email="unique@example.com",
        password_hash="hashedpassword"
    )
    
    # Get the user by username
    user = user_service.get_by_username("uniqueuser")
    assert user is not None
    assert user.email == "unique@example.com"

def test_update_user(user_service):
    # Create a user
    user = user_service.create_user(
        username="updateuser",
        email="update@example.com",
        password_hash="hashedpassword"
    )
    
    # Update the user
    updated_user = user_service.update(
        id=user.user_id,
        obj_in={"name": "Updated Name"}
    )
    
    assert updated_user.name == "Updated Name"

def test_delete_user(user_service):
    # Create a user
    user = user_service.create_user(
        username="deleteuser",
        email="delete@example.com",
        password_hash="hashedpassword"
    )
    
    # Delete the user
    result = user_service.delete(id=user.user_id)
    assert result is True
    
    # Try to get the deleted user
    deleted_user = user_service.get(user.user_id)
    assert deleted_user is None
