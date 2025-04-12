#!/usr/bin/env python3
"""
Скрипт для синхронизации полей type и memory_type в таблице memory_entries.
Решает проблему рассинхронизации между ИИ-сохранением и админ-панелью.
"""
import os
import sys
import logging
import time
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def wait_for_db(max_retries=30, retry_interval=2):
    """Ожидание доступности базы данных"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL не найден в переменных окружения")
        return False
    
    logger.info(f"Ожидание доступности базы данных: {db_url}")
    engine = create_engine(db_url)
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                logger.info("✅ База данных доступна!")
                return True
        except Exception as e:
            logger.info(f"База данных еще не готова ({attempt+1}/{max_retries}): {str(e)}")
            time.sleep(retry_interval)
    
    logger.error("❌ Таймаут подключения к базе данных")
    return False

def sync_memory_fields():
    """Синхронизация полей type и memory_type в таблице memory_entries"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL не найден в переменных окружения")
        return False
    
    logger.info(f"Синхронизация полей memory_type и type в базе данных: {db_url}")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        with conn.begin():
            try:
                # Проверяем существование таблицы memory_entries
                memory_exists = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memory_entries')"
                )).scalar()
                
                if not memory_exists:
                    logger.info("Таблица memory_entries не существует, будет создана в процессе инициализации")
                    return True
                
                # Получаем список столбцов
                columns = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'memory_entries'"
                )).fetchall()
                
                column_names = [col[0] for col in columns]
                logger.info(f"Найдены столбцы в таблице memory_entries: {', '.join(column_names)}")
                
                # Проверяем наличие обоих столбцов
                has_type = 'type' in column_names
                has_memory_type = 'memory_type' in column_names
                
                if not has_type and not has_memory_type:
                    logger.error("Отсутствуют оба столбца type и memory_type - серьезная проблема со схемой!")
                    return False
                
                # Добавляем отсутствующие столбцы
                if not has_type:
                    logger.info("Добавление отсутствующего столбца type")
                    conn.execute(text("ALTER TABLE memory_entries ADD COLUMN type VARCHAR(50) DEFAULT 'unknown'"))
                    logger.info("✅ Столбец type добавлен")
                    has_type = True
                
                if not has_memory_type:
                    logger.info("Добавление отсутствующего столбца memory_type")
                    conn.execute(text("ALTER TABLE memory_entries ADD COLUMN memory_type VARCHAR(50) DEFAULT 'unknown'"))
                    logger.info("✅ Столбец memory_type добавлен")
                    has_memory_type = True
                
                # Проверяем наличие category
                has_category = 'category' in column_names
                if not has_category:
                    logger.info("Добавление отсутствующего столбца category")
                    conn.execute(text("ALTER TABLE memory_entries ADD COLUMN category VARCHAR(50) DEFAULT 'general'"))
                    logger.info("✅ Столбец category добавлен")
                
                # Синхронизируем данные между столбцами
                if has_type and has_memory_type:
                    logger.info("Синхронизация данных между столбцами type и memory_type")
                    
                    # Обновляем memory_type из type, где memory_type отсутствует
                    result = conn.execute(text("""
                        UPDATE memory_entries 
                        SET memory_type = type 
                        WHERE memory_type IS NULL AND type IS NOT NULL
                    """))
                    if result.rowcount > 0:
                        logger.info(f"✅ Обновлено {result.rowcount} записей из type в memory_type")
                    
                    # Обновляем type из memory_type, где type отсутствует
                    result = conn.execute(text("""
                        UPDATE memory_entries 
                        SET type = memory_type 
                        WHERE type IS NULL AND memory_type IS NOT NULL
                    """))
                    if result.rowcount > 0:
                        logger.info(f"✅ Обновлено {result.rowcount} записей из memory_type в type")
                    
                    # Устанавливаем значения по умолчанию, если оба поля NULL
                    result = conn.execute(text("""
                        UPDATE memory_entries 
                        SET type = 'unknown', memory_type = 'unknown' 
                        WHERE type IS NULL AND memory_type IS NULL
                    """))
                    if result.rowcount > 0:
                        logger.info(f"✅ Установлены значения по умолчанию для {result.rowcount} записей")
                
                # Заполняем пустые значения category
                result = conn.execute(text("""
                    UPDATE memory_entries 
                    SET category = 'general' 
                    WHERE category IS NULL OR category = ''
                """))
                if result.rowcount > 0:
                    logger.info(f"✅ Обновлено {result.rowcount} записей с NULL в category")
                
                # Создаем или обновляем триггеры для синхронизации
                logger.info("Создание триггеров для автоматической синхронизации")
                
                # Функция синхронизации memory_type -> type
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION sync_memory_type_to_type()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.type = NEW.memory_type;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # Функция синхронизации type -> memory_type
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION sync_type_to_memory_type()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.memory_type = NEW.type;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
                
                # Удаляем существующие триггеры, чтобы избежать конфликтов
                conn.execute(text("DROP TRIGGER IF EXISTS sync_memory_type_trigger ON memory_entries"))
                conn.execute(text("DROP TRIGGER IF EXISTS sync_type_trigger ON memory_entries"))
                
                # Создаем новые триггеры
                conn.execute(text("""
                    CREATE TRIGGER sync_memory_type_trigger
                    BEFORE INSERT OR UPDATE OF memory_type ON memory_entries
                    FOR EACH ROW
                    WHEN (NEW.memory_type IS DISTINCT FROM NEW.type)
                    EXECUTE FUNCTION sync_memory_type_to_type();
                """))
                
                conn.execute(text("""
                    CREATE TRIGGER sync_type_trigger
                    BEFORE INSERT OR UPDATE OF type ON memory_entries
                    FOR EACH ROW
                    WHEN (NEW.type IS DISTINCT FROM NEW.memory_type)
                    EXECUTE FUNCTION sync_type_to_memory_type();
                """))
                
                logger.info("✅ Триггеры синхронизации созданы")
                
                # Создаем представление для согласованного доступа
                logger.info("Создание представления для согласованного доступа")
                conn.execute(text("""
                    CREATE OR REPLACE VIEW memory_entries_view AS
                    SELECT 
                        id, 
                        character_id, 
                        user_id, 
                        COALESCE(memory_type, type, 'unknown') as memory_type,
                        COALESCE(type, memory_type, 'unknown') as type,
                        COALESCE(category, 'general') as category,
                        content, 
                        importance, 
                        is_active, 
                        created_at, 
                        updated_at 
                    FROM memory_entries;
                """))
                logger.info("✅ Представление memory_entries_view создано")
                
                # Создаем индексы для повышения производительности
                logger.info("Создание индексов для повышения производительности")
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type ON memory_entries(memory_type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_category ON memory_entries(category)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_character_user ON memory_entries(character_id, user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id_text ON memory_entries((character_id::text))"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id_text ON memory_entries((user_id::text))"))
                logger.info("✅ Индексы созданы")
                
                # Проверяем результаты синхронизации
                type_count = conn.execute(text("SELECT COUNT(*) FROM memory_entries WHERE type IS NOT NULL")).scalar()
                memory_type_count = conn.execute(text("SELECT COUNT(*) FROM memory_entries WHERE memory_type IS NOT NULL")).scalar()
                category_count = conn.execute(text("SELECT COUNT(*) FROM memory_entries WHERE category IS NOT NULL")).scalar()
                total_count = conn.execute(text("SELECT COUNT(*) FROM memory_entries")).scalar()
                
                logger.info(f"Итоги синхронизации:")
                logger.info(f"  - Всего записей: {total_count}")
                logger.info(f"  - Записей с type: {type_count}")
                logger.info(f"  - Записей с memory_type: {memory_type_count}")
                logger.info(f"  - Записей с category: {category_count}")
                
                return True
            except Exception as e:
                logger.error(f"Ошибка при синхронизации полей: {e}")
                return False

def main():
    """Основная функция скрипта"""
    load_dotenv()
    
    if not wait_for_db():
        logger.error("База данных недоступна, продолжение невозможно")
        return False
    
    if not sync_memory_fields():
        logger.error("Ошибка при синхронизации полей memory_type и type")
        return False
    
    logger.info("✅ Синхронизация полей memory_type и type завершена успешно")
    return True

if __name__ == "__main__":
    main()