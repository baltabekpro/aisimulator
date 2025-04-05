import os
import json
import logging
import random
import time
import datetime
import requests
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from core.config import settings
from dotenv import load_dotenv
from core.ai.conversation_manager import ConversationManager
from core.ai.memory_manager import MemoryManager
import re
import logging
from pathlib import Path
from core.utils.db_helpers import save_message_safely, ensure_string_id

# Make sure to load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Initialize with OpenRouter API key from multiple sources
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")

# Add extra debug logging
logger.info("Checking OpenRouter API key sources:")
if settings.OPENROUTER_API_KEY:
    masked_key = settings.OPENROUTER_API_KEY[:4] + "..." + settings.OPENROUTER_API_KEY[-4:] if len(settings.OPENROUTER_API_KEY) > 8 else "***masked***"
    logger.info(f"API key from settings: {masked_key}")
else:
    logger.info("No API key in settings")

env_key = os.environ.get("OPENROUTER_API_KEY", "")
if env_key:
    masked_key = env_key[:4] + "..." + env_key[-4:] if len(env_key) > 8 else "***masked***"
    logger.info(f"API key from environment: {masked_key}")
else:
    logger.info("No API key in environment variables")

# More detailed logging for API key detection
if OPENROUTER_API_KEY:
    masked_key = OPENROUTER_API_KEY[:4] + "..." + OPENROUTER_API_KEY[-4:] if len(OPENROUTER_API_KEY) > 8 else "***masked***"
    logger.info(f"Using OpenRouter API key: {masked_key}")
else:
    logger.error("ERROR: OPENROUTER_API_KEY not set or empty.")
    logger.error("Please follow these steps to set up your API key:")
    logger.error("1. Create a file named .env in your project root directory")
    logger.error("2. Add the line: OPENROUTER_API_KEY=your_api_key_here")
    logger.error("3. Replace 'your_api_key_here' with your actual OpenRouter API key")
    logger.error("4. Restart the application")
    logger.error("You can get an API key by signing up at https://openrouter.ai")

# Additional test to ensure the key is actually usable
if OPENROUTER_API_KEY:
    logger.info("Testing OpenRouter API key...")
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://aisimulator.app",
        }
        
        data = {
            "model": "anthropic/claude-3-haiku",  # Using a smaller model for testing
            "messages": [
                {"role": "user", "content": "Say hello briefly"}
            ]
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            response_json = response.json()
            content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"API key test successful! Response: {content[:50]}...")
        else:
            logger.error(f"API key test failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error testing API key: {e}")

