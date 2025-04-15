from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)

# Моковые данные для демонстрации работы
MOCK_SUBSCRIPTIONS = [
    {
        "id": "sub-monthly-basic",
        "name": "Базовая подписка",
        "description": "Доступ к основному функционалу приложения",
        "type": "monthly",
        "price": 9.99,
        "currency": "USD",
        "duration_days": 30,
        "features": ["Неограниченные сообщения", "Доступ к 5 персонажам", "Базовые эмоции"],
        "is_popular": False
    },
    {
        "id": "sub-monthly-premium",
        "name": "Премиум подписка",
        "description": "Полный доступ ко всем возможностям приложения",
        "type": "monthly",
        "price": 19.99,
        "currency": "USD",
        "duration_days": 30,
        "features": ["Неограниченные сообщения", "Доступ ко всем персонажам", "Все эмоции", "100 звезд ежемесячно", "Приоритетная поддержка"],
        "is_popular": True
    },
    {
        "id": "sub-yearly-premium",
        "name": "Годовая Премиум подписка",
        "description": "Годовой доступ ко всем возможностям приложения",
        "type": "yearly",
        "price": 179.99,
        "currency": "USD",
        "duration_days": 365,
        "features": ["Неограниченные сообщения", "Доступ ко всем персонажам", "Все эмоции", "200 звезд ежемесячно", "VIP поддержка", "Скидка 25%"],
        "is_popular": False
    }
]

MOCK_STARS_PACKAGES = [
    {
        "id": "stars-small",
        "name": "Малый пакет звезд",
        "description": "50 звезд для подарков и особых действий",
        "type": "small",
        "price": 4.99,
        "currency": "USD",
        "stars_amount": 50,
        "bonus_stars": 0,
        "is_popular": False
    },
    {
        "id": "stars-medium",
        "name": "Средний пакет звезд",
        "description": "200 звезд для подарков и особых действий",
        "type": "medium",
        "price": 14.99,
        "currency": "USD",
        "stars_amount": 200,
        "bonus_stars": 20,
        "is_popular": True
    },
    {
        "id": "stars-large",
        "name": "Большой пакет звезд",
        "description": "500 звезд для подарков и особых действий",
        "type": "large",
        "price": 29.99,
        "currency": "USD",
        "stars_amount": 500,
        "bonus_stars": 75,
        "is_popular": False
    },
    {
        "id": "stars-premium",
        "name": "Премиум пакет звезд",
        "description": "1200 звезд для подарков и особых действий",
        "type": "premium",
        "price": 59.99,
        "currency": "USD",
        "stars_amount": 1200,
        "bonus_stars": 300,
        "is_popular": False
    }
]

def get_available_subscriptions(db: Session) -> List[Dict[str, Any]]:
    """
    Получение списка доступных подписок
    
    В реальной реализации данные должны быть получены из БД
    """
    try:
        # Для демонстрации используем моковые данные
        # В реальной реализации здесь нужно будет делать запрос к БД
        return MOCK_SUBSCRIPTIONS
    except Exception as e:
        logger.error(f"Ошибка получения подписок: {e}")
        return []

def get_stars_packages(db: Session) -> List[Dict[str, Any]]:
    """
    Получение списка доступных пакетов звездочек
    
    В реальной реализации данные должны быть получены из БД
    """
    try:
        # Для демонстрации используем моковые данные
        # В реальной реализации здесь нужно будет делать запрос к БД
        return MOCK_STARS_PACKAGES
    except Exception as e:
        logger.error(f"Ошибка получения пакетов звездочек: {e}")
        return []

def get_subscription_by_id(db: Session, subscription_id: str) -> Optional[Dict[str, Any]]:
    """
    Получение информации о подписке по ID
    
    В реальной реализации данные должны быть получены из БД
    """
    try:
        # Поиск подписки по ID в моковых данных
        for subscription in MOCK_SUBSCRIPTIONS:
            if subscription["id"] == subscription_id:
                return subscription
        return None
    except Exception as e:
        logger.error(f"Ошибка получения подписки по ID: {e}")
        return None

def get_stars_package_by_id(db: Session, package_id: str) -> Optional[Dict[str, Any]]:
    """
    Получение информации о пакете звездочек по ID
    
    В реальной реализации данные должны быть получены из БД
    """
    try:
        # Поиск пакета по ID в моковых данных
        for package in MOCK_STARS_PACKAGES:
            if package["id"] == package_id:
                return package
        return None
    except Exception as e:
        logger.error(f"Ошибка получения пакета звездочек по ID: {e}")
        return None

def get_user_subscription(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Получение текущей подписки пользователя
    
    В реальной реализации данные должны быть получены из БД
    """
    try:
        # В реальной реализации здесь нужно будет делать запрос к БД
        # Для демонстрации просто возвращаем первую подписку из моковых данных
        if MOCK_SUBSCRIPTIONS:
            subscription = MOCK_SUBSCRIPTIONS[0].copy()
            subscription["expires_at"] = (datetime.now() + timedelta(days=subscription["duration_days"])).isoformat()
            return subscription
        return None
    except Exception as e:
        logger.error(f"Ошибка получения подписки пользователя: {e}")
        return None

def purchase_subscription(db: Session, user_id: str, subscription_id: str, payment_method: str, transaction_id: str) -> bool:
    """
    Покупка подписки пользователем
    
    В реальной реализации должно быть сохранение в БД и интеграция с платежной системой
    """
    try:
        # Проверяем существование подписки
        subscription = get_subscription_by_id(db, subscription_id)
        if not subscription:
            return False
        
        # В реальной реализации здесь должна быть интеграция с платежной системой
        # и сохранение данных о подписке пользователя в БД
        
        # Для демонстрации просто возвращаем успех
        logger.info(f"Пользователь {user_id} приобрел подписку {subscription_id}, транзакция {transaction_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка покупки подписки: {e}")
        return False

def purchase_stars_package(db: Session, user_id: str, package_id: str, payment_method: str, transaction_id: str) -> Tuple[bool, int]:
    """
    Покупка пакета звездочек пользователем
    
    В реальной реализации должно быть сохранение в БД, интеграция с платежной системой и обновление баланса пользователя
    
    Возвращает (успех операции, количество добавленных звезд)
    """
    try:
        # Проверяем существование пакета
        package = get_stars_package_by_id(db, package_id)
        if not package:
            return False, 0
        
        # В реальной реализации здесь должна быть интеграция с платежной системой
        # и обновление баланса звездочек пользователя в БД
        
        # Рассчитываем общее количество звезд
        stars_total = package["stars_amount"] + package["bonus_stars"]
        
        # Для демонстрации просто логируем успешную покупку
        logger.info(f"Пользователь {user_id} приобрел пакет звездочек {package_id}, добавлено {stars_total} звезд, транзакция {transaction_id}")
        
        # В реальной реализации здесь нужно обновить баланс пользователя в БД
        from app.services import profile_service
        current_balance = profile_service.get_user_stars_balance(db, user_id) or 0
        new_balance = current_balance + stars_total
        profile_service.update_user_stars_balance(db, user_id, new_balance)
        
        return True, stars_total
    except Exception as e:
        logger.error(f"Ошибка покупки пакета звездочек: {e}")
        return False, 0