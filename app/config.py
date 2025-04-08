import os
from typing import List, Optional

# Try to import from pydantic_settings, fallback to compatibility module
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Try to use our compatibility module
    try:
        from app.compat.pydantic_settings import BaseSettings
    except ImportError:
        # Last resort - use Pydantic directly
        from pydantic import BaseSettings


class Settings(BaseSettings):
    """API configuration settings loaded from environment variables."""
    
    # API settings
    PROJECT_NAME: str = "AI Simulator API"
    API_V1_PREFIX: str = "/api/v1"
    API_BASE_URL: str = "http://api:8000/api/v1"
    API_KEY: str = "secure_bot_api_key_12345"
    API_USER: str = "admin"
    API_PASSWORD: str = "admin_password"
    
    # Security settings
    SECRET_KEY: str = "2060e3d0c7387262f35c869fc526c0b9b04a9375e1ace6c15f63d175062c183c"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BOT_API_KEY: str = "secure_bot_api_key_12345"
    
    # Admin settings
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin_password"
    
    # Database settings
    DATABASE_URL: str = "postgresql://aibot:postgres@postgres:5432/aibot"
    DB_TYPE: str = "postgresql"
    SQL_ECHO: bool = False
    
    # OpenRouter settings
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "openai/gpt-4o-2024-11-20"
    OPENROUTER_WORKING: bool = False
    
    # Telegram Bot settings
    TELEGRAM_TOKEN: str = ""
    
    # Environment settings
    ENVIRONMENT: str = "development"
    debug: bool = True  # Changed DEBUG to debug to match usage
    AUTO_ACTIVATE_USERS: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # Make settings case-insensitive
        extra = "allow"


# Create global settings instance
settings = Settings()

# In debug mode, print the settings
if settings.debug:  # This should now work with case-insensitive config
    print(f"API settings: {settings}")
