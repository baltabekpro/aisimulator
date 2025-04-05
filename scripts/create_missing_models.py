"""
Script to create missing model files in the database models directory.
This helps resolve issues with missing imports in the codebase.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_missing_models():
    """Create missing model files if they don't exist"""
    # Load environment variables
    load_dotenv()
    
    # Models directory
    models_dir = os.path.join("core", "db", "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # Define model templates
    model_templates = {
        "user.py": """from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.db.base import Base
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True)
    hashed_password = Column(String(200))
    name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<User {self.username}>"
""",
        "message.py": """from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.db.base import Base
import uuid

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, nullable=False)
    sender_type = Column(String, nullable=False)  # 'user' or 'character'
    recipient_id = Column(String, nullable=False)
    recipient_type = Column(String, nullable=False)  # 'user' or 'character'
    content = Column(Text, nullable=False)
    emotion = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    conversation_id = Column(String)
    is_read = Column(Boolean, default=False)
    is_gift = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Message {self.id}: {self.sender_type}({self.sender_id}) -> {self.recipient_type}({self.recipient_id})>"
""",
        "character.py": """from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.db.base import Base
import uuid

class Character(Base):
    __tablename__ = "characters"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    age = Column(Integer)
    gender = Column(String(20))
    personality = Column(Text)
    background = Column(Text)
    interests = Column(Text)
    appearance = Column(Text)
    system_prompt = Column(Text)
    greeting_message = Column(Text)
    avatar_url = Column(String(500))
    creator_id = Column(String)
    is_active = Column(Boolean, default=True)
    character_metadata = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<Character {self.name}>"
""",
        "chat_history.py": """from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.db.base import Base
import uuid

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    character_id = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<ChatHistory {self.id}: {self.user_id} -> {self.character_id}>"
""",
        "memory_entry.py": """from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.db.base import Base
import uuid

class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    character_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Integer, default=1)  # 1-10 scale
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<MemoryEntry {self.id}: {self.character_id} -> {self.user_id}>"
"""
    }
    
    # Check and create each model file
    for filename, content in model_templates.items():
        file_path = os.path.join(models_dir, filename)
        
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✅ Created missing model file: {file_path}")
        else:
            logger.info(f"Model file already exists: {file_path}")
    
    # Create an __init__.py file in the models directory
    init_path = os.path.join(models_dir, "__init__.py")
    init_content = """# Import all models for convenient access
try:
    from core.db.models.user import User
    from core.db.models.message import Message
    from core.db.models.character import Character
    from core.db.models.chat_history import ChatHistory
    from core.db.models.memory_entry import MemoryEntry
except ImportError as e:
    import logging
    logging.warning(f"Could not import some models: {e}")
"""
    
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(init_content)
    logger.info(f"✅ Created models __init__.py at {init_path}")
    
    logger.info("Missing model files created successfully!")
    return True

if __name__ == "__main__":
    create_missing_models()
