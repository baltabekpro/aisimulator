import pytest
from uuid import UUID

from core.services.user import UserService
from core.services.ai_partner import AIPartnerService
from core.services.love_rating import LoveRatingService

@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

@pytest.fixture
def partner_service(db_session):
    return AIPartnerService(db_session)

@pytest.fixture
def rating_service(db_session):
    return LoveRatingService(db_session)

@pytest.fixture
def test_user(user_service):
    return user_service.create_user(
        username="ratinguser",
        email="rating@example.com",
        password_hash="password123",
        name="Rating User"
    )

@pytest.fixture
def test_partner(partner_service, test_user):
    return partner_service.create_partner(
        user_id=test_user.user_id,
        name="Rating Partner",
        age=25,
        biography="Partner for rating tests"
    )

def test_create_rating(rating_service, test_user, test_partner):
    rating = rating_service.create_rating(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        score=75
    )
    
    assert rating.user_id == test_user.user_id
    assert rating.partner_id == test_partner.partner_id
    assert rating.score == 75
    assert isinstance(rating.rating_id, UUID)

def test_get_rating(rating_service, test_user, test_partner):
    # Create a rating
    rating = rating_service.create_rating(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        score=60
    )
    
    # Get the rating by ID
    retrieved_rating = rating_service.get(rating.rating_id)
    assert retrieved_rating is not None
    assert retrieved_rating.score == 60

def test_get_by_user_and_partner(rating_service, test_user, test_partner):
    # Create a rating
    rating_service.create_rating(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        score=65
    )
    
    # Get the rating by user and partner
    rating = rating_service.get_by_user_and_partner(
        test_user.user_id, 
        test_partner.partner_id
    )
    assert rating is not None
    assert rating.score == 65

def test_update_score(rating_service, test_user, test_partner):
    # Create a rating
    rating = rating_service.create_rating(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        score=50
    )
    
    # Update the rating score
    updated_rating = rating_service.update_score(
        rating_id=rating.rating_id,
        score=80
    )
    
    assert updated_rating.score == 80

def test_adjust_score(rating_service, test_user, test_partner):
    # Create a rating
    rating = rating_service.create_rating(
        user_id=test_user.user_id,
        partner_id=test_partner.partner_id,
        score=50
    )
    
    # Adjust the rating score by adding points
    adjusted_rating = rating_service.adjust_score(
        rating_id=rating.rating_id,
        adjustment=10
    )
    
    assert adjusted_rating.score == 60
    
    # Adjust the rating score by subtracting points
    adjusted_rating = rating_service.adjust_score(
        rating_id=rating.rating_id,
        adjustment=-20
    )
    
    assert adjusted_rating.score == 40
