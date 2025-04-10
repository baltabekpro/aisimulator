import uuid
from typing import Union, Optional

def ensure_uuid(value: Union[str, uuid.UUID, int]) -> str:
    """
    Ensure a value is a valid UUID string.
    Converts different formats to a standard string UUID.
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    
    if isinstance(value, int):
        # For numeric IDs like Telegram user IDs, create a deterministic UUID
        # This matches the format used in the bot: c7cb5b5c-e469-586e-8e87-{telegram_id:012d}
        return f"c7cb5b5c-e469-586e-8e87-{value:012d}"
    
    if isinstance(value, str):
        try:
            # Test if it's a valid UUID
            uuid_obj = uuid.UUID(value)
            return str(uuid_obj)
        except ValueError:
            try:
                # Try to interpret as an integer
                int_val = int(value)
                return ensure_uuid(int_val)
            except ValueError:
                # Generate a new UUID if all else fails
                return str(uuid.uuid4())
    
    # Default fallback
    return str(uuid.uuid4())

def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID
    """
    try:
        uuid_obj = uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False

def get_user_uuid_for_telegram_id(telegram_id: int) -> str:
    """
    Generate a deterministic UUID for a Telegram user ID.
    This matches the format used in the bot code.
    """
    return f"c7cb5b5c-e469-586e-8e87-{telegram_id:012d}"
