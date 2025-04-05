import json
import logging
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.utils.db_helpers import save_message_safely, find_message_by_id_safely, ensure_string_id, reset_failed_transaction, execute_with_retry, execute_safe_uuid_query
from core.db.session import get_db_session, SessionLocal
from sqlalchemy import text
import uuid

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Manages conversation histories for AI characters.
    Provides methods to store, retrieve, and manipulate conversation context.
    """
    
    def __init__(self):
        # Dictionary to store conversation history by character_id
        self.conversations = {}
        # Dictionary to store character system prompts
        self.system_prompts = {}
        # Maximum number of messages to keep in history (excluding system prompt)
        self.max_history_length = 15
        self.logger = logging.getLogger(__name__)  # Initialize logger as instance attribute
        
    def start_conversation(self, character_id: str, system_prompt: str, character_info: Dict[str, Any], db_session=None) -> None:
        """
        Initialize a new conversation for a character.
        
        Args:
            character_id: Unique identifier for the character
            system_prompt: The system prompt containing character instructions
            character_info: Dictionary with character metadata
            db_session: Database session for storing in DB (optional)
        """
        logger.info(f"Starting new conversation for character {character_id}")
        
        # Append memory inclusion instruction to the system prompt
        system_prompt += "\nВсегда включай данные памяти (memory) в каждом твоем ответе."
        
        # Format character description
        char_description = self._format_character_description(character_info)
        
        # Initialize the conversation with system messages
        self.conversations[character_id] = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": char_description}
        ]
        
        # Store the system prompt for future reference
        self.system_prompts[character_id] = system_prompt
        
        # Store in database if session provided
        if db_session:
            self._store_conversation_in_db(character_id, system_prompt, char_description, db_session)
        
        logger.info(f"Conversation initialized for character {character_id}")
    
    def _format_character_description(self, character_info: Dict[str, Any]) -> str:
        """
        Format character information into a structured description string.
        
        Args:
            character_info: Dictionary containing character metadata
            
        Returns:
            Formatted character description string
        """
        # Default values if information is missing
        name = character_info.get("name", "Неизвестно")
        age = character_info.get("age", "Неизвестно")
        gender = character_info.get("gender", "female")
        
        # Format personality traits
        traits = character_info.get("personality_traits", [])
        if isinstance(traits, str):
            try:
                traits = json.loads(traits)
            except json.JSONDecodeError:
                traits = [traits]
        traits_str = ", ".join(traits) if traits else "разносторонняя"
        
        # Format interests
        interests = character_info.get("interests", [])
        if isinstance(interests, str):
            try:
                interests = json.loads(interests)
            except json.JSONDecodeError:
                interests = [interests]
        interests_str = ", ".join(interests) if interests else "разнообразные интересы"
        
        # Get background or create a default one
        background = character_info.get("background", "")
        if not background:
            background = f"{name} - интересная личность с разносторонними увлечениями."
        
        # Create formatted description
        description = f"""Имя: {name}
