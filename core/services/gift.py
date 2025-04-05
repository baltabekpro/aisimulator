from typing import Dict, Any, Tuple, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

from core.db.models.gift import Gift
from core.db.models.gift_history import GiftHistory
from core.services.base import BaseService
from core.services.love_rating import LoveRatingService
from core.services.message import MessageService

# Список доступных подарков
AVAILABLE_GIFTS = [
    {
        "id": "flower", 
        "name": "Букет цветов", 
        "description": "Прекрасный букет свежих цветов",
        "emoji": "💐",
        "price": 10, 
        "effect": {
            "general": 3,
            "friendship": 1.5,
            "romance": 3.0,
            "trust": 1.0
        }
    },
    {
        "id": "chocolate", 
        "name": "Коробка конфет", 
        "description": "Вкусные шоколадные конфеты в красивой упаковке",
        "emoji": "🍫",
        "price": 15, 
        "effect": {
            "general": 5,
            "friendship": 2.0,
            "romance": 3.0,
            "trust": 1.5
        }
    },
    {
        "id": "jewelry", 
        "name": "Украшение", 
        "description": "Красивое украшение из драгоценных металлов",
        "emoji": "💍",
        "price": 50, 
        "effect": {
            "general": 15,
            "friendship": 3.0,
            "romance": 10.0,
            "trust": 5.0
        }
    },
    {
        "id": "perfume", 
        "name": "Духи", 
        "description": "Изысканный аромат, который покорит сердце",
        "emoji": "🧴",
        "price": 30, 
        "effect": {
            "general": 10,
            "friendship": 2.0,
            "romance": 7.0,
            "trust": 3.0
        }
    },
    {
        "id": "teddy", 
        "name": "Плюшевый мишка", 
        "description": "Милый и мягкий плюшевый мишка",
        "emoji": "🧸",
        "price": 20, 
        "effect": {
            "general": 7,
            "friendship": 4.0,
            "romance": 4.0,
            "trust": 2.0
        }
    },
    {
        "id": "vip_gift", 
        "name": "VIP Подарок", 
        "description": "Эксклюзивный подарок, который произведет незабываемое впечатление",
        "emoji": "✨",
        "price": 100, 
        "effect": {
            "general": 25,
            "friendship": 8.0,
            "romance": 15.0,
            "trust": 10.0
        }
    }
]

class GiftService(BaseService):
    """Сервис для работы с подарками."""
    
    def __init__(self, db: Session):
        super().__init__(Gift, db)
        self.love_rating_service = LoveRatingService(db)
    
    def get_available_gifts(self) -> List[Dict[str, Any]]:
        """Получить список доступных подарков."""
        return AVAILABLE_GIFTS
    
    def get_gift_by_id(self, gift_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о подарке по ID."""
        return next((g for g in AVAILABLE_GIFTS if g["id"] == gift_id), None)
    
    def send_gift(self, user_id: UUID, partner_id: UUID, gift_id: str) -> Dict[str, Any]:
        """
        Отправить подарок персонажу и обработать его эффект.
        
        Args:
            user_id: ID пользователя
            partner_id: ID партнера
            gift_id: ID подарка
            
        Returns:
            Словарь с информацией о результате отправки подарка
        """
        # Находим подарок по ID
        gift = self.get_gift_by_id(gift_id)
        if not gift:
            raise ValueError(f"Подарок с ID {gift_id} не найден")
        
        # Создаем запись в истории подарков
        gift_history = GiftHistory(
            user_id=user_id,
            partner_id=partner_id,
            gift_id=gift_id,
            gift_name=gift["name"],
            sent_at=datetime.utcnow()
        )
        self.db.add(gift_history)
        self.db.commit()
        
        # Применяем эффект подарка на рейтинг отношений
        effects = gift["effect"]
        general_effect = effects.get("general", 0)
        
        # Обновляем основной рейтинг
        if general_effect != 0:
            self.love_rating_service.update_rating(user_id, partner_id, general_effect)
        
        # Генерируем реакцию бота на подарок
        message_service = MessageService(db=self.db)
        gift_message = f"Пользователь подарил подарок {gift['name']} {gift['emoji']}! Пожалуйста, сгенерируй реакцию на подарок."
        ai_reaction = message_service.generate_bot_response(
            user_id=user_id,
            partner_id=partner_id,
            message=gift_message
        )
        
        # Check if this is a multi-message response
        if "multi_messages" in ai_reaction:
            # Already properly formatted, return as is
            return {
                "gift": gift,
                "reaction": ai_reaction,
                "relationship_changes": ai_reaction.get("relationship_changes", {"general": 0})
            }
        
        # Check if response contains JSON code block
        response_text = ai_reaction.get("text", "")
        if response_text.startswith("```json") and response_text.endswith("```"):
            try:
                # Extract the JSON content
                json_text = response_text.replace("```json", "").replace("```", "").strip()
                json_data = json.loads(json_text)
                
                # Check if this contains multi-message format
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
                        
                        bot_submsg = message_service.create_bot_message(
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
                    
                    # Replace raw response with properly parsed multi-message format
                    ai_reaction = {
                        "multi_messages": final_responses,
                        "relationship_changes": relationship_changes
                    }
                else:
                    # Update the AI reaction with the parsed content
                    ai_reaction["text"] = json_data.get("text", response_text)
                    if "emotion" in json_data:
                        ai_reaction["emotion"] = json_data["emotion"]
                    if "relationship_changes" in json_data:
                        ai_reaction["relationship_changes"] = json_data["relationship_changes"]
                    
            except json.JSONDecodeError:
                # Keep the response as is if parsing fails
                logging.getLogger(__name__).warning(f"Failed to parse JSON from gift response: {response_text[:100]}...")
        
        # Ensure emotion is properly formatted
        if isinstance(ai_reaction.get("emotion"), str):
            ai_reaction["emotion"] = {
                "name": ai_reaction["emotion"],
                "intensity": 0.8,
                "timestamp": datetime.now().isoformat()
            }
        
        # Ensure relationship changes are always present
        relationship_changes = ai_reaction.get("relationship_changes", {})
        if not relationship_changes or "general" not in relationship_changes:
            relationship_changes = {"general": 0}
        
        # Формируем результат
        return {
            "gift": gift,
            "reaction": ai_reaction,
            "relationship_changes": relationship_changes
        }
    
    def get_gift_history(self, user_id: UUID, partner_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить историю подарков для пары пользователь-партнер."""
        gift_history = self.db.query(GiftHistory).filter(
            GiftHistory.user_id == user_id,
            GiftHistory.partner_id == partner_id
        ).order_by(GiftHistory.sent_at.desc()).limit(limit).all()
        
        return [
            {
                "id": str(h.id),
                "gift_id": h.gift_id,
                "gift_name": h.gift_name,
                "sent_at": h.sent_at.isoformat()
            }
            for h in gift_history
        ]
