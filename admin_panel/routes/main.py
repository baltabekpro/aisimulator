"""
Main routes for the admin panel.
"""
import logging
from flask import Blueprint, render_template
from flask_login import login_required, current_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models
from admin_panel.models import UserView, CharacterView, MessageView

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page."""
    try:
        # Get counts for dashboard
        user_count = UserView.query.count()
        character_count = CharacterView.query.count()
        message_count = MessageView.query.count()
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        user_count = 0
        character_count = 0
        message_count = 0
        
    return render_template(
        'dashboard.html', 
        title='Dashboard',
        user_count=user_count,
        character_count=character_count,
        message_count=message_count
    )

@main_bp.route('/health')
def health():
    """Health check endpoint."""
    return {"status": "ok"}
