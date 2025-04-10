"""
API dependencies module.
Contains common dependencies for API endpoints, like authentication.
"""
import os
import uuid
from typing import Optional, Union
from datetime import datetime
from types import SimpleNamespace

import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.config import settings
from core.db.session import get_db
from core.db.models import User

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False  # Don't automatically raise errors for missing tokens
)

# Secret key from settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

def get_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")) -> Optional[str]:
    """Extract API key from header"""
    return api_key

def validate_api_key(api_key: str) -> bool:
    """Validate API key"""
    expected_api_key = settings.BOT_API_KEY
    if not expected_api_key:
        return False
    return api_key == expected_api_key

def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(get_api_key)
) -> Union[User, SimpleNamespace]:
    """
    Get current user from JWT token or API key.
    If neither is valid, raise HTTPException.
    """
    # Check if API key is provided and valid
    if api_key and validate_api_key(api_key):
        # Create a temporary User object for API access
        return SimpleNamespace(
            id=uuid.uuid4(),
            username="api_user",
            is_active=True,
            is_superuser=False
        )
    
    # If no valid API key, try JWT token authentication
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract user ID from token
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Check token expiration
        token_exp = payload.get("exp")
        if token_exp and datetime.fromtimestamp(token_exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Use a dummy user for development if needed
        if settings.debug and (token == "test_token" or user_id == "test_user_id"):
            return SimpleNamespace(
                id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                username="test_user",
                email="test@example.com",
                is_active=True,
                is_superuser=True
            )
            
        # Get user from database if not in development mode or using real token
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )
            
        return user
        
    except (jwt.exceptions.DecodeError, jwt.exceptions.InvalidTokenError, ValidationError) as e:
        # For development, return a test user if DEBUG mode is enabled
        if settings.debug:
            return SimpleNamespace(
                id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                username="test_user",
                email="test@example.com",
                is_active=True,
                is_superuser=True
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_active_user(current_user = Depends(get_current_user)):
    """
    Get current active user.
    This is just a wrapper around get_current_user that ensures the user is active.
    """
    if not getattr(current_user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_current_superuser(current_user = Depends(get_current_user)):
    """
    Get current superuser.
    This is just a wrapper around get_current_user that ensures the user is a superuser.
    """
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
