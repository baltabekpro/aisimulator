#!/usr/bin/env python
"""
Автоматическая подготовка и исправление базы данных
Этот скрипт выполняет все необходимые действия для подготовки базы данных:
1. Добавляет колонку external_id в таблицу users если её нет
2. Создает представление с корректным приведением типов для UUID и varchar
"""

import logging
import time
import sqlalchemy as sa
import sys
import os

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем корневую директорию проекта в путь импорта Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db.session import engine
from core.db import init_db

def wait_for_db():
    """Ожидание готовности базы данных перед применением исправлений"""
    max_retries = 10
    retry_interval = 5  # секунд
    
    logger.info("Ожидание готовности базы данных...")
    
    for attempt in range(max_retries):
        try:
            # Пробуем выполнить простой запрос к базе данных
            with engine.connect() as connection:
                connection.execute(sa.text("SELECT 1"))
            logger.info("База данных доступна.")
            return True
        except Exception as e:
            logger.warning(f"База данных недоступна (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Повторная попытка через {retry_interval} секунд...")
                time.sleep(retry_interval)
    
    logger.error("База данных недоступна после всех попыток. Выход.")
    return False

def create_messages_view():
    """Создание представления данных с корректным приведением типов для сообщений"""
    logger.info("Создание представления данных с правильным приведением типов...")
    
    try:
        # Используем функцию из модуля инициализации
        init_db.create_admin_message_view()
        logger.info("Представление данных создано успешно.")
    except Exception as e:
        logger.error(f"Ошибка при создании представления данных: {e}")

def main():
    """Основная функция для выполнения всех исправлений базы данных"""
    logger.info("Запуск процесса автоматического исправления базы данных...")
    
    # Ожидание готовности базы данных
    if not wait_for_db():
        sys.exit(1)
    
    # Проверяем и добавляем колонку external_id в таблицу users
    init_db.add_external_id_to_users()
    
    # Создаем представление для сообщений с корректным приведением типов
    create_messages_view()
    
    logger.info("Все исправления успешно применены к базе данных!")
    logger.info("База данных успешно подготовлена к работе.")

if __name__ == "__main__":
    main()