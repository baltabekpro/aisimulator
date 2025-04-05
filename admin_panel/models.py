# filepath: admin_panel/models.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from uuid import uuid4

# Create a separate MetaData instance for admin panel models
# to avoid conflicts with the main application models
admin_metadata = MetaData()
AdminBase = declarative_base(metadata=admin_metadata)

# Admin User model
class AdminUser(AdminBase, UserMixin):
    __tablename__ = "admin_users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_id(self):
        return self.id

# View-only classes for other models to prevent SQLAlchemy conflicts
# These are not ORM models, just data containers

# View-only model for Messages - used only for admin panel displays
class MessageView:
    """View-only representation of a Message"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# View-only model for Users
class UserView:
    """View-only representation of a User"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# View-only model for Characters
class CharacterView:
    """View-only representation of a Character"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
