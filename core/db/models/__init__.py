# Import all models for convenient access
try:
    from core.db.models.user import User
    from core.db.models.message import Message
    from core.db.models.character import Character
    from core.db.models.chat_history import ChatHistory
    from core.db.models.memory_entry import MemoryEntry
    from core.db.models.ai_partner import AIPartner  # Add AIPartner import
    from core.db.models.user_profile import UserProfile  # Добавляем модель профиля пользователя
    from core.db.models.user_photo import UserPhoto  # Добавляем модель фотографий пользователя
except ImportError as e:
    import logging
    logging.warning(f"Could not import some models: {e}")
