"""
Скрипт инициализации базы данных для административной панели.

Этот скрипт создает необходимые таблицы для работы административной панели.

Использование:
    python init_db.py
"""
import os
import sys
import uuid
import logging
from werkzeug.security import generate_password_hash
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text, create_engine

# Add the parent directory to sys.path to make module imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Now import from the module using relative imports
try:
    from db.session import engine, Base, get_session
    from admin_panel.models import AdminUser as Admin, UserView as User, CharacterView as Character, MessageView as Message
except ImportError:
    print("Failed to import from existing modules, using direct SQL instead.")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_tables():
    """Создание всех таблиц, определенных в моделях"""
    try:
        logger.info("Создание таблиц базы данных PostgreSQL...")
        
        # Create tables if they don't exist
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Таблицы успешно созданы через SQLAlchemy")
        except Exception as orm_error:
            logger.error(f"Ошибка создания таблиц через ORM: {orm_error}")
            logger.info("Пробуем создать таблицы напрямую через SQL...")
            
            # Fallback to direct SQL
            try:
                # Get database URL from environment
                db_url = os.environ.get("DATABASE_URL")
                if not db_url:
                    db_url = "postgresql://aibot:postgres@postgres:5432/aibot"
                
                # Connect directly
                direct_engine = create_engine(db_url)
                with direct_engine.connect() as conn:
                    # Create admin_users table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS admin_users (
                            id VARCHAR(36) PRIMARY KEY,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            email VARCHAR(100),
                            password_hash VARCHAR(200) NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.commit()
                    logger.info("Таблица admin_users создана через SQL")
            except Exception as sql_error:
                logger.error(f"Ошибка создания таблиц через SQL: {sql_error}")
                raise
        
        logger.info("Таблицы успешно созданы")
        return True
    except Exception as e:
        logger.error(f"Ошибка создания таблиц: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_admin_user():
    """Создание администратора по умолчанию, если его не существует"""
    try:
        # Get database URL from environment
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            db_url = "postgresql://aibot:postgres@postgres:5432/aibot"
        
        # Try different approaches
        try:
            # Using ORM
            session = get_session()
            
            # Create default admin user
            default_username = os.getenv('ADMIN_USERNAME', 'admin')
            default_password = os.getenv('ADMIN_PASSWORD', 'admin_password')
            
            # Check if admin user already exists
            try:
                existing_admin = session.query(Admin).filter_by(username=default_username).first()
                if existing_admin:
                    logger.info("Администратор по умолчанию уже существует (ORM)")
                    return True
            except:
                # Table might not exist yet or other error, continue with creation
                pass
            
            admin = Admin(
                id=str(uuid.uuid4()),
                username=default_username,
                password_hash=generate_password_hash(default_password),
                email="admin@example.com",
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            session.add(admin)
            session.commit()
            logger.info(f"Создан администратор по умолчанию: {default_username} (ORM)")
            return True
        except Exception as orm_error:
            logger.error(f"Ошибка создания администратора через ORM: {orm_error}")
            
            # Fallback to direct SQL
            try:
                logger.info("Пробуем создать администратора напрямую через SQL...")
                direct_engine = create_engine(db_url)
                
                default_username = os.getenv('ADMIN_USERNAME', 'admin')
                default_password = os.getenv('ADMIN_PASSWORD', 'admin_password')
                
                with direct_engine.connect() as conn:
                    # Check if user exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM admin_users WHERE username = :username"
                    ), {"username": default_username})
                    
                    count = result.scalar()
                    if count > 0:
                        logger.info("Администратор по умолчанию уже существует (SQL)")
                        return True
                    
                    # Create admin user
                    admin_id = str(uuid.uuid4())
                    password_hash = generate_password_hash(default_password)
                    
                    conn.execute(text("""
                        INSERT INTO admin_users (id, username, email, password_hash, is_active)
                        VALUES (:id, :username, :email, :password_hash, TRUE)
                    """), {
                        "id": admin_id,
                        "username": default_username,
                        "email": f"{default_username}@example.com",
                        "password_hash": password_hash
                    })
                    conn.commit()
                    logger.info(f"Создан администратор по умолчанию: {default_username} (SQL)")
                return True
            except Exception as sql_error:
                logger.error(f"Ошибка создания администратора через SQL: {sql_error}")
                raise
    except Exception as e:
        logger.error(f"Ошибка создания администратора: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_database_connection():
    """Проверка подключения к базе данных"""
    try:
        # Get database URL from environment
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            db_url = "postgresql://aibot:postgres@postgres:5432/aibot"
        
        direct_engine = create_engine(db_url)
        
        with direct_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
            logger.info("Успешное подключение к PostgreSQL")
            
            # Check for admin_users table
            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_users')"
            ))
            if result.scalar():
                logger.info("Таблица admin_users существует")
            else:
                logger.warning("Таблица admin_users не существует")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    print("🔧 Инициализация базы данных административной панели 🔧")
    print("----------------------------------------------------")
    
    # Load environment variables
    load_dotenv()
    
    # Проверка подключения к базе данных
    print("Проверка подключения к базе данных PostgreSQL...")
    if not check_database_connection():
        print("❌ Не удалось подключиться к базе данных PostgreSQL.")
        print("Убедитесь, что PostgreSQL запущен и настройки подключения верны.")
        return 1
    
    # Create tables
    if create_tables():
        print("✅ Таблицы базы данных успешно созданы")
    else:
        print("❌ Не удалось создать таблицы базы данных")
        return 1
    
    # Create admin user
    if create_admin_user():
        print("✅ Администратор создан/проверен")
    else:
        print("❌ Не удалось создать администратора")
    
    print("\nИнициализация базы данных завершена. Теперь вы можете запустить административную панель:")
    print("python app.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
