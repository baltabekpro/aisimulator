from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.auth.jwt import create_tokens, verify_token, get_current_user
from app.schemas.auth import AppleAuthRequest, TokenResponse, UserResponse
from core.services.user import UserService
from core.db.models.user import User
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/apple/auth", response_model=TokenResponse)
def apple_auth(
    request: AppleAuthRequest, db: Session = Depends(get_db)
) -> Any:
    """
    Авторизация через Apple OAuth
    """
    # Здесь должна быть валидация токена Apple и получение данных пользователя
    # В этом примере предположим, что токен валидный и у нас есть данные пользователя
    
    user_service = UserService(db)
    # Проверяем, существует ли пользователь с таким external_id
    user = user_service.get_by_email(request.email)
    
    if user is None:
        # Создаем нового пользователя
        user = user_service.create_user(
            username=request.email.split("@")[0],  # Используем часть email как username
            email=request.email,
            password_hash="",  # Для OAuth пользователей не нужен пароль
            name=request.name,
            external_id=f"apple_{request.email}"  # Используем email как внешний ID
        )
    
    # Создаем токены
    return create_tokens(str(user.user_id))

@router.post("/refresh")
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Refresh access token using a valid refresh token
    """
    try:
        # Verify the refresh token and get user_id
        user_id = verify_token(refresh_token)
        
        try:
            # Convert string user_id to UUID before querying
            uuid_user_id = UUID(user_id)
            # Get user from database using UUID
            user = db.query(User).filter(User.user_id == uuid_user_id).first()
        except ValueError:
            # If user_id is not a valid UUID
            logger.error(f"Invalid UUID format for user_id in refresh token: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user or inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new tokens
        tokens = create_tokens(
            subject=str(user.user_id),
            is_admin=user.is_admin,
            debug=settings.debug
        )
        
        return {
            **tokens,
            "user_id": str(user.user_id),
            "is_admin": user.is_admin
        }
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Try to find the user in the database
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Check if user exists and password is correct
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access and refresh tokens using user_id instead of id
    tokens = create_tokens(
        subject=str(user.user_id),
        is_admin=user.is_admin,
        debug=settings.debug
    )
    
    return {
        **tokens,
        "user_id": str(user.user_id),
        "is_admin": user.is_admin
    }

@router.post("/register")
async def register(
    email: str,
    password: str,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Register a new user
    """
    # Check if user with this email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create new user
    user = User(
        email=email,
        name=name or email.split("@")[0],
        is_admin=False
    )
    user.set_password(password)
    
    # Set as active based on settings
    user.is_active = getattr(settings, "AUTO_ACTIVATE_USERS", True)
    
    # Add to database
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create tokens for the new user
    tokens = create_tokens(
        subject=str(user.id),
        is_admin=user.is_admin,
        debug=settings.debug
    )
    
    return {
        **tokens,
        "user_id": str(user.id),
        "is_admin": user.is_admin
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user info
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active
    }

# Create a test token endpoint for development purposes
@router.get("/test-token", response_model=TokenResponse)
def get_test_token() -> Any:
    """
    Get a test token for development purposes.
    This endpoint should be disabled in production.
    """
    # Create a static test user ID
    test_user_id = "test_user_id"
    
    # Create tokens
    return create_tokens(test_user_id)

# Вспомогательная функция для проверки пароля
def verify_password(hashed_password: str, plain_password: str) -> bool:
    """
    Проверка пароля. В реальном проекте здесь был бы более сложный механизм.
    """
    # TODO: Implement proper password hashing (e.g., bcrypt)
    # Для примера используем простое сравнение
    return hashed_password == plain_password

# For now, include a simple endpoint so the router is usable
@router.get("/status")
def auth_status():
    return {"status": "Authentication service active"}
