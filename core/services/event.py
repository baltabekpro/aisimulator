from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from core.db.models.event import Event
from core.services.base import BaseService
from core.services.love_rating import LoveRatingService

class EventService(BaseService):
    """Service for handling Event operations."""
    
    def __init__(self, db: Session):
        super().__init__(Event, db)
        self.love_rating_service = LoveRatingService(db)
    
    def get_by_user_id(self, user_id: UUID) -> List[Event]:
        """Get all events for a specific user."""
        return self.db.query(Event).filter(Event.user_id == user_id).all()
    
    def get_by_partner_id(self, partner_id: UUID) -> List[Event]:
        """Get all events for a specific AI partner."""
        return self.db.query(Event).filter(Event.partner_id == partner_id).all()
    
    def get_by_type(self, event_type: str) -> List[Event]:
        """Get all events of a specific type."""
        return self.db.query(Event).filter(Event.type == event_type).all()
    
    def get_by_status(self, status: str) -> List[Event]:
        """Get all events with a specific status."""
        return self.db.query(Event).filter(Event.status == status).all()
    
    def create_event(self, *, user_id: UUID, partner_id: UUID, event_type: str,
                   status: str = "pending", schedule: Dict = None, 
                   details: Dict = None) -> Event:
        """Create a new event."""
        event_data = {
            "user_id": user_id,
            "partner_id": partner_id,
            "type": event_type,
            "status": status,
            "schedule": schedule or {},
            "details": details or {}
        }
        return self.create(obj_in=event_data)
    
    def update_status(self, *, event_id: UUID, status: str) -> Optional[Event]:
        """Update just the event status."""
        return self.update(id=event_id, obj_in={"status": status})
    
    # Новые методы для реализации бизнес-логики
    
    def complete_event(self, event_id: UUID) -> Event:
        """
        Отмечает событие как завершенное и применяет соответствующие эффекты.
        
        Args:
            event_id: UUID события
            
        Returns:
            Обновленное событие
        """
        event = self.get(event_id)
        if not event:
            raise ValueError(f"Event with ID {event_id} not found")
        
        if event.status == "completed":
            return event  # Событие уже завершено
        
        # Обновляем статус
        event.status = "completed"
        
        # Обрабатываем разные типы событий
        if event.type == "daily":
            # Небольшое изменение рейтинга для ежедневных событий
            self.love_rating_service.update_rating(
                event.user_id, 
                event.partner_id, 
                delta=2
            )
        elif event.type == "quest":
            # Квесты дают больше бонусов
            self.love_rating_service.update_rating(
                event.user_id, 
                event.partner_id, 
                delta=5
            )
        elif event.type == "global":
            # Глобальные события могут давать специальные награды
            self.love_rating_service.update_rating(
                event.user_id, 
                event.partner_id, 
                delta=10
            )
        
        # Добавляем информацию о завершении
        if not event.details:
            event.details = {}
        
        event.details["completed_at"] = datetime.utcnow().isoformat()
        event.details["reward_applied"] = True
        
        # Сохраняем изменения
        self.db.commit()
        self.db.refresh(event)
        
        return event
    
    def generate_event(self, user_id: UUID, partner_id: UUID) -> Event:
        """
        Генерирует новое случайное событие для пары.
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            
        Returns:
            Созданное событие
        """
        # Получаем текущий рейтинг для определения типа события
        rating = self.love_rating_service.get_by_user_and_partner(user_id, partner_id)
        score = rating.score if rating else 50
        
        # Типы событий в зависимости от рейтинга
        event_types = {
            "daily": ["совместный завтрак", "прогулка", "обмен сообщениями"],
            "quest": ["помощь в работе", "совместное хобби", "личная встреча"],
            "global": ["романтическое свидание", "путешествие", "особое мероприятие"]
        }
        
        # Выбираем тип события на основе рейтинга
        if score < 30:
            event_type = "daily"
        elif score < 70:
            event_type = random.choice(["daily", "quest"])
        else:
            event_type = random.choice(["daily", "quest", "global"])
        
        # Выбираем конкретное описание события
        event_name = random.choice(event_types[event_type])
        
        # Создаем расписание (для примера - в ближайшие 1-7 дней)
        days_ahead = random.randint(1, 7)
        schedule_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat()
        
        # Создаем детали события
        details = {
            "name": event_name,
            "description": f"Событие: {event_name}",
            "difficulty": random.randint(1, 5),
            "target_date": schedule_date
        }
        
        # Создаем событие
        return self.create_event(
            user_id=user_id,
            partner_id=partner_id,
            event_type=event_type,
            status="pending",
            schedule={"target_date": schedule_date},
            details=details
        )
    
    def check_due_events(self, user_id: UUID, partner_id: UUID) -> List[Event]:
        """
        Проверяет наличие событий, срок выполнения которых подходит.
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            
        Returns:
            Список событий, которые скоро наступят
        """
        now = datetime.utcnow()
        upcoming_events = []
        
        # Получаем все активные события
        pending_events = self.db.query(Event).filter(
            Event.user_id == user_id,
            Event.partner_id == partner_id,
            Event.status == "pending"
        ).all()
        
        for event in pending_events:
            if not event.schedule or "target_date" not in event.schedule:
                continue
                
            # Парсим дату события
            try:
                target_date = datetime.fromisoformat(event.schedule["target_date"])
                
                # Проверяем, близко ли событие (в пределах 24 часов)
                time_delta = target_date - now
                if 0 <= time_delta.total_seconds() <= 86400:  # 24 часа в секундах
                    upcoming_events.append(event)
            except (ValueError, TypeError):
                continue
        
        return upcoming_events
    
    def get_active_event_context(self, user_id: UUID, partner_id: UUID) -> Dict:
        """
        Получает контекст активных событий для диалога.
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            
        Returns:
            Словарь с контекстом для диалога
        """
        upcoming_events = self.check_due_events(user_id, partner_id)
        
        if not upcoming_events:
            return {"has_events": False}
        
        # Формируем контекст на основе ближайшего события
        next_event = upcoming_events[0]
        
        context = {
            "has_events": True,
            "event_type": next_event.type,
            "event_name": next_event.details.get("name", "событие"),
            "event_description": next_event.details.get("description", ""),
            "event_date": next_event.schedule.get("target_date", ""),
            "days_left": "скоро"  # Можно рассчитать точнее при необходимости
        }
        
        return context
