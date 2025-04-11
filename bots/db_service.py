import os
import json
import logging
import aiohttp
import requests
from typing import Dict, List, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class ApiClient:
    """Client for interacting with the AI Simulator API"""
    
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or os.getenv("BOT_API_KEY", "secure_bot_api_key_12345")
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        self.session = None
        logger.info(f"Initialized API client with base URL: {self.base_url}")
        
    def _get_headers(self):
        """Get headers with authentication"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,  # Include both auth methods for compatibility
            "Content-Type": "application/json"
        }
        return headers
        
    def get_character_memories(self, 
                              character_id: str, 
                              user_id: Union[str, int, Tuple[str, ...]] = None, 
                              include_all: bool = True) -> List[Dict[str, Any]]:
        """
        Get memories for a character from the API
        
        Args:
            character_id: ID of the character
            user_id: Optional user ID - can be a string, integer or tuple of ID formats
            include_all: Whether to include all memories or just user-specific ones
            
        Returns:
            List of memory objects
        """
        try:
            memories_endpoint = f"{self.base_url}/chat/characters/{character_id}/memories"
            headers = self._get_headers()
            
            # Prepare parameters for the request
            params = {}
            
            # If user_id is a tuple, we'll try multiple formats
            if isinstance(user_id, tuple):
                # Try each format in sequence
                for uid_format in user_id:
                    attempt_params = {"telegram_id": str(uid_format)}
                    logger.debug(f"Trying memory retrieval with params: {attempt_params}")
                    
                    try:
                        response = requests.get(
                            memories_endpoint, 
                            headers=headers,
                            params=attempt_params,
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            memories = data.get("memories", [])
                            
                            if memories:  # If we got results, return them
                                logger.info(f"Found {len(memories)} memories with format: {uid_format}")
                                return memories
                            else:
                                logger.info(f"No memories found with format: {uid_format}")
                    except Exception as e:
                        logger.error(f"Error fetching memories with format {uid_format}: {e}")
                        continue
                
                # If we reach here, none of the formats worked - try one more time with both formats
                # Create a special parameter that includes multiple formats
                logger.info("Trying final attempt with combined formats")
                params = {
                    "telegram_id": str(user_id[0]),  # First format in telegram_id
                    "user_id": str(user_id[1] if len(user_id) > 1 else user_id[0])  # Second format in user_id
                }
            
            # If user_id is provided but not a tuple, use it as is
            elif user_id is not None:
                # Try with both parameter names for compatibility
                params = {
                    "telegram_id": str(user_id),
                    "user_id": str(user_id)
                }
                logger.debug(f"Using direct user ID: {user_id}")
            
            # Make the final request
            logger.debug(f"Making final memory request with params: {params}")
            response = requests.get(
                memories_endpoint, 
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                memories = data.get("memories", [])
                logger.info(f"Retrieved {len(memories)} memories for character {character_id}")
                return memories
            else:
                logger.error(f"Failed to get memories: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.exception(f"Error in get_character_memories: {e}")
            return []