"""
Authentication routes for the admin panel
"""
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from admin_panel.extensions import db, csrf
from admin_panel.models import AdminUser
from admin_panel.forms import LoginForm

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            remember = form.remember.data
            
            try:
                # Find the user
                user = AdminUser.query.filter_by(username=username).first()
                
                if user and check_password_hash(user.password_hash, password):
                    login_user(user, remember=remember)
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('main.dashboard'))
                else:
                    flash('Неверное имя пользователя или пароль', 'danger')
            except Exception as e:
                logger.error(f"Login error: {e}")
                flash('Ошибка при входе. Пожалуйста, попробуйте позже.', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('auth.login'))
