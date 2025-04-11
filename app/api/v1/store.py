from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid

from app.api.deps import get_current_user
from app.config import settings

router = APIRouter()

# --- Models ---
class UserBalance(BaseModel):
    """Модель баланса пользователя"""
    stars: int = Field(..., description="Текущее количество звезд пользователя")
    last_updated: datetime = Field(..., description="Время последнего обновления баланса")

class SubscriptionPlan(BaseModel):
    """Модель плана подписки"""
    id: str = Field(..., description="Уникальный идентификатор плана подписки")
    name: str = Field(..., description="Название плана подписки")
    description: str = Field(..., description="Описание преимуществ подписки")
    price: float = Field(..., description="Цена подписки в долларах США")
    duration_days: int = Field(..., description="Длительность подписки в днях")
    apple_product_id: str = Field(..., description="Идентификатор продукта в Apple In-App Purchase")
    features: List[str] = Field(default_factory=list, description="Список преимуществ подписки")
    is_popular: bool = Field(False, description="Флаг наиболее популярного плана подписки")

class StarPackage(BaseModel):
    """Модель пакета звезд"""
    id: str = Field(..., description="Уникальный идентификатор пакета звезд")
    name: str = Field(..., description="Название пакета звезд")
    description: str = Field(..., description="Описание пакета")
    price: float = Field(..., description="Цена в долларах США")
    stars: int = Field(..., description="Количество звезд в пакете")
    bonus_stars: int = Field(0, description="Дополнительные бонусные звезды")
    apple_product_id: str = Field(..., description="Идентификатор продукта в Apple In-App Purchase")
    is_best_deal: bool = Field(False, description="Флаг лучшего предложения")

class PurchaseResponse(BaseModel):
    """Ответ на запрос покупки"""
    success: bool = Field(..., description="Статус операции")
    message: str = Field(..., description="Сообщение о результате операции")
    transaction_id: Optional[str] = Field(None, description="Идентификатор транзакции")
    balance: Optional[int] = Field(None, description="Новый баланс после покупки")

# --- Endpoints ---
@router.get("/users/me/balance", response_model=UserBalance)
async def get_user_balance(
    current_user = Depends(get_current_user)
):
    """Получить текущий баланс звезд пользователя"""
    # В реальной реализации нужно получать данные из базы данных
    # Для примера возвращаем фиксированные значения
    return UserBalance(
        stars=250,  # Заменить на real_stars = db.query(UserBalance).filter(UserBalance.user_id == current_user.id).first().stars
        last_updated=datetime.now()
    )

@router.get("/store/subscriptions", response_model=List[SubscriptionPlan])
async def get_available_subscriptions(
    current_user = Depends(get_current_user)
):
    """Получить список доступных планов подписки"""
    # В реальной реализации нужно получать данные из базы данных
    # Для примера возвращаем фиксированные планы
    return [
        SubscriptionPlan(
            id="sub-monthly",
            name="1 месяц",
            description="Месячный доступ ко всем функциям",
            price=9.99,
            duration_days=30,
            apple_product_id="com.aisimulator.sub.monthly",
            features=[
                "Неограниченное количество сообщений", 
                "Расширенные диалоги",
                "Глубокая память персонажей"
            ],
            is_popular=False
        ),
        SubscriptionPlan(
            id="sub-quarterly",
            name="3 месяца",
            description="Квартальная подписка со скидкой",
            price=24.99,
            duration_days=90,
            apple_product_id="com.aisimulator.sub.quarterly",
            features=[
                "Неограниченное количество сообщений", 
                "Расширенные диалоги",
                "Глубокая память персонажей",
                "Скидка 16% (по сравнению с месячным планом)"
            ],
            is_popular=True
        ),
        SubscriptionPlan(
            id="sub-annual",
            name="12 месяцев",
            description="Годовая подписка с максимальной скидкой",
            price=79.99,
            duration_days=365,
            apple_product_id="com.aisimulator.sub.annual",
            features=[
                "Неограниченное количество сообщений", 
                "Расширенные диалоги",
                "Глубокая память персонажей",
                "Скидка 33% (по сравнению с месячным планом)",
                "Премиум персонажи"
            ],
            is_popular=False
        )
    ]

@router.get("/store/star-packages", response_model=List[StarPackage])
async def get_star_packages(
    current_user = Depends(get_current_user)
):
    """Получить список доступных пакетов звезд"""
    # В реальной реализации нужно получать данные из базы данных
    # Для примера возвращаем фиксированные пакеты
    return [
        StarPackage(
            id="stars-100",
            name="100 звезд",
            description="Базовый пакет звезд",
            price=4.99,
            stars=100,
            bonus_stars=0,
            apple_product_id="com.aisimulator.stars.100",
            is_best_deal=False
        ),
        StarPackage(
            id="stars-500",
            name="500 звезд",
            description="Популярный выбор",
            price=19.99,
            stars=500,
            bonus_stars=50,
            apple_product_id="com.aisimulator.stars.500",
            is_best_deal=True
        ),
        StarPackage(
            id="stars-1000",
            name="1000 звезд",
            description="Экономичный пакет",
            price=34.99,
            stars=1000,
            bonus_stars=150,
            apple_product_id="com.aisimulator.stars.1000",
            is_best_deal=False
        ),
        StarPackage(
            id="stars-2500",
            name="2500 звезд",
            description="Максимальное значение",
            price=79.99,
            stars=2500,
            bonus_stars=500,
            apple_product_id="com.aisimulator.stars.2500",
            is_best_deal=False
        )
    ]

@router.post("/store/verify-purchase", response_model=PurchaseResponse)
async def verify_iap_purchase(
    receipt_data: str = Query(..., description="Данные чека от Apple IAP"),
    product_id: str = Query(..., description="Идентификатор приобретенного продукта"),
    current_user = Depends(get_current_user)
):
    """Верифицировать покупку в приложении через Apple In-App Purchase"""
    # В реальной реализации:
    # 1. Отправить receipt_data на сервер Apple для проверки
    # 2. Обновить подписку/баланс пользователя в БД
    # 3. Вернуть обновленную информацию
    
    # Для примера:
    if "sub" in product_id:
        # Обработка подписки
        return PurchaseResponse(
            success=True,
            message="Подписка успешно активирована",
            transaction_id="test-transaction-123456"
        )
    else:
        # Обработка покупки звезд
        stars_added = 0
        
        if product_id == "com.aisimulator.stars.100":
            stars_added = 100
        elif product_id == "com.aisimulator.stars.500":
            stars_added = 550  # 500 + 50 бонусных
        elif product_id == "com.aisimulator.stars.1000":
            stars_added = 1150  # 1000 + 150 бонусных
        elif product_id == "com.aisimulator.stars.2500":
            stars_added = 3000  # 2500 + 500 бонусных
            
        new_balance = 250 + stars_added  # 250 - текущий баланс из get_user_balance
            
        return PurchaseResponse(
            success=True,
            message=f"Успешно добавлено {stars_added} звезд",
            transaction_id="test-transaction-123456",
            balance=new_balance
        )