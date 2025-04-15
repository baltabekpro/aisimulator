from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, status, Path
from sqlalchemy.orm import Session
from uuid import UUID
import os
import logging
import shutil
from datetime import datetime

from app.db.session import get_db
from app.auth.jwt import get_current_user
from app.schemas.user import UserProfileResponse, UserProfileUpdate
from app.services import photo_service, profile_service
from core.db.models.user import User
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Путь для хранения фотографий
UPLOAD_DIRECTORY = os.environ.get("UPLOAD_DIRECTORY", "uploads/photos/")
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Настройки загрузки фотографий
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/jpg"]

@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Получить профиль текущего пользователя
    """
    user_id = str(current_user.user_id)
    profile = profile_service.get_user_profile(db, user_id)
    
    if not profile:
        # Если профиль не найден, создаем с базовыми данными
        profile_data = {
            "name": current_user.name,
            "interests": []
        }
        
        profile = profile_service.create_or_update_profile(db, user_id, profile_data)
        
    # Добавляем фотографии
    photos = photo_service.get_user_photos(db, user_id)
    
    # Объединяем данные профиля и фотографии
    result = profile.copy() if profile else {"user_id": user_id}
    result["photos"] = photos
    result["email"] = current_user.email
    result["username"] = current_user.username
    
    return result

@router.put("/me", response_model=UserProfileResponse)
def update_current_user_profile(
    profile_update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Обновить профиль текущего пользователя
    """
    user_id = str(current_user.user_id)
    
    # Преобразуем данные в словарь для обновления
    update_data = profile_update.dict(exclude_unset=True)
    
    # Обновляем профиль
    profile = profile_service.create_or_update_profile(db, user_id, update_data)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить профиль"
        )
    
    # Добавляем фотографии
    photos = photo_service.get_user_photos(db, user_id)
    
    # Возвращаем обновленный профиль
    result = profile.copy()
    result["photos"] = photos
    result["email"] = current_user.email
    result["username"] = current_user.username
    
    return result

@router.post("/me/photos")
async def upload_user_photo(
    photo: UploadFile = File(...),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Загрузить фотографию пользователя
    """
    user_id = str(current_user.user_id)
    
    # Проверка типа файла
    if photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат файла. Разрешены только: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
    
    # Получаем размер файла
    photo.file.seek(0, os.SEEK_END)
    size = photo.file.tell()
    photo.file.seek(0)  # Сбрасываем указатель
    
    # Проверка размера
    if size > MAX_PHOTO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Размер файла превышает максимально допустимый ({MAX_PHOTO_SIZE / 1024 / 1024} MB)"
        )
    
    # Генерируем имя файла и путь
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{timestamp}_{photo.filename}"
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)
    
    # Создаем директорию, если не существует
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Сохраняем файл
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить файл"
        )
    
    # Формируем URL для доступа к файлу
    base_url = settings.BASE_URL.rstrip("/")
    url = f"{base_url}/uploads/photos/{filename}"
    
    # Сохраняем информацию о фото в БД
    photo_id = photo_service.create_photo(
        db, user_id, url, filename, 
        content_type=photo.content_type, 
        size=size,
        is_primary=is_primary
    )
    
    if not photo_id:
        # Если не удалось сохранить в БД, удаляем файл
        try:
            os.unlink(file_path)
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить информацию о фотографии"
        )
    
    return {
        "id": photo_id,
        "url": url,
        "is_primary": is_primary,
        "message": "Фотография успешно загружена"
    }

@router.delete("/me/photos/{photo_id}")
def delete_user_photo(
    photo_id: str = Path(..., title="ID фотографии"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Удалить фотографию пользователя
    """
    user_id = str(current_user.user_id)
    
    # Удаляем запись из БД
    success = photo_service.delete_photo(db, user_id, photo_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена или не принадлежит текущему пользователю"
        )
    
    return {"message": "Фотография успешно удалена"}

@router.put("/me/photos/{photo_id}/primary")
def set_primary_photo(
    photo_id: str = Path(..., title="ID фотографии"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Установить фотографию как основную
    """
    user_id = str(current_user.user_id)
    
    # Обновляем флаг is_primary
    success = photo_service.set_primary_photo(db, user_id, photo_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена или произошла ошибка при обновлении"
        )
    
    return {"message": "Фотография установлена как основная"}

@router.get("/me/balance")
def get_user_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Получить текущий баланс звезд пользователя
    """
    user_id = str(current_user.user_id)
    
    # Используем сервис для получения реального баланса пользователя из БД
    balance = profile_service.get_user_stars_balance(db, user_id)
    
    if balance is None:
        # Если баланс не найден, инициализируем с нулевым значением
        balance = 0
        profile_service.update_user_stars_balance(db, user_id, balance)
    
    return {
        "balance": balance,
        "currency": "stars",
        "last_updated": datetime.now().isoformat()
    }

@router.get("/interests")
def get_interests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Получить список доступных интересов
    """
    interests = profile_service.get_all_interests(db)
    return {"interests": interests}