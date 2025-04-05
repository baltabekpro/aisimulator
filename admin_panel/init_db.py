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

# Add the parent directory to sys.path to make module imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Now import from the module using relative imports
from db.session import engine, Base, get_session
from models import Admin, Character, User, Message, Memory, Event

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_tables():
    """Создание всех таблиц, определенных в моделях"""
    try:
        logger.info("Создание таблиц базы данных PostgreSQL...")
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
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
        session = get_session()
        
        # Create default admin user
        default_username = os.getenv('ADMIN_USERNAME', 'admin')
        default_password = os.getenv('ADMIN_PASSWORD', 'admin_password')
        
        # Check if admin user already exists
        try:
            existing_admin = session.query(Admin).filter_by(username=default_username).first()
            if existing_admin:
                logger.info("Администратор по умолчанию уже существует")
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
        logger.info(f"Создан администратор по умолчанию: {default_username}")
        return True
    except Exception as e:
        logger.error(f"Ошибка создания администратора: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if session:
            session.rollback()
        return False
    finally:
        if session:
            session.close()

def check_database_connection():
    """Проверка подключения к базе данных"""
    try:
        from sqlalchemy import inspect
        
        # Проверяем соединение
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Успешное подключение к PostgreSQL. Найдено таблиц: {len(tables)}")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    print("🔧 Инициализация базы данных административной панели 🔧")
    print("----------------------------------------------------")
    
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
