from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID

from app.db.session import get_db
from app.auth.jwt import get_current_user
from app.services import iap_service
from core.db.models.user import User

router = APIRouter()

class PurchaseVerification(BaseModel):
    product_id: str = Field(..., description="Идентификатор продукта")
    receipt_data: str = Field(..., description="Данные чека в формате base64")
    transaction_id: Optional[str] = Field(None, description="Идентификатор транзакции")

class PurchaseResponse(BaseModel):
    success: bool
    purchase_id: Optional[str] = None
    error: Optional[str] = None
    product: Optional[Dict[str, Any]] = None
    transaction_id: Optional[str] = None
    purchase_date: Optional[str] = None

@router.get("/products")
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Получить список доступных для покупки продуктов
    """
    products = iap_service.get_available_products(db)
    
    return {
        "products": products
    }

@router.post("/verify", response_model=PurchaseResponse)
def verify_purchase(
    purchase: PurchaseVerification,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Проверить и обработать покупку из App Store
    """
    user_id = str(current_user.user_id)
    
    result = iap_service.process_purchase(
        db=db,
        user_id=user_id,
        product_id=purchase.product_id,
        receipt_data=purchase.receipt_data,
        transaction_id=purchase.transaction_id
    )
    
    if not result.get("success"):
        # Фильтруем детали ошибки в продакшене
        error = result.get("error", "Unknown error")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return result

@router.get("/history")
def get_purchase_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Получить историю покупок пользователя
    """
    user_id = str(current_user.user_id)
    
    purchases = iap_service.get_user_purchases(db, user_id)
    
    return {
        "purchases": purchases
    }