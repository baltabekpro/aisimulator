from sqlalchemy.ext.declarative import declarative_base

# Create Base class for models
Base = declarative_base()

# Note: Models are imported in other modules when needed
# The imports are commented out here to avoid circular imports
# These were causing "Import could not be resolved" errors
#
# from core.db.models.user import User
# from core.db.models.message import Message
# from core.db.models.character import Character
# from core.db.models.chat_history import ChatHistory
# from core.db.models.memory_entry import MemoryEntry
