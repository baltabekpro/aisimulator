import os
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Base settings
    PROJECT_NAME: str = "AI Character Simulator"
    API_V1_STR: str = "/api/v1"
    API_V1_PREFIX: str = "/api/v1"  # Alias for compatibility
    
    # API settings
    API_BASE_URL: Optional[str] = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
    API_KEY: Optional[str] = os.environ.get("API_KEY", "")
    
    # Database
    DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQL_ECHO: bool = False  # Add the missing setting
    
    # JWT settings
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "default_secret_key_do_not_use_in_production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    
    # Google API settings
    GOOGLE_API_KEY: Optional[str] = os.environ.get("GOOGLE_API_KEY", "")
    
    # OpenRouter API (replaces Gemini)
    OPENROUTER_API_KEY: Optional[str] = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-2024-11-20")
    OPENROUTER_WORKING: bool = False  # Track if the API key is valid and working
    
    # Image storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Telegram bot
    TELEGRAM_TOKEN: Optional[str] = os.environ.get("TELEGRAM_TOKEN")
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # Debug mode
    debug: bool = True
    
    # Bot
    BOT_API_KEY: str = os.getenv("BOT_API_KEY", "secure_bot_api_key_12345")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Настройки для Apple OAuth
    APPLE_CLIENT_ID: Optional[str] = os.environ.get("APPLE_CLIENT_ID")
    APPLE_REDIRECT_URI: Optional[str] = os.environ.get("APPLE_REDIRECT_URI")
    APPLE_KEY_ID: Optional[str] = os.environ.get("APPLE_KEY_ID")
    APPLE_TEAM_ID: Optional[str] = os.environ.get("APPLE_TEAM_ID")
    APPLE_BUNDLE_ID: Optional[str] = os.environ.get("APPLE_BUNDLE_ID", "com.yourapp.identifier")
    APPLE_AUTH_KEY_PATH: str = os.environ.get("APPLE_AUTH_KEY_PATH", "keys/AuthKey_Apple.p8")
    APPLE_USE_SANDBOX: bool = os.environ.get("APPLE_USE_SANDBOX", "True").lower() == "true"
    
    # URL базовый для сервиса
    BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")
    
    # Настройки хранилища файлов
    STORAGE_TYPE: str = os.environ.get("STORAGE_TYPE", "local")  # local, s3, minio
    S3_ENDPOINT: Optional[str] = os.environ.get("S3_ENDPOINT")
    S3_ACCESS_KEY: Optional[str] = os.environ.get("S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = os.environ.get("S3_SECRET_KEY")
    S3_BUCKET_NAME: str = os.environ.get("S3_BUCKET_NAME", "user-files")
    S3_REGION: Optional[str] = os.environ.get("S3_REGION")
    # Public URL for MinIO/S3 access, fallback to endpoint
    MINIO_PUBLIC_URL: Optional[str] = os.environ.get("MINIO_PUBLIC_URL")

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Allow extra inputs to avoid future errors from new environment variables
        extra = 'ignore'

    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: Optional[str]) -> str:
        if not v:
            return "sqlite:///app.db"
        return v

settings = Settings()
