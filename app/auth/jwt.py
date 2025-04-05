import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID
import logging
from core.db.session import get_db
from core.db.models import User
from core.config import settings

# Set up logger
logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

# Token payload model
class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

def create_access_token(
    subject: str, expires_delta: Optional[timedelta] = None, is_admin: bool = False, debug: bool = False
) -> str:
    """
    Create a new JWT access token.
    
    Args:
        subject: Subject (typically user ID)
        expires_delta: Optional custom expiration time
        is_admin: Whether the user is an admin
        debug: Whether debug mode is enabled
    
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Create payload with expiration time
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "is_admin": is_admin,
        "debug": debug
    }
    
    # Encode the JWT with the settings.SECRET_KEY and settings.ALGORITHM
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    subject: str, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT refresh token with longer expiration.
    
    Args:
        subject: Subject (typically user ID)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Create payload with expiration time
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "token_type": "refresh"
    }
    
    # Encode the JWT with the settings.SECRET_KEY and settings.ALGORITHM
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_tokens(
    subject: str, 
    is_admin: bool = False, 
    debug: bool = False
) -> Dict[str, str]:
    """
    Create both access and refresh tokens.
    
    Args:
        subject: Subject (typically user ID)
        is_admin: Whether the user is an admin
        debug: Whether debug mode is enabled
    
    Returns:
        Dictionary with access and refresh tokens
    """
    # Create access token with standard expiration
    access_token = create_access_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        is_admin=is_admin,
        debug=debug
    )
    
    # Create refresh token with longer expiration
    refresh_token = create_refresh_token(
        subject=subject,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def verify_token(token: str) -> str:
    """
    Verify a JWT token and return the user ID.
    
    Args:
        token: JWT token to verify
    
    Returns:
        User ID from token
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode JWT token using the settings.SECRET_KEY and settings.ALGORITHM
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Return the user ID from the token
        return user_id
    
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Function to get current user (required auth)
async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get the current authenticated user.
    
    Args:
        db: Database session
        token: JWT token
    
    Returns:
        User model instance
    
    Raises:
        HTTPException: If user is not authenticated
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = verify_token(token)
    
    try:
        # Convert string user_id to UUID before querying
        uuid_user_id = UUID(user_id)
        # Get user from database using UUID instead of string
        user = db.query(User).filter(User.user_id == uuid_user_id).first()
    except ValueError:
        # If user_id is not a valid UUID
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# Function to get current user (optional auth)
async def get_current_user_optional(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.
    
    Args:
        db: Database session
        token: JWT token
    
    Returns:
        User model instance or None
    """
    if not token:
        return None
    
    try:
        user_id = verify_token(token)
        try:
            # Convert string user_id to UUID before querying
            uuid_user_id = UUID(user_id)
            # Get user from database using UUID instead of string
            user = db.query(User).filter(User.user_id == uuid_user_id).first()
            return user
        except ValueError:
            # If user_id is not a valid UUID
            logger.warning(f"Invalid UUID format for user_id: {user_id}")
            return None
    except HTTPException:
        return None
