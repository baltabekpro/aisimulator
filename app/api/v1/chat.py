from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form, Path, Body, Header
from pydantic import UUID4
from sqlalchemy.orm import Session
from sqlalchemy import func, text  # Add this import for the func reference
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import logging
import random
import json
import os

from app.db.session import get_db
from app.auth.jwt import get_current_user, get_current_user_optional
from app.schemas.chat import CharacterResponse, ConversationResponse, UserMessage, MessageResponse
from app.schemas.memory import MemorySchema
from core.services.message import MessageService
from core.services.ai_partner import AIPartnerService
from core.services.user import UserService
from core.services.gift import GiftService
from core.models import User, AIPartner, Message

from core.ai.gemini import GeminiAI

logger = logging.getLogger(__name__)

router = APIRouter()

ai_client = GeminiAI()

def safe_set_attributes(obj, data_dict):
    """
    Safely copy attributes from a dictionary to an object.
    Only sets attributes that already exist on the object.
    """
    allowed_attrs = vars(obj).keys()
    for key, value in data_dict.items():
        if key in allowed_attrs or hasattr(obj, key):
            setattr(obj, key, value)
    
    # Always ensure partner_id is set (it may be used in queries)
    if hasattr(obj, 'id') and hasattr(obj, 'partner_id'):
        obj.partner_id = obj.id
    return obj

