"""
Flask extensions module.
This module initializes all Flask extensions used in the admin panel.
"""
import logging

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions without binding to an app instance (will be bound later)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()  # This initializes CSRF protection

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Make sure CSRF protection is applied to all forms
# This enables CSRF protection globally
logger.info("CSRF protection initialized")

logger.info("Flask extensions initialized")
