"""
Dependencies module for the admin panel.

This module provides common dependencies used across the admin panel,
including template handling and authentication utilities.
"""
import os
import logging
from functools import wraps
from typing import Optional, Dict, Any, Callable
from flask import request, session, redirect, url_for, render_template, flash, Response, Flask
from werkzeug.local import LocalProxy
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Try to import models
    from admin_panel.models import AdminUser
except ImportError:
    # Fallback for direct import without package
    try:
        from models import AdminUser
    except ImportError:
        logger.warning("Could not import AdminUser model")
        # Define a stub class for AdminUser if we can't import it
        class AdminUser:
            id: str
            username: str
            email: str
            is_active: bool

try:
    # Try to import database session
    from admin_panel.db import get_db_session
except ImportError:
    # Fallback for direct import
    try:
        from db import get_db_session
    except ImportError:
        logger.warning("Could not import database session, using dummy function")
        # Provide a dummy session getter if we can't import the real one
        def get_db_session():
            logger.warning("Using dummy DB session")
            return None

# Template rendering functions
def render_with_context(template_name: str, **context) -> str:
    """Render a template with the given context, adding common variables."""
    # Add common variables to all templates
    base_context = {
        'app_name': 'AI Simulator Admin Panel',
        'version': '0.1.0',
        'nav_links': [
            {'name': 'Dashboard', 'url': '/admin/dashboard', 'icon': 'dashboard'},
            {'name': 'Users', 'url': '/admin/users', 'icon': 'users'},
            {'name': 'Characters', 'url': '/admin/characters', 'icon': 'robot'},
            {'name': 'Messages', 'url': '/admin/messages', 'icon': 'comments'},
            {'name': 'Settings', 'url': '/admin/settings', 'icon': 'cog'},
        ]
    }
    
    # Merge with provided context
    context.update(base_context)
    
    # Add current user if available
    current_user = get_current_admin_user()
    if current_user:
        context['current_user'] = current_user
    
    return render_template(template_name, **context)

# Template singleton object with helper methods
class TemplateRenderer:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    def render(self, template_name: str, **context) -> str:
        """Render a template with common context variables."""
        return render_with_context(template_name, **context)
    
    def flash_message(self, message: str, category: str = 'info') -> None:
        """Flash a message to the user."""
        flash(message, category)

# Create a global templates object
templates = TemplateRenderer()

# Authentication functions
def get_current_admin_user() -> Optional[AdminUser]:
    """Get the currently logged-in admin user."""
    user_id = session.get('admin_user_id')
    if not user_id:
        return None
    
    try:
        db_session = get_db_session()
        if not db_session:
            return None
        
        user = db_session.query(AdminUser).filter_by(id=user_id).first()
        return user
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting current user: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error when getting current user: {e}")
        return None

def login_required(f: Callable) -> Callable:
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        if not get_current_admin_user():
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f: Callable) -> Callable:
    """Decorator to require admin privileges for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        user = get_current_admin_user()
        if not user:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        # Add additional admin check here if needed
        return f(*args, **kwargs)
    return decorated_function

# Export these as the main dependencies
__all__ = ['templates', 'get_current_admin_user', 'login_required', 'admin_required']
