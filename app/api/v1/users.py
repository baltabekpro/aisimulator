from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.schemas.user import UserProfileUpdate, UserProfileResponse
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/me", response_model=UserProfileResponse)
async def get_user_profile(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить данные профиля текущего пользователя"""
    # В реальной реализации извлечем данные из БД
    # Для примера возвращаем заглушку
    return UserProfileResponse(
        user_id=str(current_user.id),
        name=current_user.name,
        age=None,
        gender=None,
        location=None,
        bio=None,
        interests=[],
        photos=[],
        matching_preferences={},
        created_at=datetime.now(),
        updated_at=None
    )

@router.put("/me", response_model=UserProfileResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить данные профиля текущего пользователя"""
    # В реальной реализации обновляем данные в БД
    # Для примера просто возвращаем обновленные данные
    
    # Можно добавить валидацию входных данных
    if profile_update.age is not None and (profile_update.age < 18 or profile_update.age > 100):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Возраст должен быть между 18 и 100"
        )
    
    # В реальной реализации мы бы сохранили фотографии, загруженные пользователем
    # в хранилище (например, S3, MinIO) и сохранили бы URL в профиле
    
    return UserProfileResponse(
        user_id=str(current_user.id),
        name=profile_update.name or current_user.name,
        age=profile_update.age,
        gender=profile_update.gender,
        location=profile_update.location,
        bio=profile_update.bio,
        interests=profile_update.interests,
        photos=profile_update.photos,
        matching_preferences=profile_update.matching_preferences,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@router.post("/me/photos", response_model=Dict[str, Any])
async def upload_profile_photo(
    current_user = Depends(get_current_user)
):
    """Загрузить фотографию профиля"""
    # В реальной реализации нужно:
    # 1. Принять загруженный файл
    # 2. Проверить, что это изображение
    # 3. Загрузить его в хранилище (S3/MinIO)
    # 4. Сохранить URL в базе данных
    # 5. Вернуть URL загруженного изображения
    
    # Заглушка
    return {
        "success": True,
        "message": "Фото успешно загружено",
        "photo_url": f"https://example.com/photos/users/{current_user.id}/profile.jpg"
    }

@router.delete("/me/photos/{photo_id}", response_model=Dict[str, Any])
async def delete_profile_photo(
    photo_id: str,
    current_user = Depends(get_current_user)
):
    """Удалить фотографию профиля"""
    # В реальной реализации нужно:
    # 1. Проверить, что фото принадлежит пользователю
    # 2. Удалить фото из хранилища
    # 3. Удалить URL из базы данных
    
    # Заглушка
    return {
        "success": True,
        "message": f"Фото {photo_id} успешно удалено"
    }