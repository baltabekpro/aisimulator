from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from uuid import UUID, uuid4
import jwt
import requests
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.jwt import create_tokens, verify_token, get_current_user
from app.schemas.auth import AppleAuthRequest, TokenResponse, UserResponse
from core.services.user import UserService
from core.db.models.user import User
from core.db.models.user_profile import UserProfile
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Константы для Apple авторизации
APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

def get_apple_public_keys():
    """Получить публичные ключи Apple для проверки токена"""
    try:
        response = requests.get(APPLE_PUBLIC_KEY_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения ключей Apple: {e}")
        return None

def verify_apple_token(identity_token: str) -> Dict[str, Any]:
    """Проверить токен идентификации Apple и вернуть его утверждения"""
    try:
        # Получение публичных ключей Apple
        keys_data = get_apple_public_keys()
        if not keys_data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                               detail="Не удалось получить ключи авторизации Apple")
        
        # Декодирование заголовка токена для получения kid (key id)
        header = jwt.get_unverified_header(identity_token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                               detail="Неверный формат токена Apple")
        
        # Поиск соответствующего ключа
        key_data = None
        for key in keys_data.get("keys", []):
            if key.get("kid") == kid:
                key_data = key
                break
        
        if not key_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                               detail="Не найден ключ для проверки токена Apple")
        
        # Создание публичного ключа из данных JWKS
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))
        
        # Проверка токена
        payload = jwt.decode(
            identity_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.APPLE_CLIENT_ID,
            issuer=APPLE_ISSUER,
            options={
                "verify_exp": True,  # Проверка срока действия
                "verify_aud": settings.APPLE_CLIENT_ID is not None,  # Проверка аудитории только если ID клиента задан
                "verify_iss": True,  # Проверка издателя
            }
        )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                           detail="Срок действия токена Apple истек")
    except jwt.InvalidTokenError as e:
        logger.error(f"Ошибка проверки токена Apple: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                           detail="Недействительный токен Apple")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при проверке токена Apple: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                           detail="Ошибка проверки токена Apple")

@router.post("/apple/auth", response_model=TokenResponse)
def apple_auth(
    request: AppleAuthRequest, db: Session = Depends(get_db)
) -> Any:
    """
    Авторизация через Apple OAuth
    """
    # Верификация токена Apple в prod-окружении
    if not settings.debug:  # В production окружении всегда проверяем токен
        apple_data = verify_apple_token(request.identity_token)
        
        # Валидация, что email в запросе соответствует email из токена Apple
        apple_email = apple_data.get("email")
        if apple_email and apple_email != request.email:
            logger.warning(f"Email в запросе ({request.email}) не совпадает с email в токене Apple ({apple_email})")
            request.email = apple_email  # Используем email из токена для безопасности
            
        # Получение дополнительных данных из токена
        apple_user_id = apple_data.get("sub")  # sub в токене Apple - это уникальный ID пользователя
        if apple_user_id:
            request.apple_user_id = apple_user_id
    
    # Создание уникального external_id на основе apple_user_id, если доступен
    external_id = f"apple_{request.apple_user_id}" if request.apple_user_id else f"apple_{request.email}"
    
    user_service = UserService(db)
    
    # Поиск пользователя сначала по external_id, затем по email
    user = user_service.get_by_external_id(external_id)
    
    if not user:
        user = user_service.get_by_email(request.email)
    
    if not user:
        # Создаем нового пользователя
        username = request.email.split("@")[0]
        
        # Проверяем уникальность username
        if user_service.get_by_username(username):
            # Если username занят, добавляем случайный суффикс
            username = f"{username}_{uuid4().hex[:6]}"
        
        user = user_service.create_user(
            username=username,
            email=request.email,
            password_hash="",  # Для OAuth пользователей не задаем пароль
            name=request.name or (f"{request.given_name} {request.family_name}" if request.given_name else None),
            external_id=external_id,
            is_active=True
        )
        
        # Создаем профиль пользователя
        try:
            profile = UserProfile(
                user_id=user.user_id,
                name=request.name or (f"{request.given_name} {request.family_name}" if request.given_name else None),
                interests=[]
            )
            db.add(profile)
            db.commit()
        except Exception as e:
            logger.error(f"Ошибка создания профиля пользователя: {e}")
            # Не возвращаем ошибку, если не удалось создать профиль - создадим его позже
            db.rollback()
    else:
        # Обновляем информацию о существующем пользователе, если нужно
        if request.name and not user.name:
            user.name = request.name
            db.commit()
    
    # Создаем токены
    tokens = create_tokens(str(user.user_id))
    
    return tokens

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
        subject=str(user.user_id),
        is_admin=user.is_admin,
        debug=settings.debug
    )
    
    return {
        **tokens,
        "user_id": str(user.user_id),
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
        "id": str(current_user.user_id),
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
