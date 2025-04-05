"""
Helper functions for memory-related operations.
"""
import uuid
from typing import Optional, Union

def convert_user_id_to_uuid(user_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
    """
    Convert a user ID string to UUID format.
    
    Args:
        user_id: String or UUID object representing a user ID
        
    Returns:
        UUID object if conversion is successful, None otherwise
    """
    if not user_id:
        return None
        
    if isinstance(user_id, uuid.UUID):
        return user_id
        
    try:
        return uuid.UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        return None

def parse_memory_data(memory_data: str) -> list:
    """
    Parse memory data from string JSON format to Python objects.
    
    Args:
        memory_data: JSON string of memory data
        
    Returns:
        List of memory items, empty list if parsing fails
    """
    import json
    
    if not memory_data:
        return []
        
    try:
        return json.loads(memory_data)
    except json.JSONDecodeError:
        return []
