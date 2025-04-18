from sqlalchemy.orm import Session
import uuid
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.db.models.user_photo import UserPhoto
from app.services.storage_service import delete_file
from core.config import settings

logger = logging.getLogger(__name__)

def get_user_photos(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """
    Получить все фотографии пользователя
    """
    try:
        photos = db.query(UserPhoto).filter(UserPhoto.user_id == user_id).order_by(UserPhoto.order).all()
        return [
            {
                "id": str(photo.id),
                "url": photo.url,
                "is_primary": photo.is_primary,
                "created_at": photo.created_at.isoformat() if photo.created_at else None
            }
            for photo in photos
        ]
    except Exception as e:
        logger.error(f"Error getting user photos: {e}")
        return []

def create_photo(db: Session, user_id: str, url: str, filename: str, 
                content_type: str = None, size: int = None, is_primary: bool = False) -> Optional[str]:
    """
    Создать новую запись о фотографии пользователя
    """
    try:
        # Сначала сбрасываем primary флаг у всех фото, если новое фото помечено как primary
        if is_primary:
            primary_photos = db.query(UserPhoto).filter(
                UserPhoto.user_id == user_id,
                UserPhoto.is_primary == True
            ).all()
            
            for photo in primary_photos:
                photo.is_primary = False
                
            db.commit()
        
        # Определяем порядок фото
        max_order = db.query(UserPhoto).filter(UserPhoto.user_id == user_id).count()
        
        # Создаем новую запись фото
        new_photo = UserPhoto(
            id=uuid.uuid4(),
            user_id=user_id,
            url=url,
            filename=filename,
            content_type=content_type,
            size=size,
            is_primary=is_primary,
            order=max_order,
            created_at=datetime.utcnow()
        )
        
        db.add(new_photo)
        db.commit()
        db.refresh(new_photo)
        
        return str(new_photo.id)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user photo: {e}")
        return None

def delete_photo(db: Session, user_id: str, photo_id: str) -> bool:
    """
    Удалить фотографию пользователя
    """
    try:
        photo = db.query(UserPhoto).filter(
            UserPhoto.id == photo_id,
            UserPhoto.user_id == user_id
        ).first()
        
        if not photo:
            logger.warning(f"Photo {photo_id} not found for user {user_id}")
            return False
        
        # Delete file from storage
        try:
            bucket = settings.S3_BUCKET_NAME
            delete_file(bucket, photo.filename)
        except Exception as e:
            logger.error(f"Error deleting file from storage: {e}")
        
        # Delete DB record
        db.delete(photo)
        db.commit()
        
        # Обновляем порядок оставшихся фото
        photos = db.query(UserPhoto).filter(UserPhoto.user_id == user_id).order_by(UserPhoto.order).all()
        for i, photo in enumerate(photos):
            photo.order = i
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting photo: {e}")
        return False

def set_primary_photo(db: Session, user_id: str, photo_id: str) -> bool:
    """
    Установить фотографию как основную
    """
    try:
        # Сначала сбрасываем primary флаг у всех фото
        photos = db.query(UserPhoto).filter(UserPhoto.user_id == user_id).all()
        for photo in photos:
            photo.is_primary = (str(photo.id) == photo_id)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error setting primary photo: {e}")
        return False