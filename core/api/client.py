import os
import requests
import logging
import re

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
            self.headers["X-API-Key"] = self.api_key
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_character_memories(self, character_id, user_id=None, include_all=False):
        """
        Get memories for a specific character and user
        
        Args:
            character_id: ID of the character
            user_id: Optional ID of the user or tuple of IDs in different formats
            include_all: Whether to include all memories regardless of user ID
            
        Returns:
            list: List of memories
        """
        # Build the URL
        url = f"{self.base_url}/chat/characters/{character_id}/memories"
        
        # Make sure we have authorization headers (double-check since this has been an issue)
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}"
        }
        
        memories = []
        tried_urls = []
        
        # Prepare multiple user ID formats to try
        user_id_formats = []
        
        if include_all:
            # If include_all is True, we don't need any user_id parameters
            user_id_formats = [None]
        elif user_id is None:
            # If no user_id provided, just make a basic request
            user_id_formats = [None]
        else:
            # Handle both tuple format and single format
            if isinstance(user_id, tuple):
                # Add all items in the tuple
                user_id_formats.extend(list(user_id))
            else:
                # Add the single user_id
                user_id_formats.append(user_id)
            
            # Handle various UUID formats for Telegram IDs
            for uid in list(user_id_formats):  # Make a copy to safely modify
                if isinstance(uid, (int, str)):
                    # Convert to string
                    uid_str = str(uid)
                    
                    # Extract telegram ID from UUID format if possible
                    telegram_id = None
                    
                    # UUID format with embedded Telegram ID (decimal with leading zeros)
                    if re.match(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-00\d+$', uid_str):
                        telegram_id = uid_str.split('-')[-1].lstrip('0')
                        if telegram_id:
                            # Original format with leading zeros
                            if uid_str not in user_id_formats:
                                user_id_formats.append(uid_str)
                            
                            # Add raw numeric format
                            if telegram_id not in user_id_formats:
                                user_id_formats.append(telegram_id)
                            
                            # Add hex format without leading zeros (used by memory manager)
                            try:
                                hex_format = f"c7cb5b5c-e469-586e-8e87-{int(telegram_id):x}"
                                if hex_format not in user_id_formats:
                                    user_id_formats.append(hex_format)
                            except (ValueError, TypeError):
                                pass
                    
                    # UUID format with embedded Telegram ID (hex format)
                    elif re.match(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', uid_str):
                        hex_part = uid_str.split('-')[-1]
                        try:
                            # Convert hex to decimal
                            telegram_id = str(int(hex_part, 16))
                            
                            # Add decimal format with leading zeros
                            decimal_format = f"c7cb5b5c-e469-586e-8e87-{int(telegram_id):012d}"
                            if decimal_format not in user_id_formats:
                                user_id_formats.append(decimal_format)
                                
                            # Add raw numeric format
                            if telegram_id not in user_id_formats:
                                user_id_formats.append(telegram_id)
                        except (ValueError, TypeError):
                            pass
                    
                    # Plain numeric Telegram ID
                    elif uid_str.isdigit():
                        telegram_id = uid_str
                        
                        # Add UUID format with leading zeros
                        decimal_format = f"c7cb5b5c-e469-586e-8e87-{int(telegram_id):012d}"
                        if decimal_format not in user_id_formats:
                            user_id_formats.append(decimal_format)
                        
                        # Add hex format
                        try:
                            hex_format = f"c7cb5b5c-e469-586e-8e87-{int(telegram_id):x}"
                            if hex_format not in user_id_formats:
                                user_id_formats.append(hex_format)
                        except (ValueError, TypeError):
                            pass
        
        # Try all the user ID formats until we find memories
        for format_idx, uid_format in enumerate(user_id_formats):
            params = {}
            # Initialize param_name to support logging when include_all
            param_name = None
            
            # Add parameters based on format
            if include_all:
                param_name = "include_all"
                params["include_all"] = "true"
            elif uid_format is not None:
                # Decide whether to use user_id or telegram_id parameter
                param_name = "telegram_id" if isinstance(uid_format, int) or (isinstance(uid_format, str) and uid_format.isdigit()) else "user_id"
                params[param_name] = str(uid_format)
            
            # Construct URL with parameters
            request_url = url
            if params:
                param_strings = [f"{k}={v}" for k, v in params.items()]
                request_url += f"?{'&'.join(param_strings)}"
            
            # Skip if we already tried this exact URL
            if request_url in tried_urls:
                continue
                
            tried_urls.append(request_url)
            
            try:
                logger.debug(f"Trying to fetch memories with format {format_idx+1}/{len(user_id_formats)}: {request_url}")
                
                response = self.session.get(request_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    new_memories = data.get("memories", [])
                    
                    if new_memories and len(new_memories) > 0:
                        logger.info(f"Found {len(new_memories)} memories using {param_name}={uid_format}")
                        memories = new_memories
                        break  # Success! No need to try other formats
            except Exception as e:
                logger.error(f"Error with URL {request_url}: {e}")
                continue
        
        if not memories:
            logger.warning(f"No memories found for character {character_id} after trying {len(tried_urls)} different formats")
            # Fallback: fetch general memories without user filter
            if not include_all:
                logger.info("Falling back to fetch general memories (include_all=True)")
                return self.get_character_memories(character_id, None, include_all=True)
        return memories