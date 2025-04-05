# Import all models for convenient access
try:
    from core.db.models.user import User
    from core.db.models.message import Message
    from core.db.models.character import Character
    from core.db.models.chat_history import ChatHistory
    from core.db.models.memory_entry import MemoryEntry
except ImportError as e:
    import logging
    logging.warning(f"Could not import some models: {e}")
