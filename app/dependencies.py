"""
Dependency injection functions for FastAPI.
"""
import os
import uuid
from typing import Optional
from types import SimpleNamespace
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import ValidationError

# Fix these imports to match the correct project structure
from dotenv import load_dotenv
from core.db.session import get_db
from core.db.models.user import User  # Changed from app.models.user

# Load environment variables
load_dotenv()

# Get configuration values from environment
SECRET_KEY = os.getenv("SECRET_KEY", "2060e3d0c7387262f35c869fc526c0b9b04a9375e1ace6c15f63d175062c183c")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
API_V1_STR = "/api/v1"

# OAuth2 scheme for JWT tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_STR}/auth/login")

def get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Get API key from header"""
    return x_api_key

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )
        
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
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Get user from database
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

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user

def validate_api_key(api_key: str = Depends(get_api_key)) -> bool:
    """Validate API key"""
    expected_api_key = os.getenv("BOT_API_KEY")
    if not expected_api_key:
        return False
    return api_key == expected_api_key

def get_current_user_or_api_key(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(get_api_key),
):
    """
    Get current user or validate API key.
    Allow either JWT token or API key authentication.
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
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        return get_current_user(db=db, token=token)
    except HTTPException:
        # If both fail, raise authentication error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )