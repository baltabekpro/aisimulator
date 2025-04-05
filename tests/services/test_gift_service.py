import pytest
from uuid import UUID

from core.services.user import UserService
from core.services.ai_partner import AIPartnerService
from core.services.gift import GiftService

@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

@pytest.fixture
def partner_service(db_session):
    return AIPartnerService(db_session)

@pytest.fixture
def gift_service(db_session):
    return GiftService(db_session)

@pytest.fixture
def test_user(user_service):
    return user_service.create_user(
        username="giftuser",
        email="gift@example.com",
        password_hash="password123",
        name="Gift User"
    )

@pytest.fixture
def test_partner(partner_service, test_user):
    return partner_service.create_partner(
        user_id=test_user.user_id,
        name="Gift Partner",
        age=25,
        biography="Partner for gift tests"
    )

def test_create_gift(gift_service, test_user, test_partner):
    gift = gift_service.create_gift(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        gift_type="цветы",
        impact=3
    )
    
    assert gift.user_id == test_user.user_id
    assert gift.partner_id == test_partner.partner_id
    assert gift.gift_type == "цветы"
    assert gift.impact == 3
    assert isinstance(gift.gift_id, UUID)

def test_get_gift(gift_service, test_user, test_partner):
    # Create a gift
    gift = gift_service.create_gift(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        gift_type="конфеты",
        impact=2
    )
    
    # Get the gift by ID
    retrieved_gift = gift_service.get(gift.gift_id)
    assert retrieved_gift is not None
    assert retrieved_gift.gift_type == "конфеты"
    assert retrieved_gift.impact == 2

def test_get_by_user_id(gift_service, test_user, test_partner):
    # Create multiple gifts from the same user
    gift_service.create_gift(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        gift_type="цветы",
        impact=3
    )
    
    gift_service.create_gift(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        gift_type="игрушка",
        impact=4
    )
    
    # Get all gifts from the user
    gifts = gift_service.get_by_user_id(test_user.user_id)
    assert len(gifts) == 2
    assert {g.gift_type for g in gifts} == {"цветы", "игрушка"}

def test_get_by_partner_id(gift_service, test_user, test_partner):
    # Create multiple gifts for the same partner
    gift_service.create_gift(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        gift_type="цветы",
        impact=3
    )
    
    gift_service.create_gift(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        gift_type="конфеты",
        impact=2
    )
    
    # Get all gifts for the partner
    gifts = gift_service.get_by_partner_id(test_partner.partner_id)
    assert len(gifts) == 2
    assert {g.gift_type for g in gifts} == {"цветы", "конфеты"}

def test_impact_constraint(gift_service, test_user, test_partner):
    # Test that impact is constrained to range -5 to 5
    gift_too_high = gift_service.create_gift(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        gift_type="цветы",
        impact=10  # Should be constrained to 5
    )
    assert gift_too_high.impact == 5
    
    gift_too_low = gift_service.create_gift(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        gift_type="конфеты",
        impact=-10  # Should be constrained to -5
    )
    assert gift_too_low.impact == -5
