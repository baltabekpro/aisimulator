"""
Database models for the admin panel.
"""
import uuid
import logging
from datetime import datetime
from flask_login import UserMixin

from admin_panel.extensions import db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminUser(db.Model, UserMixin):
    """Admin user model for authentication."""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AdminUser {self.username}>"
    
    def get_id(self):
        """Return the user ID as a string as required by Flask-Login."""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return True
    
    @property
    def is_anonymous(self):
        """Return False as anonymous users aren't supported."""
        return False

# View models for other tables in the database
class UserView(db.Model):
    """User model for viewing user data."""
    __tablename__ = 'users'
    
    user_id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(50))
    email = db.Column(db.String(100))
    password_hash = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f"<User {self.username}>"

class CharacterView(db.Model):
    """Character model for viewing character data."""
    __tablename__ = 'characters'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f"<Character {self.name}>"

class MessageView(db.Model):
    """Message model for viewing message data."""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36))
    character_id = db.Column(db.String(36))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f"<Message {self.id}>"

logger.info("Models initialized")
