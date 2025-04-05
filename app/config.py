import os
from pydantic_settings import BaseSettings
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Project information
    PROJECT_NAME: str = "AI Character Simulator"
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    # Debug mode
    debug: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key_do_not_use_in_production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # OpenRouter API
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")
    OPENROUTER_WORKING: bool = False  # Will be set at runtime after API check
    
    # Telegram bot
    TELEGRAM_TOKEN: Optional[str] = os.getenv("TELEGRAM_TOKEN")
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Allow extra fields to avoid future validation errors
        extra = 'ignore'

# Create the settings instance
settings = Settings()
