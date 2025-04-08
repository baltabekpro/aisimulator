"""
Compatibility module for pydantic_settings if the package isn't available.
This provides minimal implementation of BaseSettings that still works with older Pydantic versions.
"""
import os
import warnings
from typing import Any, Dict, List, Optional, Tuple, Type, Union

try:
    # Try to import from pydantic directly
    from pydantic import BaseModel, Field
    from pydantic.env_settings import BaseSettings as PydanticBaseSettings
    
    class BaseSettings(PydanticBaseSettings):
        """Compatibility wrapper for pydantic_settings.BaseSettings using old pydantic."""
        pass
    
except ImportError:
    # If that fails, create a stub implementation using pydantic
    from pydantic import BaseModel, Field
    
    class BaseSettings(BaseModel):
        """Minimal implementation of BaseSettings when pydantic_settings is not available."""
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            env_nested_delimiter = "__"
            
        def __init__(self, *args, **kwargs):
            # Load environment variables
            env_values = {}
            for key, field in self.__annotations__.items():
                env_key = key.upper()
                if env_key in os.environ:
                    env_values[key] = os.environ[env_key]
            
            # Override with any provided values
            for key, value in kwargs.items():
                env_values[key] = value
                
            super().__init__(**env_values)
            
            warnings.warn(
                "Using compatibility BaseSettings implementation. Consider installing pydantic-settings.",
                UserWarning
            )

# Export the symbols
__all__ = ["BaseSettings", "Field"]