@router.get("/characters", response_model=List[Dict[str, Any]])
async def get_characters(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> List[Dict[str, Any]]:
    """
    Get a list of available AI characters
    """
    # Enhanced debugging for database inspection
    logger.info("Fetching AI characters from database")
    
    try:
        # First, check what tables exist in the database
        from sqlalchemy import inspect, text
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        logger.info(f"Available tables in database: {tables}")
        
        # Try to get characters from both potential tables
        result = []
        
        # First try the characters table since admin panel seems to be using it
        if 'characters' in tables:
            logger.info("Checking characters table")
            try:
                # Check columns in the characters table
                columns = [col['name'] for col in inspector.get_columns('characters')]
                logger.info(f"Columns in characters table: {columns}")
                
                # Try direct SQL query to count records
                count = db.execute(text("SELECT COUNT(*) FROM characters")).scalar()
                logger.info(f"Count of records in characters table: {count}")
                
                if count > 0:
                    # Get character records from characters table
                    char_rows = db.execute(text("SELECT * FROM characters")).fetchall()
                    logger.info(f"Found {len(char_rows)} records in characters table")
                    
                    for row in char_rows:
                        row_dict = dict(row)
                        logger.info(f"Character record: {row_dict}")
                        
                        # Create a dictionary with fields from the characters table
                        char_dict = {
                            "id": str(row_dict.get('id')),
                            "name": row_dict.get('name', 'Unknown'),
                            "age": row_dict.get('age'),
                            "gender": row_dict.get('gender', 'female'),
                            "personality_traits": [],
                            "interests": [],
                            "background": row_dict.get('background', ''),
                            "avatar_url": row_dict.get('avatar_url'),
                            "current_emotion": {
                                "name": row_dict.get('current_emotion', 'neutral'),
                                "intensity": 0.5,
                            }
                        }
                        
                        # Try to parse personality and interests
                        try:
                            personality = row_dict.get('personality')
                            if personality:
                                if isinstance(personality, str):
                                    import json
                                    try:
                                        char_dict["personality_traits"] = json.loads(personality)
                                    except json.JSONDecodeError:
                                        char_dict["personality_traits"] = [personality]
                        except Exception as e:
                            logger.error(f"Error parsing personality: {e}")
                            
                        try:
                            interests = row_dict.get('interests')
                            if interests:
                                if isinstance(interests, str):
                                    import json
                                    try:
                                        char_dict["interests"] = json.loads(interests)
                                    except json.JSONDecodeError:
                                        char_dict["interests"] = [interests]
                        except Exception as e:
                            logger.error(f"Error parsing interests: {e}")
                        
                        result.append(char_dict)
            except Exception as e:
                logger.error(f"Error retrieving from characters table: {e}")
        
        # If no characters found, then try ai_partners table as a fallback
        if not result and 'ai_partners' in tables:
            logger.info("Checking ai_partners table")
            try:
                # Check columns in the ai_partners table
                columns = [col['name'] for col in inspector.get_columns('ai_partners')]
                logger.info(f"Columns in ai_partners table: {columns}")
                
                # Try direct SQL query to count records
                count = db.execute(text("SELECT COUNT(*) FROM ai_partners")).scalar()
                logger.info(f"Count of records in ai_partners table: {count}")
                
                if count > 0:
                    # Get character records from ai_partners table
                    char_rows = db.execute(text("SELECT * FROM ai_partners")).fetchall()
                    logger.info(f"Found {len(char_rows)} records in ai_partners table")
                    
                    for row in char_rows:
                        row_dict = dict(row)
                        logger.info(f"Character record: {row_dict}")
                        
                        # Create a dictionary with fields from the ai_partners table
                        char_dict = {
                            "id": str(row_dict.get('id')),
                            "name": row_dict.get('name', 'Unknown'),
                            "age": row_dict.get('age'),
                            "gender": row_dict.get('gender', 'female'),
                            "personality_traits": [],
                            "interests": [],
                            "background": row_dict.get('background', ''),
                            "avatar_url": row_dict.get('avatar_url'),
                            "current_emotion": {
                                "name": row_dict.get('current_emotion', 'neutral'),
                                "intensity": 0.5,
                            }
                        }
                        
                        # Try to parse personality and interests
                        try:
                            personality = row_dict.get('personality')
                            if personality:
                                if isinstance(personality, str):
                                    import json
                                    try:
                                        char_dict["personality_traits"] = json.loads(personality)
                                    except json.JSONDecodeError:
                                        char_dict["personality_traits"] = [personality]
                        except Exception as e:
                            logger.error(f"Error parsing personality: {e}")
                            
                        try:
                            interests = row_dict.get('interests')
                            if interests:
                                if isinstance(interests, str):
                                    import json
                                    try:
                                        char_dict["interests"] = json.loads(interests)
                                    except json.JSONDecodeError:
                                        char_dict["interests"] = [interests]
                        except Exception as e:
                            logger.error(f"Error parsing interests: {e}")
                        
                        result.append(char_dict)
            except Exception as e:
                logger.error(f"Error retrieving from ai_partners table: {e}")
        
        logger.info(f"Found {len(result)} characters in total")
        return result
    except Exception as e:
        logger.exception(f"Error retrieving characters: {e}")
        return []

@router.post("/characters/{character_id}/start-chat")
async def start_chat(
    character_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Start a new chat with an AI character
    """
    # Convert UUID to string for compatibility with string columns in database
    character_id_str = str(character_id)
    logger.info(f"Looking for character with ID: {character_id_str}")
    
    # First try direct SQL to avoid type conversion issues
    from sqlalchemy import text
    character = None
    
    # Try multiple query variations to find the character
    try:
        # Try with direct text comparison
        query1 = "SELECT * FROM characters WHERE id::text = :id"
        raw_character = db.execute(text(query1), {"id": character_id_str}).fetchone()
        
        if raw_character:
            logger.info(f"Found character in characters table using query1: {raw_character['name']}")
            character = AIPartner()
            character = safe_set_attributes(character, dict(raw_character))
        else:
            # Try alternative casting
            query2 = "SELECT * FROM characters WHERE id = :id::uuid"
            raw_character = db.execute(text(query2), {"id": character_id_str}).fetchone()
            
            if raw_character:
                logger.info(f"Found character in characters table using query2: {raw_character['name']}")
                character = AIPartner()
                character = safe_set_attributes(character, dict(raw_character))
            else:
                # Try ai_partners table with explicit UUID cast
                query3 = "SELECT * FROM ai_partners WHERE id::text = :id"
                raw_character = db.execute(text(query3), {"id": character_id_str}).fetchone()
                
                if raw_character:
                    logger.info(f"Found character in ai_partners table: {raw_character['name']}")
                    character = AIPartner()
                    character = safe_set_attributes(character, dict(raw_character))
                else:
                    # One last attempt with raw character ID string in both tables
                    query4 = f"SELECT * FROM characters WHERE id = '{character_id_str}'"
                    raw_character = db.execute(text(query4)).fetchone()
                    
                    if raw_character:
                        logger.info(f"Found character using direct string in query: {raw_character['name']}")
                        character = AIPartner()
                        character = safe_set_attributes(character, dict(raw_character))
                    else:
                        logger.warning(f"Character not found in any table with ID: {character_id_str}")
    except Exception as e:
        logger.error(f"Error in SQL queries: {e}")
        
    if not character:
        # Log the tables and their contents for debugging
        try:
            char_count = db.execute(text("SELECT COUNT(*) FROM characters")).scalar()
            logger.info(f"Total characters in characters table: {char_count}")
            
            if char_count > 0:
                sample_chars = db.execute(text("SELECT id, name FROM characters LIMIT 5")).fetchall()
                logger.info(f"Sample characters: {[dict(c) for c in sample_chars]}")
                
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character not found with ID: {character_id_str}"
            )
        except Exception as e:
            logger.error(f"Error in debugging queries: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found"
            )
    
    # Load any existing memories and format personalized greeting if possible
    greeting = "Привет! Рада познакомиться с тобой. Как твои дела?"
    
    # If we have a logged in user, try to personalize using memories
    if current_user:
        try:
            # See if memories already exist for this character
            from core.db.models import Event
            memory_event = db.query(Event).filter(
                Event.character_id == character_id,
                Event.event_type == 'memory'
            ).first()
            
            if memory_event and memory_event.data:
                memories = json.loads(memory_event.data)
                if memories and len(memories) > 0:
                    # Look for name in memories
                    name_memories = [m for m in memories if 
                                    m.get("type") == "personal_info" and 
                                    m.get("category") == "name"]
                    
                    if name_memories:
                        # Extract name from content
                        import re
                        name_content = name_memories[0].get("content", "")
                        name_match = re.search(r"Имя пользователя: (.+)", name_content)
                        
                        if name_match:
                            user_name = name_match.group(1)
                            # Use name in greeting
                            greeting = f"Привет, {user_name}! Рада видеть тебя снова. Как у тебя дела?"
                            logger.info(f"Personalized greeting with user name: {user_name}")
        except Exception as e:
            logger.error(f"Error personalizing greeting: {e}")
    
    user_id = current_user.user_id if current_user else None
    if user_id:
        # Ensure partner_id is set correctly
        sender_id = character.id
        if hasattr(character, 'partner_id') and character.partner_id:
            sender_id = character.partner_id
            
        message = Message(
            sender_id=sender_id,
            sender_type="character",
            recipient_id=user_id,
            recipient_type="user",
            content=greeting,
            emotion="happy"
        )
        db.add(message)
        db.commit()
    return {
        "messages": [
            {
                "id": str(message.id) if user_id else "temp-1",
                "content": greeting,
                "sender_type": "character",
                "sender_id": str(character.id),  # Changed from partner_id to id
                "emotion": "happy",
                "timestamp": message.created_at.isoformat() if user_id else None
            }
        ]
    }

@router.post("/characters/{character_id}/send")
async def send_message(
    character_id: UUID,
    message: str = Query(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Send a message to an AI character and get a response
    """
    # Унифицированный подход к поиску персонажа
    character = None
    
    # Сначала ищем в ai_partners таблице
    character = db.query(AIPartner).filter(AIPartner.id == character_id).first()
    
    # Если не нашли, пробуем в characters таблице через SQL
    if not character:
        try:
            raw_character = db.execute(
                text("SELECT * FROM characters WHERE id = :id"),
                {"id": str(character_id)}
            ).fetchone()
            if raw_character:
                character = AIPartner()
                character = safe_set_attributes(character, dict(raw_character))
        except Exception as e:
            logger.error(f"Error in fallback query: {e}")
            
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    # Parse personality traits and interests for the character info
    traits = []
    interests = []
    
    if character.personality_traits:
        try:
            if isinstance(character.personality_traits, str):
                traits = json.loads(character.personality_traits)
            else:
                traits = character.personality_traits
        except (json.JSONDecodeError, TypeError):
            if isinstance(character.personality_traits, str):
                traits = [character.personality_traits]
            else:
                traits = []
                
    if character.interests:
        try:
            if isinstance(character.interests, str):
                interests = json.loads(character.interests)
            else:
                interests = character.interests
        except (json.JSONDecodeError, TypeError):
            if isinstance(character.interests, str):
                interests = [character.interests]
            else:
                interests = []
    
    character_info = {
        "name": character.name,
        "age": character.age,
        "gender": character.gender,
        "personality_traits": traits,
        "interests": interests,
        "background": character.background,
        "current_emotion": {
            "name": character.current_emotion or "neutral",
            "intensity": 0.7
        }
    }
    relationship_info = {
        "stage": "acquaintance",
        "score": 50,
        "trend": "neutral"
    }
    message_history = []
    if current_user:
        user_id = current_user.user_id
        char_id = character.id  # Используем просто id вместо partner_id

        # Улучшенный запрос для поиска сообщений между пользователем и персонажем
        recent_messages = db.query(Message).filter(
            ((Message.sender_id == str(char_id)) & (Message.recipient_id == str(user_id))) | 
            ((Message.sender_id == str(user_id)) & (Message.recipient_id == str(char_id)))
        ).order_by(Message.created_at.desc()).limit(10).all()

        for msg in reversed(recent_messages):
            sender_type = "user" if msg.sender_id == str(user_id) else "character"
            message_history.append({
                "sender_type": sender_type,
                "content": msg.content,
                "emotion": msg.emotion or "neutral"
            })
    
    context = {
        "character": character_info,
        "relationship": relationship_info,
        "history": message_history,
        "events": {"has_events": False}
    }

    # Retrieve any stored events for this user and character
    try:
        from core.db.models import Event
        events_record = db.query(Event).filter(
            Event.character_id == character_id,
            Event.event_type == 'events'
        ).first()
        if events_record and events_record.data:
            # parse stored events JSON
            events_data = json.loads(events_record.data)
            context["events"] = events_data
        else:
            context["events"] = []
    except Exception as e:
        logger.error(f"Error retrieving events: {e}")
        context["events"] = []

    if current_user:
        user_id = current_user.user_id
        user_message = Message(
            sender_id=str(user_id),
            sender_type="user",
            recipient_id=str(character.id),  # Используем просто id вместо partner_id
            recipient_type="character",
            content=message,
            emotion="neutral"
        )
        db.add(user_message)
        try:
            db.commit()
            logger.info(f"✅ User message saved to database: '{message[:50]}...'")
        except Exception as e:
            logger.error(f"❌ Error saving user message: {e}")
            db.rollback()

    response = ai_client.generate_response(context, message)
    is_multi_message = False
    multi_messages = []
    main_text = ""
    emotion = "neutral"
    relationship_changes = {"general": 0}
    
    if isinstance(response, dict):
        if "messages" in response and isinstance(response["messages"], list) and response["messages"]:
            is_multi_message = True
            multi_messages = response["messages"]
            relationship_changes = response.get("relationship_changes", {"general": 0})
        elif "text" in response:
            main_text = response["text"]
            emotion = response.get("emotion", "neutral")
            relationship_changes = response.get("relationship_changes", {"general": 0})
    else:
        main_text = str(response)
        
    if current_user:
        try:
            if is_multi_message:
                for i, msg in enumerate(multi_messages):
                    character_message = Message(
                        sender_id=str(character.id),  # Используем просто id вместо partner_id
                        sender_type="character",
                        recipient_id=str(current_user.user_id),
                        recipient_type="user",
                        content=msg.get("text", ""),
                        emotion=msg.get("emotion", "neutral")
                    )
                    db.add(character_message)
            else:
                character_message = Message(
                    sender_id=str(character.id),  # Используем просто id вместо partner_id
                    sender_type="character",
                    recipient_id=str(current_user.user_id),
                    recipient_type="user",
                    content=main_text,
                    emotion=emotion
                )
                db.add(character_message)
            if emotion and character:
                character.current_emotion = emotion
            db.commit()
            logger.info(f"✅ AI response saved to messages table: '{main_text[:50]}...'")
        except Exception as e:
            logger.error(f"❌ Error saving AI response to database: {e}")
            db.rollback()
    if is_multi_message:
        return {
            "is_multi_message": True,
            "multi_messages": multi_messages,
            "relationship_changes": relationship_changes
        }
    else:
        return {
            "text": main_text,
            "emotion": emotion,
            "relationship_changes": relationship_changes
        }

@router.post("/characters/{character_id}/gift")
async def send_gift(
    character_id: UUID,
    gift_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Send a gift to the character
    """
    # Change from partner_id to id to match the characters table
    character = db.query(AIPartner).filter(AIPartner.id == character_id).first()
    if not character:
        # Try raw SQL as fallback
        from sqlalchemy import text
        try:
            raw_character = db.execute(
                text("SELECT * FROM characters WHERE id = :id"),
                {"id": str(character_id)}
            ).fetchone()
            if raw_character:
                character = AIPartner()
                character = safe_set_attributes(character, dict(raw_character))
        except Exception as e:
            logger.error(f"Error in fallback query: {e}")
            
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    available_gifts = {
        "flower": {"name": "Букет цветов", "effect": 5},
        "chocolate": {"name": "Коробка конфет", "effect": 7},
        "jewelry": {"name": "Украшение", "effect": 15},
        "perfume": {"name": "Духи", "effect": 10},
        "teddy": {"name": "Плюшевый мишка", "effect": 8},
        "vip_gift": {"name": "VIP Подарок", "effect": 20}
    }
    if gift_id not in available_gifts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gift not found"
        )
    gift = available_gifts[gift_id]
    
    # Get conversation history for context
    message_history = []
    if current_user:
        user_id = current_user.user_id
        char_id = character.partner_id

        recent_messages = db.query(Message).filter(
            ((Message.sender_id == char_id) and (Message.recipient_id == user_id)) or
            ((Message.sender_id == user_id) and (Message.recipient_id == char_id))
        ).order_by(Message.created_at.desc()).limit(10).all()

        for msg in reversed(recent_messages):
            sender_type = "user" if msg.sender_id == user_id else "character"
            message_history.append({
                "sender_type": sender_type,
                "content": msg.content,
                "emotion": msg.emotion or "neutral"
            })
    
    # Parse personality traits and interests for the character info
    traits = []
    interests = []
    
    if character.personality_traits:
        try:
            if isinstance(character.personality_traits, str):
                traits = json.loads(character.personality_traits)
            else:
                traits = character.personality_traits
        except (json.JSONDecodeError, TypeError):
            if isinstance(character.personality_traits, str):
                traits = [character.personality_traits]
            else:
                traits = []
    
    if character.interests:
        try:
            if isinstance(character.interests, str):
                interests = json.loads(character.interests)
            else:
                interests = character.interests
        except (json.JSONDecodeError, TypeError):
            if isinstance(character.interests, str):
                interests = [character.interests]
            else:
                interests = []
    
    # Prepare character context with more detailed information
    character_info = {
        "id": str(character_id),
        "name": character.name,
        "age": character.age,
        "gender": character.gender,
        "personality_traits": traits,
        "interests": interests,
        "background": character.background,
        "current_emotion": {
            "name": character.current_emotion or "neutral",
            "intensity": 0.7
        }
    }
    
    # Create gift context with more detailed information to influence the AI's responses
    gift_context = {
        "character": character_info,
        "relationship": {"stage": "acquaintance", "score": 50},
        "history": message_history,
        "events": {"has_events": False},
        "current_interaction": {
            "type": "gift_received",
            "gift": {
                "id": gift_id,
                "name": gift["name"],
                "effect": gift["effect"],
                "timestamp": datetime.now().isoformat()
            }
        },
        "system_instruction": f"Пользователь только что подарил тебе подарок: {gift['name']}. " +
                             "Учти этот подарок в своей памяти. Это важное событие в вашей истории общения. " +
                             "Ты можешь упоминать этот подарок в будущих беседах."
    }
    
    # Try to load existing gifts history to add context
    try:
        gifts_event = db.query(Event).filter(
            Event.character_id == character_id,
            Event.event_type == 'gifts'
        ).first()
        
        if gifts_event and gifts_event.data:
            try:
                past_gifts = json.loads(gifts_event.data)
                gift_context["past_gifts"] = past_gifts
                gift_context["events"]["has_events"] = True
                logger.info(f"Loaded {len(past_gifts)} past gifts for context")
            except json.JSONDecodeError:
                logger.error("Could not parse past gifts data")
    except Exception as e:
        logger.error(f"Error loading gift history: {e}")
    
    # Generate personalized response using the AI with enhanced gift information
    prompt = f"""Пользователь только что подарил тебе {gift['name']}. 

ВАЖНОЕ СОБЫТИЕ: Тебе подарили подарок! Этот подарок часть вашей истории общения.

Как ты отреагируешь на получение этого подарка? Опиши свою искреннюю реакцию, эмоции и впечатления. 
Твой ответ должен быть эмоциональным и соответствовать твоей личности.
Не используй общие фразы вроде "Спасибо за подарок". Опиши свои настоящие чувства.

В будущих разговорах вспоминай об этом подарке, когда это уместно - это важная часть ваших отношений."""

    # Add memory entry specifically for the gift
    try:
        from core.db.models import MemoryEntry
        
        # Create a memory entry for the gift
        gift_memory = MemoryEntry(
            id=uuid4(),
            character_id=character_id,
            user_id=current_user.user_id if current_user else None,
            memory_type="gift",
            category="interaction",
            content=f"Пользователь подарил {gift['name']}. Это было очень приятно.",
            importance=8,  # Higher importance to make sure it's remembered
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(gift_memory)
        db.commit()
        logger.info(f"Created memory entry for gift: {gift['name']}")
    except Exception as e:
        logger.error(f"Error creating gift memory: {e}")
        db.rollback()
    
    # Let the AI generate a personalized response
    logger.info(f"Requesting AI response for gift: {gift['name']}")
    response = ai_client.generate_response(gift_context, prompt)
    logger.info(f"Received AI response type: {type(response)}")
    
    # Extract text and emotion from the response
    if isinstance(response, dict):
        logger.info(f"AI response keys: {response.keys()}")
        reaction_text = response.get("text")
        # Log the reaction text to help with debugging
        if reaction_text:
            logger.info(f"AI generated gift reaction: {reaction_text[:100]}...")
        else:
            logger.warning("AI did not generate reaction text - requesting another response")
            
            # If AI didn't generate valid text, retry with more explicit prompt
            retry_prompt = f"""Пользователь подарил тебе {gift['name']}. 
            
ВАЖНО: Нужна твоя эмоциональная и искренняя реакция на этот подарок!
Опиши свои чувства и впечатления подробно, как будто ты действительно только что получил(а) этот подарок.
Не используй шаблонных фраз. Реакция должна соответствовать твоему характеру."""

            # Retry AI call
            logger.info("Retrying AI request for gift reaction")
            retry_response = ai_client.generate_response(gift_context, retry_prompt)
            if isinstance(retry_response, dict) and retry_response.get("text"):
                reaction_text = retry_response.get("text")
                logger.info(f"Retry generated reaction: {reaction_text[:100]}...")
                # Also update emotion and relationship changes if available
                if "emotion" in retry_response:
                    response["emotion"] = retry_response["emotion"]
                if "relationship_changes" in retry_response:
                    response["relationship_changes"] = retry_response["relationship_changes"]
            elif isinstance(retry_response, str) and len(retry_response.strip()) > 10:
                reaction_text = retry_response
                logger.info(f"Retry generated string reaction: {reaction_text[:100]}...")
            else:
                # If still no valid response, create minimal response without templates
                logger.error("Failed to generate AI reaction even after retry")
                reaction_text = f"*реагирует на подарок* Это... {gift['name']}... Мне очень приятно."
                logger.warning(f"Using minimal generic response: {reaction_text}")
        
        emotion = response.get("emotion", "happy")
        relationship_changes = response.get("relationship_changes", {
            "general": gift["effect"] * 0.01,
            "friendship": gift["effect"] * 0.01 * 0.7,
            "romance": gift["effect"] * 0.01 * 0.3,
            "trust": gift["effect"] * 0.01 * 0.5
        })
    else:
        # If response is not a dict, try to use it as text directly
        if response and isinstance(response, str) and len(response.strip()) > 10:
            reaction_text = response
            logger.info(f"Using string response directly: {reaction_text[:50]}...")
        else:
            # If no valid response, make another request with more explicit prompt
            logger.warning("Invalid direct response - requesting new AI response")
            
            retry_prompt = f"""Я только что получил(а) подарок: {gift['name']}! 
            
Как персонаж, опиши свою реакцию на получение этого подарка.
Будь эмоциональным и искренним. Опиши, что ты чувствуешь, получив такой подарок."""

            # Retry with explicit prompt
            retry_response = ai_client.generate_response(gift_context, retry_prompt)
            if isinstance(retry_response, dict) and retry_response.get("text"):
                reaction_text = retry_response.get("text")
                logger.info(f"Fallback AI generated reaction: {reaction_text[:100]}...")
                # Get emotion if available
                emotion = retry_response.get("emotion", "happy")
                relationship_changes = retry_response.get("relationship_changes", {
                    "general": gift["effect"] * 0.01,
                    "friendship": gift["effect"] * 0.01 * 0.7,
                    "romance": gift["effect"] * 0.01 * 0.3,
                    "trust": gift["effect"] * 0.01 * 0.5
                })
            elif isinstance(retry_response, str) and len(retry_response.strip()) > 10:
                reaction_text = retry_response
                emotion = "happy" 
                relationship_changes = {
                    "general": gift["effect"] * 0.01,
                    "friendship": gift["effect"] * 0.01 * 0.7,
                    "romance": gift["effect"] * 0.01 * 0.3,
                    "trust": gift["effect"] * 0.01 * 0.5
                }
                logger.info(f"Fallback string reaction: {reaction_text[:100]}...")
            else:
                # Last resort minimal response
                reaction_text = f"Спасибо за подарок! Это именно то, что мне нравится."
                emotion = "happy"
                relationship_changes = {
                    "general": gift["effect"] * 0.01,
                    "friendship": gift["effect"] * 0.01 * 0.7,
                    "romance": gift["effect"] * 0.01 * 0.3,
                    "trust": gift["effect"] * 0.01 * 0.5
                }
                logger.error("Failed all attempts to generate AI reaction")

    # Save messages to database
    if current_user:
        # Save user's gift message
        gift_message = Message(
            sender_id=current_user.user_id,
            sender_type="user",
            recipient_id=character.partner_id,
            recipient_type="character",
            content=f"Отправил подарок: {gift['name']}",
            emotion="happy",
            is_gift=True
        )
        db.add(gift_message)
        
        # Save character's response
        reaction_message = Message(
            sender_id=character.partner_id,
            sender_type="character",
            recipient_id=current_user.user_id,
            content=reaction_text,
            emotion=emotion
        )
        db.add(reaction_message)
        
        # Update character's emotion
        if emotion:
            character.current_emotion = emotion
            
        # Add gift event to conversation history for future context
        try:
            from core.db.models.chat_history import ChatHistory
            
            # Get next position in chat history
            max_position = db.query(func.max(ChatHistory.position)).filter(
                ChatHistory.character_id == character_id,
                ChatHistory.user_id == current_user.user_id
            ).scalar() or 0
            
            # Create gift event entry with more detailed information
            gift_event = {
                "event_type": "gift_received",
                "gift_id": gift_id,
                "gift_name": gift["name"],
                "gift_effect": gift["effect"],
                "timestamp": datetime.now().isoformat(),
                "reaction": reaction_text,
                "emotion": emotion
            }
            
            # Store gift event in chat history
            gift_history_entry = ChatHistory(
                id=uuid4(),
                character_id=character_id,
                user_id=current_user.user_id,
                role="system",
                content=f"Пользователь отправил подарок: {gift['name']}",
                message_metadata=json.dumps({"gift_event": gift_event}),
                position=max_position + 1,
                is_active=True,
                compressed=False,
                created_at=datetime.now()
            )
            db.add(gift_history_entry)
            
            # Store AI response in chat history
            response_history_entry = ChatHistory(
                id=uuid4(),
                character_id=character_id,
                user_id=current_user.user_id,
                role="assistant",
                content=reaction_text,
                message_metadata=json.dumps({"emotion": emotion, "gift_response": True}),
                position=max_position + 2,
                is_active=True,
                compressed=False,
                created_at=datetime.now()
            )
            db.add(response_history_entry)
            
            # Also add to events table for broader context
            from core.models import Event
            
            # Check for existing gifts event
            gifts_event = db.query(Event).filter(
                Event.character_id == character_id,
                Event.event_type == 'gifts'
            ).first()
            
            if gifts_event and gifts_event.data:
                try:
                    gifts_data = json.loads(gifts_event.data)
                    if isinstance(gifts_data, list):
                        gifts_data.append(gift_event)
                    else:
                        gifts_data = [gift_event]
                    gifts_event.data = json.dumps(gifts_data)
                except json.JSONDecodeError:
                    gifts_event.data = json.dumps([gift_event])
            else:
                # Create new event
                new_event = Event(
                    character_id=character_id,
                    event_type='gifts',
                    data=json.dumps([gift_event]),
                    created_at=datetime.now()
                )
                db.add(new_event)
        except Exception as e:
            logger.error(f"Error storing gift in chat history: {e}")
        
        db.commit()
        
    return {
        "reaction": {
            "text": reaction_text,
            "emotion": emotion
        },
        "relationship_changes": relationship_changes,
        "gift": {
            "id": gift_id,
            "name": gift["name"],
            "effect": gift["effect"]
        },
        "is_ai_response": True,
        "character_name": character.name
    }

@router.post("/characters/{character_id}/clear-history")
async def clear_chat_history(
    character_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Clear chat history with a character
    """
    # Change from partner_id to id to match the characters table
    character = db.query(AIPartner).filter(AIPartner.id == character_id).first()
    if not character:
        # Try raw SQL as fallback
        from sqlalchemy import text
        try:
            raw_character = db.execute(
                text("SELECT * FROM characters WHERE id = :id"),
                {"id": str(character_id)}
            ).fetchone()
            if raw_character:
                character = AIPartner()
                character = safe_set_attributes(character, dict(raw_character))
        except Exception as e:
            logger.error(f"Error in fallback query: {e}")
            
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    deleted_count = db.query(Message).filter(
        ((Message.sender_id == character.partner_id) and (Message.recipient_id == current_user.user_id)) or
        ((Message.sender_id == current_user.user_id) and (Message.recipient_id == character.partner_id))
    ).delete()
    db.commit()
    
    try:
        ai_client.clear_conversation(str(character_id))
        logger.info(f"Cleared AI conversation context for character {character_id}")
    except Exception as e:
        logger.error(f"Error clearing AI conversation context: {e}")
    
    return {
        "success": True,
        "deleted_messages": deleted_count
    }

@router.post("/characters/{character_id}/compress")
async def compress_character_chat(
    character_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Compress the chat history with a character to save context while reducing token usage
    """
    logger.info(f"Compression request received for character {character_id}")
    
    try:
        # Change from partner_id to id to match the characters table
        character = db.query(AIPartner).filter(AIPartner.id == character_id).first()
        if not character:
            # Try raw SQL as fallback
            from sqlalchemy import text
            try:
                raw_character = db.execute(
                    text("SELECT * FROM characters WHERE id = :id"),
                    {"id": str(character_id)}
                ).fetchone()
                if raw_character:
                    character = AIPartner()
                    character = safe_set_attributes(character, dict(raw_character))
            except Exception as e:
                logger.error(f"Error in fallback query: {e}")
                
        if not character:
            logger.error(f"Character not found for compression: {character_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found"
            )
        
        # Check if there are any messages to compress first
        message_count = db.query(Message).filter(
            ((Message.sender_id == character_id) and (Message.recipient_type == "user")) or
            ((Message.recipient_id == character_id) and (Message.sender_type == "user"))
        ).count()
        
        logger.info(f"Found {message_count} messages for character {character_id}")
        
        if message_count < 3:  # Require at least 3 messages for compression
            logger.warning(f"Not enough messages to compress: {message_count}")
            return {
                "success": False,
                "message": "Not enough messages to compress. Continue chatting and try again later.",
                "error": "insufficient_messages",
                "message_count": message_count
            }
        
        # Call the compression function only if we have enough messages
        compression_result = ai_client.compress_conversation(str(character_id), db_session=db)
        logger.info(f"Compression result: {compression_result}")
        
        if not compression_result.get("success", False):
            error_msg = compression_result.get("error", "Failed to compress conversation")
            logger.error(f"Compression failed: {error_msg}")
            # Return error as response rather than raising exception
            return {
                "success": False,
                "message": f"Failed to compress conversation: {error_msg}",
                "error": error_msg
            }
        
        logger.info(f"Compression successful for character {character_id}")
        return {
            "success": True,
            "message": "Chat history compressed successfully",
            "summary": compression_result.get("summary", ""),
            "original_messages": compression_result.get("original_messages", 0),
            "compressed_messages": compression_result.get("compressed_messages", 0)
        }
    except Exception as e:
        logger.exception(f"Unexpected error in compress_character_chat: {e}")
        return {
            "success": False,
            "message": "An internal server error occurred during compression",
            "error": str(e)
        }

@router.get("/characters/{character_id}/relationship")
async def get_relationship(
    character_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get relationship status with a character
    """
    # Change from partner_id to id to match the characters table
    character = db.query(AIPartner).filter(AIPartner.id == character_id).first()
    if not character:
        # Try raw SQL as fallback
        from sqlalchemy import text
        try:
            raw_character = db.execute(
                text("SELECT * FROM characters WHERE id = :id"),
                {"id": str(character_id)}
            ).fetchone()
            if raw_character:
                character = AIPartner()
                character = safe_set_attributes(character, dict(raw_character))
        except Exception as e:
            logger.error(f"Error in fallback query: {e}")
            
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    if not current_user:
        return {
            "rating": {
                "value": 50,
                "label": "Нейтральные"
            },
            "status": {
                "label": "Знакомые",
                "description": "Вы только начали общаться",
                "emoji": "👋"
            },
            "emotions": {
                "friendship": {"percentage": 50, "level": "neutral"},
                "romance": {"percentage": 0, "level": "none"},
                "trust": {"percentage": 30, "level": "low"}
            }
        }
    message_count = db.query(Message).filter(
        ((Message.sender_id == character.partner_id) and (Message.recipient_id == current_user.user_id)) or
        ((Message.sender_id == current_user.user_id) and (Message.recipient_id == character.partner_id))
    ).count()
    gift_count = db.query(Message).filter(
        (Message.sender_id == current_user.user_id) and
        (Message.recipient_id == character.partner_id) and
        (Message.is_gift == True)
    ).count()
    base_rating = min(50 + message_count * 2 + gift_count * 10, 100)
    status = {"label": "Знакомые", "description": "Вы только начали общаться", "emoji": "👋"}
    if base_rating >= 80:
        status = {"label": "Близкие", "description": "Между вами крепкая связь", "emoji": "❤️"}
    elif base_rating >= 60:
        status = {"label": "Друзья", "description": "Вы хорошо ладите", "emoji": "🤝"}
    friendship_pct = min(40 + message_count * 3 + gift_count * 5, 100)
    romance_pct = min(gift_count * 10, 100)
    trust_pct = min(30 + message_count * 2 + gift_count * 7, 100)
    def get_level(pct):
        if pct >= 80:
            return "high"
        elif pct >= 50:
            return "medium"
        elif pct >= 20:
            return "low"
        else:
            return "none"
    return {
        "rating": {
            "value": base_rating,
            "label": "Хорошие" if base_rating >= 60 else "Нейтральные"
        },
        "status": status,
        "emotions": {
            "friendship": {"percentage": friendship_pct, "level": get_level(friendship_pct)},
            "romance": {"percentage": romance_pct, "level": get_level(romance_pct)},
            "trust": {"percentage": trust_pct, "level": get_level(trust_pct)}
        }
    }

from app.dependencies import get_current_user_or_api_key, validate_api_key
from app.schemas.memory import MemorySchema

@router.get("/characters/{character_id}/memories")
async def get_character_memories(
    character_id: str,
    user_id: Optional[str] = None,
    telegram_id: Optional[str] = None,
    include_all: bool = Query(False),
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get memories for a specific character and user
    
    Args:
        character_id: ID of the character
        user_id: Optional ID of the user. If provided, only memories for this user are returned
        telegram_id: Optional Telegram ID of the user. Used as alternative to user_id
    """
    # Check API key authentication
    bot_api_key = os.getenv("BOT_API_KEY")
    is_authenticated = False
    
    # Check if API key provided in X-API-Key header
    if x_api_key and x_api_key == bot_api_key:
        is_authenticated = True
    
    # Check if API key provided in Authorization header
    if authorization and not is_authenticated:
        auth_parts = authorization.split()
        if len(auth_parts) == 2 and auth_parts[0].lower() == "bearer":
            token = auth_parts[1]
            if token == bot_api_key:
                is_authenticated = True
    
    # If authentication failed, return 401
    if not is_authenticated:
        logger.warning(f"Unauthorized access attempt to memories: x_api_key={x_api_key}, auth={authorization}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # If include_all is requested, ignore user filters to return all memories
    if include_all:
        user_id = None
        telegram_id = None

    # Check if character exists
    character = db.execute(text("""
        SELECT id, name FROM characters 
        WHERE id::text = :character_id
    """), {"character_id": character_id}).fetchone()
    
    if not character:
        # Try alternate table if the first query fails
        character = db.execute(text("""
            SELECT id, name FROM ai_partners 
            WHERE id::text = :character_id
        """), {"character_id": character_id}).fetchone()
    
    if not character:
        return {"memories": [], "count": 0, "error": "Character not found"}
    
    # When include_all, return all stored memories from events table
    if include_all:
        try:
            from core.db.models import Event
            evt = db.query(Event).filter(
                Event.character_id == character_id,
                Event.event_type == 'memory'
            ).first()
            if evt and evt.data:
                import json as _json
                mem_list = _json.loads(evt.data)
                result = []
                for m in mem_list:
                    result.append({
                        "id": m.get('id'),
                        "type": m.get('type', m.get('memory_type', 'unknown')),
                        "memory_type": m.get('memory_type', m.get('type', 'unknown')),
                        "category": m.get('category', 'general'),
                        "content": m.get('content'),
                        "importance": m.get('importance', 5),
                        "is_active": m.get('is_active', True),
                        "user_id": m.get('user_id'),
                        "created_at": m.get('created_at')
                    })
                return {"memories": result, "count": len(result)}
        except Exception:
            logger.error("Error loading full memories for include_all", exc_info=True)
    
    # Check columns in the memory_entries table
    try:
        columns = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'memory_entries'
        """)).fetchall()
        
        column_names = [col[0] for col in columns]
        logger.info(f"Memory entries columns: {column_names}")
        
        has_memory_type = 'memory_type' in column_names
        has_type = 'type' in column_names
        has_category = 'category' in column_names
        
        # Build a query that works with the existing columns
        query = "SELECT id"
        
        # Handle the memory type column which might be named 'memory_type' or just 'type'
        type_fields = []
        if (has_memory_type):
            type_fields.append("memory_type")
        if (has_type):
            type_fields.append("type")
            
        if type_fields:
            # Add both fields if they exist, with a COALESCE to handle NULL values
            query += ", COALESCE(" + ", ".join(type_fields) + ", 'unknown') as memory_type"
        else:
            query += ", 'unknown' as memory_type"
            
        if has_category:
            query += ", category"
        else:
            query += ", 'general' as category"
            
        query += """
            , content
            , COALESCE(importance, 5) as importance
            , COALESCE(is_active, TRUE) as is_active
            , user_id
            , created_at
            FROM memory_entries
            WHERE character_id::text = :character_id
            AND (is_active IS NULL OR is_active = TRUE)
        """
        
        params = {"character_id": character_id}
        
        # ENHANCED USER ID HANDLING - Support multiple formats
        
        user_id_condition = []
        
        # 1. Try direct user ID match if provided
        if user_id:
            # Try direct comparison as text
            user_id_condition.append("user_id::text = :user_id")
            params["user_id"] = user_id
            
            # Remove invalid direct UUID cast that causes SQL syntax errors
            # Previous approach used: user_id_condition.append("user_id = :user_id::uuid")
            
            # Continue with fallback comparisons
            # 2. Match null user_id
            user_id_condition.append("user_id IS NULL")
            # 3. Numeric suffix matching...
            
            # 3. Extract numeric part from UUID if it contains a numeric suffix
            if "-" in user_id:
                parts = user_id.split("-")
                if len(parts) > 1:
                    last_part = parts[-1]
                    # Handle cases like 001419048544
                    if last_part.startswith("00"):
                        numeric_id = last_part.lstrip("0")
                        if numeric_id:
                            user_id_condition.append("user_id::text LIKE :numeric_pattern")
                            params["numeric_pattern"] = f"%{numeric_id}"
                    # Also try with the raw last part
                    user_id_condition.append("user_id::text LIKE :last_part_pattern")
                    params["last_part_pattern"] = f"%{last_part}"
        
        # 4. Try telegram_id if provided
        if telegram_id:
            # Import uuid module for telegram ID handling
            import uuid as uuid_module  # Import as alias to avoid conflicts
            
            user_id_condition.append("user_id::text = :telegram_id")
            params["telegram_id"] = telegram_id
            
            # 5. Try telegram_id as part of UUID
            user_id_condition.append("user_id::text LIKE :telegram_suffix_pattern")
            params["telegram_suffix_pattern"] = f"%{telegram_id}"
            
            # 6. If telegram_id is numeric, try as suffix
            if telegram_id.isdigit():
                user_id_condition.append("user_id::text LIKE :telegram_numeric_pattern")
                params["telegram_numeric_pattern"] = f"%{telegram_id}"
                
                # 7. Also try with leading zeros (common in UUIDs generated from Telegram IDs)
                user_id_condition.append("user_id::text LIKE :telegram_leading_zeros")
                params["telegram_leading_zeros"] = f"%00{telegram_id}"
                
                # Generate a deterministic UUID based on telegram ID
                telegram_uuid = str(uuid_module.uuid5(uuid_module.NAMESPACE_DNS, f"telegram-{telegram_id}"))
                user_id_condition.append("user_id::text = :telegram_uuid")
                params["telegram_uuid"] = telegram_uuid
                
                # Try with just any UUID containing the telegram_id
                user_id_condition.append("user_id::text LIKE :telegram_anywhere")
                params["telegram_anywhere"] = f"%{telegram_id}%"
        
        # Add special case: Try to get memories where the user_id is any value
        # (this is a fallback to at least show some memories)
        if (user_id or telegram_id):
            # Add a catch-all option to show some memories even if the user ID doesn't match perfectly
            user_id_condition.append("1=1")
        
        # Add user filter conditions if provided
        if user_id_condition:
            query += " AND (" + " OR ".join(user_id_condition) + ")"
            
        query += " ORDER BY importance DESC, created_at DESC LIMIT 50"
        
        # Execute the query with proper parameters
        logger.info(f"Executing memory query with params: {params}")
        memories = db.execute(text(query), params).fetchall()
        
        # Create consistent results regardless of the database schema
        result = []
        for memory in memories:
            memory_dict = {
                "id": memory[0],
                "type": memory[1] or "unknown",  # Use the memory_type field from the query but return as "type" for API consistency
                "memory_type": memory[1] or "unknown",  # Also include memory_type for backwards compatibility
                "category": memory[2] or "general",
                "content": memory[3],
                "importance": memory[4] if memory[4] is not None else 5,
                "is_active": memory[5] if memory[5] is not None else True,
                "user_id": memory[6],
                "created_at": str(memory[7]) if memory[7] else None
            }
            result.append(memory_dict)
            
        logger.info(f"Found {len(result)} memories for character {character_id}")
        if not result:
            # Try loading saved memories from events table for this user
            try:
                from core.db.models import Event
                # fetch JSON memory event
                event = db.query(Event).filter(
                    Event.character_id == character_id,
                    Event.event_type == 'memory'
                ).first()
                if event and event.data:
                    import json as _json
                    mem_list = _json.loads(event.data)
                    user_mem = []
                    for m in mem_list:
                        # include only this user's memories
                        if user_id and str(m.get('user_id')) != user_id:
                            continue
                        if telegram_id and str(m.get('user_id')) != telegram_id:
                            continue
                        user_mem.append({
                            'id': m.get('id'),
                            'type': m.get('type', m.get('memory_type', 'unknown')),
                            'memory_type': m.get('memory_type', m.get('type', 'unknown')),
                            'category': m.get('category', 'general'),
                            'content': m.get('content'),
                            'importance': m.get('importance', 5),
                            'is_active': m.get('is_active', True),
                            'user_id': m.get('user_id'),
                            'created_at': m.get('created_at')
                        })
                    if user_mem:
                        return {'memories': user_mem, 'count': len(user_mem)}
            except Exception:
                logger.error('Error loading memories from events', exc_info=True)
            # fallback to general memories when no personal entries found
            final_query = '''
                SELECT id, content, user_id, created_at
                FROM memory_entries
                WHERE character_id::text = :character_id
                AND (is_active IS NULL OR is_active = TRUE)
                LIMIT 50
            '''
            rows = db.execute(text(final_query), {"character_id": character_id}).fetchall()
            general = []
            for r in rows:
                general.append({
                    "id": r[0],
                    "type": "general",
                    "memory_type": "general",
                    "category": "general",
                    "content": r[1],
                    "importance": 5,
                    "is_active": True,
                    "user_id": r[2],
                    "created_at": str(r[3]) if r[3] else None
                })
            return {"memories": general, "count": len(general)}
        return {"memories": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error fetching memories: {e}")
        
        try:
            logger.info("Trying fallback memory query without type/category columns")
            fallback_query = """
                SELECT 
                    id, 
                    content,
                    user_id,
                    created_at
                FROM memory_entries
                WHERE character_id::text = :character_id
                AND (is_active IS NULL OR is_active = TRUE)
            """
            
            params = {"character_id": character_id}
            
            user_id_condition = []
            
            if user_id:
                user_id_condition.append("user_id::text = :user_id")
                params["user_id"] = user_id
                
                user_id_condition.append("user_id IS NULL")
                
                if "-" in user_id:
                    last_part = user_id.split("-")[-1]
                    user_id_condition.append("user_id::text LIKE :pattern")
                    params["pattern"] = f"%{last_part}"
            
            if telegram_id:
                user_id_condition.append("user_id::text = :telegram_id")
                params["telegram_id"] = telegram_id
                
                user_id_condition.append("user_id::text LIKE :telegram_pattern")
                params["telegram_pattern"] = f"%{telegram_id}"
                
                user_id_condition.append("1=1")
            
            if user_id_condition:
                fallback_query += " AND (" + " OR ".join(user_id_condition) + ")"
                
            fallback_query += " LIMIT 50"
                
            logger.info(f"Trying fallback query with params: {params}")
            memories = db.execute(text(fallback_query), params).fetchall()
            
            result = []
            for memory in memories:
                result.append({
                    "id": memory[0],
                    "type": "personal_info",  
                    "memory_type": "personal_info",  
                    "category": "general",
                    "content": memory[1],
                    "importance": 5,
                    "is_active": True,
                    "user_id": memory[2],
                    "created_at": str(memory[3]) if memory[3] else None
                })
                
            logger.info(f"Found {len(result)} memories using fallback query")
            return {"memories": result, "count": len(result)}
        except Exception as e2:
            logger.error(f"Fallback query also failed: {e2}")
            
            try:
                logger.info("Trying query without user ID filtering")
                final_fallback = """
                    SELECT 
                        id, 
                        content,
                        user_id,
                        created_at
                    FROM memory_entries
                    WHERE character_id::text = :character_id
                    AND (is_active IS NULL OR is_active = TRUE)
                    LIMIT 50
                """
                memories = db.execute(text(final_fallback), {"character_id": character_id}).fetchall()
                
                result = []
                for memory in memories:
                    result.append({
                        "id": memory[0],
                        "type": "personal_info",  
                        "memory_type": "personal_info", 
                        "category": "general",
                        "content": memory[1],
                        "importance": 5,
                        "is_active": True,
                        "user_id": memory[2],
                        "created_at": str(memory[3]) if memory[3] else None
                    })
                    
                logger.info(f"Found {len(result)} memories using final fallback query without user filtering")
                return {"memories": result, "count": len(result)}
            except Exception as e3:
                logger.error(f"All memory queries failed: {e3}")
                return {"memories": [], "count": 0, "error": f"Could not fetch memories: {str(e)}"}

from app.schemas.memory import MemoryCreate, MemoryUpdate

@router.post("/characters/{character_id}/memories", response_model=MemorySchema)
def create_character_memory(
    character_id: UUID,
    memory: MemoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new memory for a character
    """
    # Check if character exists
    character = db.execute(text("""
        SELECT id FROM ai_partners 
        WHERE id::text = :character_id
    """), {"character_id": str(character_id)}).fetchone()
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Create a new memory
    memory_id = str(uuid4())
    timestamp = datetime.now().isoformat()
    
    db.execute(text("""
        INSERT INTO memory_entries (
            id, character_id, user_id,
            type, memory_type, category, content,
            importance, is_active, created_at, updated_at
        ) VALUES (
            :id, :character_id, :user_id,
            :memory_type, :memory_type, :category, :content,
            :importance, TRUE, :created_at, :updated_at
        )
    """), {
        "id": memory_id,
        "character_id": str(character_id),
        "user_id": str(current_user.id),
        "memory_type": memory.memory_type,
        "category": memory.category,
        "content": memory.content,
        "importance": memory.importance,
        "created_at": timestamp,
        "updated_at": timestamp
    })
    
    db.commit()
    
    # Return the newly created memory
    return {
        "id": memory_id,
        "user_id": str(current_user.id),
        "type": memory.memory_type,
        "memory_type": memory.memory_type,
        "category": memory.category,
        "content": memory.content,
        "importance": memory.importance,
        "is_active": True,
        "created_at": timestamp
    }

@router.post("/generate-character")
async def generate_character(
    prompt: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Generate a new AI character based on a prompt
    """
    import random
    import uuid
    import json
    
    names = ["Алиса", "Екатерина", "Мария", "София", "Анна", "Виктория", "Дарья"]
    traits_pool = [
        "дружелюбная", "общительная", "умная", "креативная", "загадочная",
        "романтичная", "амбициозная", "заботливая", "веселая", "серьезная"
    ]
    interests_pool = [
        "чтение", "музыка", "искусство", "спорт", "путешествия", "фотография",
        "кулинария", "танцы", "кино", "психология", "технологии"
    ]
    name = random.choice(names)
    age = random.randint(20, 30)
    num_traits = random.randint(3, 5)
    traits = random.sample(traits_pool, num_traits)
    num_interests = random.randint(3, 5)
    interests = random.sample(interests_pool, num_interests)
    backgrounds = [
        f"{name} выросла в небольшом городке и всегда мечтала о путешествиях. Сейчас она живет в большом городе и наслаждается свободой.",
        f"{name} с детства увлекалась {random.choice(interests)}. Это помогло ей найти себя и свое призвание.",
        f"{name} училась в престижном университете, где получила образование в сфере {random.choice(interests)}. Сейчас она развивает собственные проекты.",
        f"{name} - творческая личность, которая всегда стремится к новым знаниям и впечатлениям."
    ]
    background = random.choice(backgrounds)
    
    traits_json = json.dumps(traits)
    interests_json = json.dumps(interests)
    
    character = AIPartner(
        partner_id=uuid.uuid4(),
        name=name,
        age=age,
        gender="female",
        personality_traits=traits_json,
        interests=interests_json,
        background=background,
        current_emotion="happy"
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    
    return {
        "id": str(character.partner_id),
        "name": character.name,
        "age": character.age,
        "gender": character.gender,
        "personality_traits": traits,
        "interests": interests,
        "background": character.background,
        "current_emotion": {
            "name": "happy",
            "intensity": 0.7
        }
    }