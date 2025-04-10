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
        existing_partners = db.query(AIPartner).count()
        
        if existing_users > 0 and existing_partners > 0:
            logger.info("Test data already exists, skipping creation")
            return
        
        logger.info("Creating test data...")
        
        # Create test admin user
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
        
        # Create test regular user
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
        
        # Create test AI partners
        test_partners = [
            {
                "partner_id": uuid.uuid4(),
                "name": "Алиса",
                "age": 24,
                "gender": "female",
                "personality_traits": json.dumps(["дружелюбная", "общительная", "веселая"]),
                "interests": json.dumps(["музыка", "искусство", "путешествия"]),
                "background": "Алиса - творческая личность, которая любит путешествовать и знакомиться с новыми людьми.",
                "current_emotion": "happy"
            },
            {
                "partner_id": uuid.uuid4(),
                "name": "Мария",
                "age": 26,
                "gender": "female",
                "personality_traits": json.dumps(["умная", "спокойная", "загадочная"]),
                "interests": json.dumps(["чтение", "психология", "йога"]),
                "background": "Мария - глубокая и философски настроенная натура, интересующаяся духовным развитием.",
                "current_emotion": "neutral"
            },
            {
                "partner_id": uuid.uuid4(),
                "name": "София",
                "age": 22,
                "gender": "female",
                "personality_traits": json.dumps(["энергичная", "амбициозная", "уверенная"]),
                "interests": json.dumps(["спорт", "бизнес", "технологии"]),
                "background": "София - целеустремленная девушка, увлеченная саморазвитием и новыми технологиями.",
                "current_emotion": "excited"
            }
        ]
        
        for partner_data in test_partners:
            test_partner = AIPartner(**partner_data)
            db.add(test_partner)
        
        db.commit()
        logger.info("Test data created successfully")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating test data: {e}")
        raise
    finally:
        db.close()

def fix_schema_issues():
    """
    Fix common schema issues by checking columns and adding missing ones
    This is a simple alternative to full migrations for development
    """
    from sqlalchemy import inspect, Column, String, Integer, DateTime, Text, Boolean, UUID
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
                        # Check if PostgreSQL supports gen_random_uuid() function
                        try:
                            conn.execute(sa.text("SELECT gen_random_uuid()"))
                            uuid_func = "gen_random_uuid()"
                        except Exception:
                            # Fallback to other UUID generation methods depending on database
                            if 'postgres' in str(engine.url).lower():
                                uuid_func = "uuid_generate_v4()"
                            else:
                                uuid_func = "uuid()"
                                
                        conn.execute(sa.text(f"ALTER TABLE messages ADD COLUMN id UUID DEFAULT {uuid_func}"))
                except Exception as e:
                    logger.warning(f"Could not add id column: {e}")
                    
            # Handle column rename with better error checking
            if 'message_id' in msg_existing_cols and 'id' not in msg_existing_cols:
                logger.info("Renaming message_id column to id in messages table (non-SQLite)")
                try:
                    with engine.begin() as conn:
                        conn.execute(sa.text("ALTER TABLE messages RENAME COLUMN message_id TO id"))
                except Exception as e:
                    logger.warning(f"Could not rename message_id column: {e}")

    logger.info("Schema fix completed successfully")

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
