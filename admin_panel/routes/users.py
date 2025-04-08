"""
User management routes for the admin panel
"""
import uuid
import logging
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from werkzeug.security import generate_password_hash

from admin_panel.routes import users_bp
from admin_panel.database import db_session
from admin_panel.models import UserView

logger = logging.getLogger(__name__)

@users_bp.route('/')
@login_required
def list_users():
    """List all users"""
    try:
        with db_session() as db:
            users = db.query(UserView).order_by(UserView.created_at.desc()).all()
        return render_template('users/list.html', users=users)
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        flash(f"Error loading users: {e}", "danger")
        return render_template('users/list.html', users=[])

@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """Create a new user"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Simple validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('users/create.html')
        
        try:
            with db_session() as db:
                # Check if user already exists
                existing_user = db.query(UserView).filter(
                    (UserView.username == username) | (UserView.email == email)
                ).first()
                
                if existing_user:
                    flash('Username or email already in use', 'danger')
                    return render_template('users/create.html')
                
                # Create new user object
                new_user = UserView(
                    id=str(uuid.uuid4()),
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password),
                    is_active=True
                )
                
                db.add(new_user)
                
                flash('User created successfully', 'success')
                return redirect(url_for('users.list_users'))
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            flash(f"Error creating user: {e}", "danger")
    
    return render_template('users/create.html')

@users_bp.route('/<user_id>')
@login_required
def view_user(user_id):
    """View a user's details"""
    try:
        with db_session() as db:
            user = db.query(UserView).filter_by(id=user_id).first()
            
            if not user:
                flash('User not found', 'danger')
                return redirect(url_for('users.list_users'))
            
            # Get user-specific data here if needed
            
            return render_template('users/view.html', user=user)
    except Exception as e:
        logger.error(f"Error viewing user: {e}")
        flash(f"Error viewing user: {e}", "danger")
        return redirect(url_for('users.list_users'))