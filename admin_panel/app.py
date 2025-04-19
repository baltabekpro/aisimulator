"""
Административная панель для AI бота

Это приложение предоставляет веб-интерфейс для управления AI персонажами, 
просмотра разговоров и администрирования системы AI бота.

Использование:
    python admin_panel/app.py
"""
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_from_directory, render_template_string
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import logging
import uuid
import contextlib
import psycopg2
import psycopg2.extras
import json
from datetime import datetime
from werkzeug.utils import secure_filename

# Заменим неработающий импорт
# from admin_panel.context_processors import utility_processor

# Создадим функцию utility_processor прямо в файле app.py
import datetime as dt
import os

def utility_processor():
    """
    Предоставляет утилитарные функции для шаблонов
    """
    return {
        'hasattr': hasattr,
        'getattr': getattr,
        'isinstance': isinstance,
        'str': str,
        'len': len,
        'current_year': datetime.now().year,
        'app_version': os.getenv('APP_VERSION', '1.0.0'),
        'is_admin': lambda user: user and hasattr(user, 'is_admin') and user.is_admin,
        'debug_mode': os.getenv('DEBUG', 'False').lower() == 'true'
    }

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, 
            template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
            static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'static')))

# Make sure static folders exist when starting the app
@app.before_first_request
def setup_folders():
    # Create static/css directory if it doesn't exist
    css_dir = os.path.join(app.static_folder, 'css')
    if not os.path.exists(css_dir):
        os.makedirs(css_dir)
        logger.info(f"Created static CSS directory: {css_dir}")
        
    # Create static/js directory if it doesn't exist
    js_dir = os.path.join(app.static_folder, 'js')
    if not os.path.exists(js_dir):
        os.makedirs(js_dir)
        logger.info(f"Created static JS directory: {js_dir}")
        
    # Copy admin.css if it doesn't exist
    admin_css_path = os.path.join(css_dir, 'admin.css')
    if not os.path.exists(admin_css_path):
        default_css = """/* Default admin CSS */
/* This will be replaced by the real CSS file */
.sidebar { background: #4e73df; }
"""
        with open(admin_css_path, 'w') as f:
            f.write(default_css)
        logger.info(f"Created default admin.css file: {admin_css_path}")

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['DATABASE_URL'] = os.getenv('DATABASE_URL')

# Database setup - create a single engine but don't reuse connections
engine = create_engine(app.config['DATABASE_URL'])

# Context manager for database connections
@contextlib.contextmanager
def get_connection():
    """Get a fresh database connection and ensure it's properly closed."""
    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()

# Helper function for database queries that returns results
def execute_query(query, params=None):
    """Execute a query and return the results."""
    with get_connection() as conn:
        with conn.begin():
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            # Fetch all results before the connection is closed
            if query.strip().upper().startswith('SELECT'):
                return result.fetchall()
            return True

# Helper function for database operations that don't need results
def execute_command(query, params=None):
    """Execute a command (INSERT, UPDATE, etc.) with no results needed."""
    with get_connection() as conn:
        with conn.begin():
            if params:
                conn.execute(text(query), params)
            else:
                conn.execute(text(query))
            return True

# Add the missing get_db_connection function
def get_db_connection():
    """Create a connection to the database"""
    try:
        # Get database URL from environment variable
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL not set in environment variables")
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Create and return database connection
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simple User class for Flask-Login
class AdminUser:
    def __init__(self, id, username, is_active=True):
        self.id = id
        self.username = username
        self.is_active = is_active
        self.is_authenticated = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    try:
        query = "SELECT id, username, is_active FROM admin_users WHERE id = :id"
        results = execute_query(query, {"id": user_id})
        if results and len(results) > 0:
            user_data = results[0]
            return AdminUser(id=user_data.id, username=user_data.username, is_active=user_data.is_active)
        return None
    except Exception as e:
        logger.error(f"Error loading user: {e}")
        return None

# Add hasattr function to Jinja2 context
app.jinja_env.globals['hasattr'] = hasattr

# Регистрируем контекстный процессор
app.context_processor(utility_processor)

