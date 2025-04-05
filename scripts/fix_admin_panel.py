"""
Script to fix the admin panel dashboard issues caused by the timestamp/created_at column rename.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, create_engine
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_dashboard_routes():
    """Creates a replacement dashboard route file with safe SQL queries"""
    dashboard_py_path = os.path.join("admin_panel", "routes", "dashboard.py")
    
    # Check if directory exists, create if not
    dashboard_dir = os.path.join("admin_panel", "routes")
    if not os.path.exists(dashboard_dir):
        os.makedirs(dashboard_dir)
        logger.info(f"Created directory: {dashboard_dir}")
    
    # Content for the fixed dashboard routes file
    dashboard_content = '''# filepath: admin_panel/routes/dashboard.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import text

from admin_panel.app import db
from core.utils.db_helpers import (
    safe_count_query, 
    execute_safe_query, 
    reset_db_connection
)

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard page with system overview"""
    try:
        # Reset any failed transaction
        reset_db_connection(db)
        
        # Get table counts using safe method
        stats = {
            "users": safe_count_query(db, "users"),
            "characters": safe_count_query(db, "characters"),
            "messages": safe_count_query(db, "messages"),
            "total_memory_entries": safe_count_query(db, "memory_entries")
        }
        
        # Get recent messages directly using SQL with created_at
        recent_messages_query = text("""
            SELECT id, sender_id, sender_type, recipient_id, recipient_type, 
                   content, emotion, created_at
            FROM messages
            ORDER BY created_at DESC
            LIMIT 10
        """)
        result = db.execute(recent_messages_query)
        recent_messages = [dict(row) for row in result]
        
        # Get recent users
        recent_users_query = text("""
            SELECT user_id, username, email, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 5
        """)
        result = db.execute(recent_users_query)
        recent_users = [dict(row) for row in result]
        
        # Get recent characters
        recent_characters_query = text("""
            SELECT id, name, gender, age
            FROM characters
            ORDER BY id DESC
            LIMIT 5
        """)
        result = db.execute(recent_characters_query)
        recent_characters = [dict(row) for row in result]
        
        return render_template(
            "dashboard.html",
            stats=stats,
            recent_messages=recent_messages,
            recent_users=recent_users,
            recent_characters=recent_characters
        )
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template("dashboard.html", stats={}, recent_messages=[], recent_users=[], recent_characters=[])

# Add other dashboard routes as needed
'''
    
    # Write the file
    with open(dashboard_py_path, 'w', encoding='utf-8') as f:
        f.write(dashboard_content)
    
    logger.info(f"Created fixed dashboard routes file at {dashboard_py_path}")
    return True

def fix_admin_models():
    """Updates the admin panel's model definitions"""
    models_py_path = os.path.join("admin_panel", "models.py")
    
    models_content = '''# filepath: admin_panel/models.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from uuid import uuid4

# Import the correct Base class
from core.db.base import Base

# Admin User model
class AdminUser(Base, UserMixin):
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

# User model (application users)
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(200), nullable=True)
    name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, nullable=True)

# Character model
class Character(Base):
    __tablename__ = "characters"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    personality = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    interests = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, nullable=True)
    current_emotion = Column(String(50), nullable=True)

# Message model - updated to use created_at
class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    sender_id = Column(String, nullable=False)
    sender_type = Column(String, nullable=False)
    recipient_id = Column(String, nullable=False)
    recipient_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    emotion = Column(String, nullable=True)
    conversation_id = Column(String, nullable=True)
    
    # Use created_at instead of timestamp
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, nullable=True)
    
    # Include the additional columns
    is_read = Column(Boolean, default=False)
    is_gift = Column(Boolean, default=False)
'''
    
    # Write the file
    with open(models_py_path, 'w', encoding='utf-8') as f:
        f.write(models_content)
    
    logger.info(f"Updated admin panel models at {models_py_path}")
    return True

if __name__ == "__main__":
    load_dotenv()
    
    # Fix admin panel routes
    update_dashboard_routes()
    
    # Fix admin panel models
    fix_admin_models()
    
    logger.info("Admin panel fixes applied successfully!")
