"""
Core models package initialization.
This file imports and exposes all model classes for easy access.
"""

# Import from db.models to expose them in core.models namespace
from core.db.models.user import User
from core.db.models.ai_partner import AIPartner
from core.db.models.message import Message
from core.db.models.event import Event  # Make sure Event is imported
from core.db.models.gift import Gift
from core.db.models.love_rating import LoveRating
from core.db.models.chat_history import ChatHistory  # Add the new model

# Export all models for easy importing from core.models
__all__ = [
    "User", 
    "AIPartner", 
    "LoveRating", 
    "Event",
    "Message", 
    "Gift",
    "ChatHistory"  # Add to exports
]
