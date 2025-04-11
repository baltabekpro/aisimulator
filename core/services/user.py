from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.db.models.user import User
from core.services.base import BaseService

class UserService(BaseService):
    """Service for User operations."""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_external_id(self, external_id: str) -> Optional[User]:
        """Get a user by external_id (используется для OAuth авторизации)."""
        return self.db.query(User).filter(User.external_id == external_id).first()
    
    def search_users(self, query: str, skip: int = 0, limit: int = 10) -> List[User]:
        """Search users by username or email."""
        return self.db.query(User).filter(
            or_(
                User.username.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%")
            )
        ).offset(skip).limit(limit).all()
    
    def create_user(self, username: str, email: str, password_hash: str, 
                  name: str = None, external_id: str = None) -> User:
        """Create a new user."""
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": password_hash,  # Fix: changed from password_hash to hashed_password
            "is_active": True
        }
        
        if name:
            user_data["name"] = name
            
        if external_id:
            user_data["external_id"] = external_id
            
        return self.create(obj_in=user_data)
    
    def update_password(self, user_id: UUID, new_password_hash: str) -> Optional[User]:
        """Update user password."""
        return self.update(id=user_id, obj_in={"hashed_password": new_password_hash})  # Fix: use hashed_password
    
    def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Deactivate a user."""
        return self.update(id=user_id, obj_in={"is_active": False})
