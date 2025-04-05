import pytest
from uuid import UUID

from core.services.user import UserService
from core.services.ai_partner import AIPartnerService
from core.services.event import EventService

@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

@pytest.fixture
def partner_service(db_session):
    return AIPartnerService(db_session)

@pytest.fixture
def event_service(db_session):
    return EventService(db_session)

@pytest.fixture
def test_user(user_service):
    return user_service.create_user(
        username="eventuser",
        email="event@example.com",
        password_hash="password123",
        name="Event User"
    )

@pytest.fixture
def test_partner(partner_service, test_user):
    return partner_service.create_partner(
        user_id=test_user.user_id,
        name="Event Partner",
        age=25,
        biography="Partner for event tests"
    )

def test_create_event(event_service, test_user, test_partner):
    event = event_service.create_event(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        event_type="daily",
        status="pending",
        schedule={"time": "18:00", "repeat": "daily"},
        details={"title": "Daily Chat", "description": "Regular conversation"}
    )
    
    assert event.user_id == test_user.user_id
    assert event.partner_id == test_partner.partner_id
    assert event.type == "daily"
    assert event.status == "pending"
    assert event.schedule == {"time": "18:00", "repeat": "daily"}
    assert event.details == {"title": "Daily Chat", "description": "Regular conversation"}
    assert isinstance(event.event_id, UUID)

def test_get_event(event_service, test_user, test_partner):
    # Create an event
    event = event_service.create_event(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        event_type="quest",
        status="active"
    )
    
    # Get the event by ID
    retrieved_event = event_service.get(event.event_id)
    assert retrieved_event is not None
    assert retrieved_event.type == "quest"
    assert retrieved_event.status == "active"

def test_get_by_user_id(event_service, test_user, test_partner):
    # Create multiple events for the same user
    event_service.create_event(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        event_type="daily",
        status="pending"
    )
    
    event_service.create_event(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        event_type="global",
        status="active"
    )
    
    # Get all events for the user
    events = event_service.get_by_user_id(test_user.user_id)
    assert len(events) == 2
    assert {e.type for e in events} == {"daily", "global"}

def test_get_by_type(event_service, test_user, test_partner):
    # Create multiple events of different types
    event_service.create_event(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        event_type="daily",
        status="pending"
    )
    
    event_service.create_event(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        event_type="daily",
        status="active"
    )
    
    event_service.create_event(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        event_type="quest",
        status="active"
    )
    
    # Get all events of a specific type
    daily_events = event_service.get_by_type("daily")
    assert len(daily_events) == 2
    
    quest_events = event_service.get_by_type("quest")
    assert len(quest_events) == 1

def test_update_status(event_service, test_user, test_partner):
    # Create an event
    event = event_service.create_event(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        event_type="daily",
        status="pending"
    )
    
    # Update the event status
    updated_event = event_service.update_status(
        event_id=event.event_id,
        status="completed"
    )
    
    assert updated_event.status == "completed"
