"""
Utility for logging complete AI conversations to JSON files.
Captures raw, unfiltered conversation data including all JSON responses.
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs/conversations")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def log_conversation(
    character_id: str,
    user_message: str, 
    ai_response_raw: str,
    ai_response_processed: Dict[str, Any],
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Log a complete conversation exchange to a JSON file.
    
    Args:
        character_id: ID of the AI character
        user_message: The user's message text
        ai_response_raw: Raw response from the AI (unfiltered)
        ai_response_processed: Processed response (filtered for display)
        system_prompt: The system prompt used (if available)
        conversation_history: Previous conversation history (if available)
        
    Returns:
        Path to the created log file
    """
    try:
        # Create unique filename based on timestamp and character ID
        timestamp = int(time.time())
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{timestamp}_{character_id}.json"
        
        # Ensure character-specific directory exists
        char_dir = LOGS_DIR / character_id
        char_dir.mkdir(exist_ok=True)
        
        # Full path for the log file
        file_path = char_dir / filename
        
        # Prepare the log data
        log_data = {
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "character_id": character_id,
            "user_message": user_message,
            "ai_response": {
                "raw": ai_response_raw,
                "processed": ai_response_processed
            },
            "system_prompt": system_prompt,
            "conversation_history": conversation_history
        }
        
        # Write to JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Conversation logged to {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"Error logging conversation: {e}")
        return ""

def log_model_request(
    character_id: str,
    messages: List[Dict[str, Any]],
    response: str
) -> str:
    """
    Log the raw API request and response.
    
    Args:
        character_id: ID of the AI character
        messages: The messages sent to the API
        response: The raw response from the API
        
    Returns:
        Path to the created log file
    """
    try:
        # Create unique filename
        timestamp = int(time.time())
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{timestamp}_{character_id}_api.json"
        
        # Ensure directory exists
        api_dir = LOGS_DIR / character_id / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        
        # Full path
        file_path = api_dir / filename
        
        # Prepare log data
        log_data = {
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "character_id": character_id,
            "request": {
                "messages": messages
            },
            "response": response
        }
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
            
        return str(file_path)
    
    except Exception as e:
        logger.error(f"Error logging API request: {e}")
        return ""

def get_recent_conversations(character_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent conversation logs for a character.
    
    Args:
        character_id: ID of the AI character
        limit: Maximum number of logs to return
        
    Returns:
        List of conversation logs
    """
    try:
        char_dir = LOGS_DIR / character_id
        if not char_dir.exists():
            return []
            
        # Get all JSON files in the character directory
        files = list(char_dir.glob("*.json"))
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Load the files
        logs = []
        for file in files[:limit]:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    logs.append(json.load(f))
            except Exception as e:
                logger.error(f"Error reading log file {file}: {e}")
                
        return logs
        
    except Exception as e:
        logger.error(f"Error getting recent conversations: {e}")
        return []
