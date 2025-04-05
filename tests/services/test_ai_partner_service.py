import pytest
from uuid import UUID
from sqlalchemy.orm import Session

from core.services.ai_partner import AIPartnerService
from core.services.user import UserService
from core.db.models.ai_partner import AIPartner

@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

@pytest.fixture
def partner_service(db_session):
    return AIPartnerService(db_session)

@pytest.fixture
def test_user(user_service):
    return user_service.create_user(
        username="partnerowner",
        email="owner@example.com",
        password_hash="hashedpassword456",
        name="Partner Owner"
    )

def test_create_partner(partner_service, test_user):
    partner = partner_service.create_partner(
        user_id=test_user.user_id,
        name="AI Helper",
        age=25,
        biography="I'm an AI assistant designed to help with various tasks.",
        personality={"friendly": 8, "helpful": 9}
    )
    
    assert partner.name == "AI Helper"
    assert partner.age == 25
    assert partner.biography == "I'm an AI assistant designed to help with various tasks."
    assert partner.personality == {"friendly": 8, "helpful": 9}
    assert isinstance(partner.partner_id, UUID)

def test_get_partner(partner_service, test_user):
    # Create an AI partner
    partner = partner_service.create_partner(
        user_id=test_user.user_id,
        name="Get Partner",
        age=30,
        biography="Partner for testing get functionality"
    )
    
    # Get the partner by ID
    retrieved_partner = partner_service.get(partner.partner_id)
    assert retrieved_partner is not None
    assert retrieved_partner.name == "Get Partner"

def test_get_by_user_id(partner_service, test_user):
    # Create multiple AI partners for the same user
    partner_service.create_partner(
        user_id=test_user.user_id,
        name="Partner 1",
        age=20,
        biography="First partner"
    )
    
    partner_service.create_partner(
        user_id=test_user.user_id,
        name="Partner 2",
        age=25,
        biography="Second partner"
    )
    
    # Get all partners for the user
    partners = partner_service.get_by_user_id(test_user.user_id)
    assert len(partners) == 2
    assert {p.name for p in partners} == {"Partner 1", "Partner 2"}

def test_update_partner(partner_service, test_user):
    # Create an AI partner
    partner = partner_service.create_partner(
        user_id=test_user.user_id,
        name="Update Partner",
        age=22,
        biography="Partner for testing update functionality"
    )
    
    # Update the partner
    updated_partner = partner_service.update(
        id=partner.partner_id,
        obj_in={"age": 23, "biography": "Updated biography"}
    )
    
    assert updated_partner.age == 23
    assert updated_partner.biography == "Updated biography"

def test_delete_partner(partner_service, test_user):
    # Create an AI partner
    partner = partner_service.create_partner(
        user_id=test_user.user_id,
        name="Delete Partner",
        age=28,
        biography="Partner for testing delete functionality"
    )
    
    # Delete the partner
    result = partner_service.delete(id=partner.partner_id)
    assert result is True
    
    # Try to get the deleted partner
    deleted_partner = partner_service.get(partner.partner_id)
    assert deleted_partner is None