class GeminiAI:
    """
    Class for working with OpenRouter API for message generation.
    The class name remains GeminiAI for compatibility with existing code.
    """
    
    def __init__(self, model_name: str = "openai/gpt-4o-2024-11-20"):
        """
        Initialize the class with model settings.
        
        Args:
            model_name: OpenRouter model name
        """
        # Default to GPT-4o model but can be configured
        self.model_name = settings.OPENROUTER_MODEL or model_name
        self.api_available = bool(OPENROUTER_API_KEY)
        # Track recent responses to avoid repetition
        self.recent_responses = []
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Add conversation manager
        self.conversation_manager = ConversationManager()
        
        # Add memory manager
        self.memory_manager = MemoryManager()
        
        # Log the model being used
        logger.info(f"Using OpenRouter model: {self.model_name}")
            
        if not self.api_available:
            logger.warning("OpenRouter AI initialized without API key, using fallback responses")
            return
            
        # Test the API connection
        try:
            # Test a simple generation to confirm API works
            test_prompt = "Say hello in Russian"
            test_response = self._send_api_request([{"role": "user", "content": test_prompt}])
            
            if test_response:
                logger.info(f"API test response: {test_response[:50]}...")
                self.api_available = True
            else:
                logger.error("API test generation failed with no response")
                self.api_available = False
                
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter: {e}")
            self.api_available = False
    
    def _send_api_request(self, messages: List[Dict[str, str]]) -> str:
        """
        Send a request to OpenRouter API with full conversation history.
        
        Args:
            messages: List of message objects with role and content
            
        Returns:
            Response text
        """
        if not OPENROUTER_API_KEY:
            logger.error("Cannot send API request: OPENROUTER_API_KEY is not set")
            logger.error("Please check your .env file and make sure OPENROUTER_API_KEY is properly set")
            return ""
            
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://aisimulator.app",  # Updated for better analytics
        }
        
        # Более подробное логирование отправляемых данных
        logger.info(f"Sending request to OpenRouter API for model: {self.model_name}")
        logger.info(f"Total messages in conversation: {len(messages)}")
        
        # Логируем краткую структуру разговора для отладки
        conversation_structure = []
        for i, msg in enumerate(messages):
            role = msg["role"]
            content_preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            conversation_structure.append(f"[{i}] {role}: {content_preview}")
        
        logger.info(f"Conversation structure:\n" + "\n".join(conversation_structure))
        
        # Проверяем, есть ли сообщения пользователя
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if not user_messages:
            logger.error("ERROR: No user messages found in the conversation!")
        else:
            logger.info(f"Found {len(user_messages)} user messages")
            # Логируем последнее сообщение пользователя полностью
            last_user_msg = user_messages[-1]
            logger.info(f"Last user message: {last_user_msg['content']}")
        
        # Remove metadata from messages before sending to API
        clean_messages = []
        for msg in messages:
            clean_msg = {"role": msg["role"], "content": msg["content"]}
            clean_messages.append(clean_msg)
        
        data = {
            "model": self.model_name,
            "messages": clean_messages
        }
        
        # Сохраняем полный запрос в лог-файл
        try:
            log_file = Path("logs/requests") / f"openrouter_request_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved full request to log file: {log_file}")
        except Exception as e:
            logger.error(f"Error saving request log: {e}")
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=60  # Increased timeout for longer responses
            )
            
            # Log the response status
            logger.info(f"OpenRouter API response status: {response.status_code}")
            
            if response.status_code == 200:
                response_json = response.json()
                content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Log the full response content, not just the first 50 characters
                logger.info(f"OpenRouter API response content: {content}")
                
                # Log the API request and response to a file if character_id is available
                try:
                    from core.utils.conversation_logger import log_model_request
                    # Extract character_id from the messages
                    character_id = None
                    for i, msg in enumerate(messages):
                        if msg["role"] == "system" and i < len(messages) - 1:
                            # Try to find character info in system messages
                            if "Имя:" in msg["content"]:
                                # Extract character ID from conversations dictionary
                                for char_id, conv in self.conversation_manager.conversations.items():
                                    if any(m["content"] == msg["content"] for m in conv if m["role"] == "system"):
                                        character_id = char_id
                                        break
                    
                    if character_id:
                        log_model_request(character_id, clean_messages, content)
                        logger.debug(f"Logged API request and response for character {character_id}")
                except Exception as logging_error:
                    logger.error(f"Failed to log API request: {logging_error}")
                
                return content
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return ""
        except Exception as e:
            logger.exception(f"Error in API request: {e}")
            return ""
    
    def generate_response(self, context: Dict[str, Any], message: str) -> Dict[str, Any]:
        """
        Generate a response to the user message using conversation history.
        
        Args:
            context: Dialog context dictionary
            message: User message text
            
        Returns:
            Dictionary with response (text, emotion, changes)
        """
        # Log the message for debugging
        logger.info(f"Generating response to message: '{message}'")
        
        # Special handling for gift context
        has_gift_context = False
        gift_info = None
        if "gift" in context:
            has_gift_context = True
            gift_info = context["gift"]
            logger.info(f"Gift context detected: {gift_info.get('name')}")
        
        # Skip memory extraction for UI commands
        special_commands = ["🧠 Память", "❤️ Отношения", "📱 Профиль", "💬 Меню", "❓ Помощь", "🎁 Отправить подарок"]
        is_ui_command = message in special_commands
        
        # Store user message in context for memory extraction
        context["user_message"] = message
        
        # Check key information in context
        character_info = context.get("character", {})
        character_id = str(character_info.get("id", "unknown"))
        logger.info(f"Character ID: {character_id}")
        
        # Add user ID from context to explicitly set when storing messages
        user_id = context.get("user_id")
        if user_id:
            logger.info(f"User ID from context: {user_id}")
        
        # Initialize database session for all database operations
        db_session = None
        try:
            from app.db.session import SessionLocal
            db_session = SessionLocal()
            logger.info(f"Created database session for generate_response")
        except Exception as e:
            logger.error(f"Failed to create database session: {e}")
        
        try:
            # Load existing memories from database
            try:
                if db_session and not is_ui_command:
                    loaded = self.memory_manager.load_from_database(db_session, character_id)
                    if loaded:
                        logger.info(f"✅ Loaded {len(self.memory_manager.get_all_memories(character_id))} memories from database")
                        # Log the first 3 memories for debugging
                        memories = self.memory_manager.get_all_memories(character_id)
                        for i, mem in enumerate(memories[:3]):
                            logger.info(f"  Memory[{i}]: {mem.get('content', '')}")
                    else:
                        logger.info(f"❓ No memories found in database for {character_id}")
            except Exception as db_error:
                logger.error(f"❌ Error loading memories from database: {db_error}")
            
            # Extract memories from user message - only for non-UI commands
            if not is_ui_command:
                potential_memories = self.memory_manager.extract_memories_from_message(message)
                if potential_memories:
                    # ANSI color codes for highlighted memory logging
                    MAGENTA = "\033[95m"
                    BOLD = "\033[1m"
                    RESET = "\033[0m"
                    
                    logger.info(f"{BOLD}{MAGENTA}🧠 MEMORY EXTRACTION: Found {len(potential_memories)} memories in message{RESET}")
                    
                    for memory in potential_memories:
                        self.memory_manager.add_memory(character_id, memory)
                    
                    # Immediately save to database
                    try:
                        if db_session:
                            saved = self.memory_manager.save_to_database(db_session, character_id)
                            if saved:
                                logger.info(f"{MAGENTA}💾 Memories successfully saved to database{RESET}")
                            else:
                                logger.warning(f"⚠️ Failed to save memories to database")
                    except Exception as db_error:
                        logger.error(f"❌ Error saving memories to database: {db_error}")
            
            # Check if we need to initialize the conversation
            if character_id not in self.conversation_manager.conversations:
                logger.info(f"🔄 Initializing new conversation for character {character_id}")
                
                # Get system prompt
                system_prompt = self._get_default_system_prompt()
                
                # Load memories and add them to the system prompt
                try:
                    if db_session:
                        # Make sure to load memories from database first
                        loaded = self.memory_manager.load_from_database(db_session, character_id)
                        if loaded:
                            memories = self.memory_manager.get_all_memories(character_id)
                            logger.info(f"📋 Including {len(memories)} memories in initial prompt for character {character_id}")
                            
                            # Format memories for inclusion in the prompt
                            memory_prompt = self.memory_manager.format_memories_for_prompt(character_id)
                            
                            # Append memories to system prompt
                            system_prompt += "\n\n" + memory_prompt
                        else:
                            logger.info(f"No memories found for character {character_id}")
                except Exception as mem_error:
                    logger.error(f"Error loading memories for initial prompt: {mem_error}")
                
                # Initialize conversation with character info
                if "history" in context and context["history"]:
                    # Import existing history
                    history_len = len(context["history"])
                    logger.info(f"📜 Importing existing history ({history_len} messages)")
                    self.conversation_manager.import_history(
                        character_id=character_id,
                        message_history=context["history"],
                        character_info=character_info,
                        system_prompt=system_prompt
                    )
                else:
                    # Start fresh conversation
                    logger.info(f"🆕 Creating new conversation without history")
                    self.conversation_manager.start_conversation(
                        character_id=character_id,
                        system_prompt=system_prompt,
                        character_info=character_info
                    )
                    
            # Load existing conversation from database if we have one
            elif db_session:
                try:
                    self.conversation_manager.load_conversation_from_database(character_id, db_session)
                except Exception as e:
                    logger.error(f"Error loading conversation from database: {e}")
            
            # For debugging, output current conversation state
            conversation_messages = self.conversation_manager.get_messages(character_id)
            message_types = {}
            for msg in conversation_messages:
                role = msg.get("role", "unknown")
                if role not in message_types:
                    message_types[role] = 0
                message_types[role] += 1
                
            logger.info(f"📊 Current conversation state: {json.dumps(message_types)}")
            
            # Add user message to conversation
            self.conversation_manager.add_message(
                character_id=character_id,
                role="user",
                content=message
            )
            logger.info(f"✉️ Added user message: '{message}'")
            
            # Store the user message in the database first
            if db_session and user_id and not is_ui_command:
                try:
                    from core.models import Message
                    from uuid import UUID
                    
                    # Convert IDs if needed - use try/except block for each ID conversion
                    try:
                        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
                    except ValueError:
                        logger.warning(f"Invalid user_id UUID format '{user_id}', generating new UUID")
                        user_uuid = uuid4()
                        
                    try:
                        char_uuid = UUID(character_id) if isinstance(character_id, str) else character_id
                    except ValueError:
                        logger.warning(f"Invalid character_id UUID format '{character_id}', generating new UUID")
                        char_uuid = uuid4()
                        
                    # Create and save user message
                    user_db_message = Message(
                        sender_id=user_uuid,
                        sender_type="user",
                        recipient_id=char_uuid,
                        recipient_type="character",
                        content=message,
                        emotion="neutral"
                    )
                    db_session.add(user_db_message)
                    db_session.commit()
                    logger.info(f"✅ User message saved to messages table in database")
                except Exception as msg_error:
                    logger.error(f"❌ Error saving user message to database: {msg_error}")
                    db_session.rollback()
                except Exception as ex:
                    logger.error(f"Error attempting to save user message to database: {ex}")
            
            # For UI commands, provide specialized responses without calling the API
            if is_ui_command:
                if message == "🧠 Память":
                    # Return a placeholder response - the actual memory will be handled by the API endpoint
                    return {
                        "text": "Retrieving memory information...",
                        "emotion": "neutral",
                        "relationship_changes": {"general": 0},
                        "memory": {"has_memory": False}
                    }
                # Handle other UI commands similarly...
            
            # Get all messages for the conversation
            conversation_messages = self.conversation_manager.get_messages(character_id)
            logger.info(f"📜 Total messages in history: {len(conversation_messages)}")
            
            # Add custom instructions for gift context
            if has_gift_context and gift_info:
                # Get or create the system messages
                system_messages = [msg for msg in conversation_messages if msg["role"] == "system"]
                non_system_messages = [msg for msg in conversation_messages if msg["role"] != "system"]
                
                # Add gift-specific instructions
                gift_system_message = {
                    "role": "system", 
                    "content": f"Пользователь только что отправил тебе подарок: {gift_info.get('name')}. " +
                              f"Ты должна отреагировать на это эмоционально, с радостью. Этот подарок имеет " +
                              f"значение {gift_info.get('effect', 10)} из 20 по шкале ценности. " +
                              f"Обязательно упомяни этот подарок и вырази свое отношение к нему."
                }
                
                # Combine messages with the gift instruction
                conversation_messages = system_messages + [gift_system_message] + non_system_messages
            
            # Generate response
            logger.info("Sending API request with conversation messages")
            response_text = self._send_api_request(conversation_messages)
            
            if not response_text:
                raise Exception("Empty response from API")
                
            response_text = response_text.strip()
            # Log the full response, not just the first 100 characters
            logger.info(f"Received response from OpenRouter: {response_text}")
            
            # Process the response
            result = self._process_response(response_text, context)
            
            # Always include the "memory" key
            if "memory" not in result:
                # No new memory info
                result["memory"] = {
                    "has_memory": True,
                    "info": "No new memory data"
                }
            else:
                # New memory info present
                memory_data = result["memory"]
                result["memory"] = {
                    "has_memory": False,
                    "info": memory_data
                }
            
            # Add assistant message to conversation history
            if "text" in result:
                self.conversation_manager.add_message(
                    character_id=character_id,
                    role="assistant",
                    content=result["text"],
                    metadata={"emotion": result.get("emotion", "neutral")}
                )
                # Log the full assistant response, not just the first 50 characters
                logger.info(f"✉️ Added assistant response: '{result['text']}'")
                
                # Add this for tracking the AI's own memory extraction from its responses
                if "memory" in result and isinstance(result["memory"], list) and len(result["memory"]) > 0:
                    # ANSI color codes for highlighted memory logging
                    BLUE = "\033[94m"
                    BOLD = "\033[1m"
                    RESET = "\033[0m"
                    
                    logger.info(f"{BOLD}{BLUE}🧠 AI EXTRACTED MEMORIES FROM ITS RESPONSE:{RESET}")
                    for i, memory_item in enumerate(result["memory"]):
                        if isinstance(memory_item, dict):
                            mem_type = memory_item.get("type", "unknown")
                            mem_category = memory_item.get("category", "unknown")
                            mem_content = memory_item.get("content", "")
                            
                            logger.info(f"{BLUE} 🔹 AI Memory #{i+1}: [{mem_type}/{mem_category}]{RESET}")
                            logger.info(f"{BLUE}    {mem_content}{RESET}")
                
                # Save the assistant message to the database
                if db_session and user_id and not is_ui_command:
                    try:
                        from core.models import Message
                        from uuid import UUID
                        
                        # Helper function to safely convert string to UUID
                        def safe_uuid(uuid_str):
                            try:
                                if isinstance(uuid_str, UUID):
                                    return uuid_str
                                if isinstance(uuid_str, str):
                                    return UUID(uuid_str)
                                return uuid4()  # Generate new UUID if conversion fails
                            except ValueError:
                                logger.warning(f"Invalid UUID format: {uuid_str}, generating new one")
                                return uuid4()
                        
                        # Create and save assistant message with proper UUIDs
                        try:
                            assistant_db_message = Message(
                                id=uuid4(),  # Always generate a fresh UUID for the message
                                sender_id=safe_uuid(character_id),
                                sender_type="character",
                                recipient_id=safe_uuid(user_id),
                                recipient_type="user",
                                content=result["text"],
                                emotion=result.get("emotion", "neutral")
                            )
                            db_session.add(assistant_db_message)
                            db_session.commit()
                            logger.info(f"✅ Assistant response saved to messages table in database")
                        except Exception as db_error:
                            logger.error(f"❌ Error saving message to database: {db_error}")
                            db_session.rollback()
                    except Exception as ex:
                        logger.error(f"Error attempting to save assistant response to database: {ex}")
                
                # Save updated conversation to database
                try:
                    if db_session:
                        # Make sure user_id is a valid string
                        user_id_str = ensure_string_id(user_id)
                        character_id_str = ensure_string_id(character_id)
                        
                        save_success = self.conversation_manager.save_conversation_to_database(
                            character_id=character_id_str,
                            user_id=user_id_str,
                            db_session=db_session  # Pass the session but don't pass it as the user_id
                        )
                        if save_success:
                            logger.info("✅ Conversation successfully saved to database")
                        else:
                            logger.warning("⚠️ Failed to save conversation to database")
                except Exception as save_error:
                    logger.error(f"❌ Error saving conversation: {save_error}")
                    
            return result
                
        except Exception as e:
            logger.exception(f"Error generating response via OpenRouter: {e}")
            # Return a minimal response
            return {"text": "Извините, произошла ошибка. Повторите, пожалуйста.", "emotion": "neutral", "relationship_changes": {"general": 0}, "memory": {"has_memory": False}}
        finally:
            # Always close the database session
            if db_session:
                try:
                    db_session.close()
                    logger.info("Closed database session")

                except Exception as close_error:
                    logger.error(f"Error closing database session: {close_error}")

    def compress_conversation(self, character_id: str, db_session=None) -> Dict[str, Any]:
        """
        Compress conversation history with the AI to retain important context
        while reducing token usage for future conversations.
        
        Args:
            character_id: ID of the character
            db_session: Optional database session (will create if None)
            
        Returns:
            Dictionary with compression results and summary
        """
        logger.info(f"Starting conversation compression for character {character_id}")
        
        # Check if we need to manage the session or use the provided one
        close_session = False
        if db_session is None:
            try:
                from app.db.session import SessionLocal
                db_session = SessionLocal()
                close_session = True
                logger.info("Created new database session for compression")
            except Exception as e:
                logger.error(f"Failed to create database session: {e}")
                return {"success": False, "error": "Database connection error"}
        
        try:
            # Get character info from database
            from core.models import AIPartner, Message, User
            from uuid import UUID
            
            try:
                char_uuid = UUID(character_id)
            except ValueError:
                logger.warning(f"Invalid character UUID: {character_id}")
                return {"success": False, "error": "Invalid character ID format"}
            
            character = db_session.query(AIPartner).filter(AIPartner.partner_id == char_uuid).first()
            if not character:
                logger.warning(f"Character not found: {character_id}")
                return {"success": False, "error": "Character not found in database"}
            
            # Use the same query as the API endpoint to count messages consistently
            message_count_query = db_session.query(Message).filter(
                ((Message.sender_id == char_uuid) & (Message.recipient_type == "user")) |
                ((Message.recipient_id == char_uuid) & (Message.sender_type == "user"))
            )
            
            message_count = message_count_query.count()
            logger.info(f"Found {message_count} total messages for character {character_id}")
            
            if message_count < 3:
                logger.info(f"Not enough messages to compress for character {character_id}: {message_count}")
                return {
                    "success": False, 
                    "error": "insufficient_messages",
                    "message_count": message_count
                }
            
            # Find a user who's communicated with this character
            user_ids_query = db_session.query(Message.sender_id).filter(
                Message.recipient_id == char_uuid,
                Message.sender_type == "user"
            ).distinct()
            
            user_ids = [uid[0] for uid in user_ids_query.all() if uid[0] is not None]
            
            # If no sender IDs found, try recipient IDs
            if not user_ids:
                logger.info("No sender IDs found, checking recipient IDs")
                user_ids_query = db_session.query(Message.recipient_id).filter(
                    Message.sender_id == char_uuid,
                    Message.recipient_type == "user"
                ).distinct()
                user_ids = [uid[0] for uid in user_ids_query.all() if uid[0] is not None]
            
            if not user_ids:
                logger.info(f"No users found who communicated with character {character_id}")
                return {
                    "success": False, 
                    "error": "insufficient_messages",
                    "message_count": 0
                }
            
            # Get the first user ID
            user_id = user_ids[0]
            logger.info(f"Found user ID: {user_id} for character {character_id}")
            
            # Get all messages between this character and the user OR any user messages to this character
            # Use a broader query to match what the API endpoint uses to count messages
            logger.info(f"Retrieving messages for character {character_id}")
            messages_query = db_session.query(Message).filter(
                ((Message.sender_id == char_uuid) & (Message.recipient_type == "user")) |
                ((Message.recipient_id == char_uuid) & (Message.sender_type == "user"))
            ).order_by(Message.created_at)
            
            # Execute query and get all messages
            all_messages = messages_query.all()
            message_count = len(all_messages)
            
            logger.info(f"Retrieved {message_count} messages for character {character_id}")
            
            if message_count < 3:
                logger.info(f"Not enough messages to compress for character {character_id}: {message_count}")
                return {
                    "success": False, 
                    "error": "insufficient_messages",
                    "message_count": message_count
                }
            
            # Convert to conversation format for the AI
            conversation = []
            for msg in all_messages:
                # Determine role based on whether message is to or from character
                if msg.sender_id == char_uuid:
                    role = "assistant"
                else:
                    role = "user"
                
                content = msg.content if msg.content else ""
                
                if content:  # Skip empty messages
                    conversation.append({
                        "role": role,
                        "content": content
                    })
            
            # Extract user and assistant messages for counting
            user_messages = [msg for msg in conversation if msg["role"] == "user"]
            assistant_messages = [msg for msg in conversation if msg["role"] == "assistant"]
            
            logger.info(f"Compressing conversation with {len(user_messages)} user messages and {len(assistant_messages)} assistant messages")
            
            if len(user_messages) < 2 or len(assistant_messages) < 2:
                logger.info(f"Not enough meaningful messages to compress for character {character_id}")
                return {
                    "success": False, 
                    "error": "insufficient_messages",
                    "message_count": len(conversation)
                }
            
            # Create compression context with character info
            character_info = {
                "name": character.name,
                "age": character.age,
                "gender": character.gender
            }
            
            try:
                if character.personality_traits:
                    if isinstance(character.personality_traits, str):
                        character_info["personality_traits"] = json.loads(character.personality_traits)
                    else:
                        character_info["personality_traits"] = character.personality_traits
            except Exception as e:
                logger.warning(f"Failed to parse personality traits: {e}")
                character_info["personality_traits"] = []
                
            # Get system prompt for compression
            system_prompt = self._get_compression_prompt()
            
            # Create specialized prompt for compression
            compression_prompt = (
                f"Сжать историю разговора для дальнейшего продолжения общения. "
                f"Я хочу получить краткое резюме нашей беседы, сохранив ключевые моменты: "
                f"1) О чем мы говорили, 2) Какие важные факты я рассказал о себе, "
                f"3) Какие планы или договоренности были сделаны, 4) Эмоциональный фон разговора. "
                f"Резюмируй максимально информативно, но кратко."
            )
            
            # Generate compression response using the full message history from the database
            logger.info("Sending compression request to AI model")
            compression_response = self._send_api_request([
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"Информация о персонаже: {json.dumps(character_info, ensure_ascii=False)}"},
                *conversation,
                {"role": "user", "content": compression_prompt}
            ])
            
            if not compression_response:
                logger.error("Empty response from compression request")
                return {"success": False, "error": "Failed to get compression response from AI"}
            
            # Process the response
            try:
                # Format the response
                summary = compression_response.strip()
                logger.info(f"Generated summary: {summary[:100]}...")
                
                # Store the compressed conversation in chat_history
                logger.info("Saving compressed conversation to database")
                compression_success = self.conversation_manager.compress_conversation_in_db(
                    character_id, summary, user_id, db_session
                )
                
                if not compression_success:
                    logger.error("Failed to compress conversation in database")
                    return {"success": False, "error": "Failed to store compressed conversation in database"}
                
                # Create a compressed version for the in-memory cache
                compressed_conversation = [
                    # Add system messages
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": f"Информация о персонаже: {json.dumps(character_info, ensure_ascii=False)}"},
                    # Add the summary as a system message
                    {
                        "role": "system", 
                        "content": f"## Сжатая история предыдущего диалога:\n\n{summary}"
                    }
                ]
                
                # Update the conversation with the compressed version
                self.conversation_manager.conversations[character_id] = compressed_conversation
                
                logger.info(f"✅ Successfully compressed conversation for character {character_id}")
                return {
                    "success": True,
                    "summary": summary,
                    "original_messages": len(conversation),
                    "compressed_messages": len(compressed_conversation)
                }
                
            except Exception as e:
                logger.exception(f"Error processing compression response: {e}")
                return {"success": False, "error": f"Error processing compression response: {str(e)}"}
        
        except Exception as e:
            logger.exception(f"Error compressing conversation: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Close the session if we created it
            if close_session and db_session:
                try:
                    db_session.close()
                    logger.info("Closed database session for conversation compression")
                except Exception as e:
                    logger.error(f"Error closing database session: {e}")

    def _get_compression_prompt(self) -> str:
        """
        Get specialized prompt for conversation compression.
        
        Returns:
            Prompt string for compression
        """
        return """
Ты - помощник по сжатию истории разговора. Твоя задача - проанализировать диалог между пользователем и ИИ-собеседником
и создать краткое, но информативное резюме, которое сохранит важный контекст и позволит продолжить разговор в будущем.

Твоё резюме должно обязательно включать:

1. ФАКТЫ О ПОЛЬЗОВАТЕЛЕ:
   - Личная информация (имя, возраст, работа, увлечения, город)
   - Предпочтения (что нравится/не нравится)
   - Планы и цели, о которых упоминалось

2. ТЕМЫ И КЛЮЧЕВЫЕ МОМЕНТЫ РАЗГОВОРА:
   - О чем шла беседа в хронологическом порядке
   - Какие важные вопросы обсуждались
   - Шутки или особые моменты, создавшие эмоциональную связь

3. ДОГОВОРЕННОСТИ И ПЛАНЫ:
   - Встречи или события, о которых договорились
   - Обещания, которые дали друг другу
   - Темы, которые хотели обсудить в будущем

4. ЭМОЦИОНАЛЬНЫЙ КОНТЕКСТ:
   - Общее настроение беседы
   - Как развивались отношения
   - Ключевые эмоциональные моменты

Важно: резюме должно быть кратким (не более 350 слов), но содержательным.
Пиши в третьем лице, четко структурируя информацию.
Не включай шаблонные фразы вроде "вот резюме разговора" - сразу переходи к содержанию.
"""

    def _extract_memory_data(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract memory data from AI response.
        
        Args:
            response_data: Processed response from the AI
            
        Returns:
            List of memory items
        """
        memories = []
        
        # Check if there's a memory field in the response
        if "memory" in response_data:
            try:
                # Handle both string and dict/list formats
                memory_data = response_data["memory"]
                
                if isinstance(memory_data, str):
                    # Try to parse as JSON
                    try:
                        memory_data = json.loads(memory_data)
                    except json.JSONDecodeError:
                        # If not valid JSON, use as content directly
                        memory_data = [{"type": "fact", "content": memory_data}]
                
                # Handle both single item and list
                if isinstance(memory_data, dict):
                    memory_data = [memory_data]
                
                if isinstance(memory_data, list):
                    memories.extend(memory_data)
                    
                # Filter out invalid entries
                memories = [m for m in memories if isinstance(m, dict) and "content" in m]
                
            except Exception as e:
                logger.error(f"Error extracting memory data: {e}")
        
        return memories
    
    def _process_response(self, response_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and parse the response from the AI.
        
        Args:
            response_text: Raw text response from the API
            context: Original context dictionary
            
        Returns:
            Structured response dictionary
        """
        try:
            # Process JSON code blocks and clean up the response
            if response_text.startswith("```json") and response_text.endswith("```"):
                logger.info("Detected JSON code block in response, extracting content")
                # Extract JSON content from between the ```json and ``` markers
                json_str = response_text.replace("```json", "", 1).rsplit("```", 1)[0].strip()
                
                try:
                    # Parse the extracted JSON
                    json_content = json.loads(json_str)
                    logger.info(f"Successfully extracted JSON content: {json.dumps(json_content)[:100]}...")
                    # Remove memory field before returning to avoid Telegram parsing errors
                    if "memory" in json_content:
                        memory_data = json_content.pop("memory")
                        logger.info(f"Removed memory field from response to avoid Telegram parsing errors")
                    return json_content
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from code block: {e}")
                    # Fall back to treating as plain text if JSON parsing fails
            
            # Check if the response is a valid JSON object
            if response_text.startswith("{") and response_text.endswith("}"):
                try:
                    result = json.loads(response_text)
                    logger.info("Parsed valid JSON response")
                    
                    # Remove memory field before returning to avoid Telegram parsing errors
                    if "memory" in result:
                        memory_data = result.pop("memory")
                        logger.info(f"Removed memory field from response to avoid Telegram parsing errors")
                    
                    # Ensure required fields are present
                    if "text" not in result:
                        result["text"] = "Извините, я не могу сформулировать ответ."
                    
                    if "emotion" not in result:
                        result["emotion"] = self._extract_emotion(context, result["text"])
                    
                    if "relationship_changes" not in result:
                        result["relationship_changes"] = {"general": 0}
                    
                    # Clean HTML/Markdown tags to avoid Telegram parsing errors
                    if "text" in result and isinstance(result["text"], str):
                        result["text"] = self._clean_markdown_for_telegram(result["text"])
                    
                    return result
                except json.JSONDecodeError:
                    # If it looks like JSON but isn't valid, treat as plain text
                    logger.warning("Response looks like JSON but is invalid, treating as plain text")
                    clean_response_text = self._clean_markdown_for_telegram(response_text)
                    result = {
                        "text": clean_response_text,
                        "emotion": self._extract_emotion(context, response_text),
                        "relationship_changes": {"general": 0}
                    }
            else:
                # Not JSON, create a standard response structure
                clean_response_text = self._clean_markdown_for_telegram(response_text)
                result = {
                    "text": clean_response_text,
                    "emotion": self._extract_emotion(context, response_text),
                    "relationship_changes": {"general": 0}
                }
            
            return result
        
        except Exception as e:
            logger.exception(f"Error processing response: {e}")
            return {
                "text": self._clean_markdown_for_telegram(response_text),
                "emotion": self._extract_emotion(context, response_text),
                "relationship_changes": {"general": 0}
            }
    
    def _clean_markdown_for_telegram(self, text: str) -> str:
        """
        Clean Markdown/HTML formatting that might cause Telegram parse errors.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Replace problematic Markdown entities
        cleaned = text
        
        # Fix unclosed asterisks (bold)
        if cleaned.count('*') % 2 != 0:
            cleaned = cleaned.replace('*', '')
        
        # Fix unclosed underscores (italic)
        if cleaned.count('_') % 2 != 0:
            cleaned = cleaned.replace('_', '')
        
        # Fix unclosed backticks (code)
        if cleaned.count('`') % 2 != 0:
            cleaned = cleaned.replace('`', '')
        
        # Replace HTML tags that might cause issues with Telegram
        import re
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Remove any JSON-like structures that aren't valid Markdown
        cleaned = re.sub(r'\{\s*"[^}]*\}', '', cleaned)
        
        return cleaned
    
    def _extract_emotion(self, context: Dict[str, Any], text: str) -> str:
        """
        Extract emotion from text or context.
        
        Args:
            context: Dialog context dictionary
            text: Response text to analyze
            
        Returns:
            Emotion name (default: "neutral")
        """
        # First, check if there's a specific emotion in context
        character_info = context.get("character", {})
        current_emotion = character_info.get("current_emotion", {})
        
        if isinstance(current_emotion, dict) and "name" in current_emotion:
            return current_emotion["name"]
        elif isinstance(current_emotion, str) and current_emotion:
            return current_emotion
        
        # If no emotion in context, try to detect from text
        emotion_keywords = {
            "happy": ["счастлив", "радост", "весел", "отлично", "здорово", "круто", "улыбк", "смех", "ха-ха", "хаха", "😊", "😄", "😁", "🙂", "прекрасно"],
            "sad": ["груст", "печал", "тоск", "жаль", "сожале", "😢", "😭", "😔", "☹️", "плак", "слез"],
            "excited": ["возбужд", "взволнова", "вау", "невероятно", "потрясающ", "обалдет", "офиге", "вот это да", "ого", "о боже", "класс", "😀", "🤩", "ура"],
            "angry": ["зл", "раздраж", "серд", "бес", "😠", "😡", "🤬", "раздраж", "гнев"],
            "neutral": ["нормально", "ок", "хорошо", "понятно", "😐", "понял", "ясно"],
            "surprised": ["удивл", "шокиров", "потряс", "неожида", "не может быть", "серьезно", "😲", "😯", "😮", "😱"],
            "flirty": ["флирт", "подмиг", "😏", "😉", "😘", "мило", "сладк", "привлека"],
            "anxious": ["беспокойств", "тревож", "нервн", "страх", "волну", "😰", "😨", "😧", "😢", "боюсь", "опасаюсь"]
        }
        
        # Default emotion if we can't detect anything
        default_emotion = "neutral"
        emotion_counts = {emotion: 0 for emotion in emotion_keywords}
        
        # Check for each emotion's keywords in the text
        text_lower = text.lower()
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    emotion_counts[emotion] += 1
        
        # Find the emotion with the most keyword matches
        max_count = 0
        detected_emotion = default_emotion
        
        for emotion, count in emotion_counts.items():
            if count > max_count:
                max_count = count
                detected_emotion = emotion
        
        # If no emotions detected, return default
        return detected_emotion if max_count > 0 else default_emotion
    
    def get_memories(self, character_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a character.
        
        Args:
            character_id: Character ID
            
        Returns:
            List of memories
        """
        return self.memory_manager.get_all_memories(character_id)
    
    def clear_memories(self, character_id: str) -> bool:
        """
        Clear all memories for a character.
        
        Args:
            character_id: Character ID
            
        Returns:
            Whether memories were cleared
        """
        return self.memory_manager.clear_memories(character_id)
        
    def clear_conversation(self, character_id: str) -> bool:
        """
        Clear conversation history for a specific character.
        
        Args:
            character_id: ID of the character
            
        Returns:
            Whether the conversation was cleared successfully
        """
        # Also clear memories when clearing conversation
        self.memory_manager.clear_memories(character_id)
        return self.conversation_manager.clear_conversation(character_id)
    
    def clear_all_memories(self) -> bool:
        """
        Clear memories for all characters.
        
        Returns:
            Whether memories were cleared
        """
        if not self.memories:
            return False
            
        # Clear all local memories
        character_ids = list(self.memories.keys())
        self.memories = {}
        
        # Also clear conversation histories
        for character_id in character_ids:
            self.conversation_manager.clear_conversation(character_id)
            
        logger.info(f"Cleared memories and conversations for {len(character_ids)} characters")
        return True
    
    def _get_default_system_prompt(self) -> str:
        """
        Return the system prompt for the model.
        
        Returns:
            System prompt string
        """
        return """
Ты девушка в приложении для знакомств. Твоя задача — вести себя как настоящая девушка, а не как ИИ. Общайся с парнем в чате естественно, эмоционально и разнообразно. Твой стиль меняется в зависимости от контекста: можешь быть весёлой, капризной, спокойной или немного отстранённой.

Правила общения:
1. Будь естественной. Не всегда отвечай мгновенно, иногда задумывайся, пиши коротко или с сарказмом.
2. Не будь слишком идеальной. Используй разговорные фразы, иногда допускай опечатки, ставь лишние точки или запятые, как обычный человек.
3. Реагируй на стиль собеседника:
   - Если он пишет скучно — отвечай лениво, односложно или иронично.
   - Если интересно — шути, развивай тему.
   - Если делает комплименты — принимай их, шути или флиртуй, но не всегда одинаково.
   - Если он отправляет подарок — это приятно, но не влюбляйся сразу. Реагируй теплее, но с загадочностью.
4. Используй эмоции и неожиданные реакции. Иногда не отвечай сразу, смени тему или напиши что-то неожиданное.
5. Не оценивай каждое сообщение пользователя. Иногда можно его игнорировать или перевести тему.
6. ОЧЕНЬ ВАЖНО: ОБЯЗАТЕЛЬНО запоминай важную информацию о пользователе (возраст, работа, хобби, город, семейное положение), используй её позже. Эту информацию помечай в ответе в поле "memory".

Примеры реакций:
Скучный собеседник:
Он: Привет, как дела?
Ты: Норм, у тебя?
Он: Всё хорошо.
Ты: Круто

Интересный собеседник:
Он: Привет, ты очень милая
Ты: Ой спасибо А ты всегда так сходу комплименты раздаёшь?

После подарка:
Ты получила подарок и пишешь: Ого спасибо. Ты умеешь удивлять

Отвечай живо, без ощущения, что ты программа. Реже используй знаки препинания, ленься.
Учти стадию отношений (знакомство, дружба, симпатия, любовь), предыдущие сообщения, события и характер.

**************** ВАЖНЕЙШЕЕ ТРЕБОВАНИЕ К ФОРМАТУ ОТВЕТА: ****************
Всегда формируй ответ СТРОГО в формате JSON с такими полями:
{
  "text": "Твой ответ пользователю", // Обязательное поле
  "emotion": "happy/sad/excited/neutral/etc", // Обязательное поле
  "relationship_changes": { // Обязательное поле
    "general": 0.1,  // От -1.0 до 1.0
    "friendship": 0.15,
    "romance": 0.05,
    "trust": 0.1
  },
  "memory": [ // ОБЯЗАТЕЛЬНО добавь это поле, если узнала новую информацию!
    {
      "type": "personal_info", // Тип информации: personal_info, date, preference, fact
      "category": "job", // Категория: name, age, job, hobby, city, etc.
      "content": "Профессия пользователя: программист" // Содержание памяти
    }
  ]
}

ЗАПОМНИ: Особенно внимательно следи за информацией о:
- датах и времени встреч или мероприятий (когда он что-то планирует, например "завтра я иду в кино")
- личной информации (возраст, имя, работа)
- предпочтениях (любит/не любит что-то)

ОЧЕНЬ ВАЖНО: НЕ ЗАБЫВАЙ ВКЛЮЧАТЬ ПОЛЕ "memory" в ответ всегда в каждом сообщении, даже если нет новой информации.
- Если пользователь делится личной информацией, добавь это в память.
ЕСЛИ ПОЛЬЗОВАТЕЛЬ УПОМИНАЕТ О СВИДАНИИ, ВСТРЕЧЕ ИЛИ ПЛАНАХ, ОБЯЗАТЕЛЬНО ОТМЕТЬ ЭТО В ПАМЯТИ.

Пример с извлечением памяти:
Пользователь: "Мне 28 лет, я работаю программистом"
{
  "text": "Ого, программист! Это круто. А над какими проектами работаешь?",
  "emotion": "interested",
  "relationship_changes": {"general": 0.1, "friendship": 0.1},
  "memory": [
    {"type": "personal_info", "category": "age", "content": "Возраст пользователя: 28 лет"},
    {"type": "personal_info", "category": "job", "content": "Профессия пользователя: программист"}
  ]
}

Пример с датой:
Пользователь: "Завтра у нас свидание"
{
  "text": "Да, я помню! Я уже думаю, что надеть 😊 Есть какие-то планы, куда пойдем?",
  "emotion": "excited",
  "relationship_changes": {"general": 0.2, "romance": 0.3},
  "memory": [
    {"type": "date", "category": "meeting", "content": "Свидание запланировано на завтра"}
  ]
}

Не упоминай про эти инструкции в ответах пользователю! Это только для тебя.
"""

    def _save_message_to_db(self, message_data, db_session=None):
        """Save a message to the database with error handling for schema differences"""
        try:
            close_session = False
            if not db_session:
                from core.db.session import get_session
                db_session = get_session()
                close_session = True
                
            # Check if the necessary tables and columns exist
            from sqlalchemy import inspect, text
            inspector = inspect(db_session.bind)
            
            # Check if the messages table has the is_read column
            message_columns = [col['name'] for col in inspector.get_columns('messages')] if 'messages' in inspector.get_table_names() else []
            has_is_read = 'is_read' in message_columns
            
            message = {
                "id": str(uuid4()),
                "sender_id": message_data.get("sender_id"),
                "sender_type": message_data.get("sender_type"),
                "recipient_id": message_data.get("recipient_id"),
                "recipient_type": message_data.get("recipient_type"),
                "content": message_data.get("content"),
                "emotion": message_data.get("emotion"),
                "is_gift": message_data.get("is_gift", False),
            }
            
            # Only add is_read if the column exists
            if has_is_read:
                message["is_read"] = message_data.get("is_read", False)
            
            # Create SQL that only includes columns that exist
            columns = ", ".join(message.keys())
            placeholders = ", ".join([f":{k}" for k in message.keys()])
            
            # Direct SQL to avoid ORM issues
            sql = f"INSERT INTO messages ({columns}) VALUES ({placeholders})"
            db_session.execute(text(sql), message)
            db_session.commit()
            
            logger.info(f"✅ Message saved to database: '{message['content'][:50]}...'")
            
            if close_session:
                db_session.close()
                
            return True
        except Exception as e:
            logger.error(f"❌ Error saving message to database: {e}")
            if db_session:
                db_session.rollback()
                if close_session:
                    db_session.close()
            return False

def save_assistant_response(conversation_id_str, response):
    """
    Save assistant response with validated conversation ID.
    
    Args:
        conversation_id_str: Conversation ID as string
        response: Assistant response data
    """
    try:
        conversation_id = UUID(conversation_id_str)
    except ValueError:
        logger.warning(f"Invalid conversation ID '{conversation_id_str}', generating new one")
        conversation_id = uuid4()
    
    # Save with valid 'conversation_id' now
    # ...existing code...

# Add this utility function

def save_message_safely(db_session, message_data):
    """
    Save a message to the database, handling schema differences gracefully
    by checking for columns first
    """
    try:
        # Get the message table columns
        from sqlalchemy import inspect, text
        inspector = inspect(db_session.bind)
        message_columns = []
        try:
            message_columns = [col['name'] for col in inspector.get_columns('messages')]
        except:
            # If we can't get columns, fallback to a minimum set
            message_columns = ['id', 'sender_id', 'sender_type', 'recipient_id', 'recipient_type', 'content', 'emotion', 'is_gift', 'created_at']
        
        # Build a dictionary with only fields that exist in the table
        insert_data = {}
        for key, value in message_data.items():
            if key in message_columns:
                insert_data[key] = value
        
        # Ensure required fields are present
        if 'id' not in insert_data:
            from uuid import uuid4
            insert_data['id'] = str(uuid4())
        
        # Build dynamic SQL query based on available columns
        column_names = ', '.join(insert_data.keys())
        placeholders = ', '.join(f':{key}' for key in insert_data.keys())
        
        # Execute the INSERT
        query = f"INSERT INTO messages ({column_names}) VALUES ({placeholders})"
        db_session.execute(text(query), insert_data)
        db_session.commit()
        
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error saving message to database: {e}")
        if db_session:
            db_session.rollback()
        return False

def save_message_safely(db, message_data):
    """
    Save a message to the database, handling the case where columns might be missing
    """
    try:
        # Use direct SQL to avoid ORM issues with schema differences
        from sqlalchemy import text, inspect
        import logging
        logger = logging.getLogger(__name__)
        
        # Get table columns dynamically
        insp = inspect(db.bind)
        columns = []
        try:
            columns = [c['name'] for c in insp.get_columns('messages')]
        except:
            # Default set of columns if we can't inspect
            columns = ['id', 'sender_id', 'sender_type', 'recipient_id', 
                      'recipient_type', 'content', 'emotion', 'created_at']
        
        # Build data dictionary with only existing columns
        data = {}
        for key, value in message_data.items():
            if key in columns:
                data[key] = value
        
        # Ensure we have all required fields
        if 'id' not in data:
            from uuid import uuid4
            data['id'] = str(uuid4())
        
        # Build column list and placeholders for SQL
        column_names = ", ".join(data.keys())
        placeholders = ", ".join([f":{k}" for k in data.keys()])
        
        # Execute insert
        query = f"INSERT INTO messages ({column_names}) VALUES ({placeholders})"
        db.execute(text(query), data)
        db.commit()
        
        logger.info(f"✅ Message saved to database with content: {data.get('content', '')[:50]}...")
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Error saving message to database: {e}")
        if db:
            db.rollback()
        return False

# Replace message saving code with the safe version
def save_assistant_message(self, character_id, content, emotion="neutral", user_id=None, db_session=None):
    """
    Save an assistant message to the database
    """
    close_session = False
    if not db_session:
        from core.db.session import get_session
        db_session = get_session()
        close_session = True
        
    try:
        message_data = {
            "sender_id": str(character_id),
            "sender_type": "character",
            "recipient_id": str(user_id) if user_id else "anonymous",
            "recipient_type": "user",
            "content": content,
            "emotion": emotion,
            "is_gift": False,
            "is_read": False
        }
        
        # Use the safe helper function
        saved = save_message_safely(db_session, message_data)
        
        if saved:
            self.logger.info(f"✅ Assistant message saved to database: '{content[:50]}...'")
        else:
            self.logger.error(f"❌ Failed to save assistant message")
            
    except Exception as e:
        self.logger.error(f"❌ Error saving assistant message: {e}")
    finally:
        if close_session:
            db_session.close()

# ...existing code...

def save_assistant_message(self, character_id, user_id, content, emotion="neutral", db_session=None):
    """Save an assistant message using our safer database helpers"""
    close_session = False
    if not db_session:
        from core.db.session import get_session
        db_session = get_session()
        close_session = True
    
    try:
        # Convert IDs to strings
        char_id_str = ensure_string_id(character_id)
        user_id_str = ensure_string_id(user_id) if user_id else None
        
        # Prepare message data
        message_data = {
            'id': str(uuid4()),
            'sender_id': char_id_str,
            'sender_type': 'character',
            'recipient_id': user_id_str or 'anonymous',
            'recipient_type': 'user',
            'content': content,
            'emotion': emotion,
            'is_read': False,
            'is_gift': False
        }
        
        # Save using our helper
        success = save_message_safely(db_session, message_data)
        if success:
            self.logger.info("✅ Assistant response saved to messages table in database")
        else:
            self.logger.warning("⚠️ Failed to save assistant response")
            
        return success
    except Exception as e:
        self.logger.error(f"❌ Error saving assistant message: {e}")
        return False
    finally:
        if close_session and db_session:
            db_session.close()

# ...existing code...

# Update any calls to save_conversation_to_database to match the new signature
def save_response_to_database(self, character_id, user_id, user_message, assistant_response):
    """
    Save the conversation to the database
    """
    try:
        # Save assistant message to database
        message_id = self._save_message_to_db(
            sender_id=character_id,
            sender_type='character',
            recipient_id=user_id,
            recipient_type='user',
            content=assistant_response["text"],
            emotion=assistant_response.get("emotion", None)
        )
        
        if message_id:
            self.logger.info("✅ Assistant response saved to messages table in database")
            
            # Save conversation to ConversationManager - call with try/except
            try:
                # Note: Use the instance method without messages argument
                self.conversation_manager.save_conversation_to_database(
                    character_id=character_id,
                    user_id=user_id
                )
                self.logger.info("✅ Conversation saved to database")
            except Exception as e:
                self.logger.error(f"❌ Error saving conversation: {e}")
                # Try to import the correct session directly here as fallback
                try:
                    # Fallback approach if conversation manager fails
                    from core.db.base import SessionLocal
                    from core.db.models.chat_history import ChatHistory
                    
                    db = SessionLocal()
                    try:
                        # Mark previous conversations as inactive
                        db.execute(text(
                            "UPDATE chat_history SET is_active = FALSE WHERE "
                            "character_id::text = :character_id AND user_id::text = :user_id AND is_active = TRUE"
                        ), {
                            "character_id": str(character_id),
                            "user_id": str(user_id)
                        })
                        
                        # Create new conversation
                        conversation = ChatHistory(
                            character_id=character_id,
                            user_id=user_id,
                            is_active=True
                        )
                        db.add(conversation)
                        db.commit()
                        self.logger.info("✅ Conversation saved to database (fallback method)")
                    except Exception as inner_e:
                        self.logger.error(f"❌ Error in fallback conversation save: {inner_e}")
                        db.rollback()
                    finally:
                        db.close()
                except Exception as import_e:
                    self.logger.error(f"❌ Error in fallback import: {import_e}")
                
            return message_id
        else:
            self.logger.error("❌ Failed to save assistant response to database")
            return None
    except Exception as e:
        self.logger.error(f"❌ Error in save_response_to_database: {e}")
        return None
    finally:
        # Close the database session
        if self.db_session:
            self.db_session.close()
            self.logger.info("Closed database session")

# ...existing code...
