"""
Universal ID utility module for handling user identifiers across different platforms.

This module provides utility functions to convert different types of identifiers
(telegram IDs, API user IDs, UUIDs, etc.) to a consistent UUID format, making the
system platform-agnostic rather than just Telegram-specific.
"""
import uuid
import logging
import hashlib
from enum import Enum
from typing import Union, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Define a namespace UUID for consistent conversion of numeric IDs
# This ensures deterministic generation of UUIDs from the same numeric ID
NAMESPACE_USER_ID = uuid.UUID('c7e7f1d0-5a5d-5a5e-a2b0-914b8c42a3d7')

# Standard prefix for Telegram IDs (matches existing code)
TELEGRAM_PREFIX = "c7cb5b5c-e469-586e-8e87"

class Platform(Enum):
    """Enum for supported platforms"""
    UNKNOWN = "unknown"
    TELEGRAM = "telegram" 
    WEBSITE = "website"
    MOBILE_APP = "mobile_app"
    API = "api"

def ensure_uuid(value: Union[str, uuid.UUID, int, None]) -> str:
    """
    Ensure a value is a valid UUID string.
    Converts different formats to a standard string UUID.
    
    Args:
        value: Input value that could be a UUID, string, or numeric ID
        
    Returns:
        A string representation of a valid UUID
    """
    if value is None:
        return str(uuid.uuid4())
        
    if isinstance(value, uuid.UUID):
        return str(value)
    
    if isinstance(value, int):
        # For numeric IDs like Telegram user IDs, create a deterministic UUID
        # This matches the format used throughout the application
        return f"{TELEGRAM_PREFIX}-{value:012d}"
    
    if isinstance(value, str):
        try:
            # Test if it's already a valid UUID
            uuid_obj = uuid.UUID(value)
            return str(uuid_obj)
        except ValueError:
            try:
                # Try to interpret as an integer (like a Telegram ID)
                int_val = int(value)
                return ensure_uuid(int_val)
            except ValueError:
                # For non-integer strings, use UUID5 with namespace for deterministic generation
                return str(uuid.uuid5(NAMESPACE_USER_ID, value))
    
    # For any other types, generate a completely new UUID
    logger.warning(f"Unrecognized ID type: {type(value)}, generating new UUID")
    return str(uuid.uuid4())

def is_valid_uuid(value: Any) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        value: Value to check
        
    Returns:
        True if value is a valid UUID, False otherwise
    """
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False

def get_user_id_formats(user_id: Union[int, str]) -> Tuple[str, str, str]:
    """
    Generate multiple UUID formats for a user ID.
    This allows trying different formats when querying the database.
    
    Args:
        user_id: User ID (typically a Telegram ID)
        
    Returns:
        Tuple of (hex format UUID, decimal format UUID, raw ID)
    """
    try:
        # Convert to integer if it's a string
        if isinstance(user_id, str) and user_id.isdigit():
            user_id_int = int(user_id)
        else:
            user_id_int = int(user_id)
        
        # Format 1: Hexadecimal format
        user_uuid_hex = f"{TELEGRAM_PREFIX}-{user_id_int:x}".replace(" ", "0")
        
        # Format 2: Decimal format with leading zeros
        user_uuid_decimal = f"{TELEGRAM_PREFIX}-{user_id_int:012d}"
        
        # Format 3: Raw ID (for direct parameter usage)
        user_uuid_raw = str(user_id_int)
        
        return (user_uuid_hex, user_uuid_decimal, user_uuid_raw)
    except (ValueError, TypeError):
        # For non-numeric IDs, use a hash-based approach
        if isinstance(user_id, str):
            hash_obj = hashlib.md5(user_id.encode())
        else:
            hash_obj = hashlib.md5(str(user_id).encode())
            
        hex_dig = hash_obj.hexdigest()
        uuid_str = f"{TELEGRAM_PREFIX}-{hex_dig[-12:]}"
        
        # Return the same UUID in all three formats
        return (uuid_str, uuid_str, str(user_id))

def get_platform_user_id(value: Union[str, int, uuid.UUID], platform: Platform = Platform.UNKNOWN) -> str:
    """
    Convert a platform-specific ID to our universal UUID format.
    
    Args:
        value: The platform-specific user ID
        platform: The platform type (default: UNKNOWN)
        
    Returns:
        UUID string in a deterministic format based on the platform and ID
    """
    if platform == Platform.TELEGRAM:
        # For Telegram, use our standard Telegram ID format
        try:
            telegram_id = int(value)
            return f"{TELEGRAM_PREFIX}-{telegram_id:012d}"
        except (ValueError, TypeError):
            # If it's not a valid integer, generate a UUID from string
            return ensure_uuid(value)
    
    elif platform == Platform.WEBSITE:
        # For website users, they should already have UUIDs
        if is_valid_uuid(value):
            return str(uuid.UUID(str(value)))
        else:
            # If not a valid UUID, create one deterministically
            return str(uuid.uuid5(NAMESPACE_USER_ID, f"web-{value}"))
            
    elif platform == Platform.MOBILE_APP:
        # Mobile app might use device IDs or user accounts
        if is_valid_uuid(value):
            return str(uuid.UUID(str(value)))
        else:
            # If not a UUID, create a deterministic one with a prefix
            return str(uuid.uuid5(NAMESPACE_USER_ID, f"mobile-{value}"))
            
    elif platform == Platform.API:
        # API users should have proper UUIDs
        if is_valid_uuid(value):
            return str(uuid.UUID(str(value)))
        else:
            return str(uuid.uuid5(NAMESPACE_USER_ID, f"api-{value}"))
    
    else:
        # For unknown platforms, use the general ensure_uuid method
        return ensure_uuid(value)

def extract_platform_from_id(user_id: Union[str, int, uuid.UUID]) -> Platform:
    """
    Try to determine which platform a user ID is from based on its format.
    
    Args:
        user_id: User ID to analyze
        
    Returns:
        Platform enum value
    """
    user_id_str = str(user_id)
    
    # Check if it follows our Telegram ID pattern
    if f"{TELEGRAM_PREFIX}-" in user_id_str:
        return Platform.TELEGRAM
    
    # Check if it's a plain number (likely Telegram)
    if isinstance(user_id, int) or user_id_str.isdigit():
        return Platform.TELEGRAM
    
    # Check if it's a valid UUID
    if is_valid_uuid(user_id):
        # We don't have a way to know for sure, assume API
        return Platform.API
    
    # Default for unknown formats
    return Platform.UNKNOWN