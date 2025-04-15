from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from app.db.session import get_db
from app.auth.jwt import get_current_user
from app.schemas.subscription import (
    Subscription, 
    StarsPackage, 
    SubscriptionResponse, 
    StarsPackageResponse,
    SubscriptionPurchase,
    StarsPackagePurchase,
    PurchaseResponse
)
from app.services import subscription_service
from core.db.models.user import User

router = APIRouter()

@router.get("/subscriptions", response_model=SubscriptionResponse)
def get_available_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Получить список доступных подписок
    """
    subscriptions = subscription_service.get_available_subscriptions(db)
    
    return {
        "subscriptions": subscriptions,
        "total": len(subscriptions)
    }

@router.get("/stars/packages", response_model=StarsPackageResponse)
def get_stars_packages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Получить список доступных пакетов звездочек
    """
    packages = subscription_service.get_stars_packages(db)
    
    return {
        "packages": packages,
        "total": len(packages)
    }

@router.post("/subscriptions/purchase", response_model=PurchaseResponse)
def purchase_subscription(
    purchase_data: SubscriptionPurchase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Приобрести подписку
    """
    user_id = str(current_user.user_id)
    
    # Проверяем существование подписки
    subscription = subscription_service.get_subscription_by_id(db, purchase_data.subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена"
        )
    
    # Логика покупки подписки
    transaction_id = str(uuid4())
    success = subscription_service.purchase_subscription(
        db, 
        user_id=user_id, 
        subscription_id=purchase_data.subscription_id,
        payment_method=purchase_data.payment_method,
        transaction_id=transaction_id
    )
    
    if not success:
        return {
            "success": False,
            "error_message": "Не удалось выполнить покупку подписки"
        }
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "purchase_date": datetime.now()
    }

@router.post("/stars/purchase", response_model=PurchaseResponse)
def purchase_stars_package(
    purchase_data: StarsPackagePurchase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Приобрести пакет звездочек
    """
    user_id = str(current_user.user_id)
    
    # Проверяем существование пакета
    package = subscription_service.get_stars_package_by_id(db, purchase_data.package_id)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пакет звездочек не найден"
        )
    
    # Логика покупки пакета звездочек
    transaction_id = str(uuid4())
    success, stars_added = subscription_service.purchase_stars_package(
        db, 
        user_id=user_id, 
        package_id=purchase_data.package_id,
        payment_method=purchase_data.payment_method,
        transaction_id=transaction_id
    )
    
    if not success:
        return {
            "success": False,
            "error_message": "Не удалось выполнить покупку пакета звездочек"
        }
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "purchase_date": datetime.now(),
        "stars_added": stars_added
    }

@router.get("/user/subscription", response_model=Subscription)
def get_user_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Получить информацию о текущей подписке пользователя
    """
    user_id = str(current_user.user_id)
    
    # Получаем текущую подписку пользователя
    subscription = subscription_service.get_user_subscription(db, user_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У пользователя нет активной подписки"
        )
    
    return subscription