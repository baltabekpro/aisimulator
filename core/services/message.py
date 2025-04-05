from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import random
from core.db.models.message import Message
from core.services.base import BaseService
from core.services.love_rating import LoveRatingService
from core.services.event import EventService
from core.services.ai_partner import AIPartnerService
from core.ai.gemini import GeminiAI
import json
import time

class MessageService(BaseService):
    """Service for handling Message operations."""
    
    def __init__(self, db: Session):
        super().__init__(Message, db)
        self.love_rating_service = LoveRatingService(db)
        self.event_service = EventService(db)
        self.partner_service = AIPartnerService(db)
        self.ai = GeminiAI()
    
    def get_conversation(self, user_id: UUID, partner_id: UUID, limit: int = 50) -> List[Message]:
        """Get recent conversation messages between a user and an AI partner."""
        # For reliable ordering in tests, explicitly use message_id as the primary sort
        # This ensures consistent ordering even if timestamps are identical
        return self.db.query(Message).filter(
            Message.user_id == user_id,
            Message.partner_id == partner_id
        ).order_by(
            desc(Message.message_id)  # Sort by message_id in descending order
        ).limit(limit).all()
    
    def create_message(self, *, user_id: UUID, partner_id: UUID, content: str,
                     sender_type: str, emotion: str = None) -> Message:
        """Create a new message."""
        message_data = {
            "user_id": user_id,
            "partner_id": partner_id,
            "content": content,
            "sender_type": sender_type,
            "emotion": emotion
        }
        return self.create(obj_in=message_data)
    
    def create_user_message(self, *, user_id: UUID, partner_id: UUID, 
                          content: str) -> Message:
        """Create a message from the user."""
        # Обрабатываем влияние сообщения на рейтинг
        delta, reason = self.love_rating_service.process_interaction(
            user_id=user_id,
            partner_id=partner_id,
            interaction_type="message", 
            content=content
        )
        
        return self.create_message(
            user_id=user_id,
            partner_id=partner_id,
            content=content,
            sender_type="user"
        )
    
    def create_bot_message(self, *, user_id: UUID, partner_id: UUID,
                         content: str, emotion: str = None) -> Message:
        """Create a message from the AI partner."""
        # Ensure emotion is a string, not a dictionary
        if isinstance(emotion, dict):
            emotion = emotion.get("name", "neutral")
        
        return self.create_message(
            user_id=user_id,
            partner_id=partner_id,
            content=content,
            sender_type="bot",
            emotion=emotion
        )
    
    # Новые методы для реализации бизнес-логики
    
    def get_context(self, user_id: UUID, partner_id: UUID) -> Dict[str, Any]:
        """
        Собирает контекст диалога для генерации ответа ИИ.
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            
        Returns:
            Словарь с контекстом диалога
        """
        # Получаем информацию о персонаже
        partner = self.partner_service.get(partner_id)
        if not partner:
            return {"error": "Partner not found"}
        
        if partner.personality:
            try:
                personality_data = json.loads(partner.personality)
            except json.JSONDecodeError:
                personality_data = {}
        else:
            personality_data = {}

        character_info = {
            "id": str(partner.partner_id),
            "name": partner.name,
            "age": partner.age,
            "gender": "female",
            "personality_traits": personality_data.get("traits", ["friendly"]),
            "interests": personality_data.get("interests", ["talking"]),
            "biography": partner.biography,
            "current_emotion": {
                "name": "neutral",
                "intensity": 0.5,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Получаем информацию об отношениях
        relationship_info = self.love_rating_service.analyze_recent_changes(user_id, partner_id)
        
        # Получаем информацию о событиях
        event_context = self.event_service.get_active_event_context(user_id, partner_id)
        
        # Получаем историю сообщений
        history = self.get_conversation(user_id, partner_id, limit=10)
        history_list = [
            {
                "id": str(msg.message_id),
                "sender_type": msg.sender_type,
                "content": msg.content,
                "emotion": msg.emotion,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in history
        ]
        
        return {
            "character": character_info,
            "relationship": relationship_info, 
            "events": event_context,
            "history": history_list
        }
    
    def generate_bot_response(self, user_id: UUID, partner_id: UUID, message: str) -> Dict[str, Any]:
        """
        Генерирует ответ бота с использованием Gemini.
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            message: Текст сообщения пользователя
            
        Returns:
            Словарь с ответом бота
        """
        # Получаем контекст диалога
        context = self.get_context(user_id, partner_id)
        
        # Логирование для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Generating response to: {message}")
        logger.debug(f"Context for generation: {context}")
        
        instructions = (
            "You can respond with either a single 'text' field or a multi-message JSON:\n"
            "{\n"
            '  "messages": [\n'
            '    {"text": "First message", "delay": 1},\n'
            '    {"text": "Second message", "delay": 2}\n'
            '  ]\n'
            "}\n"
            "If multi-messages are present, each will be sent with the specified delay."
        )
        
        # Генерируем ответ с помощью Gemini
        try:
            ai_response = self.ai.generate_response(context, message)
            logger.info(f"AI response received: {ai_response}")
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            # Check if it's a quota/rate limit error (429)
            if "429" in str(e) or "Resource has been exhausted" in str(e) or "quota" in str(e).lower():
                logger.warning("API quota or rate limit reached, using simplified response")
                # Create a simple response when API quota is exceeded
                ai_response = {
                    "text": "Извини, мне нужно немного подумать...",
                    "emotion": "thoughtful",
                    "relationship_changes": {"general": 0}
                }
            else:
                # For other errors, re-raise
                raise
        
        # Если ответ пустой или содержит только пробелы, используем запасной ответ
        if not ai_response.get("text", "").strip():
            ai_response["text"] = "Я подумаю над этим..."
        
        # Ensure emotion is valid
        emotion = ai_response.get("emotion", "neutral")
        if isinstance(emotion, dict):
            emotion = emotion.get("name", "neutral")
        if emotion not in ["happy", "sad", "angry", "excited", "anxious", "neutral"]:
            emotion = "neutral"
        
        # Handle multiple messages
        multi_messages = ai_response.get("messages", [])
        if multi_messages:
            ai_response["text"] = ""  # Clear single message if multi_messages exist
            final_responses = []
            for msg_info in multi_messages:
                emotion = msg_info.get("emotion", "neutral")
                if isinstance(emotion, dict):
                    emotion = emotion.get("name", "neutral")
                if emotion not in ["happy", "sad", "angry", "excited", "anxious", "neutral"]:
                    emotion = "neutral"
                msg_info["emotion"] = emotion
                
                text = msg_info.get("text", "")
                
                # Get or calculate appropriate delay based on message content
                delay = msg_info.get("delay")
                if delay is None:
                    # Calculate dynamic delay based on message length and content
                    delay = self._calculate_message_delay(text, emotion)
                
                bot_submsg = self.create_bot_message(
                    user_id=user_id,
                    partner_id=partner_id,
                    content=text,
                    emotion=emotion
                )
                final_responses.append({
                    "id": str(bot_submsg.message_id),
                    "text": text,
                    "delay": delay,
                    "typing_status": "typing",
                    "emotion": emotion
                })
            return {"multi_messages": final_responses}

        # Создаем сообщение от бота
        bot_message = self.create_bot_message(
            user_id=user_id,
            partner_id=partner_id,
            content=ai_response["text"],
            emotion=emotion
        )
        
        # Ensure relationship changes are always present
        relationship_changes = ai_response.get("relationship_changes", {})
        if not relationship_changes or "general" not in relationship_changes:
            # Use the analyze_recent_changes method which we know exists and returns relationship info
            relationship_info = self.love_rating_service.analyze_recent_changes(user_id, partner_id)
            rating = relationship_info.get("current_rating", 50)
            
            # Initialize relationship changes with at least a general field
            if not relationship_changes:
                relationship_changes = {"general": 0}
            if "general" not in relationship_changes:
                relationship_changes["general"] = 0
            
            # Add friendliness indicator based on current rating
            relationship_changes["friendliness"] = rating / 100.0  # Convert to scale 0-1
        
        # Apply relationship changes from AI response
        for rel_type, change_value in relationship_changes.items():
            if rel_type == "general" and change_value != 0:
                # Преобразуем изменения в целочисленное значение для совместимости
                delta = int(change_value * 10) if abs(change_value) < 1 else int(change_value)
                self.love_rating_service.update_rating(user_id, partner_id, delta)
        
        # Get updated relationship data after changes
        updated_relationship_info = self.love_rating_service.analyze_recent_changes(user_id, partner_id)
        current_rating = updated_relationship_info.get("current_rating", 50)
        
        # Ensure emotion is in the correct format for the response model
        emotion_object = {
            "name": emotion,
            "intensity": 0.8,
            "timestamp": bot_message.created_at.isoformat()
        }
        
        # Get change values for different relationship aspects
        general_change = relationship_changes.get("general", 0)
        
        # Calculate different relationship aspects with more dynamic changes
        friendship_value = min(1.0, current_rating / 80.0)
        friendship_change = general_change / 20.0  # More noticeable changes
        
        romance_value = min(1.0, max(0, current_rating - 40) / 60.0)
        romance_change = general_change / 15.0 if current_rating > 40 else 0
        
        trust_value = min(1.0, current_rating / 90.0)
        trust_change = general_change / 25.0
        
        # Enhanced relationship metrics with more expressive values and changes
        relationship_metrics = {
            # Core numeric values with formatted display values
            "rating": {
                "value": current_rating,
                "display": f"{current_rating}%",
                "max": 100,
                "change": general_change,
                "change_display": f"{'+' if general_change > 0 else ''}{general_change}%"
            },
            
            # Key emotional metrics with changes (for UI animations)
            "emotions": {
                "friendship": {
                    "value": friendship_value,
                    "percentage": int(friendship_value * 100),
                    "display": f"{int(friendship_value * 100)}%",
                    "change": friendship_change,
                    "change_display": f"{'+' if friendship_change > 0 else ''}{friendship_change:.2f}"
                },
                "romance": {
                    "value": romance_value,
                    "percentage": int(romance_value * 100),
                    "display": f"{int(romance_value * 100)}%",
                    "change": romance_change,
                    "change_display": f"{'+' if romance_change > 0 else ''}{romance_change:.2f}"
                },
                "trust": {
                    "value": trust_value,
                    "percentage": int(trust_value * 100),
                    "display": f"{int(trust_value * 100)}%",
                    "change": trust_change,
                    "change_display": f"{'+' if trust_change > 0 else ''}{trust_change:.2f}"
                }
            },
            
            # Additional indicators with emojis for visual appeal
            "indicators": {
                "affection": {
                    "value": min(1.0, current_rating / 100.0),
                    "emoji": self._get_affection_emoji(current_rating),
                    "label": self._get_affection_label(current_rating)
                },
                "mood": {
                    "value": self._calculate_mood_value(current_rating, general_change),
                    "emoji": self._get_mood_emoji(current_rating, general_change),
                    "label": self._get_relationship_mood(current_rating, relationship_changes)
                },
                "intimacy": {
                    "value": min(1.0, max(0, current_rating - 50) / 50.0),
                    "emoji": "💕" if current_rating > 75 else ("💬" if current_rating > 50 else "👋"),
                    "label": "Интимно" if current_rating > 75 else ("Близко" if current_rating > 50 else "Формально")
                }
            },
            
            # Textual descriptions with emojis
            "status": {
                "level": self._calculate_relationship_level(current_rating),
                "label": self._get_relationship_status(current_rating),
                "emoji": self._get_status_emoji(current_rating),
                "description": self._get_status_description(current_rating)
            },
            
            # Visually appealing representation for UI
            "visual": {
                "color": self._get_relationship_color(current_rating),
                "gradient": self._get_relationship_gradient(current_rating),
                "icon": self._get_relationship_icon(current_rating),
                "progress": current_rating / 100.0,
                "style": self._get_relationship_style(current_rating)
            },
            
            # Summary of changes in readable format with emojis
            "changes": {
                "summary": self._format_changes_summary(relationship_changes),
                "details": [
                    {
                        "type": "friendship",
                        "value": friendship_change,
                        "display": f"{'+' if friendship_change > 0 else ''}{friendship_change:.2f}",
                        "emoji": "🤝" if friendship_change > 0 else ("💔" if friendship_change < 0 else "🤝")
                    },
                    {
                        "type": "romance",
                        "value": romance_change,
                        "display": f"{'+' if romance_change > 0 else ''}{romance_change:.2f}",
                        "emoji": "❤️" if romance_change > 0 else ("💔" if romance_change < 0 else "❤️")
                    },
                    {
                        "type": "trust",
                        "value": trust_change,
                        "display": f"{'+' if trust_change > 0 else ''}{trust_change:.2f}",
                        "emoji": "🔒" if trust_change > 0 else ("🔓" if trust_change < 0 else "🔒")
                    }
                ],
                "history": updated_relationship_info.get("recent_changes", [])
            },
            
            # Milestones with emojis and clear progress
            "milestones": self._get_enhanced_relationship_milestones(current_rating)
        }
        
        # Create a simple, clear display string for relationship changes
        friendship_display = f"дружба: {int(friendship_value * 100)}% ({'+' if friendship_change > 0 else ''}{friendship_change:.2f})"
        romance_display = f"романтика: {int(romance_value * 100)}% ({'+' if romance_change > 0 else ''}{romance_change:.2f})"
        trust_display = f"доверие: {int(trust_value * 100)}% ({'+' if trust_change > 0 else ''}{trust_change:.2f})"
        
        relationship_display = (
            f"Отношения: {current_rating}% {self._get_status_emoji(current_rating)} | "
            f"{friendship_display} | {romance_display} | {trust_display}"
        )
        
        # Get relationship mood description
        relationship_mood = self._get_relationship_mood(current_rating, relationship_changes)
        
        # Create relationship summary with emoji
        relationship_summary = f"{self._get_status_emoji(current_rating)} {self._get_relationship_status(current_rating)} - {relationship_mood}"
        
        return {
            "id": str(bot_message.message_id),
            "text": bot_message.content,
            "photo_url": None,
            "timestamp": bot_message.created_at,
            "relationship_changes": relationship_changes,
            "relationship": relationship_metrics,
            "relationship_display": relationship_display,  # Simple text display
            "relationship_summary": relationship_summary,  # Text summary with emoji
            "emotion": emotion_object
        }
    
    def _format_changes_summary(self, changes: Dict[str, Any]) -> str:
        """Format relationship changes into a human-readable summary with emojis."""
        general_change = changes.get("general", 0)
        if general_change == 0:
            return "Без изменений 🔄"
        elif general_change > 5:
            return f"Значительное улучшение отношений ⬆️⬆️ (+{general_change})"
        elif general_change > 0:
            return f"Улучшение отношений ⬆️ (+{general_change})"
        elif general_change < -5:
            return f"Значительное ухудшение отношений ⬇️⬇️ ({general_change})"
        else:
            return f"Ухудшение отношений ⬇️ ({general_change})"
    
    def _calculate_mood_value(self, rating: int, change: float) -> float:
        """Calculate a numeric value for mood based on rating and recent change."""
        # Base mood on current rating
        base_mood = rating / 100.0
        
        # Adjust based on recent change
        if change > 5:
            mood_boost = 0.2
        elif change > 0:
            mood_boost = 0.1
        elif change < -5:
            mood_boost = -0.2
        elif change < 0:
            mood_boost = -0.1
        else:
            mood_boost = 0
        
        # Return value clamped between 0 and 1
        return max(0.0, min(1.0, base_mood + mood_boost))

    def _get_mood_emoji(self, rating: int, change: float) -> str:
        """Get emoji representing the current relationship mood."""
        if change > 5:
            return "😍"
        elif change > 2:
            return "😊"
        elif change < -5:
            return "😢"
        elif change < -2:
            return "😕"
        else:
            # No significant change, base on absolute rating
            if rating < 30:
                return "😐"
            elif rating < 50:
                return "🙂"
            elif rating < 70:
                return "😊"
            elif rating < 90:
                return "😍"
            else:
                return "❤️"

    def _get_affection_emoji(self, rating: int) -> str:
        """Get emoji representing affection level."""
        if rating < 20:
            return "🧊"  # Ice (cold)
        elif rating < 40:
            return "👋"  # Wave (acquaintance)
        elif rating < 60:
            return "🤝"  # Handshake (friendly)
        elif rating < 80:
            return "🫂"  # Hug (close)
        elif rating < 95:
            return "💕"  # Love (romantic)
        else:
            return "❤️‍🔥"  # Burning heart (deep love)
            
    def _get_affection_label(self, rating: int) -> str:
        """Get text label for affection level."""
        if rating < 20:
            return "Холодно"
        elif rating < 40:
            return "Сдержанно"
        elif rating < 60:
            return "Дружелюбно"
        elif rating < 80:
            return "Близко"
        elif rating < 95:
            return "Романтично"
        else:
            return "Страстно"
            
    def _get_status_emoji(self, rating: int) -> str:
        """Get emoji representing relationship status."""
        if rating < 20:
            return "🧊"  # Cold
        elif rating < 40:
            return "👤"  # Acquaintance
        elif rating < 60:
            return "👭"  # Friends
        elif rating < 80:
            return "💫"  # Close friends
        elif rating < 95:
            return "💘"  # Romance
        else:
            return "💞"  # Deep love
            
    def _get_status_description(self, rating: int) -> str:
        """Get a detailed description of the relationship status."""
        if rating < 20:
            return "Отношения в самом начале или напряженные"
        elif rating < 40:
            return "Знакомые, общение на формальном уровне"
        elif rating < 60:
            return "Дружеские отношения, общие интересы"
        elif rating < 80:
            return "Близкая дружба, доверительные отношения"
        elif rating < 95:
            return "Романтические чувства, сильная привязанность"
        else:
            return "Глубокая эмоциональная связь и привязанность"
    
    def _get_relationship_gradient(self, rating: int) -> str:
        """Get a CSS gradient for visual representation."""
        if rating < 20:
            return "linear-gradient(135deg, #6c757d, #495057)"
        elif rating < 40:
            return "linear-gradient(135deg, #17a2b8, #138496)"
        elif rating < 60:
            return "linear-gradient(135deg, #28a745, #218838)"
        elif rating < 80:
            return "linear-gradient(135deg, #ffc107, #e0a800)"
        elif rating < 95:
            return "linear-gradient(135deg, #e83e8c, #d81b60)"
        else:
            return "linear-gradient(135deg, #dc3545, #c82333)"
            
    def _get_relationship_style(self, rating: int) -> str:
        """Get a style keyword for UI display."""
        if rating < 20:
            return "cold"
        elif rating < 40:
            return "casual"
        elif rating < 60:
            return "friendly"
        elif rating < 80:
            return "close"
        elif rating < 95:
            return "romantic"
        else:
            return "passionate"

    def _get_enhanced_relationship_milestones(self, rating: int) -> List[Dict[str, Any]]:
        """Get enhanced relationship milestones with emojis and detailed info."""
        milestones = []
        
        milestone_definitions = [
            {"level": 20, "name": "Знакомство", "emoji": "👋", "description": "Начало знакомства"},
            {"level": 40, "name": "Дружба", "emoji": "🤝", "description": "Зарождение дружбы"},
            {"level": 60, "name": "Близость", "emoji": "🫂", "description": "Формирование близости"},
            {"level": 80, "name": "Романтика", "emoji": "💕", "description": "Романтические чувства"},
            {"level": 95, "name": "Любовь", "emoji": "❤️", "description": "Глубокая привязанность"}
        ]
        
        for milestone in milestone_definitions:
            progress = min(1.0, rating / milestone["level"]) if rating < milestone["level"] else 1.0
            achieved = rating >= milestone["level"]
            
            milestones.append({
                "name": milestone["name"],
                "emoji": milestone["emoji"],
                "description": milestone["description"],
                "achieved": achieved,
                "progress": progress,
                "progress_display": f"{int(progress * 100)}%",
                "next": not achieved and (len(milestones) == 0 or milestones[-1]["achieved"]),
                "style": "completed" if achieved else ("active" if progress > 0 else "locked")
            })
        
        return milestones

    def process_user_message(self, user_id: UUID, partner_id: UUID, content: str) -> Dict[str, Any]:
        """
        Полный процесс обработки сообщения пользователя:
        1. Сохранение сообщения пользователя
        2. Применение эффектов к рейтингу
        3. Генерация ответа бота
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            content: Текст сообщения
            
        Returns:
            Словарь с ответом бота
        """
        # Log the incoming message for debugging
        import logging
        import random
        logger = logging.getLogger(__name__)
        logger.info(f"Processing user message: '{content}' for partner {partner_id}")
        
        # Создаем сообщение пользователя
        user_message = self.create_user_message(
            user_id=user_id,
            partner_id=partner_id,
            content=content
        )
        
        # Получаем последние несколько сообщений для проверки на повторы
        recent_messages = self.db.query(Message).filter(
            Message.user_id == user_id,
            Message.partner_id == partner_id,
            Message.sender_type == "bot"
        ).order_by(desc(Message.created_at)).limit(10).all()
        
        recent_bot_texts = [msg.content for msg in recent_messages]
        logger.debug(f"Recent bot messages: {recent_bot_texts}")
        
        try:
            # Генерируем ответ бота
            bot_response = self.generate_bot_response(user_id, partner_id, content)
            
            # Check if this is a multi-message response and return it directly if so
            if "multi_messages" in bot_response:
                # Add timestamp to each message if missing
                current_time = datetime.now()
                for msg in bot_response["multi_messages"]:
                    if "timestamp" not in msg:
                        msg["timestamp"] = current_time.isoformat()
                
                # Explicitly set the is_multi_message flag to help frontend
                bot_response["is_multi_message"] = True
                
                return bot_response
            
            # Проверяем, не повторяется ли ответ
            response_text = bot_response.get("text", "")
            
            # Check if response is from JSON format (Gemini sometimes returns raw JSON)
            if response_text.startswith("```json") and response_text.endswith("```"):
                try:
                    # Extract the JSON content
                    json_text = response_text.replace("```json", "").replace("```", "").strip()
                    logger.debug(f"Extracted JSON from code block: {json_text[:100]}...")
                    json_data = json.loads(json_text)
                    
                    # Check if this is a multi-message response format
                    if "messages" in json_data:
                        # Process multi-message format
                        multi_messages = json_data.get("messages", [])
                        relationship_changes = json_data.get("relationship_changes", {"general": 0})
                        
                        # Create bot messages for each message in the array
                        final_responses = []
                        for msg_info in multi_messages:
                            emotion = msg_info.get("emotion", "neutral")
                            if isinstance(emotion, dict):
                                emotion = emotion.get("name", "neutral")
                            if emotion not in ["happy", "sad", "angry", "excited", "anxious", "neutral"]:
                                emotion = "neutral"
                            
                            text = msg_info.get("text", "")
                            delay = msg_info.get("delay", 1)
                            
                            bot_submsg = self.create_bot_message(
                                user_id=user_id,
                                partner_id=partner_id,
                                content=text,
                                emotion=emotion
                            )
                            
                            final_responses.append({
                                "id": str(bot_submsg.message_id),
                                "text": text,
                                "delay": delay,
                                "typing_status": "typing",
                                "emotion": emotion,
                                "timestamp": bot_submsg.created_at.isoformat()
                            })
                        
                        # Return multi-messages response with additional required fields
                        # Get the first message to use for required fields
                        first_msg = final_responses[0] if final_responses else {}
                        return {
                            "multi_messages": final_responses,
                            "relationship_changes": relationship_changes,
                            # Add required fields from schema
                            "id": first_msg.get("id", str(uuid4())),
                            "text": first_msg.get("text", ""),
                            "timestamp": datetime.now(),
                            "emotion": {
                                "name": first_msg.get("emotion", "neutral"),
                                "intensity": 0.8,
                                "timestamp": datetime.now().isoformat()
                            },
                            # Explicitly set the is_multi_message flag
                            "is_multi_message": True
                        }
                    # If it's a regular single message JSON response, update the bot_response
                    if "text" in json_data:
                        # Update the core message content
                        bot_response["text"] = json_data["text"]
                        
                        # Update emotion if present
                        if "emotion" in json_data:
                            emotion = json_data["emotion"]
                            if isinstance(emotion, dict):
                                emotion = emotion.get("name", "neutral")
                            if emotion not in ["happy", "sad", "angry", "excited", "anxious", "neutral"]:
                                emotion = "neutral"
                                
                            # Update the bot message in the database with the correct emotion
                            bot_message = self.db.query(Message).filter(Message.message_id == UUID(bot_response["id"])).first()
                            if bot_message:
                                bot_message.emotion = emotion
                                self.db.commit()
                                
                            # Update the response emotion
                            bot_response["emotion"] = {
                                "name": emotion,
                                "intensity": 0.8,
                                "timestamp": datetime.now().isoformat()
                            }
                        
                        # Update relationship changes if present
                        if "relationship_changes" in json_data:
                            bot_response["relationship_changes"] = json_data["relationship_changes"]
                            
                            # Process relationship changes properly
                            relationship_changes = json_data["relationship_changes"]
                            general_change = relationship_changes.get("general", 0)
                            if general_change != 0:
                                # Apply the relationship changes
                                delta = int(general_change * 10) if abs(general_change) < 1 else int(general_change)
                                self.love_rating_service.update_rating(user_id, partner_id, delta)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON from response: {response_text}")
                    # Keep the response as is if parsing fails
            
            if response_text in recent_bot_texts:
                logger.warning(f"Detected repeated response: '{response_text}'. Requesting new response.")
                
                try:
                    # Request a fresh response from the AI
                    retry_bot_response = self.generate_bot_response(user_id, partner_id, content)
                    retry_text = retry_bot_response.get("text", "")
                    
                    # Only use the new response if it's different
                    if retry_text and retry_text != response_text and retry_text not in recent_bot_texts:
                        bot_response = retry_bot_response
                except Exception as retry_error:
                    # If retry fails, keep the original response
                    logger.warning(f"Retry failed: {str(retry_error)}, keeping original response")
            
            # Always append relationship information to the message
            relationship_changes = bot_response.get("relationship_changes", {})
            general_change = relationship_changes.get("general", 0)
            friendship_change = relationship_changes.get("friendship", general_change / 20.0)
            romance_change = relationship_changes.get("romance", general_change / 15.0 if bot_response["relationship"]["rating"]["value"] > 40 else 0)
            trust_change = relationship_changes.get("trust", general_change / 25.0)
            
            # Format changes for display, always include at least friendship
            changes_display = []
            
            # Filter out very small changes and use Russian terms with emojis
            if abs(friendship_change) > 0.01:
                changes_display.append(f"дружба: {'+' if friendship_change > 0 else ''}{friendship_change:.2f} 🤝")
            if abs(romance_change) > 0.01:
                changes_display.append(f"симпатия: {'+' if romance_change > 0 else ''}{romance_change:.2f} 💖")
            if abs(trust_change) > 0.01:
                changes_display.append(f"доверие: {'+' if trust_change > 0 else ''}{trust_change:.2f} 🔒")
            
            # If no specific changes, show a general change if it exists
            if not changes_display and abs(general_change) > 0:
                changes_display.append(f"отношения: {'+' if general_change > 0 else ''}{general_change} 💫")
            
            # Show elegant, minimalistic display
            if changes_display:
                # Get emoji indicator for the direction of the relationship
                direction_emoji = "⬆️" if general_change > 0 else ("⬇️" if general_change < 0 else "")
                
                # Append changes to message with attractive formatting
                updated_content = f"{bot_response['text']}\n\n{direction_emoji} {' • '.join(changes_display)}"
            else:
                # If there are no changes, don't show anything
                updated_content = bot_response['text']
            
            # Update the message in the database
            bot_message = self.db.query(Message).filter(Message.message_id == UUID(bot_response["id"])).first()
            if bot_message:
                bot_message.content = updated_content
                self.db.commit()
            
            # Update the response text
            bot_response["text"] = updated_content
            
            return bot_response
            
        except Exception as e:
            logger.exception(f"Error in process_user_message: {e}")
            
            # Get relationship info using the known working method
            relationship_info = self.love_rating_service.analyze_recent_changes(user_id, partner_id)
            current_rating = relationship_info.get("current_rating", 50)
            
            # Create fallback relationship metrics with the same enhanced format
            relationship_metrics = {
                # Core numeric values with formatted display values
                "rating": {
                    "value": current_rating,
                    "display": f"{current_rating}%",
                    "max": 100,
                    "change": 0,
                    "change_display": "0%"
                },
                
                # Key emotional metrics without changes
                "emotions": {
                    "friendship": {
                        "value": min(1.0, current_rating / 80.0),
                        "percentage": int(min(1.0, current_rating / 80.0) * 100),
                        "display": f"{int(min(1.0, current_rating / 80.0) * 100)}%",
                        "change": 0,
                        "change_display": "0"
                    },
                    "romance": {
                        "value": min(1.0, max(0, current_rating - 40) / 60.0),
                        "percentage": int(min(1.0, max(0, current_rating - 40) / 60.0) * 100),
                        "display": f"{int(min(1.0, max(0, current_rating - 40) / 60.0) * 100)}%",
                        "change": 0,
                        "change_display": "0"
                    },
                    "trust": {
                        "value": min(1.0, current_rating / 90.0),
                        "percentage": int(min(1.0, current_rating / 90.0) * 100),
                        "display": f"{int(min(1.0, current_rating / 90.0) * 100)}%",
                        "change": 0,
                        "change_display": "0"
                    }
                },
                
                # Other fields same as in normal response
                "indicators": {
                    "affection": {
                        "value": min(1.0, current_rating / 100.0),
                        "emoji": self._get_affection_emoji(current_rating),
                        "label": self._get_affection_label(current_rating)
                    },
                    "mood": {
                        "value": self._calculate_mood_value(current_rating, 0),
                        "emoji": self._get_mood_emoji(current_rating, 0),
                        "label": "Нейтральное"
                    },
                    "intimacy": {
                        "value": min(1.0, max(0, current_rating - 50) / 50.0),
                        "emoji": "💕" if current_rating > 75 else ("💬" if current_rating > 50 else "👋"),
                        "label": "Интимно" if current_rating > 75 else ("Близко" if current_rating > 50 else "Формально")
                    }
                },
                
                "status": {
                    "level": self._calculate_relationship_level(current_rating),
                    "label": self._get_relationship_status(current_rating),
                    "emoji": self._get_status_emoji(current_rating),
                    "description": self._get_status_description(current_rating)
                },
                
                "visual": {
                    "color": self._get_relationship_color(current_rating),
                    "gradient": self._get_relationship_gradient(current_rating),
                    "icon": self._get_relationship_icon(current_rating),
                    "progress": current_rating / 100.0,
                    "style": self._get_relationship_style(current_rating)
                },
                
                "changes": {
                    "summary": "Без изменений 🔄",
                    "details": [
                        {"type": "friendship", "value": 0, "display": "0", "emoji": "🤝"},
                        {"type": "romance", "value": 0, "display": "0", "emoji": "❤️"},
                        {"type": "trust", "value": 0, "display": "0", "emoji": "🔒"}
                    ],
                    "history": relationship_info.get("recent_changes", [])
                },
                
                "milestones": self._get_enhanced_relationship_milestones(current_rating)
            }
            
            # Create simple display strings for error cases too
            friendship_value = min(1.0, current_rating / 80.0)
            romance_value = min(1.0, max(0, current_rating - 40) / 60.0)
            trust_value = min(1.0, current_rating / 90.0)
            
            friendship_display = f"дружба: {int(friendship_value * 100)}%"
            romance_display = f"романтика: {int(romance_value * 100)}%"
            trust_display = f"доверие: {int(trust_value * 100)}%"
            
            relationship_display = (
                f"Отношения: {current_rating}% {self._get_status_emoji(current_rating)} | "
                f"{friendship_display} | {romance_display} | {trust_display}"
            )
            
            relationship_summary = f"{self._get_status_emoji(current_rating)} {self._get_relationship_status(current_rating)} - Нейтральное"
            
            # Return minimal response with relationship data
            bot_message = self.create_bot_message(
                user_id=user_id,
                partner_id=partner_id,
                content="...",
                emotion="neutral"
            )
            
            return {
                "id": str(bot_message.message_id),
                "text": "...",
                "photo_url": None,
                "timestamp": bot_message.created_at,
                "relationship_changes": {"general": 0},
                "relationship": relationship_metrics,
                "relationship_display": relationship_display,  # Simple text display
                "relationship_summary": relationship_summary,  # Text summary with emoji
                "emotion": {
                    "name": "neutral",
                    "intensity": 0.5,
                    "timestamp": bot_message.created_at.isoformat()
                }
            }
    
    def _calculate_relationship_level(self, rating: int) -> int:
        """Calculate relationship level based on rating."""
        if rating < 20:
            return 1
        elif rating < 40:
            return 2
        elif rating < 60:
            return 3
        elif rating < 80:
            return 4
        else:
            return 5
    
    def _get_relationship_status(self, rating: int) -> str:
        """Get a text description of relationship status based on rating."""
        if rating < 20:
            return "Холодные"
        elif rating < 40:
            return "Знакомые"
        elif rating < 60:
            return "Друзья"
        elif rating < 80:
            return "Близкие друзья"
        elif rating < 95:
            return "Романтические отношения"
        else:
            return "Глубокая привязанность"
    
    def _get_relationship_mood(self, rating: int, changes: Dict[str, Any]) -> str:
        """Get the current mood of the relationship based on rating and recent changes."""
        # Get the general change value
        change = changes.get("general", 0)
        
        if change > 5:
            return "Восторженное"
        elif change > 2:
            return "Улучшающееся"
        elif change < -5:
            return "Ухудшающееся"
        elif change < -2:
            return "Напряженное"
        else:
            # No significant change, base on absolute rating
            if rating < 30:
                return "Прохладное"
            elif rating < 50:
                return "Нейтральное"
            elif rating < 70:
                return "Дружелюбное"
            elif rating < 90:
                return "Теплое"
            else:
                return "Влюбленное"
    
    def _get_relationship_color(self, rating: int) -> str:
        """Get a color code representing the relationship level for UI display."""
        if rating < 20:
            return "#6c757d"  # Gray
        elif rating < 40:
            return "#17a2b8"  # Teal
        elif rating < 60:
            return "#28a745"  # Green
        elif rating < 80:
            return "#ffc107"  # Yellow
        elif rating < 95:
            return "#e83e8c"  # Pink
        else:
            return "#dc3545"  # Red
    
    def _get_relationship_icon(self, rating: int) -> str:
        """Get an icon name representing the relationship level for UI display."""
        if rating < 20:
            return "person"
        elif rating < 40:
            return "chat"
        elif rating < 60:
            return "people"
        elif rating < 80:
            return "favorite_border"
        elif rating < 95:
            return "favorite"
        else:
            return "emoji_emotions"
    
    def _calculate_message_delay(self, text: str, emotion: str = "neutral") -> int:
        """
        Calculate an appropriate delay for a message based on its content.
        
        Args:
            text: The message text
            emotion: The emotion associated with the message
            
        Returns:
            Appropriate delay in seconds
        """
        # Base delay on message length
        message_length = len(text)
        
        # Short messages (greetings, quick responses)
        if message_length < 20:
            base_delay = 1
        # Medium messages (normal conversation)
        elif message_length < 80:
            base_delay = 2
        # Long messages (explanations, stories)
        elif message_length < 200:
            base_delay = 3
        # Very long messages (detailed responses)
        else:
            base_delay = 4
        
        # Adjust for emotion
        emotion_factor = 1.0
        if emotion in ["excited", "angry"]:
            # Excited or angry messages come more quickly
            emotion_factor = 0.8
        elif emotion in ["sad", "anxious"]:
            # Sad or anxious messages take longer to compose
            emotion_factor = 1.3
        
        # Add randomness for natural feel (±20%)
        import random
        randomness = random.uniform(0.8, 1.2)
        
        # Calculate final delay with minimum of 1 second
        delay = max(1, round(base_delay * emotion_factor * randomness))
        
        return delay
