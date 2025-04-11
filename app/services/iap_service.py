from sqlalchemy.orm import Session
import logging
import json
import requests
import uuid
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from core.db.models.in_app_purchase import InAppPurchase, PurchaseProduct
from core.db.models.user import User
from core.config import settings

logger = logging.getLogger(__name__)

# Конечные точки для проверки чеков в App Store
PRODUCTION_VERIFY_URL = "https://buy.itunes.apple.com/verifyReceipt"
SANDBOX_VERIFY_URL = "https://sandbox.itunes.apple.com/verifyReceipt"

def get_available_products(db: Session) -> List[Dict[str, Any]]:
    """Получить список доступных для покупки товаров"""
    try:
        products = db.query(PurchaseProduct).filter(PurchaseProduct.is_active == True).all()
        
        return [
            {
                "id": str(product.id),
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "type": product.type,
                "price_usd": product.price_usd,
                "stars_amount": product.stars_amount,
                "duration_days": product.duration_days
            }
            for product in products
        ]
    except Exception as e:
        logger.error(f"Error getting available products: {e}")
        return []

def verify_apple_receipt(receipt_data: str, password: Optional[str] = None) -> Dict[str, Any]:
    """Проверка чека Apple App Store"""
    payload = {
        "receipt-data": receipt_data
    }
    
    # Если указан пароль для подписок
    if password:
        payload["password"] = password
        
    try:
        # Сначала пробуем проверить в production
        response = requests.post(
            PRODUCTION_VERIFY_URL,
            json=payload,
            timeout=15
        )
        
        # Парсим ответ
        result = response.json()
        
        # Проверяем, нужно ли использовать sandbox
        if result.get("status") == 21007:
            # Тестовый чек, проверяем в sandbox
            response = requests.post(
                SANDBOX_VERIFY_URL,
                json=payload,
                timeout=15
            )
            result = response.json()
            result["environment"] = "sandbox"
        else:
            result["environment"] = "production"
            
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"Error verifying receipt: {e}")
        return {"status": -1, "error": str(e)}

def process_purchase(
    db: Session, 
    user_id: str, 
    product_id: str, 
    receipt_data: str,
    transaction_id: Optional[str] = None
) -> Dict[str, Any]:
    """Обработка покупки после проверки чека"""
    try:
        # Проверяем чек в Apple
        verification = verify_apple_receipt(receipt_data, settings.IAP_SECRET)
        
        # Проверяем статус ответа от Apple
        if verification.get("status") != 0:
            return {
                "success": False,
                "error": f"Invalid receipt: {verification.get('status')}",
                "details": verification
            }
            
        # Извлекаем данные о транзакции из ответа
        receipt_info = verification.get("receipt", {})
        in_app_purchases = receipt_info.get("in_app", [])
        
        # Если transaction_id не указан, берем из первой транзакции
        if not transaction_id and in_app_purchases:
            transaction_id = in_app_purchases[0].get("transaction_id")
            
        if not transaction_id:
            return {
                "success": False,
                "error": "Transaction ID not found in receipt"
            }
            
        # Проверяем, существует ли уже такая транзакция
        existing_purchase = db.query(InAppPurchase).filter(
            InAppPurchase.transaction_id == transaction_id
        ).first()
        
        if existing_purchase:
            return {
                "success": False,
                "error": "Transaction already processed",
                "purchase_id": str(existing_purchase.id)
            }
            
        # Получаем информацию о продукте
        product = db.query(PurchaseProduct).filter(
            PurchaseProduct.product_id == product_id,
            PurchaseProduct.is_active == True
        ).first()
        
        if not product:
            return {
                "success": False,
                "error": "Product not found or inactive"
            }
            
        # Находим соответствующую транзакцию в чеке
        purchase_info = None
        for purchase in in_app_purchases:
            if purchase.get("product_id") == product_id and purchase.get("transaction_id") == transaction_id:
                purchase_info = purchase
                break
                
        if not purchase_info:
            return {
                "success": False,
                "error": "Transaction for this product not found in receipt"
            }
            
        # Преобразуем данные покупки
        try:
            purchase_date_ms = int(purchase_info.get("purchase_date_ms", 0))
            purchase_date = datetime.fromtimestamp(purchase_date_ms / 1000)
            
            # Для подписок также получаем дату истечения
            expiration_date = None
            if product.type == "subscription" and purchase_info.get("expires_date_ms"):
                expiration_date_ms = int(purchase_info.get("expires_date_ms", 0))
                expiration_date = datetime.fromtimestamp(expiration_date_ms / 1000)
        except Exception as e:
            logger.error(f"Error parsing dates: {e}")
            purchase_date = datetime.now()
            
        # Сохраняем информацию о покупке
        new_purchase = InAppPurchase(
            id=uuid.uuid4(),
            user_id=user_id,
            product_id=product_id,
            transaction_id=transaction_id,
            receipt_data=receipt_data,
            purchase_date=purchase_date,
            expiration_date=expiration_date,
            status="completed",
            quantity=int(purchase_info.get("quantity", 1)),
            environment=verification.get("environment", "production"),
            metadata=purchase_info
        )
        
        db.add(new_purchase)
        
        # Начисляем вознаграждение пользователю в зависимости от типа продукта
        if product.type == "consumable" and product.stars_amount:
            # Реализуйте логику начисления внутриигровой валюты
            # Например, обновление баланса пользователя
            pass
            
        elif product.type == "subscription":
            # Реализуйте логику активации подписки
            # Например, обновление статуса подписки пользователя
            pass
            
        db.commit()
        
        return {
            "success": True,
            "purchase_id": str(new_purchase.id),
            "product": {
                "id": product.product_id,
                "type": product.type,
                "name": product.name
            },
            "transaction_id": transaction_id,
            "purchase_date": purchase_date.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing purchase: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def get_user_purchases(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """Получить историю покупок пользователя"""
    try:
        purchases = db.query(InAppPurchase).filter(
            InAppPurchase.user_id == user_id
        ).order_by(InAppPurchase.purchase_date.desc()).all()
        
        return [
            {
                "id": str(purchase.id),
                "product_id": purchase.product_id,
                "transaction_id": purchase.transaction_id,
                "purchase_date": purchase.purchase_date.isoformat() if purchase.purchase_date else None,
                "expiration_date": purchase.expiration_date.isoformat() if purchase.expiration_date else None,
                "status": purchase.status,
                "quantity": purchase.quantity
            }
            for purchase in purchases
        ]
    except Exception as e:
        logger.error(f"Error getting user purchases: {e}")
        return []