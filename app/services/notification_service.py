from sqlalchemy.orm import Session
import logging
import json
import requests
import uuid
from typing import Dict, Any, List, Optional
import time
import jwt
from datetime import datetime, timedelta

from core.db.models.device_token import DeviceToken
from core.config import settings

logger = logging.getLogger(__name__)

class APNSConfig:
    """Конфигурация для Apple Push Notification Service"""
    team_id = settings.APPLE_TEAM_ID
    key_id = settings.APPLE_KEY_ID
    bundle_id = settings.APPLE_BUNDLE_ID
    auth_key_path = settings.APPLE_AUTH_KEY_PATH
    use_sandbox = settings.APPLE_USE_SANDBOX

    @classmethod
    def get_apns_url(cls) -> str:
        """Получить URL для APNS в зависимости от режима (sandbox/prod)"""
        if cls.use_sandbox:
            return "https://api.sandbox.push.apple.com/3/device"
        return "https://api.push.apple.com/3/device"

    @classmethod
    def get_auth_token(cls) -> str:
        """Генерировать JWT токен для авторизации в APNS"""
        try:
            with open(cls.auth_key_path, "r") as key_file:
                private_key = key_file.read()

            token = jwt.encode(
                {
                    "iss": cls.team_id,
                    "iat": time.time()
                },
                private_key,
                algorithm="ES256",
                headers={
                    "alg": "ES256",
                    "kid": cls.key_id
                }
            )
            return token
        except Exception as e:
            logger.error(f"Error generating APNS auth token: {e}")
            raise

def register_device_token(db: Session, user_id: str, device_token: str, 
                        device_type: str, app_version: str = None, 
                        os_version: str = None, device_model: str = None) -> Optional[str]:
    """
    Регистрация или обновление токена устройства для пуш-уведомлений
    """
    try:
        # Проверяем, существует ли уже такой токен
        existing_token = db.query(DeviceToken).filter(
            DeviceToken.device_token == device_token,
            DeviceToken.user_id == user_id
        ).first()
        
        if existing_token:
            # Обновляем существующую запись
            existing_token.app_version = app_version or existing_token.app_version
            existing_token.os_version = os_version or existing_token.os_version
            existing_token.device_model = device_model or existing_token.device_model
            existing_token.is_active = True
            existing_token.updated_at = datetime.now()
            db.commit()
            return str(existing_token.id)
            
        # Создаем новую запись
        new_token = DeviceToken(
            id=uuid.uuid4(),
            user_id=user_id,
            device_token=device_token,
            device_type=device_type.lower(),
            app_version=app_version,
            os_version=os_version,
            device_model=device_model,
            is_active=True
        )
        
        db.add(new_token)
        db.commit()
        db.refresh(new_token)
        
        return str(new_token.id)
    except Exception as e:
        db.rollback()
        logger.error(f"Error registering device token: {e}")
        return None

def unregister_device_token(db: Session, device_token: str) -> bool:
    """
    Отмена регистрации токена устройства
    """
    try:
        tokens = db.query(DeviceToken).filter(
            DeviceToken.device_token == device_token
        ).all()
        
        if not tokens:
            return False
            
        for token in tokens:
            token.is_active = False
            
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error unregistering device token: {e}")
        return False

def send_apple_push(device_token: str, title: str, body: str, 
                  data: Dict[str, Any] = None, badge: int = None) -> bool:
    """
    Отправка push-уведомления на устройство Apple
    """
    try:
        url = f"{APNSConfig.get_apns_url()}/{device_token}"
        
        # Заголовки запроса
        headers = {
            "apns-topic": APNSConfig.bundle_id,
            "authorization": f"bearer {APNSConfig.get_auth_token()}"
        }
        
        # Тело уведомления
        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body
                },
                "sound": "default"
            }
        }
        
        # Добавляем badge, если он указан
        if badge is not None:
            payload["aps"]["badge"] = badge
            
        # Добавляем дополнительные данные, если они указаны
        if data:
            payload["data"] = data
            
        # Отправляем запрос
        response = requests.post(
            url, 
            headers=headers,
            json=payload
        )
        
        # Проверяем статус ответа
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Error sending push notification: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception sending push notification: {e}")
        return False

def send_notification_to_user(db: Session, user_id: str, title: str, body: str, 
                            data: Dict[str, Any] = None) -> int:
    """
    Отправка уведомления всем устройствам пользователя
    
    Возвращает количество успешно отправленных уведомлений
    """
    try:
        # Получаем все активные токены пользователя
        device_tokens = db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active == True
        ).all()
        
        if not device_tokens:
            return 0
            
        success_count = 0
        
        # Отправляем уведомления на все устройства
        for device in device_tokens:
            if device.device_type.lower() == 'ios':
                # Отправляем через APNS
                if send_apple_push(device.device_token, title, body, data):
                    success_count += 1
            elif device.device_type.lower() == 'android':
                # TODO: Реализовать отправку через FCM для Android
                pass
                
        return success_count
    except Exception as e:
        logger.error(f"Error sending notification to user: {e}")
        return 0