import pytest
from uuid import UUID
import time

from core.services.user import UserService
from core.services.ai_partner import AIPartnerService
from core.services.message import MessageService

@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

@pytest.fixture
def partner_service(db_session):
    return AIPartnerService(db_session)

@pytest.fixture
def message_service(db_session):
    return MessageService(db_session)

@pytest.fixture
def test_user(user_service):
    return user_service.create_user(
        username="messageuser",
        email="message@example.com",
        password_hash="password123",
        name="Message User"
    )

@pytest.fixture
def test_partner(partner_service, test_user):
    return partner_service.create_partner(
        user_id=test_user.user_id,
        name="Message Partner",
        age=25,
        biography="Partner for message tests"
    )

def test_create_message(message_service, test_user, test_partner):
    message = message_service.create_message(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        content="Hello, how are you?",
        sender_type="user"
    )
    
    assert message.user_id == test_user.user_id
    assert message.partner_id == test_partner.partner_id
    assert message.content == "Hello, how are you?"
    assert message.sender_type == "user"
    assert isinstance(message.message_id, UUID)

def test_create_user_message(message_service, test_user, test_partner):
    message = message_service.create_user_message(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        content="This is a user message"
    )
    
    assert message.content == "This is a user message"
    assert message.sender_type == "user"

def test_create_bot_message(message_service, test_user, test_partner):
    message = message_service.create_bot_message(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        content="This is a bot message",
        emotion="happy"
    )
    
    assert message.content == "This is a bot message"
    assert message.sender_type == "bot"
    assert message.emotion == "happy"

def test_get_conversation(message_service, test_user, test_partner):
    # Create messages in sequence - the order is determined by message_id (UUID)
    # We'll store them and then verify by message_id later
    
    # First message
    first_msg = message_service.create_user_message(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        content="Message 1 from user"
    )
    
    # Second message
    second_msg = message_service.create_bot_message(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        content="Message 2 from bot",
        emotion="neutral"
    )
    
    # Third message
    third_msg = message_service.create_user_message(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        content="Message 3 from user"
    )
    
    # Get conversation
    messages = message_service.get_conversation(
        test_user.user_id,
        test_partner.partner_id
    )
    
    assert len(messages) == 3
    
    # Since we're now sorting by message_id in descending order,
    # verify that the most recently created message comes first
    assert messages[0].message_id == third_msg.message_id
    assert messages[1].message_id == second_msg.message_id  
    assert messages[2].message_id == first_msg.message_id
    
    # Also verify content to make test more readable
    assert messages[0].content == "Message 3 from user"
    assert messages[1].content == "Message 2 from bot"
    assert messages[2].content == "Message 1 from user"