Возраст: {age}
Пол: {gender}
Черты характера: {traits_str}
Интересы: {interests_str}
Биография: {background}"""

        # Add current emotion if available
        current_emotion = character_info.get("current_emotion", {})
        if current_emotion:
            if isinstance(current_emotion, dict) and "name" in current_emotion:
                emotion_name = current_emotion["name"]
                description += f"\nТекущее настроение: {emotion_name}"
            elif isinstance(current_emotion, str):
                description += f"\nТекущее настроение: {current_emotion}"
                
        return description
    
    def _store_conversation_in_db(self, character_id: str, system_prompt: str, char_description: str, db_session: Session) -> None:
        """Store conversation initialization in the database."""
        try:
            # Import from the specific module instead of core.models to avoid circular imports
            from core.db.models.chat_history import ChatHistory
            from uuid import UUID
            
            # Parse the character_id
            try:
                char_uuid = UUID(character_id)
            except ValueError:
                logger.warning(f"Invalid character_id UUID: {character_id}")
                char_uuid = uuid4()
            
            # Find the user_id from any existing messages
            user_id = None
            try:
                from core.models import Message
                latest_message = db_session.query(Message).filter(
                    (Message.sender_id == char_uuid) | (Message.recipient_id == char_uuid)
                ).order_by(Message.created_at.desc()).first()
                
                if latest_message:
                    if latest_message.sender_id == char_uuid:
                        user_id = latest_message.recipient_id
                    else:
                        user_id = latest_message.sender_id
            except Exception as e:
                logger.error(f"Error retrieving user_id: {e}")
                
            # If no user_id, use a placeholder
            if not user_id:
                # Try to find a user
                try:
                    from core.models import User
                    user = db_session.query(User).first()
                    if user:
                        user_id = user.user_id
                    else:
                        user_id = uuid4()  # Generate a placeholder
                except Exception as e:
                    logger.error(f"Error finding a user: {e}")
                    user_id = uuid4()
            
            # Remove existing system messages for this character-user pair
            db_session.query(ChatHistory).filter(
                ChatHistory.character_id == char_uuid,
                ChatHistory.user_id == user_id,
                ChatHistory.role == "system"
            ).delete()
            
            # Get next position
            max_position = db_session.query(func.max(ChatHistory.position)).filter(
                ChatHistory.character_id == char_uuid,
                ChatHistory.user_id == user_id
            ).scalar() or 0
            
            # Store system prompt
            system_prompt_entry = ChatHistory(
                id=uuid4(),
                character_id=char_uuid,
                user_id=user_id,
                role="system",
                content=system_prompt,
                position=max_position + 1,
                is_active=True,
                created_at=datetime.datetime.now()
            )
            db_session.add(system_prompt_entry)
            
            # Store character description
            char_desc_entry = ChatHistory(
                id=uuid4(),
                character_id=char_uuid,
                user_id=user_id,
                role="system",
                content=char_description,
                position=max_position + 2,
                is_active=True,
                created_at=datetime.datetime.now()
            )
            db_session.add(char_desc_entry)
            
            db_session.commit()
            logger.info(f"Stored system messages in database for character {character_id}")
            
        except Exception as e:
            logger.exception(f"Error storing conversation in database: {e}")
            db_session.rollback()
    
    def add_message(self, character_id: str, role: str, content: str, 
                   metadata: Optional[Dict[str, Any]] = None, db_session=None) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            character_id: Character identifier
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata (like emotion, timestamp, etc.)
            db_session: Database session for storing in DB (optional)
        """
        if character_id not in self.conversations:
            logger.warning(f"Adding message to non-existing conversation for character {character_id}. Starting new conversation.")
            # Create empty conversation if it doesn't exist
            self.conversations[character_id] = []
        
        # Create message with optional metadata
        message = {"role": role, "content": content}
        if metadata:
            message["metadata"] = metadata
        
        # Add the message to the conversation
        self.conversations[character_id].append(message)
        
        # Add to the database if session provided
        if db_session and role != "system":
            self._store_message_in_db(character_id, role, content, metadata, db_session)
        
        # Trim history if needed
        self._trim_conversation(character_id)
        
        logger.debug(f"Added {role} message to conversation {character_id}: {content[:50]}...")
    
    def _trim_conversation(self, character_id: str) -> None:
        """
        Trim conversation history to the maximum allowed length.
        
        Args:
            character_id: Character identifier
        """
        if character_id not in self.conversations:
            return
            
        conversation = self.conversations[character_id]
        
        # Extract system messages (we always want to keep these)
        system_messages = [msg for msg in conversation if msg["role"] == "system"]
        non_system_messages = [msg for msg in conversation if msg["role"] != "system"]
        
        # If we're under the limit, no need to trim
        if len(non_system_messages) <= self.max_history_length:
            return
            
        # Keep only the most recent non-system messages
        kept_non_system = non_system_messages[-self.max_history_length:]
        
        # Reconstruct the conversation with system messages first, followed by kept non-system messages
        self.conversations[character_id] = system_messages + kept_non_system
        
        logger.info(f"Trimmed conversation for character {character_id} to {len(self.conversations[character_id])} messages " 
                   f"({len(system_messages)} system + {len(kept_non_system)} non-system)")
    
    def _store_message_in_db(self, character_id: str, role: str, content: str, 
                            metadata: Optional[Dict[str, Any]], db_session: Session) -> None:
        """Store a message in the database."""
        try:
            from core.models import Message
            # Import ChatHistory directly from its module
            from core.db.models.chat_history import ChatHistory
            from uuid import UUID
            
            # Get character_id as UUID
            try:
                char_uuid = UUID(character_id)
            except ValueError:
                logger.warning(f"Invalid character_id UUID: {character_id}")
                char_uuid = uuid4()
            
            # Find the user_id from recent messages
            user_id = None
            try:
                latest_message = db_session.query(Message).filter(
                    (Message.sender_id == char_uuid) | (Message.recipient_id == char_uuid)
                ).order_by(Message.created_at.desc()).first()
                
                if latest_message:
                    if latest_message.sender_id == char_uuid:
                        user_id = latest_message.recipient_id
                    else:
                        user_id = latest_message.sender_id
            except Exception as e:
                logger.error(f"Error retrieving user_id: {e}")
            
            # If no user_id found, use a placeholder
            if not user_id:
                try:
                    from core.models import User
                    user = db_session.query(User).first()
                    if user:
                        user_id = user.user_id
                    else:
                        user_id = uuid4()
                except Exception as e:
                    logger.error(f"Error finding a user: {e}")
                    user_id = uuid4()
            
            # Get next position
            max_position = db_session.query(func.max(ChatHistory.position)).filter(
                ChatHistory.character_id == char_uuid,
                ChatHistory.user_id == user_id
            ).scalar() or 0
            
            # Convert metadata to JSON string if provided
            metadata_str = json.dumps(metadata) if metadata else None
            
            # Add message to chat_history
            chat_history_entry = ChatHistory(
                id=uuid4(),
                character_id=char_uuid,
                user_id=user_id,
                role=role,
                content=content,
                message_metadata=metadata_str,  # Updated column name
                position=max_position + 1,
                is_active=True,
                created_at=datetime.datetime.now()
            )
            db_session.add(chat_history_entry)
            db_session.commit()
            logger.info(f"Stored {role} message in database for character {character_id}")
            
        except Exception as e:
            logger.exception(f"Error storing message in database: {e}")
            db_session.rollback()
    
    def get_messages(self, character_id: str, include_system: bool = True, db_session=None) -> List[Dict[str, Any]]:
        """
        Get all messages for a character conversation.
        
        Args:
            character_id: Character identifier
            include_system: Whether to include system messages
            db_session: Database session for retrieving from DB (optional)
            
        Returns:
            List of messages
        """
        # If db_session is provided, try to get from database first
        if db_session:
            db_messages = self._get_messages_from_db(character_id, include_system, db_session)
            if db_messages:
                return db_messages
        
        # Fall back to in-memory cache if database retrieval failed or not available
        if character_id not in self.conversations:
            logger.warning(f"Attempted to get messages for non-existing conversation: {character_id}")
            return []
        
        if include_system:
            return self.conversations[character_id]
        else:
            # Filter out system messages
            return [msg for msg in self.conversations[character_id] if msg["role"] != "system"]
    
    def _get_messages_from_db(self, character_id: str, include_system: bool, db_session: Session) -> List[Dict[str, Any]]:
        """Retrieve messages from the database."""
        try:
            # Import ChatHistory directly from its module
            from core.db.models.chat_history import ChatHistory
            from uuid import UUID
            
            # Get character_id as UUID
            try:
                char_uuid = UUID(character_id)
            except ValueError:
                logger.warning(f"Invalid character_id UUID: {character_id}")
                return []
            
            # Build query
            query = db_session.query(ChatHistory).filter(
                ChatHistory.character_id == char_uuid,
                ChatHistory.is_active == True
            )
            
            if not include_system:
                query = query.filter(ChatHistory.role != "system")
            
            # Get messages in order
            chat_history = query.order_by(ChatHistory.position).all()
            
            # Format the results
            messages = []
            for entry in chat_history:
                message = {
                    "role": entry.role,
                    "content": entry.content
                }
                
                # Parse metadata if available
                if entry.message_metadata:  # Updated column name
                    try:
                        metadata = json.loads(entry.message_metadata)
                        message["metadata"] = metadata
                        
                        # Add special handling for gift events to enhance context
                        if "gift_event" in metadata:
                            gift_data = metadata["gift_event"]
                            # Slightly modify the content to better integrate gift information
                            if entry.role == "system":
                                message["content"] = f"💝 GIFT EVENT: User sent {gift_data.get('gift_name')} to the character. This should influence the conversation."
                    except json.JSONDecodeError:
                        pass
                    
                messages.append(message)
            
            logger.info(f"Retrieved {len(messages)} messages from database for character {character_id}")
            
            # Fetch gift events for additional context
            try:
                from core.models import Event
                gifts_event = db_session.query(Event).filter(
                    Event.character_id == char_uuid,
                    Event.event_type == 'gifts'
                ).first()
                
                if gifts_event and gifts_event.data:
                    try:
                        gifts_data = json.loads(gifts_event.data)
                        if isinstance(gifts_data, list) and gifts_data:
                            # Add a system prompt about gifts
                            gift_names = [g.get('gift_name', 'подарок') for g in gifts_data if 'gift_name' in g]
                            if gift_names:
                                gift_names_str = ", ".join(gift_names)
                                gift_message = {
                                    "role": "system",
                                    "content": f"Пользователь дарил тебе следующие подарки: {gift_names_str}. " +
                                              f"Это показывает его внимание и заботу. При подходящем моменте, " +
                                              f"ты можешь упомянуть об этих подарках и выразить свою благодарность."
                                }
                                # Add this as the last system message
                                system_messages = [m for m in messages if m["role"] == "system"]
                                other_messages = [m for m in messages if m["role"] != "system"]
                                messages = system_messages + [gift_message] + other_messages
                    except Exception as json_error:
                        logger.error(f"Error parsing gifts data: {json_error}")
            except Exception as e:
                logger.error(f"Error fetching gift context: {e}")
            
            return messages
                
        except Exception as e:
            logger.exception(f"Error retrieving messages from database: {e}")
            return []
    
    def import_history(self, character_id: str, message_history: List[Dict[str, Any]],
                     character_info: Dict[str, Any], system_prompt: Optional[str] = None,
                     db_session=None) -> None:
        """
        Import existing message history into a conversation.
        
        Args:
            character_id: Character identifier
            message_history: List of message dictionaries
            character_info: Dictionary with character metadata
            system_prompt: Optional system prompt (if not provided, uses default)
            db_session: Database session for storing in DB (optional)
        """
        # Get system prompt
        if not system_prompt and character_id in self.system_prompts:
            system_prompt = self.system_prompts[character_id]
        elif not system_prompt:
            logger.warning(f"No system prompt provided for conversation {character_id}. Using empty.")
            system_prompt = ""
        
        # Start fresh conversation
        self.start_conversation(character_id, system_prompt, character_info, db_session)
        
        # Add historical messages
        for msg in message_history:
            sender_type = msg.get("sender_type", "user")
            role = "user" if sender_type == "user" else "assistant"
            content = msg.get("content", "")
            emotion = msg.get("emotion", "neutral")
            
            self.add_message(
                character_id=character_id,
                role=role,
                content=content,
                metadata={"emotion": emotion},
                db_session=db_session
            )
        
        logger.info(f"Imported {len(message_history)} messages into conversation {character_id}")
    
    def clear_conversation(self, character_id: str, db_session=None) -> bool:
        """
        Clear conversation history for a character.
        
        Args:
            character_id: Character identifier
            db_session: Database session for updating DB (optional)
            
        Returns:
            Whether the conversation was cleared successfully
        """
        # Clear in-memory data
        if character_id in self.conversations:
            logger.info(f"Clearing conversation for character {character_id}")
            
            # Store system prompt temporarily if it exists
            system_prompt = None
            if character_id in self.system_prompts:
                system_prompt = self.system_prompts[character_id]
            
            # Remove the conversation
            del self.conversations[character_id]
            
            # Remove the system prompt
            if character_id in self.system_prompts:
                del self.system_prompts[character_id]
                
            # Clear in database if session provided
            if db_session:
                self._clear_conversation_in_db(character_id, db_session)
                
            return True
        else:
            logger.warning(f"Attempted to clear non-existing conversation: {character_id}")
            
            # Still try to clear database if session provided
            if db_session:
                self._clear_conversation_in_db(character_id, db_session)
                return True
                
            return False
    
    def _clear_conversation_in_db(self, character_id: str, db_session: Session) -> None:
        """Clear the conversation in the database."""
        try:
            from core.models import ChatHistory
            from uuid import UUID
            
            # Convert character_id to UUID
            try:
                char_uuid = UUID(character_id)
            except ValueError:
                logger.warning(f"Invalid character_id UUID: {character_id}")
                return
            
            # Soft delete by setting is_active to False
            db_session.query(ChatHistory).filter(
                ChatHistory.character_id == char_uuid,
                ChatHistory.is_active == True
            ).update({"is_active": False})
            
            db_session.commit()
            logger.info(f"Cleared conversation in database for character {character_id}")
            
        except Exception as e:
            logger.exception(f"Error clearing conversation in database: {e}")
            db_session.rollback()
    
    def compress_conversation_in_db(self, character_id: str, summary_text: str, user_id=None, db_session: Session = None) -> bool:
        """
        Save the compressed conversation summary to the chat_history table.
        
        Args:
            character_id: Character identifier
            summary_text: Summary of the compressed conversation
            user_id: User identifier (optional - will be looked up if not provided)
            db_session: Database session
            
        Returns:
            Whether the compression was successful
        """
        try:
            from core.db.models.chat_history import ChatHistory
            from uuid import UUID
            
            logger.info(f"Starting conversation compression in database for character {character_id}")
            
            # Convert character_id to UUID
            try:
                char_uuid = UUID(character_id)
            except ValueError:
                logger.warning(f"Invalid character_id UUID: {character_id}")
                return False
            
            # If user_id is not provided, find a user who's communicated with this character
            if not user_id:
                try:
                    from core.models import Message
                    
                    logger.info("No user_id provided, looking up from messages")
                    # Look for a user in messages
                    user_message = db_session.query(Message).filter(
                        (Message.recipient_id == char_uuid) & (Message.sender_type == "user")
                    ).order_by(Message.created_at.desc()).first()
                    
                    if user_message:
                        user_id = user_message.sender_id
                        logger.info(f"Found user_id {user_id} from recipient messages")
                    else:
                        # Try looking in the other direction
                        user_message = db_session.query(Message).filter(
                            (Message.sender_id == char_uuid) & (Message.recipient_type == "user")
                        ).order_by(Message.created_at.desc()).first()
                        
                        if user_message:
                            user_id = user_message.recipient_id
                            logger.info(f"Found user_id {user_id} from sender messages")
                except Exception as e:
                    logger.error(f"Error finding user_id: {e}")
                    
                # If still no user_id, try to find any user
                if not user_id:
                    try:
                        from core.models import User
                        logger.info("Still no user_id, looking for any user")
                        user = db_session.query(User).first()
                        if user:
                            user_id = user.user_id
                            logger.info(f"Using first available user: {user_id}")
                        else:
                            user_id = uuid4()  # Generate a placeholder
                            logger.warning(f"No users found, generating placeholder user_id: {user_id}")
                    except Exception as e:
                        logger.error(f"Error finding a user: {e}")
                        user_id = uuid4()
                        logger.warning(f"Exception finding user, generating placeholder user_id: {user_id}")
            
            # Convert user_id to UUID if it's a string
            if isinstance(user_id, str):
                try:
                    user_id = UUID(user_id)
                    logger.info(f"Converted user_id string to UUID: {user_id}")
                except ValueError:
                    logger.warning(f"Invalid user_id UUID string: {user_id}, generating new one")
                    user_id = uuid4()
            
            logger.info(f"Using character_id={char_uuid}, user_id={user_id}")
            
            # Clear previous compressed summaries in chat_history for this character-user pair
            try:
                query = db_session.query(ChatHistory).filter(
                    ChatHistory.character_id == char_uuid,
                    ChatHistory.user_id == user_id,
                    ChatHistory.is_active == True,
                    ChatHistory.compressed == True
                )
                count = query.count()
                if count > 0:
                    logger.info(f"Deactivating {count} existing compressed messages")
                    query.update({"is_active": False})
                    db_session.flush()
                else:
                    logger.info("No existing compressed messages to deactivate")
            except Exception as e:
                logger.error(f"Error clearing previous compressed histories: {e}")
                # Continue anyway to try to save the new summary
            
            # Get the max position for this character-user pair
            try:
                max_position = db_session.query(func.max(ChatHistory.position)).filter(
                    ChatHistory.character_id == char_uuid,
                    ChatHistory.user_id == user_id
                ).scalar() or 0
                logger.info(f"Current max position: {max_position}")
            except Exception as e:
                logger.error(f"Error getting max position: {e}")
                max_position = 0
            
            # Create the summary entry
            try:
                summary_id = uuid4()
                summary_message = ChatHistory(
                    id=summary_id,
                    character_id=char_uuid,
                    user_id=user_id,
                    role="system",
                    content=f"## Сжатая история предыдущего диалога:\n\n{summary_text}",
                    position=max_position + 1,
                    is_active=True,
                    compressed=True,
                    created_at=datetime.datetime.now()
                )
                db_session.add(summary_message)
                logger.info(f"Added compressed message with ID {summary_id} at position {max_position + 1}")
                
                db_session.commit()
                logger.info(f"Successfully compressed conversation in database for character {character_id}")
                return True
            except Exception as e:
                logger.exception(f"Error creating compression entry: {e}")
                db_session.rollback()
                return False
                
        except Exception as e:
            logger.exception(f"Error compressing conversation in database: {e}")
            if db_session:
                try:
                    db_session.rollback()
                except:
                    pass
            return False
    
    def save_conversation_to_database(self, character_id: str, db_session: Session) -> bool:
        """
        Save the entire conversation to the chat_history database table.
        
        Args:
            character_id: Character identifier
            db_session: Database session for accessing the database
            
        Returns:
            Whether the save operation was successful
        """
        try:
            from core.db.models.chat_history import ChatHistory
            from uuid import UUID
            
            # Get conversation messages
            if character_id not in self.conversations:
                logger.warning(f"No conversation found for character {character_id}")
                return False
                
            messages = self.conversations[character_id]
            if not messages:
                logger.warning(f"Conversation for character {character_id} is empty")
                return False
                
            # Convert character_id to UUID
            try:
                char_uuid = UUID(character_id)
            except ValueError:
                logger.warning(f"Invalid character_id UUID: {character_id}")
                char_uuid = uuid4()
                
            # Find user_id from messages table
            user_id = None
            try:
                from core.models import Message
                latest_message = db_session.query(Message).filter(
                    (Message.sender_id == char_uuid) | (Message.recipient_id == char_uuid)
                ).order_by(Message.created_at.desc()).first()
                
                if latest_message:
                    if latest_message.sender_id == char_uuid:
                        user_id = latest_message.recipient_id
                    else:
                        user_id = latest_message.sender_id
            except Exception as e:
                logger.error(f"Error retrieving user_id: {e}")
                
            # If no user_id, try to find any user
            if not user_id:
                try:
                    from core.models import User
                    user = db_session.query(User).first()
                    if user:
                        user_id = user.user_id
                    else:
                        user_id = uuid4()  # Generate a placeholder
                except Exception as e:
                    logger.error(f"Error finding a user: {e}")
                    user_id = uuid4()
            
            # Clear previous chat history
            db_session.query(ChatHistory).filter(
                ChatHistory.character_id == char_uuid,
                ChatHistory.user_id == user_id,
                ChatHistory.is_active == True
            ).update({"is_active": False})
            
            # Insert new messages
            for position, msg in enumerate(messages, 1):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if not content:
                    continue
                    
                # Convert metadata to JSON string if it exists
                metadata_str = None
                if "metadata" in msg and isinstance(msg["metadata"], dict):
                    metadata_str = json.dumps(msg["metadata"])
                    
                # Create new chat history entry
                chat_history_entry = ChatHistory(
                    id=uuid4(),
                    character_id=char_uuid,
                    user_id=user_id,
                    role=role,
                    content=content,
                    message_metadata=metadata_str,
                    position=position,
                    is_active=True,
                    created_at=datetime.datetime.now()
                )
                db_session.add(chat_history_entry)
                
            db_session.commit()
            logger.info(f"Successfully saved conversation to database for character {character_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Error saving conversation to database: {e}")
            db_session.rollback()
            return False

    def save_message_to_database(self, message_data, db_session=None):
        """Save a message to the database using the safer approach"""
        close_session = False
        if not db_session:
            from core.db.session import get_session
            db_session = get_session()
            close_session = True
            
        try:
            # Use the safe helper function
            success = save_message_safely(db_session, message_data)
            if success:
                self.logger.info("✅ Message saved to database")
            else:
                self.logger.warning("⚠️ Failed to save message")
            return success
        except Exception as e:
            self.logger.error(f"❌ Error in save_message_to_database: {e}")
            return False
        finally:
            if close_session and db_session:
                db_session.close()

    def get_user_id_from_recent_messages(self, character_id, db_session=None):
        """Get the user ID from recent messages using the safer approach"""
        close_session = False
        if not db_session:
            from core.db.session import get_session
            db_session = get_session()
            close_session = True
            
        try:
            # Use the safe helper function with proper ID conversion
            character_id_str = ensure_string_id(character_id)
            messages = find_message_by_id_safely(db_session, sender_id=character_id_str, limit=1)
            
            if messages and len(messages) > 0:
                msg = messages[0]
                return msg['recipient_id'] if msg['recipient_type'] == 'user' else None
                
            # Try as recipient
            messages = find_message_by_id_safely(db_session, recipient_id=character_id_str, limit=1)
            if messages and len(messages) > 0:
                msg = messages[0]
                return msg['sender_id'] if msg['sender_type'] == 'user' else None
                
            return None
        except Exception as e:
            self.logger.error(f"❌ Error getting user ID from messages: {e}")
            return None
        finally:
            if close_session and db_session:
                db_session.close()

    def get_user_id_from_recent_messages(self, character_id, db_session=None):
        """Get the user ID from recent messages using the safer approach"""
        close_session = False
        if not db_session:
            from core.db.session import get_session
            db_session = get_session()
            close_session = True
            
        try:
            # Convert character_id to string for safe comparison
            character_id_str = ensure_string_id(character_id)
            
            # Use explicit text casting for PostgreSQL compatibility
            if 'postgresql' in str(db_session.bind.url).lower():
                # First, check as sender
                query = text("""
                    SELECT recipient_id, recipient_type 
                    FROM messages 
                    WHERE sender_id::text = :character_id AND sender_type = 'character' 
                    ORDER BY created_at DESC LIMIT 1
                """)
                
                result = db_session.execute(query, {"character_id": character_id_str})
                row = result.fetchone()
                
                if row and row.recipient_type == 'user':
                    return row.recipient_id
                    
                # Then check as recipient
                query = text("""
                    SELECT sender_id, sender_type 
                    FROM messages 
                    WHERE recipient_id::text = :character_id AND recipient_type = 'character' 
                    ORDER BY created_at DESC LIMIT 1
                """)
                
                result = db_session.execute(query, {"character_id": character_id_str})
                row = result.fetchone()
                
                if row and row.sender_type == 'user':
                    return row.sender_id
            else:
                # For SQLite
                # First, check as sender
                query = text("""
                    SELECT recipient_id, recipient_type 
                    FROM messages 
                    WHERE sender_id = :character_id AND sender_type = 'character' 
                    ORDER BY created_at DESC LIMIT 1
                """)
                
                result = db_session.execute(query, {"character_id": character_id_str})
                row = result.fetchone()
                
                if row and row.recipient_type == 'user':
                    return row.recipient_id
                    
                # Then check as recipient
                query = text("""
                    SELECT sender_id, sender_type 
                    FROM messages 
                    WHERE recipient_id = :character_id AND recipient_type = 'character' 
                    ORDER BY created_at DESC LIMIT 1
                """)
                
                result = db_session.execute(query, {"character_id": character_id_str})
                row = result.fetchone()
                
                if row and row.sender_type == 'user':
                    return row.sender_id
                    
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving user_id: {e}")
            # Reset the transaction if it failed
            reset_failed_transaction(db_session)
            return None
        finally:
            if close_session and db_session:
                db_session.close()

    def save_conversation_to_database(self, character_id, user_id, messages=None, db_session=None):
        """
        Save conversation with proper transaction handling and error recovery
        
        Args:
            character_id: ID of the character
            user_id: ID of the user
            messages: Optional list of messages to store (default None)
            db_session: Optional SQLAlchemy session (default None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        close_session = False
        if not db_session:
            # Import directly to avoid circular imports
            try:
                from core.db.session import get_db_session
                db_session = get_db_session()
                close_session = True
            except ImportError:
                self.logger.error("Error importing get_db_session")
                try:
                    from core.db.session import get_session
                    db_session = get_session()
                    close_session = True
                    self.logger.info("Using fallback get_session()")
                except ImportError:
                    self.logger.error("Could not import database session")
                    return False
        
        try:
            # Reset any failed transaction before starting
            try:
                db_session.rollback()
                self.logger.debug("Rolled back any existing transaction")
            except:
                pass
            
            # Use string IDs for safer comparisons
            character_id_str = ensure_string_id(character_id)
            user_id_str = ensure_string_id(user_id)
            
            # Use our execute_safe_uuid_query to handle PostgreSQL UUID casting properly
            if hasattr(db_session, 'bind') and 'postgresql' in str(db_session.bind.url).lower():
                # For PostgreSQL, use explicit type casting in the query
                query = """
                    UPDATE chat_history 
                    SET is_active = FALSE, updated_at = NOW() 
                    WHERE character_id::text = :character_id 
                    AND user_id::text = :user_id 
                    AND is_active = TRUE
                """
            else:
                # For other databases like SQLite
                query = """
                    UPDATE chat_history 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP 
                    WHERE character_id = :character_id 
                    AND user_id = :user_id 
                    AND is_active = TRUE
                """
            
            # Execute the query using safe query execution
            execute_safe_uuid_query(db_session, query, {
                "character_id": character_id_str,
                "user_id": user_id_str
            })
            
            # Create a new conversation entry using ORM
            try:
                from core.db.models.chat_history import ChatHistory
                conversation = ChatHistory(
                    character_id=character_id,
                    user_id=user_id,
                    is_active=True
                )
                db_session.add(conversation)
                db_session.commit()
                self.logger.info("✅ Conversation saved to database successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error adding conversation: {e}")
                try:
                    db_session.rollback()
                except:
                    pass
                return False
        except Exception as e:
            self.logger.error(f"Error saving conversation to database: {e}")
            try:
                db_session.rollback()
            except:
                pass
            return False
        finally:
            if close_session and db_session:
                try:
                    db_session.close()
                except:
                    pass

    def _reset_failed_transaction(self, db_session):
        """Reset a database session that's in a failed transaction state"""
        try:
            # Close the current session
            db_session.close()
            
            # For PostgreSQL, create a new connection and execute a rollback
            if hasattr(db_session, 'bind') and 'postgresql' in str(db_session.bind.url).lower():
                with db_session.bind.connect() as conn:
                    conn.execute(text("ROLLBACK"))
                    self.logger.info("Successfully reset PostgreSQL transaction")
                    
            return True
        except Exception as e:
            self.logger.error(f"Error resetting transaction: {e}")
            return False

    def ensure_string_id(self, id_value):
        """Convert UUID or other ID types to string format"""
        if hasattr(id_value, 'hex'):  # Check if it's a UUID
            return str(id_value)
        return str(id_value) if id_value is not None else None

    def save_conversation_to_database(self, character_id, user_id, messages=None, db_session=None):
        """
        Save conversation with proper transaction handling and error recovery
        
        Args:
            character_id: ID of the character
            user_id: ID of the user
            messages: Optional list of messages to store (default None)
            db_session: Optional SQLAlchemy session (default None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        close_session = False
        if not db_session:
            # Import directly to avoid circular imports
            try:
                from core.db.session import get_db_session
                db_session = get_db_session()
                close_session = True
            except ImportError:
                self.logger.error("Error importing get_db_session")
                try:
                    from core.db.session import get_session
                    db_session = get_session()
                    close_session = True
                    self.logger.info("Using fallback get_session()")
                except ImportError:
                    self.logger.error("Could not import database session")
                    return False
        
        try:
            # Reset any failed transaction before starting
            try:
                db_session.rollback()
                self.logger.debug("Rolled back any existing transaction")
            except:
                pass
            
            # Ensure we're not passing None or a Session object as user_id
            if user_id is None or isinstance(user_id, type(db_session)):
                self.logger.error(f"Invalid user_id type: {type(user_id).__name__}")
                return False
                
            # Check if we're using PostgreSQL
            is_postgresql = hasattr(db_session, 'bind') and 'postgresql' in str(db_session.bind.url).lower()
            
            # For PostgreSQL, handle IDs in a special way
            if is_postgresql:
                # First check if the user_id is a numeric Telegram ID
                try:
                    # Try to convert to UUID to see if it's already a valid UUID
                    from uuid import UUID
                    UUID(str(user_id))
                    # If it succeeded, use the string representation directly
                    user_id_str = str(user_id)
                except ValueError:
                    # If not a valid UUID, create a UUID v5 using namespace and the ID as name
                    self.logger.info(f"Converting non-UUID user_id {user_id} to UUID")
                    import uuid
                    # Use a namespace UUID to ensure consistent generation
                    NAMESPACE_USER_ID = UUID('c7e7f1d0-5a5d-5a5e-a2b0-914b8c42a3d7')
                    # Generate a UUID v5 from the user ID
                    user_id_uuid = uuid.uuid5(NAMESPACE_USER_ID, str(user_id))
                    user_id_str = str(user_id_uuid)
                    self.logger.info(f"Converted user_id {user_id} to UUID {user_id_str}")
            else:
                # For non-PostgreSQL, just use string conversion
                user_id_str = str(user_id)
                
            # Convert character_id to string
            character_id_str = str(character_id)
            
            # Log for debugging
            self.logger.debug(f"Saving conversation with character_id={character_id_str}, user_id={user_id_str}")
            
            # Mark previous conversation as inactive using raw SQL with type casting
            if is_postgresql:
                # PostgreSQL with explicit type casting
                query = """
                    UPDATE chat_history 
                    SET is_active = FALSE, updated_at = NOW() 
                    WHERE character_id::text = :character_id 
                    AND user_id::text = :user_id 
                    AND is_active = TRUE
                """
            else:
                # SQLite or other database
                query = """
                    UPDATE chat_history 
                    SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP 
                    WHERE character_id = :character_id 
                    AND user_id = :user_id 
                    AND is_active = TRUE
                """
                
            db_session.execute(text(query), {
                "character_id": character_id_str,
                "user_id": user_id_str
            })
            
            # Create a new conversation entry
            try:
                # If PostgreSQL, use raw SQL to avoid ORM UUID validation
                if is_postgresql:
                    from uuid import uuid4
                    
                    # First check the schema of the chat_history table
                    table_info = db_session.execute(text("""
                        SELECT column_name, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = 'chat_history'
                        ORDER BY ordinal_position
                    """)).fetchall()
                    
                    # Build column list and values based on the actual schema
                    columns = []
                    values = {}
                    placeholders = []
                    
                    # Required default values for all records
                    values["id"] = str(uuid4())
                    values["character_id"] = character_id_str
                    values["user_id"] = user_id_str
                    values["is_active"] = True
                    values["compressed"] = False
                    
                    # Check what columns exist and which ones are required
                    for col_info in table_info:
                        col_name = col_info[0]
                        is_nullable = col_info[1].upper() == 'YES'
                        
                        # Skip columns that have default values in the database
                        if col_name in ('created_at', 'updated_at'):
                            continue
                            
                        # Include all required columns we have values for
                        if col_name in values:
                            columns.append(col_name)
                            placeholders.append(f":{col_name}")
                        # For required columns we don't have values for, provide defaults
                        elif not is_nullable and col_name not in values:
                            columns.append(col_name)
                            placeholders.append(f":{col_name}")
                            
                            # Provide sensible defaults based on column name
                            if col_name == 'role':
                                values[col_name] = 'system'  # Default role
                            elif col_name == 'content':
                                values[col_name] = ''  # Empty content
                            elif col_name == 'message_metadata':
                                values[col_name] = '{}'  # Empty JSON
                            elif col_name == 'position':
                                values[col_name] = 0  # First position
                            else:
                                # For any other required columns, use empty string
                                values[col_name] = ''
                    
                    # Add created_at column if it exists
                    if 'created_at' in [col[0] for col in table_info]:
                        columns.append('created_at')
                        placeholders.append('NOW()')
                    
                    # Create a SQL query to insert directly
                    column_list = ", ".join(columns)
                    placeholder_list = ", ".join(placeholders)
                    
                    query = f"""
                        INSERT INTO chat_history 
                        ({column_list}) 
                        VALUES 
                        ({placeholder_list})
                    """
                    
                    # Execute the SQL directly with parameters
                    db_session.execute(text(query), values)
                    
                    db_session.commit()
                    self.logger.info("✅ Conversation saved to database successfully (SQL method)")
                    return True
                else:
                    # For other databases, use ORM with all required fields
                    from core.db.models.chat_history import ChatHistory
                    from uuid import uuid4
                    
                    # Get the model's required fields
                    conversation = ChatHistory(
                        id=str(uuid4()),
                        character_id=character_id_str,
                        user_id=user_id_str,
                        role='system',  # Provide a default role
                        content='',     # Empty content
                        message_metadata='{}',  # Empty JSON
                        position=0,     # First position
                        is_active=True,
                        compressed=False
                    )
                    
                    db_session.add(conversation)
                    db_session.commit()
                    self.logger.info("✅ Conversation saved to database successfully (ORM method)")
                    return True
            except Exception as e:
                self.logger.error(f"Error adding conversation: {e}")
                try:
                    db_session.rollback()
                except:
                    pass
                return False
        except Exception as e:
            self.logger.error(f"Error saving conversation to database: {e}")
            try:
                db_session.rollback()
            except:
                pass
            return False
        finally:
            if close_session and db_session:
                try:
                    db_session.close()
                except:
                    pass

# ...existing code...
