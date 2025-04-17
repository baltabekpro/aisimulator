import logging
import os
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError
import uuid
import json
from datetime import datetime

from core.db.session import engine
from core.db.base import Base
from core.db.models import User, AIPartner
from core.db.models.message import Message

logger = logging.getLogger(__name__)

def init_db():
    """Initialize database and create all tables."""
    logger.info("Creating database tables...")
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Apply necessary schema fixes after table creation
        fix_schema_issues()
        add_external_id_to_users()
        create_admin_message_view()
        
        logger.info("Schema modifications completed successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def create_test_data():
    """Populate database with test data for development."""
    from sqlalchemy.orm import Session
    from core.db.session import SessionLocal
    
    db = SessionLocal()
    
    try:
        # Check if we already have test data
        existing_users = db.query(User).count()
        
        # Direct SQL check for AI partners (safer than ORM for this case)
        partner_count_result = db.execute(sa.text("SELECT COUNT(*) FROM ai_partners")).scalar()
        existing_partners = partner_count_result if partner_count_result is not None else 0
        
        if existing_users > 0 and existing_partners > 0:
            logger.info("Test data already exists, skipping creation")
            return
        
        logger.info("Creating test data...")
        
        # Only create users if they don't already exist
        if existing_users == 0:
            logger.info("Creating test users...")
            # Check if specific usernames already exist
            admin_exists = db.execute(sa.text("SELECT COUNT(*) FROM users WHERE username = 'admin'")).scalar() > 0
            user_exists = db.execute(sa.text("SELECT COUNT(*) FROM users WHERE username = 'user'")).scalar() > 0
            
            # Create test admin user if it doesn't exist
            if not admin_exists:
                test_admin = User(
                    user_id=uuid.uuid4(),
                    username="admin",
                    email="admin@example.com",
                    name="Admin User",
                    is_admin=True,
                    is_active=True
                )
                test_admin.set_password("admin123")
                db.add(test_admin)
                logger.info("Created admin user")
            else:
                logger.info("Admin user already exists, skipping creation")
            
            # Create test regular user if it doesn't exist
            if not user_exists:
                test_user = User(
                    user_id=uuid.uuid4(),
                    username="user",
                    email="user@example.com",
                    name="Test User",
                    is_admin=False,
                    is_active=True
                )
                test_user.set_password("password123")
                db.add(test_user)
                logger.info("Created regular user")
            else:
                logger.info("Regular user already exists, skipping creation")
            
            # Commit user changes separately
            try:
                db.commit()
                logger.info("User creation successful")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create users: {e}")
        else:
            logger.info(f"Already have {existing_users} users, skipping user creation")
        
        # Only create partners if they don't already exist
        if existing_partners == 0:
            logger.info("Creating AI partners...")
            # First check what columns actually exist in the table
            inspector = sa.inspect(engine)
            
            # Get actual column names from ai_partners table
            existing_columns = {col['name'] for col in inspector.get_columns('ai_partners')}
            logger.info(f"Available columns in ai_partners table: {existing_columns}")
            
            # Create test AI partners using only the columns that actually exist in the table
            test_partners = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Алиса",
                    "gender": "female",
                    "personality_traits": json.dumps(["дружелюбная", "общительная", "веселая"]),
                    "interests": json.dumps(["музыка", "искусство", "путешествия"]),
                    "background": "Алиса - творческая личность, которая любит путешествовать и знакомиться с новыми людьми.",
                    "current_emotion": "happy"
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Мария",
                    "gender": "female", 
                    "personality_traits": json.dumps(["умная", "спокойная", "загадочная"]),
                    "interests": json.dumps(["чтение", "психология", "йога"]),
                    "background": "Мария - глубокая и философски настроенная натура, интересующаяся духовным развитием.",
                    "current_emotion": "neutral"
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "София",
                    "gender": "female",
                    "personality_traits": json.dumps(["энергичная", "амбициозная", "уверенная"]),
                    "interests": json.dumps(["спорт", "бизнес", "технологии"]),
                    "background": "София - целеустремленная девушка, увлеченная саморазвитием и новыми технологиями.",
                    "current_emotion": "excited"
                }
            ]
            
            # Filter out non-existent columns for each partner
            partners_added = 0
            for partner in test_partners:
                # Keep only columns that exist in the table
                filtered_partner = {k: v for k, v in partner.items() if k in existing_columns}
                
                if filtered_partner:
                    columns = ", ".join(filtered_partner.keys())
                    placeholders = ", ".join([f":{key}" for key in filtered_partner.keys()])
                    
                    try:
                        insert_query = sa.text(f"INSERT INTO ai_partners ({columns}) VALUES ({placeholders})")
                        db.execute(insert_query, filtered_partner)
                        logger.info(f"Inserted partner: {filtered_partner['name']}")
                        partners_added += 1
                    except Exception as e:
                        logger.error(f"Failed to insert partner {filtered_partner.get('name', 'unknown')}: {e}")
            
            # Commit partner changes
            if partners_added > 0:
                try:
                    db.commit()
                    logger.info(f"Successfully added {partners_added} AI partners")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to commit AI partners: {e}")
        else:
            logger.info(f"Already have {existing_partners} AI partners, skipping creation")
        
        logger.info("Test data creation completed")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating test data: {e}")
    finally:
        db.close()

