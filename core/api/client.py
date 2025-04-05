import os
import requests
import logging

logger = logging.getLogger(__name__)

class ApiClient:
    """Client for interacting with the AI Bot API"""
    
    def __init__(self, base_url=None, api_key=None):
        """
        Initialize API client with base URL and credentials
        
        Args:
            base_url: Base URL for API
            api_key: API key for authentication
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
        self.api_key = api_key or os.getenv("BOT_API_KEY")
        
        if not self.api_key:
            logger.warning("API key not provided, authentication may fail")
            
        # Default headers
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_character_memories(self, character_id, user_id=None, include_all=False):
        """
        Get memories for a specific character and user
        
        Args:
            character_id: ID of the character
            user_id: Optional ID of the user or tuple of (uuid, telegram_id)
            include_all: Whether to include all memories regardless of user ID
            
        Returns:
            list: List of memories
        """
        # Extract telegram_id from user_id if it's a tuple
        telegram_id = None
        if isinstance(user_id, tuple) and len(user_id) == 2:
            user_id, telegram_id = user_id
        
        # Normalize UUID format 
        normalized_uuid = None
        if user_id and isinstance(user_id, str) and '-' in user_id:
            # Keep original UUID format for initial attempt
            normalized_uuid = user_id
        
        # Build the URL
        url = f"{self.base_url}/chat/characters/{character_id}/memories"
        
        # Add parameters based on what we have
        params = {}
        if include_all:
            params["include_all"] = "true"
        elif normalized_uuid:
            params["user_id"] = normalized_uuid
        elif user_id:
            params["user_id"] = str(user_id)
            
        # Construct URL with parameters
        if params:
            param_strings = [f"{k}={v}" for k, v in params.items()]
            url += f"?{'&'.join(param_strings)}"
        
        memories = []
        
        try:
            # Make sure we have authorization headers
            headers = {
                "X-API-Key": self.api_key,
                "Authorization": f"Bearer {self.api_key}"
            }
            
            logging.debug(f"Fetching memories from {url} with headers: {headers}")
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                memories = data.get("memories", [])
                logging.info(f"Retrieved {len(memories)} memories for character {character_id}" + 
                             (f" with user {user_id}" if user_id else " (all users)"))
                
            # If no memories found, try direct telegram_id query
            if not memories and telegram_id:
                alt_url = f"{self.base_url}/chat/characters/{character_id}/memories?telegram_id={telegram_id}"
                logging.debug(f"Trying alternative URL with telegram_id: {alt_url}")
                
                alt_response = self.session.get(alt_url, headers=headers, timeout=10)
                if alt_response.status_code == 200:
                    alt_data = alt_response.json()
                    alt_memories = alt_data.get("memories", [])
                    if len(alt_memories) > 0:
                        logging.info(f"Found {len(alt_memories)} memories using telegram_id={telegram_id}")
                        memories = alt_memories
                        
            # If still no memories found and we have both uuid formats, try the other format
            if not memories and user_id and isinstance(user_id, str) and '-' in user_id:
                # Try a different UUID format
                alt_uuid = None
                
                # If UUID follows the format with telegram ID embedded at the end
                if "c7cb5b5c-e469-586e-8e87-" in user_id:
                    # Check which format is being used
                    if user_id.startswith("c7cb5b5c-e469-586e-8e87-00"):
                        # We're using format with leading zeros, try without them
                        telegram_part = user_id.split("-")[-1].lstrip("0")
                        if telegram_part:
                            alt_uuid = f"c7cb5b5c-e469-586e-8e87-{int(telegram_part):x}"
                    else:
                        # We're using hex format, try with leading zeros
                        telegram_part = user_id.split("-")[-1]
                        try:
                            # Convert hex to int and format with leading zeros
                            tg_id_int = int(telegram_part, 16)
                            alt_uuid = f"c7cb5b5c-e469-586e-8e87-{tg_id_int:012d}"
                        except ValueError:
                            pass
                
                if alt_uuid:
                    alt_url = f"{self.base_url}/chat/characters/{character_id}/memories?user_id={alt_uuid}"
                    logging.debug(f"Trying alternative UUID format: {alt_url}")
                    
                    alt_response = self.session.get(alt_url, headers=headers, timeout=10)
                    if alt_response.status_code == 200:
                        alt_data = alt_response.json()
                        alt_memories = alt_data.get("memories", [])
                        if len(alt_memories) > 0:
                            logging.info(f"Found {len(alt_memories)} memories using alt UUID {alt_uuid}")
                            memories = alt_memories
            
            return memories
        except Exception as e:
            logging.error(f"Error getting memories: {e}")
            return []