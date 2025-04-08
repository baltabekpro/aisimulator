"""
Routes package initialization for admin panel
"""
# Import blueprints
from admin_panel.routes.main import main_bp
from admin_panel.routes.auth import auth_bp

# Create users_bp here to avoid circular imports
from flask import Blueprint
users_bp = Blueprint('users', __name__, url_prefix='/users')

# Import routes (this must come after blueprint creation to avoid circular imports)
from admin_panel.routes.users import *
