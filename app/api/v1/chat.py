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
            for key, value in dict(raw_character).items():
                setattr(character, key, value)
            character.partner_id = character.id
        else:
            # Try alternative casting
            query2 = "SELECT * FROM characters WHERE id = :id::uuid"
            raw_character = db.execute(text(query2), {"id": character_id_str}).fetchone()
            
            if raw_character:
                logger.info(f"Found character in characters table using query2: {raw_character['name']}")
                character = AIPartner()
                for key, value in dict(raw_character).items():
                    setattr(character, key, value)
                character.partner_id = character.id
            else:
                # Try ai_partners table with explicit UUID cast
                query3 = "SELECT * FROM ai_partners WHERE id::text = :id"
                raw_character = db.execute(text(query3), {"id": character_id_str}).fetchone()
                
                if raw_character:
                    logger.info(f"Found character in ai_partners table: {raw_character['name']}")
                    character = AIPartner()
                    for key, value in dict(raw_character).items():
                        setattr(character, key, value)
                    character.partner_id = character.id
                else:
                    # One last attempt with raw character ID string in both tables
                    query4 = f"SELECT * FROM characters WHERE id = '{character_id_str}'"
                    raw_character = db.execute(text(query4)).fetchone()
                    
                    if raw_character:
                        logger.info(f"Found character using direct string in query: {raw_character['name']}")
                        character = AIPartner()
                        for key, value in dict(raw_character).items():
                            setattr(character, key, value)
                        character.partner_id = character.id
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
                for key, value in dict(raw_character).items():
                    setattr(character, key, value)
                character.partner_id = character.id
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
            import json
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
            sender_id=user_id,
            sender_type="user",
            recipient_id=character.partner_id,
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
        if "events" in response:
            events_data = response.pop("events")
            if events_data:
                try:
                    events_record = db.query(Event).filter(
                        Event.character_id == character_id,
                        Event.event_type == 'events'
                    ).first()
                    if events_record:
                        try:
                            current_events = json.loads(events_record.data) if events_record.data else []
                            if isinstance(events_data, list):
                                current_events.extend(events_data)
                            else:
                                current_events.append(events_data)
                            events_record.data = json.dumps(current_events)
                            logger.info(f"Updated existing events record with new data")
                        except json.JSONDecodeError:
                            events_data_list = events_data if isinstance(events_data, list) else [events_data]
                            events_record.data = json.dumps(events_data_list)
                            logger.info(f"Replaced invalid events data with new events")
                    else:
                        from datetime import datetime
                        events_data_list = events_data if isinstance(events_data, list) else [events_data] 
                        new_event = Event(
                            character_id=character_id,
                            event_type='events',
                            data=json.dumps(events_data_list),
                            created_at=datetime.now()
                        )
                        db.add(new_event)
                        logger.info(f"Created new events record for character {character_id}")
                    db.commit()
                except Exception as db_error:
                    logger.error(f"Error saving events to database directly: {db_error}")
                    db.rollback()
                except Exception as events_error:
                    logger.error(f"Error processing events data: {events_error}")
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
                        sender_id=character.partner_id,
                        sender_type="character",
                        recipient_id=current_user.user_id,
                        recipient_type="user",
                        content=msg.get("text", ""),
                        emotion=msg.get("emotion", "neutral")
                    )
                    db.add(character_message)
            else:
                character_message = Message(
                    sender_id=character.partner_id,
                    sender_type="character",
                    recipient_id=current_user.user_id,
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
                for key, value in dict(raw_character).items():
                    setattr(character, key, value)
                character.partner_id = character.id
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
    
    # Create gift context
    gift_context = {
        "character": character_info,
        "relationship": {"stage": "acquaintance", "score": 50},
        "history": message_history,
        "events": {"has_events": False},
        "gift": {
            "id": gift_id,
            "name": gift["name"],
            "effect": gift["effect"]
        }
    }
    
    # Generate personalized response using the AI
    prompt = f"Пользователь отправил тебе подарок: {gift['name']}. Как ты отреагируешь? Опиши свою реакцию, эмоции и впечатления от подарка."
    
    # Let the AI generate a personalized response
    response = ai_client.generate_response(gift_context, prompt)
    
    # Extract text and emotion from the response
    if isinstance(response, dict):
        reaction_text = response.get("text", f"Спасибо за {gift['name']}!")
        emotion = response.get("emotion", "happy")
        relationship_changes = response.get("relationship_changes", {
            "general": gift["effect"] * 0.01,
            "friendship": gift["effect"] * 0.01 * 0.7,
            "romance": gift["effect"] * 0.01 * 0.3,
            "trust": gift["effect"] * 0.01 * 0.5
        })
    else:
        reaction_text = str(response)
        emotion = "happy"
        relationship_changes = {
            "general": gift["effect"] * 0.01,
            "friendship": gift["effect"] * 0.01 * 0.7,
            "romance": gift["effect"] * 0.01 * 0.3,
            "trust": gift["effect"] * 0.01 * 0.5
        }

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
            
            # Create gift event entry
            gift_event = {
                "gift_id": gift_id,
                "gift_name": gift["name"],
                "gift_effect": gift["effect"],
                "timestamp": datetime.now().isoformat()
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
        "relationship_changes": relationship_changes
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
                for key, value in dict(raw_character).items():
                    setattr(character, key, value)
                character.partner_id = character.id
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
                    for key, value in dict(raw_character).items():
                        setattr(character, key, value)
                    character.partner_id = character.id
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
                for key, value in dict(raw_character).items():
                    setattr(character, key, value)
                character.partner_id = character.id
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
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get memories for a specific character and user
    
    Args:
        character_id: ID of the character
        user_id: Optional ID of the user. If provided, only memories for this user are returned
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
    
    # Build the query with optional user_id filter
    query = """
        SELECT 
            id, 
            memory_type,
            category,
            content,
            importance,
            is_active,
            user_id,
            created_at
        FROM memory_entries
        WHERE character_id::text = :character_id
    """
    
    params = {"character_id": character_id}
    
    # Add user_id filter if provided
    if user_id:
        query += " AND user_id::text = :user_id"
        params["user_id"] = user_id
    
    query += " ORDER BY importance DESC, created_at DESC"
    
    # Get memories with proper type casting
    try:
        memories = db.execute(text(query), params).fetchall()
        
        result = []
        for memory in memories:
            result.append({
                "id": memory[0],
                "type": memory[1] or "unknown",
                "category": memory[2] or "general",
                "content": memory[3],
                "importance": memory[4] if memory[4] is not None else 5,
                "is_active": memory[5] if memory[5] is not None else True,
                "user_id": memory[6],
                "created_at": str(memory[7]) if memory[7] else None
            })
        
        return {"memories": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error fetching memories: {e}")
        return {"memories": [], "count": 0, "error": str(e)}

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
    memory_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    db.execute(text("""
        INSERT INTO memory_entries (
            id, character_id, user_id, memory_type, category, content,
            importance, is_active, created_at, updated_at
        ) VALUES (
            :id, :character_id, :user_id, :memory_type, :category, :content,
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