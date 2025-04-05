from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from sqlalchemy import text

from models import MessageView, UserView, CharacterView, AdminUser

def register_routes(app):
    """Register all routes with the Flask app"""
    
    @app.route('/')
    @login_required
    def index():
        """Admin panel home page"""
        try:
            # Get table counts using direct SQL
            stats = {}
            for table in ['users', 'characters', 'messages']:
                query = text(f"SELECT COUNT(*) FROM {table}")
                stats[table] = app.db.execute(query).scalar() or 0
                
            return render_template('index.html', stats=stats)
        except Exception as e:
            flash(f'Error loading dashboard: {str(e)}', 'danger')
            return render_template('index.html', stats={})

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Admin login page"""
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Find admin user
            query = text("SELECT id, username, password_hash, is_active FROM admin_users WHERE username = :username")
            user_data = app.db.execute(query, {"username": username}).fetchone()
            
            if user_data and check_password_hash(user_data.password_hash, password):
                # Create AdminUser instance manually
                admin = AdminUser()
                admin.id = user_data.id
                admin.username = user_data.username
                admin.password_hash = user_data.password_hash
                admin.is_active = user_data.is_active
                
                login_user(admin)
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'danger')
                
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        """Logout route"""
        logout_user()
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard with system statistics"""
        try:
            # Get table counts using direct SQL
            stats = {}
            for table in ['users', 'characters', 'messages', 'memory_entries']:
                query = text(f"SELECT COUNT(*) FROM {table}")
                result = app.db.execute(query).scalar()
                stats[table] = result or 0
            
            # Get recent messages using created_at
            query = text("""
                SELECT id, sender_id, sender_type, recipient_id, recipient_type, 
                       content, emotion, created_at
                FROM messages
                ORDER BY created_at DESC
                LIMIT 10
            """)
            messages_data = app.db.execute(query).fetchall()
            recent_messages = [dict(row) for row in messages_data]
            
            # Get recent users
            query = text("""
                SELECT user_id, username, email, created_at 
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            users_data = app.db.execute(query).fetchall()
            recent_users = [dict(row) for row in users_data]
            
            # Get recent characters
            query = text("""
                SELECT id, name, age, created_at 
                FROM characters 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            characters_data = app.db.execute(query).fetchall()
            recent_characters = [dict(row) for row in characters_data]
            
            return render_template(
                'dashboard.html',
                stats=stats,
                recent_messages=recent_messages,
                recent_users=recent_users,
                recent_characters=recent_characters
            )
        except Exception as e:
            flash(f'Error loading dashboard: {str(e)}', 'error')
            return render_template('dashboard.html', stats={}, recent_messages=[], recent_users=[], recent_characters=[])