def fix_schema_issues():
    """
    Fix common schema issues by checking columns and adding missing ones
    This is a simple alternative to full migrations for development
    """
    from sqlalchemy import inspect, Column, String, Integer, DateTime, Text, Boolean
    # No need to import UUID type, we'll use TEXT or native SQL for it
    import sqlite3
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Create all tables if they don't exist
    if 'ai_partners' not in tables or 'users' not in tables:
        logger.info("Some tables don't exist, creating all tables")
        Base.metadata.create_all(bind=engine)
        return

    # For SQLite, use direct SQL for safety
    if 'sqlite' in str(engine.url):
        db_path = str(engine.url).replace('sqlite:///', '')
        logger.info(f"Using SQLite database at: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fix AI Partners table
        logger.info("Checking AI Partners table schema")
        try:
            # Get existing columns in ai_partners
            cursor.execute("PRAGMA table_info(ai_partners)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            
            # Add missing columns with direct SQL
            if 'gender' not in existing_columns:
                logger.info("Adding gender column to ai_partners table")
                cursor.execute("ALTER TABLE ai_partners ADD COLUMN gender TEXT DEFAULT 'female' NOT NULL")
            
            # Define other columns to check and add if missing
            columns_to_add = [
                ('personality_traits', 'TEXT'),
                ('interests', 'TEXT'),
                ('fetishes', 'TEXT'),
                ('background', 'TEXT'),
                ('height', 'INTEGER'),
                ('weight', 'INTEGER'),
                ('hair_color', 'TEXT'),
                ('eye_color', 'TEXT'),
                ('body_type', 'TEXT'),
                ('current_emotion', 'TEXT')
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    logger.info(f"Adding {col_name} column to ai_partners table")
                    cursor.execute(f"ALTER TABLE ai_partners ADD COLUMN {col_name} {col_type}")
        except Exception as e:
            logger.error(f"Error fixing ai_partners table: {e}")

        # Fix Users table
        logger.info("Checking Users table schema")
        try:
            # Get existing columns in users
            cursor.execute("PRAGMA table_info(users)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            
            # Add missing columns with direct SQL for users table
            user_columns_to_add = [
                ('name', 'TEXT'),
                ('is_active', 'BOOLEAN DEFAULT 1'),
                ('is_admin', 'BOOLEAN DEFAULT 0'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP')
            ]
            
            for col_name, col_type in user_columns_to_add:
                if col_name not in existing_columns:
                    logger.info(f"Adding {col_name} column to users table")
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except Exception as e:
            logger.error(f"Error fixing users table: {e}")

        # Check the messages table
        if 'messages' not in tables:
            logger.info("Creating messages table")
            Base.metadata.create_all(bind=engine)
        else:
            logger.info("Checking messages table schema")
            cursor.execute("PRAGMA table_info(messages)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            messages_columns_to_add = [
                ('sender_id', 'TEXT'),
                ('sender_type', 'TEXT'),
                ('recipient_id', 'TEXT'),
                ('recipient_type', 'TEXT'),
                ('content', 'TEXT'),
                ('emotion', 'TEXT'),
                ('is_read', 'BOOLEAN DEFAULT 0'),
                ('is_gift', 'BOOLEAN DEFAULT 0'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP')
            ]
            for col_name, col_def in messages_columns_to_add:
                if col_name not in existing_columns:
                    logger.info(f"Adding {col_name} column to messages table")
                    cursor.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_def}")
            if 'id' not in existing_columns:
                logger.info("Adding id column to messages table")
                cursor.execute("ALTER TABLE messages ADD COLUMN id TEXT")
            if 'message_id' in existing_columns and 'id' not in existing_columns:
                logger.info("Renaming message_id column to id in messages table (SQLite)")
                cursor.execute("ALTER TABLE messages RENAME COLUMN message_id TO id")

        conn.commit()
        conn.close()
        logger.info("SQLite schema updates completed")
    else:
        # For non-SQLite databases, use SQLAlchemy's more powerful approach
        # Check and fix AI Partners table
        existing_columns = {col['name'] for col in inspector.get_columns('ai_partners')}
        
        # Add gender column if it doesn't exist
        if 'gender' not in existing_columns:
            logger.info("Adding gender column to ai_partners table")
            with engine.begin() as conn:
                conn.execute(sa.text("ALTER TABLE ai_partners ADD COLUMN gender VARCHAR(20) DEFAULT 'female' NOT NULL"))

        # Define and add other missing columns
        columns_to_check = {
            'personality_traits': 'TEXT',
            'interests': 'TEXT',
            'background': 'TEXT',
            'current_emotion': 'VARCHAR(50)'
        }
        
        for col_name, col_type in columns_to_check.items():
            if col_name not in existing_columns:
                logger.info(f"Adding {col_name} column to ai_partners table")
                with engine.begin() as conn:
                    conn.execute(sa.text(f"ALTER TABLE ai_partners ADD COLUMN {col_name} {col_type}"))

        # Check and fix Users table
        logger.info("Checking Users table schema")
        user_existing_columns = {col['name'] for col in inspector.get_columns('users')}
        
        # Add missing columns for Users table
        user_columns_to_check = {
            'name': 'VARCHAR(100)',
            'is_active': 'BOOLEAN DEFAULT TRUE',
            'is_admin': 'BOOLEAN DEFAULT FALSE'
        }
        
        for col_name, col_type in user_columns_to_check.items():
            if col_name not in user_existing_columns:
                logger.info(f"Adding {col_name} column to users table")
                with engine.begin() as conn:
                    conn.execute(sa.text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))

        # Check and fix Messages table
        if 'messages' not in tables:
            logger.info("Creating messages table")
            Base.metadata.create_all(bind=engine)
        else:
            msg_existing_cols = {col['name'] for col in inspector.get_columns('messages')}
            missing_cols_dict = {
                'sender_id': 'UUID',
                'sender_type': 'VARCHAR(50)',
                'recipient_id': 'UUID',
                'recipient_type': 'VARCHAR(50)',
                'content': 'TEXT',
                'emotion': 'VARCHAR(50)',
                'is_read': 'BOOLEAN DEFAULT FALSE',
                'is_gift': 'BOOLEAN DEFAULT FALSE',
                'created_at': 'TIMESTAMP DEFAULT now()',
                'updated_at': 'TIMESTAMP'
            }
            for col_name, col_type in missing_cols_dict.items():
                if col_name not in msg_existing_cols:
                    logger.info(f"Adding {col_name} column to messages table (non-SQLite)")
                    try:
                        with engine.begin() as conn:
                            conn.execute(sa.text(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}"))
                    except Exception as e:
                        logger.warning(f"Could not add column {col_name}: {e}")
                        
            # Handle the ID column separately with better error checking
            if 'id' not in msg_existing_cols:
                logger.info("Adding id column to messages table (non-SQLite)")
                try:
                    with engine.begin() as conn:
                        is_postgres = 'postgres' in str(engine.url).lower()
                        
                        if is_postgres:
                            # Use text type with PostgreSQL functions
                            try:
                                conn.execute(sa.text("SELECT gen_random_uuid()"))
                                uuid_func = "gen_random_uuid()"
                            except Exception:
                                try:
                                    # Try another PostgreSQL UUID function
                                    conn.execute(sa.text("SELECT uuid_generate_v4()"))
                                    uuid_func = "uuid_generate_v4()"
                                except Exception:
                                    # Fallback to simple text
                                    conn.execute(sa.text("ALTER TABLE messages ADD COLUMN id VARCHAR(36)"))
                                    return
                                    
                            # Add column using PostgreSQL UUID type
                            conn.execute(sa.text(f"ALTER TABLE messages ADD COLUMN id UUID DEFAULT {uuid_func}"))
                        else:
                            # For other databases, use VARCHAR
                            conn.execute(sa.text("ALTER TABLE messages ADD COLUMN id VARCHAR(36)"))
                except Exception as e:
                    logger.warning(f"Could not add id column: {e}")
                    # Fallback to simple VARCHAR
                    try:
                        with engine.begin() as conn:
                            conn.execute(sa.text("ALTER TABLE messages ADD COLUMN id VARCHAR(36)"))
                    except Exception as inner_e:
                        logger.error(f"Failed fallback for id column: {inner_e}")
                    
            # Handle column rename with better error checking
            if 'message_id' in msg_existing_cols and 'id' not in msg_existing_cols:
                logger.info("Renaming message_id column to id in messages table (non-SQLite)")
                try:
                    with engine.begin() as conn:
                        conn.execute(sa.text("ALTER TABLE messages RENAME COLUMN message_id TO id"))
                except Exception as e:
                    logger.warning(f"Could not rename message_id column: {e}")

    logger.info("Schema fix completed successfully")

def add_external_id_to_users():
    """Add external_id column to users table if it doesn't exist."""
    logger.info("Checking for external_id column in users table...")
    inspector = sa.inspect(engine)
    
    try:
        # Check if users table exists first
        if 'users' not in inspector.get_table_names():
            logger.info("Users table doesn't exist yet, skipping external_id check")
            return
        
        # Check if external_id column already exists
        user_columns = {col['name'] for col in inspector.get_columns('users')}
        
        if 'external_id' not in user_columns:
            logger.info("Adding external_id column to users table")
            with engine.begin() as conn:
                # Add external_id column
                conn.execute(sa.text("ALTER TABLE users ADD COLUMN external_id VARCHAR(255)"))
                # Create index for faster lookups
                conn.execute(sa.text("CREATE INDEX idx_users_external_id ON users(external_id)"))
            
            logger.info("Successfully added external_id column to users table")
        else:
            logger.info("external_id column already exists in users table")
    except Exception as e:
        logger.error(f"Error adding external_id column: {e}")

def create_admin_message_view():
    """Create or replace admin message view with correct type casting."""
    logger.info("Creating or replacing admin message view with portable type casting...")
    
    try:
        with engine.begin() as conn:
            # Drop the view if it exists
            try:
                conn.execute(sa.text("DROP VIEW IF EXISTS admin_messages_view"))
                logger.info("Dropped existing admin_messages_view")
            except Exception as e:
                logger.warning(f"Could not drop admin_messages_view: {e}")
            
            # Определяем диалект базы данных
            is_postgres = 'postgresql' in str(engine.url).lower()
            
            # Создаём SQL запрос в зависимости от типа базы данных
            if is_postgres:
                # PostgreSQL поддерживает приведение типов через ::
                create_view_sql = """
                CREATE OR REPLACE VIEW admin_messages_view AS
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
                """
            else:
                # SQLite и другие базы данных без поддержки ::text - используем CAST или строковые функции
                create_view_sql = """
                CREATE OR REPLACE VIEW admin_messages_view AS
                SELECT m.id, m.sender_id, m.sender_type, m.recipient_id, m.recipient_type,
                       m.content, m.emotion, m.created_at,
                       CASE 
                           WHEN m.sender_type = 'user' AND u1.username IS NOT NULL THEN u1.username
                           WHEN m.sender_type = 'character' AND c1.name IS NOT NULL THEN c1.name
                           ELSE m.sender_id
                       END as sender_name,
                       CASE 
                           WHEN m.recipient_type = 'user' AND u2.username IS NOT NULL THEN u2.username
                           WHEN m.recipient_type = 'character' AND c2.name IS NOT NULL THEN c2.name
                           ELSE m.recipient_id
                       END as recipient_name
                FROM messages m
                LEFT JOIN users u1 ON m.sender_id = u1.user_id AND m.sender_type = 'user'
                LEFT JOIN characters c1 ON m.sender_id = c1.id AND m.sender_type = 'character'
                LEFT JOIN users u2 ON m.recipient_id = u2.user_id AND m.recipient_type = 'user'
                LEFT JOIN characters c2 ON m.recipient_id = c2.id AND m.recipient_type = 'character'
                """
            
            conn.execute(sa.text(create_view_sql))
            logger.info("Successfully created admin_messages_view with proper type casting for the current database type")
    except Exception as e:
        logger.error(f"Error creating admin message view: {e}")

def create_test_character():
    """Create a test character with proper attributes to avoid errors"""
    from sqlalchemy.orm import Session
    from core.db.session import SessionLocal
    
    db = SessionLocal()
    
    try:
        # Check if characters table exists and has at least one character
        table_name = "characters"
        inspector = sa.inspect(engine)
        if table_name not in inspector.get_table_names():
            logger.info(f"Table {table_name} doesn't exist, skipping character creation")
            return
            
        # Check if we already have test characters
        query = sa.text("SELECT COUNT(*) FROM characters")
        existing_count = db.execute(query).scalar()
        
        if existing_count > 0:
            logger.info(f"Already have {existing_count} characters, skipping creation")
            return
            
        logger.info("Creating test character")
        
        # Create the character with an SQL statement to avoid attribute errors
        character_data = {
            "id": "8c054f20-4a77-4eef-83e6-245d3456bdf1", 
            "name": "Алиса",
            "age": 24,
            "gender": "female",
            "personality": json.dumps(["дружелюбная", "общительная", "веселая"]),
            "background": "Алиса - творческая личность, которая любит путешествовать и знакомиться с новыми людьми.",
            "interests": json.dumps(["музыка", "искусство", "путешествия"]),
            "greeting_message": "Привет! Рада познакомиться с тобой! Как твой день?",
            "created_at": datetime.now()
        }
        
        # Build the SQL statement dynamically based on the character data
        columns = ", ".join(character_data.keys())
        placeholders = ", ".join([f":{key}" for key in character_data.keys()])
        
        # Use raw SQL to avoid SQLAlchemy ORM issues
        insert_query = sa.text(f"INSERT INTO characters ({columns}) VALUES ({placeholders})")
        
        db.execute(insert_query, character_data)
        db.commit()
        logger.info("Test character created successfully")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating test character: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Initializing database...")
    init_db()
    logger.info("Creating test data...")
    create_test_data()
    logger.info("Creating test character...")
    create_test_character()
    logger.info("Fixing schema issues...")
    fix_schema_issues()
