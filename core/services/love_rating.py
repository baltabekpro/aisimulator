from typing import Optional, Dict, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from core.db.models.love_rating import LoveRating
from core.services.base import BaseService

class LoveRatingService(BaseService):
    """Service for handling LoveRating operations."""
    
    def __init__(self, db: Session):
        super().__init__(LoveRating, db)
    
    def get_by_user_and_partner(self, user_id: UUID, partner_id: UUID) -> Optional[LoveRating]:
        """Get the love rating between a user and an AI partner."""
        return self.db.query(LoveRating).filter(
            LoveRating.user_id == user_id,
            LoveRating.partner_id == partner_id
        ).first()
    
    def create_rating(self, *, user_id: UUID, partner_id: UUID, score: int = 50) -> LoveRating:
        """Create a new love rating between a user and an AI partner."""
        # Ensure score is within valid range (0-100)
        score = max(0, min(100, score))
        
        rating_data = {
            "user_id": user_id,
            "partner_id": partner_id,
            "score": score
        }
        return self.create(obj_in=rating_data)
    
    def update_score(self, *, rating_id: UUID, score: int) -> Optional[LoveRating]:
        """Update just the love rating score."""
        # Ensure score is within valid range (0-100)
        score = max(0, min(100, score))
        return self.update(id=rating_id, obj_in={"score": score})
    
    def adjust_score(self, *, rating_id: UUID, adjustment: int) -> Optional[LoveRating]:
        """Adjust the love rating score by adding/subtracting points."""
        rating = self.get(rating_id)
        if not rating:
            return None
        
        new_score = max(0, min(100, rating.score + adjustment))
        return self.update(id=rating_id, obj_in={"score": new_score})
    
    # Новые методы для реализации бизнес-логики
    
    def update_rating(self, user_id: UUID, partner_id: UUID, delta: int) -> LoveRating:
        """
        Обновляет рейтинг любви между пользователем и AI-партнером.
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            delta: Изменение рейтинга (положительное или отрицательное)
            
        Returns:
            Обновленный объект рейтинга
        """
        rating = self.get_by_user_and_partner(user_id, partner_id)
        
        # Если рейтинг не существует, создаем новый с начальным значением 50
        if not rating:
            rating = self.create_rating(
                user_id=user_id,
                partner_id=partner_id,
                score=50
            )
        
        # Применяем изменение с учетом ограничений
        new_score = max(0, min(100, rating.score + delta))
        
        # Обновляем значение в БД
        self.update(id=rating.rating_id, obj_in={"score": new_score})
        
        # Обновляем объект в памяти
        rating.score = new_score
        
        return rating
    
    def get_relationship_stage(self, score: int) -> str:
        """
        Определяет стадию отношений на основе рейтинга любви.
        
        Args:
            score: Текущий рейтинг любви (0-100)
            
        Returns:
            Строка с описанием стадии отношений
        """
        if score < 20:
            return "неприязнь"
        elif score < 40:
            return "знакомство"
        elif score < 60:
            return "дружба"
        elif score < 80:
            return "симпатия"
        else:
            return "любовь"
    
    def analyze_recent_changes(self, user_id: UUID, partner_id: UUID, days: int = 7) -> Dict:
        """
        Анализирует изменения рейтинга за последние дни для определения тренда.
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            days: Количество дней для анализа
            
        Returns:
            Словарь с результатами анализа (тренд, изменения)
        """
        rating = self.get_by_user_and_partner(user_id, partner_id)
        if not rating:
            return {"trend": "neutral", "change": 0}
        
        # Здесь должен быть код для получения истории изменений
        # Для примера вернем фиктивные данные
        return {
            "trend": "positive" if rating.score > 50 else "negative",
            "change": rating.score - 50,
            "stage": self.get_relationship_stage(rating.score),
            "score": rating.score
        }
        
    def process_interaction(self, user_id: UUID, partner_id: UUID, 
                          interaction_type: str, content: str = None) -> Tuple[int, str]:
        """
        Обрабатывает взаимодействие пользователя и определяет изменение рейтинга.
        
        Args:
            user_id: UUID пользователя
            partner_id: UUID партнера
            interaction_type: Тип взаимодействия (message, gift, photo, etc.)
            content: Содержимое взаимодействия (если применимо)
            
        Returns:
            Кортеж (изменение_рейтинга, обоснование)
        """
        # Базовые правила изменения рейтинга
        delta = 0
        reason = "Нейтральное взаимодействие"
        
        if interaction_type == "message":
            # Для сообщений базовое изменение +1
            delta = 1
            
            # Анализ текста сообщения
            if content:
                # Проверка на позитивные слова
                positive_words = ["люблю", "нравишься", "хорошо", "красивая", "милая"]
                negative_words = ["ненавижу", "раздражаешь", "глупая", "уродливая"]
                
                # Простая эвристика для демонстрации
                for word in positive_words:
                    if word in content.lower():
                        delta += 1
                        reason = f"Позитивное сообщение содержит '{word}'"
                
                for word in negative_words:
                    if word in content.lower():
                        delta -= 2
                        reason = f"Негативное сообщение содержит '{word}'"
        
        elif interaction_type == "gift":
            delta = 3
            reason = "Подарок повышает отношения"
            
        elif interaction_type == "photo":
            delta = 2
            reason = "Обмен фотографиями углубляет связь"
            
        elif interaction_type == "date_completed":
            delta = 5
            reason = "Успешное свидание значительно улучшает отношения"
        
        # Обновляем рейтинг
        self.update_rating(user_id, partner_id, delta)
        
        return (delta, reason)
