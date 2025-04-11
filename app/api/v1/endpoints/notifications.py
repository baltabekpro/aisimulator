from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID

from app.db.session import get_db
from app.auth.jwt import get_current_user
from app.services import notification_service
from core.db.models.user import User

router = APIRouter()

class DeviceRegistrationRequest(BaseModel):
    device_token: str = Field(..., description="Токен устройства для пуш-уведомлений")
    device_type: str = Field(..., description="Тип устройства (ios/android/web)")
    app_version: Optional[str] = Field(None, description="Версия приложения")
    os_version: Optional[str] = Field(None, description="Версия операционной системы")
    device_model: Optional[str] = Field(None, description="Модель устройства")

class DeviceTokenResponse(BaseModel):
    id: str
    message: str

class NotificationResponse(BaseModel):
    success: bool
    count: int
    message: str

@router.post("/devices", response_model=DeviceTokenResponse)
def register_device(
    request: DeviceRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Регистрация устройства для получения push-уведомлений
    """
    user_id = str(current_user.user_id)
    
    token_id = notification_service.register_device_token(
        db, 
        user_id=user_id,
        device_token=request.device_token,
        device_type=request.device_type,
        app_version=request.app_version,
        os_version=request.os_version,
        device_model=request.device_model
    )
    
    if not token_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось зарегистрировать устройство"
        )
    
    return {
        "id": token_id,
        "message": "Устройство успешно зарегистрировано"
    }

@router.delete("/devices/{device_token}")
def unregister_device(
    device_token: str = Path(..., description="Токен устройства для отмены регистрации"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Отмена регистрации устройства для push-уведомлений
    """
    success = notification_service.unregister_device_token(db, device_token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Устройство не найдено или уже отменена регистрация"
        )
    
    return {
        "message": "Регистрация устройства отменена"
    }

# Эндпоинт для тестирования пуш-уведомлений (только для разработки)
@router.post("/test", response_model=NotificationResponse)
def send_test_notification(
    title: str = Query("Тестовое уведомление", description="Заголовок уведомления"),
    body: str = Query("Это тестовое push-уведомление", description="Текст уведомления"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Отправка тестового push-уведомления на все устройства пользователя
    """
    # Этот эндпоинт должен быть отключен в production
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен"
        )
    
    user_id = str(current_user.user_id)
    count = notification_service.send_notification_to_user(
        db, user_id, title, body, {"test": True}
    )
    
    return {
        "success": count > 0,
        "count": count,
        "message": f"Отправлено {count} уведомлений" if count > 0 else "Уведомления не отправлены"
    }