# Routes
@app.route('/')
@login_required
def index():
    """Admin panel home page"""
    try:
        # Get table counts using direct SQL
        stats = {}
        for table in ['users', 'characters', 'messages']:
            query = f"SELECT COUNT(*) FROM {table}"
            results = execute_query(query)
            stats[table] = results[0][0] if results else 0
            
        return render_template('index.html', stats=stats)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        flash(f'Ошибка загрузки данных: {str(e)}', 'danger')
        return render_template('index.html', stats={})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # Find admin user
            query = "SELECT id, username, password_hash, is_active FROM admin_users WHERE username = :username"
            results = execute_query(query, {"username": username})
            
            if results and len(results) > 0:
                user_data = results[0]
                if check_password_hash(user_data.password_hash, password):
                    admin_user = AdminUser(id=user_data.id, username=user_data.username, is_active=user_data.is_active)
                    login_user(admin_user)
                    
                    # Get next parameter or default to index
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('index'))
            
            flash('Неверное имя пользователя или пароль', 'danger')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Ошибка при входе. Пожалуйста, попробуйте позже.', 'danger')
            
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
        # Get table counts
        stats = {}
        for table in ['users', 'characters', 'messages', 'memory_entries']:
            query = f"SELECT COUNT(*) FROM {table}"
            results = execute_query(query)
            stats[table] = results[0][0] if results else 0
        
        # Get recent messages using created_at
        query = """
            SELECT id, sender_id, sender_type, recipient_id, recipient_type, 
                   content, emotion, created_at
            FROM messages
            ORDER BY created_at DESC
            LIMIT 10
        """
        message_results = execute_query(query)
        recent_messages = []
        for row in message_results:
            # Convert row to dict
            message = {}
            for key in row._mapping:
                message[key] = row._mapping[key]
            recent_messages.append(message)
        
        # Get recent users
        query = """
            SELECT user_id as id, username, email, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 5
        """
        user_results = execute_query(query)
        recent_users = []
        for row in user_results:
            user = {}
            for key in row._mapping:
                user[key] = row._mapping[key]
            recent_users.append(user)
        
        # Get recent characters
        query = """
            SELECT id, name, age, created_at 
            FROM characters 
            ORDER BY created_at DESC 
            LIMIT 5
        """
        char_results = execute_query(query)
        recent_characters = []
        for row in char_results:
            character = {}
            for key in row._mapping:
                character[key] = row._mapping[key]
            recent_characters.append(character)
        
        return render_template(
            'dashboard.html',
            stats=stats,
            recent_messages=recent_messages,
            recent_users=recent_users,
            recent_characters=recent_characters
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash(f'Ошибка загрузки панели: {str(e)}', 'danger')
        return render_template('dashboard.html', stats={}, recent_messages=[], recent_users=[], recent_characters=[])

# Admin user creation - no shared connections
def ensure_admin_exists():
    """Ensure at least one admin user exists"""
    try:
        # Check if admin_users table exists
        with get_connection() as conn:
            # Check if the table exists
            inspector = inspect(engine)
            table_exists = 'admin_users' in inspector.get_table_names()
            
            if not table_exists:
                # Create admin_users table
                query = """
                    CREATE TABLE IF NOT EXISTS admin_users (
                        id VARCHAR(36) PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100),
                        password_hash VARCHAR(200) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_login TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                execute_command(query)
                logger.info("Created admin_users table")
        
        # Check if any admin exists
        query = "SELECT COUNT(*) FROM admin_users"
        results = execute_query(query)
        admin_count = results[0][0] if results else 0
        
        if admin_count == 0:
            # Create default admin user
            admin_username = os.getenv('ADMIN_USERNAME', 'admin')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin_password')
            
            # Generate password hash
            password_hash = generate_password_hash(admin_password)
            
            # Insert admin user
            admin_id = str(uuid.uuid4())
            query = """
                INSERT INTO admin_users (id, username, email, password_hash, is_active, created_at)
                VALUES (:id, :username, :email, :password_hash, true, CURRENT_TIMESTAMP)
            """
            
            execute_command(query, {
                "id": admin_id,
                "username": admin_username,
                "email": f"{admin_username}@example.com",
                "password_hash": password_hash
            })
            
            logger.info(f"Created default admin user: {admin_username}")
    except Exception as e:
        logger.error(f"Error ensuring admin exists: {e}")

# User routes
@app.route('/users')
@login_required
def users():
    try:
        # Add this to provide available endpoints to the template
        available_endpoints = [rule.endpoint for rule in app.url_map.iter_rules()]
        
        users_list = []
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            users_list = cursor.fetchall()
        
        return render_template('users/list.html', users=users_list, available_endpoints=available_endpoints)
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return render_template('users/list.html', users=[], available_endpoints=[])

# Add this route for creating users
@app.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Simple validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('users/create.html')
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if user already exists - use user_id instead of id
                cursor.execute('SELECT user_id FROM users WHERE username = %s OR email = %s', (username, email))
                if cursor.fetchone():
                    flash('Username or email already in use', 'danger')
                    return render_template('users/create.html')
                
                # Generate UUID for user
                user_id = str(uuid.uuid4())
                
                # Hash the password
                hashed_password = generate_password_hash(password)
                
                # Insert new user - using user_id as column name
                cursor.execute(
                    'INSERT INTO users (user_id, username, email, password_hash, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s)',
                    (user_id, username, email, hashed_password, True, datetime.now())
                )
                conn.commit()
                
                flash('User created successfully', 'success')
                return redirect(url_for('users'))
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            flash('An error occurred when creating the user', 'danger')
    
    return render_template('users/create.html')

@app.route('/users/<user_id>')
@login_required
def view_user(user_id):
    try:
        # Select primary key as id for template compatibility
        query = "SELECT user_id as id, username, email, created_at, updated_at, is_active FROM users WHERE user_id = :id"
        results = execute_query(query, {"id": user_id})
        
        if not results or len(results) == 0:
            abort(404)
            
        user = {}
        for key in results[0]._mapping:
            user[key] = results[0]._mapping[key]
        # Fetch primary avatar URL if exists
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT url FROM user_photos WHERE user_id = %s AND is_primary = TRUE", (user_id,))
                row = cur.fetchone()
                user['avatar_url'] = row[0] if row else None
        except Exception:
            user['avatar_url'] = None
        # Debug log avatar URL
        logger.info(f"view_user: primary avatar_url for user {user_id}: {user.get('avatar_url')}")
        # Get user characters
        query = """
            SELECT id, name, background, age, created_at
            FROM characters
            WHERE creator_id = :user_id
            ORDER BY created_at DESC
        """
        char_results = execute_query(query, {"user_id": user_id})
        user_characters = []
        for row in char_results:
            char = {}
            for key in row._mapping:
                char[key] = row._mapping[key]
            user_characters.append(char)
        
        # Get user stats
        query = """
            SELECT COUNT(*) as message_count, MAX(created_at) as last_active
            FROM messages
            WHERE sender_id = :user_id AND sender_type = 'user'
        """
        stat_results = execute_query(query, {"user_id": user_id})
        user_stats = None
        if stat_results and len(stat_results) > 0:
            user_stats = {}
            for key in stat_results[0]._mapping:
                user_stats[key] = stat_results[0]._mapping[key]
        
        return render_template(
            'users/view.html', 
            user=user, 
            user_characters=user_characters,
            user_stats=user_stats
        )
    except Exception as e:
        logger.error(f"Error viewing user: {e}")
        flash(f'Ошибка при просмотре пользователя: {str(e)}', 'danger')
        return redirect(url_for('users'))

@app.route('/users/<user_id>/avatar', methods=['POST'])
@login_required
def upload_user_avatar(user_id):
    """Upload and set primary avatar for a user using MinIO storage"""
    try:
        from minio import Minio
    except ImportError:
        logger.error("MinIO client not installed. Install with: pip install minio")
        flash("Storage error: MinIO client not installed", "danger")
        return redirect(url_for('view_user', user_id=user_id))
        
    file = request.files.get('avatar')
    if not file:
        flash('No avatar file selected', 'danger')
        return redirect(url_for('view_user', user_id=user_id))
        
    # Validate content type
    if file.content_type not in ['image/jpeg','image/png','image/jpg']:
        flash('Invalid file type. Use JPG or PNG.', 'danger')
        return redirect(url_for('view_user', user_id=user_id))
    
    try:
        # Setup MinIO client
        minio_endpoint = os.environ.get("S3_ENDPOINT", "minio:9000").replace("http://", "")
        minio_client = Minio(
            minio_endpoint,
            access_key=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
            secure=False  # Set to True if using HTTPS
        )
        
        # Make bucket if it doesn't exist
        bucket_name = os.environ.get("S3_BUCKET_NAME", "user-files")
        logger.info(f"Connecting to MinIO: {minio_endpoint}, bucket: {bucket_name}")
        
        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
        except Exception as be:
            logger.error(f"Bucket check/creation error: {be}")
            flash(f"Storage error: {str(be)}", "danger")
            return redirect(url_for('view_user', user_id=user_id))
        
        # Save file to temp location
        filename = secure_filename(file.filename)
        temp_path = f"/tmp/{filename}"
        file.save(temp_path)
        logger.info(f"Saved temp file to {temp_path}")
        
        # Upload to MinIO
        object_name = f"users/{user_id}/{filename}"
        minio_client.fput_object(bucket_name, object_name, temp_path, content_type=file.content_type)
        logger.info(f"Uploaded to MinIO as {object_name}")
        
        # Get public URL - Use localhost instead of internal Docker network name
        minio_public_url = os.environ.get('MINIO_PUBLIC_URL', 'http://localhost:9000')
        public_url = f"{minio_public_url}/{bucket_name}/{object_name}"
        logger.info(f"Avatar public URL: {public_url}")
        
        # Save to DB
        with get_db_connection() as conn:
            cur = conn.cursor()
            # Unset previous primary
            cur.execute("UPDATE user_photos SET is_primary = FALSE WHERE user_id = %s", (user_id,))
            # Insert new photo record
            photo_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO user_photos (id, user_id, url, filename, content_type, size, is_primary, created_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW())",
                (photo_id, user_id, public_url, object_name, file.content_type, os.path.getsize(temp_path))
            )
            conn.commit()
            logger.info(f"Saved avatar to DB with photo_id: {photo_id}")
            
        # Delete temp file
        os.remove(temp_path)
        flash('Avatar uploaded successfully', 'success')
    except Exception as e:
        logger.error(f"Error uploading avatar to MinIO: {e}")
        flash(f"Failed to save avatar: {str(e)}", 'danger')
        
    return redirect(url_for('view_user', user_id=user_id))

# Character routes
@app.route('/characters')
@login_required
def characters():
    try:
        query = """
            SELECT id, name, age, personality, created_at
            FROM characters
            ORDER BY created_at DESC
        """
        results = execute_query(query)
        characters_list = []
        for row in results:
            character = {}
            for key in row._mapping:
                character[key] = row._mapping[key]
            characters_list.append(character)
        
        return render_template('characters/list.html', characters=characters_list)
    except Exception as e:
        logger.error(f"Error loading characters: {e}")
        flash(f'Ошибка при загрузке персонажей: {str(e)}', 'danger')
        return render_template('characters/list.html', characters=[])

@app.route('/messages')
@login_required
def messages():
    try:
        # Use messages_with_names view or query with explicit type casting
        try:
            # First try to use pre-created view for faster performance
            query = """
                SELECT * FROM messages_with_names
                ORDER BY created_at DESC
                LIMIT 100
            """
            results = execute_query(query)
        except Exception:
            # If view not found, use full query with explicit type casting
            query = """
                SELECT m.id, m.sender_id, m.sender_type, m.recipient_id, m.recipient_type, 
                       m.content, m.emotion, m.created_at,
                       CASE 
                           WHEN m.sender_type = 'user' AND u1.username IS NOT NULL THEN u1.username::text
                           WHEN m.sender_type = 'character' AND c1.name IS NOT NULL THEN c1.name::text
                           ELSE m.sender_id::text 
                       END as sender_name,
                       CASE 
                           WHEN m.recipient_type = 'user' AND u2.username IS NOT NULL THEN u2.username::text
                           WHEN m.recipient_type = 'character' AND c2.name IS NOT NULL THEN c2.name::text
                           ELSE m.recipient_id::text 
                       END as recipient_name
                FROM messages m
                LEFT JOIN users u1 ON m.sender_id::text = u1.user_id::text AND m.sender_type = 'user'
                LEFT JOIN characters c1 ON m.sender_id::text = c1.id::text AND m.sender_type = 'character'
                LEFT JOIN users u2 ON m.recipient_id::text = u2.user_id::text AND m.recipient_type = 'user'
                LEFT JOIN characters c2 ON m.recipient_id::text = c2.id::text AND m.recipient_type = 'character'
                ORDER BY m.created_at DESC
                LIMIT 100
            """
            results = execute_query(query)
        
        messages_list = []
        if results:
            for row in results:
                # Convert Row object to dict safely, handling UUID objects
                message = {}
                for key in row._mapping:
                    # Convert all UUIDs to strings to avoid subscripting issues
                    value = row._mapping[key]
                    if hasattr(value, 'hex'):  # Check if it's a UUID
                        message[key] = str(value)
                    else:
                        message[key] = value
                messages_list.append(message)
        
        return render_template('messages/list.html', messages=messages_list)
    except Exception as e:
        logger.error(f"Error loading messages: {e}")
        flash(f'Error loading messages: {str(e)}', 'danger')
        return render_template('messages/list.html', messages=[])

@app.route('/settings')
@login_required
def settings():
    return render_template('settings/index.html')

@app.route('/memories')
@login_required
def memories():
    """Display all memories"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Get total memory count
            cursor.execute("SELECT COUNT(*) FROM memory_entries")
            total_count = cursor.fetchone()[0]
            
            # Get memories with character names - don't filter by user ID
            cursor.execute("""
                SELECT m.id, m.character_id, c.name as character_name, 
                       m.memory_type, m.category, m.content, m.importance,
                       m.user_id, m.created_at
                FROM memory_entries m
                LEFT JOIN characters c ON c.id::text = m.character_id::text
                ORDER BY m.created_at DESC
                LIMIT 200
            """)
            memories = cursor.fetchall()
            
            # Get character list for filter dropdown
            cursor.execute("""
                SELECT DISTINCT c.id, c.name 
                FROM characters c
                JOIN memory_entries m ON c.id::text = m.character_id::text
                ORDER BY c.name
            """)
            characters = cursor.fetchall()
            
        return render_template('memories/list.html', 
                              memories=memories,
                              characters=characters,
                              total_count=total_count)
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        flash(f"Error retrieving memories: {e}", "danger")
        return render_template('memories/list.html', memories=[], characters=[], total_count=0)

@app.route('/memories/character/<character_id>')
@login_required
def character_memories(character_id):
    """Display memories for a specific character"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Get character info
            cursor.execute("""
                SELECT * FROM characters WHERE id::text = %s
            """, (character_id,))
            character = cursor.fetchone()
            
            if not character:
                flash("Character not found", "danger")
                return redirect(url_for('memories'))
            
            # Get memories for this character - adjusting columns to match table schema
            cursor.execute("""
                SELECT id, memory_type, category, content, importance, user_id, created_at
                FROM memory_entries
                WHERE character_id::text = %s
                ORDER BY created_at DESC
            """, (character_id,))
            memories = cursor.fetchall()
            
            # Get users list for the dropdown
            cursor.execute("SELECT user_id, username, name FROM users ORDER BY username")
            users = cursor.fetchall()
            
            # Add system user if needed
            has_system_user = False
            for user in users:
                if str(user['user_id']) == '00000000-0000-0000-0000-000000000000':
                    has_system_user = True
                    break
            
            if not has_system_user:
                # Prepare system user for the dropdown
                system_user = {
                    'user_id': '00000000-0000-0000-0000-000000000000',
                    'username': 'system',
                    'name': 'Системный пользователь'
                }
                users = [system_user] + list(users)
            
        return render_template('memories/character.html', 
                              character=character,
                              memories=memories,
                              users=users)
    except Exception as e:
        logger.error(f"Error retrieving character memories: {e}")
        flash(f"Error retrieving character memories: {e}", "danger")
        return redirect(url_for('memories'))

@app.route('/memories/add', methods=['GET', 'POST'])
@login_required
def add_memory():
    """Add a new memory"""
    if request.method == 'POST':
        character_id = request.form.get('character_id')
        content = request.form.get('content')
        importance = request.form.get('importance', 5)
        user_id = request.form.get('user_id')
        memory_type = request.form.get('memory_type')  # Get memory_type from form
        category = request.form.get('category', 'general')  # Get category or use default
        
        # Generate a UUID for the memory
        memory_id = str(uuid.uuid4())
        
        # Validate user_id if provided - must be valid UUID
        if user_id and user_id.strip():
            try:
                # Attempt to parse as UUID to validate format
                uuid.UUID(user_id)
            except ValueError:
                # If not a valid UUID, log it and use system user instead
                logger.warning(f"Invalid user_id format: {user_id}, using system user instead")
                user_id = '00000000-0000-0000-0000-000000000000'
        else:
            # Use the standard system user UUID if no user_id provided
            user_id = '00000000-0000-0000-0000-000000000000'
            logger.info(f"No user_id provided, using system user ID: {user_id}")
        
        # Insert memory with all required fields
        sql_query = """
            INSERT INTO memory_entries 
            (id, character_id, user_id, type, memory_type, category, content, importance, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        sql_params = [
            memory_id, character_id, user_id, 
            memory_type, memory_type,  # Set both type and memory_type to same value
            category, content, importance, datetime.now()
        ]
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_query, sql_params)
                conn.commit()
                
            flash("Memory added successfully", "success")
            return redirect(url_for('character_memories', character_id=character_id))
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            flash(f"Error adding memory: {e}", "danger")
            return redirect(url_for('memories'))
    
    # GET method - show form
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # Get characters list
            cursor.execute("SELECT id, name FROM characters ORDER BY name")
            characters = cursor.fetchall()
            
            # Get users list
            cursor.execute("SELECT user_id, username, name FROM users ORDER BY username")
            users = cursor.fetchall()
            
            # Add system user if needed
            has_system_user = False
            for user in users:
                if str(user['user_id']) == '00000000-0000-0000-0000-000000000000':
                    has_system_user = True
                    break
            
            if not has_system_user:
                # Prepare system user for the dropdown
                system_user = {
                    'user_id': '00000000-0000-0000-0000-000000000000',
                    'username': 'system',
                    'name': 'Системный пользователь'
                }
                users = [system_user] + list(users)
        
        return render_template('memories/add.html', characters=characters, users=users)
    except Exception as e:
        logger.error(f"Error loading add memory form: {e}")
        flash(f"Error loading add memory form: {e}", "danger")
        return redirect(url_for('memories'))

@app.route('/memories/delete/<memory_id>', methods=['POST'])
@login_required
def delete_memory(memory_id):
    """Delete a memory"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get character_id for redirect
            cursor.execute("SELECT character_id FROM memory_entries WHERE id::text = %s", (memory_id,))
            result = cursor.fetchone()
            
            if result:
                character_id = result[0]
                
                # Delete the memory
                cursor.execute("DELETE FROM memory_entries WHERE id::text = %s", (memory_id,))
                conn.commit()
                
                flash("Memory deleted successfully", "success")
                return redirect(url_for('character_memories', character_id=character_id))
            else:
                flash("Memory not found", "danger")
                return redirect(url_for('memories'))
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        flash(f"Error deleting memory: {e}", "danger")
        return redirect(url_for('memories'))

# Fix character buttons
@app.route('/characters/<character_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_character(character_id):
    """Edit a character"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            if request.method == 'POST':
                # Update character info
                name = request.form.get('name')
                age = request.form.get('age')
                gender = request.form.get('gender')
                background = request.form.get('background')
                
                # Handle personality traits and interests
                personality_traits = request.form.get('personality_traits', '')
                interests = request.form.get('interests', '')
                
                # Convert string to list
                if isinstance(personality_traits, str):
                    personality_traits = [trait.strip() for trait in personality_traits.split(',') if trait.strip()]
                if isinstance(interests, str):
                    interests = [interest.strip() for interest in interests.split(',') if interest.strip()]
                
                cursor.execute("""
                    UPDATE characters
                    SET name = %s,
                        age = %s,
                        gender = %s,
                        background = %s,
                        personality = %s,
                        interests = %s,
                        updated_at = %s
                    WHERE id::text = %s
                """, (
                    name,
                    age,
                    gender,
                    background,
                    json.dumps(personality_traits) if isinstance(personality_traits, (list, dict)) else personality_traits,
                    json.dumps(interests) if isinstance(interests, (list, dict)) else interests,
                    datetime.now(),
                    character_id
                ))
                
                # Handle avatar upload - now using MinIO
                avatar_file = request.files.get('avatar')
                if (avatar_file and avatar_file.filename):
                    try:
                        from minio import Minio
                    except ImportError:
                        logger.error("MinIO client not installed. Install with: pip install minio")
                        flash("Storage error: MinIO client not installed", "danger")
                        return redirect(url_for('characters'))
                    
                    # Validate content type
                    if avatar_file.content_type not in ['image/jpeg','image/png','image/jpg']:
                        flash('Invalid avatar file type. Use JPG or PNG.', 'danger')
                    else:
                        try:
                            # Setup MinIO client
                            minio_endpoint = os.environ.get("S3_ENDPOINT", "minio:9000").replace("http://", "")
                            minio_client = Minio(
                                minio_endpoint,
                                access_key=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
                                secret_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
                                secure=False  # Set to True if using HTTPS
                            )
                            
                            # Make bucket if it doesn't exist
                            bucket_name = os.environ.get("S3_BUCKET_NAME", "user-files")
                            logger.info(f"Connecting to MinIO: {minio_endpoint}, bucket: {bucket_name}")
                            
                            try:
                                if not minio_client.bucket_exists(bucket_name):
                                    minio_client.make_bucket(bucket_name)
                                    logger.info(f"Created bucket: {bucket_name}")
                            except Exception as be:
                                logger.error(f"Bucket check/creation error: {be}")
                                flash(f"Storage error: {str(be)}", "danger")
                                return redirect(url_for('characters'))
                            
                            # Save file to temp location
                            avatar_filename = secure_filename(avatar_file.filename)
                            temp_path = f"/tmp/{avatar_filename}"
                            avatar_file.save(temp_path)
                            logger.info(f"Saved temp avatar file to {temp_path}")
                            
                            # Upload to MinIO
                            object_name = f"characters/{character_id}/{avatar_filename}"
                            minio_client.fput_object(bucket_name, object_name, temp_path, content_type=avatar_file.content_type)
                            logger.info(f"Uploaded character avatar to MinIO as {object_name}")
                            
                            # Get public URL - Use localhost instead of internal Docker network name
                            minio_public_url = os.environ.get('MINIO_PUBLIC_URL', 'http://localhost:9000')
                            avatar_url = f"{minio_public_url}/{bucket_name}/{object_name}"
                            logger.info(f"Character avatar public URL: {avatar_url}")
                            
                            # Update avatar URL in database
                            cursor.execute(
                                "UPDATE characters SET avatar_url = %s WHERE id::text = %s",
                                (avatar_url, character_id)
                            )
                            
                            # Delete temp file
                            os.remove(temp_path)
                            flash('Character avatar uploaded successfully', 'success')
                        except Exception as e:
                            logger.error(f"Error uploading character avatar to MinIO: {e}")
                            flash(f"Failed to save avatar: {str(e)}", "danger")
                
                # Commit all changes
                conn.commit()
                flash("Персонаж успешно обновлен", "success")
                return redirect(url_for('characters'))
            
            # GET method - fetch character data
            cursor.execute("SELECT * FROM characters WHERE id::text = %s", (character_id,))
            character = cursor.fetchone()
            
            if not character:
                flash("Персонаж не найден", "danger")
                return redirect(url_for('characters'))
            
            return render_template('characters/edit.html', character=character)
    except Exception as e:
        logger.error(f"Error editing character: {e}")
        flash(f"Ошибка при редактировании персонажа: {e}", "danger")
        return redirect(url_for('characters'))

@app.route('/characters/<character_id>/memories')
@login_required
def view_character_memories(character_id):
    """View memories for a specific character"""
    return redirect(url_for('character_memories', character_id=character_id))

@app.route('/characters/add', methods=['GET', 'POST'])
@login_required
def add_character():
    """Add a new character"""
    if request.method == 'POST':
        try:
            # Extract form data
            name = request.form.get('name')
            age = request.form.get('age', type=int)
            gender = request.form.get('gender')
            background = request.form.get('background')
            
            # Handle personality traits and interests properly
            personality_traits = request.form.get('personality_traits', '')
            interests = request.form.get('interests', '')
            
            # Convert string to list if needed
            if isinstance(personality_traits, str):
                personality_traits = [trait.strip() for trait in personality_traits.split(',') if trait.strip()]
            
            if isinstance(interests, str):
                interests = [interest.strip() for interest in interests.split(',') if interest.strip()]
            
            # Generate a UUID for the new character
            character_id = str(uuid.uuid4())
            
            # Insert the character into the database with proper casting to JSONB
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO characters (id, name, age, gender, background, 
                                           personality, interests, created_at) 
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                """, (
                    character_id, name, age, gender, background, 
                    json.dumps(personality_traits), json.dumps(interests), datetime.now()
                ))
                conn.commit()
            
            flash("Character created successfully", "success")
            return redirect(url_for('characters'))
        except Exception as e:
            logger.error(f"Error creating character: {e}")
            flash(f"Error creating character: {e}", "danger")
    
    return render_template('characters/add.html')

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# Создаем функцию для автоматического внедрения исправления меню в шаблоны
@app.context_processor
def inject_sidebar_fix():
    """
    Автоматически внедряет исправление для меню во все шаблоны
    """
    return {'include_sidebar_fix': True}

# Создаем маршрут для доступа к статическим файлам JS/CSS через API
@app.route('/auto-sidebar-fix.js')
def sidebar_fix_js():
    return send_from_directory(os.path.join(app.root_path, 'static', 'js'), 'sidebar_fix.js')

@app.route('/auto-sidebar-fix.css')
def sidebar_fix_css():
    return send_from_directory(os.path.join(app.root_path, 'static', 'css'), 'sidebar.css')

# После каждого запроса внедряем код для исправления меню
@app.after_request
def inject_menu_fix(response):
    """
    Inject menu fix JavaScript and CSS into HTML responses
    """
    if response.content_type and response.content_type.startswith('text/html'):
        body_end_marker = '</body>'
        
        if body_end_marker in response.get_data(as_text=True):
            # Load fix template
            inject_path = os.path.join(app.root_path, 'templates', 'inject_fix.html')
            
            if os.path.exists(inject_path):
                with open(inject_path, 'r') as f:
                    inject_html = f.read()
            else:
                # Create the template inline if it doesn't exist
                inject_html = """
                <!-- Menu fix injection -->
                <link rel="stylesheet" href="{{ url_for('static', filename='css/sidebar-fix.css') }}">
                <script src="{{ url_for('static', filename='js/admin.js') }}"></script>
                <script>
                    // Add mobile class to body based on screen size
                    if (window.innerWidth < 768) {
                        document.body.classList.add('mobile-view');
                    }
                </script>
                """
            
            # Render template with Flask context
            rendered_inject = render_template_string(inject_html)
            
            # Inject the fix before </body>
            html = response.get_data(as_text=True)
            modified_html = html.replace(body_end_marker, rendered_inject + body_end_marker)
            
            response.set_data(modified_html)
    
    return response

if __name__ == '__main__':
    # Make sure templates folder exists
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        logger.info(f"Created templates directory: {templates_dir}")
    
    # Make sure static folder exists
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        logger.info(f"Created static directory: {static_dir}")
    
    # Ensure admin user exists
    ensure_admin_exists()
    
    # Show template folder and all templates
    logger.info(f"Template folder: {app.template_folder}")
    logger.info(f"Templates: {os.listdir(app.template_folder) if os.path.exists(app.template_folder) else 'No templates'}")
    
    # Add hasattr function to Jinja2 context
    app.jinja_env.globals['hasattr'] = hasattr
    
    # Регистрируем контекстный процессор
    app.context_processor(utility_processor)
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)
