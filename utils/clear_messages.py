"""
Утилита для очистки истории сообщений в базе данных.
Может очистить все сообщения или только для определенного персонажа.

Использование:
    python -m utils.clear_messages --all         # Очистить все сообщения
    python -m utils.clear_messages --character=UUID   # Очистить сообщения для конкретного персонажа
"""

import argparse
import logging
import sys
import os
from typing import Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    """Основная функция для запуска из командной строки"""
    # Add the project root to the Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    parser = argparse.ArgumentParser(description="Утилита очистки истории сообщений")
    parser.add_argument("--all", action="store_true", help="Очистить все сообщения")
    parser.add_argument("--character", type=str, help="UUID персонажа для очистки его сообщений")
    
    args = parser.parse_args()
    
    if not args.all and not args.character:
        logger.error("Укажите --all для очистки всех сообщений или --character=UUID для очистки сообщений конкретного персонажа")
        return 1
    
    # Import the utility function
    try:
        from utils.clear_messages_utils import clear_messages
    except ImportError as e:
        logger.error(f"Error importing utils.clear_messages_utils: {e}")
        logger.error("Make sure the utility module exists and is in your Python path")
        return 1
    
    deleted = clear_messages(character_id=args.character, clear_all=args.all)
    
    if deleted > 0:
        logger.info(f"Успешно удалено {deleted} сообщений")
        return 0
    else:
        logger.warning("Сообщения не были удалены")
        return 1

if __name__ == "__main__":
    # Print current environment for debugging
    logger.info(f"Запуск скрипта очистки сообщений")
    logger.info(f"Текущая директория: {os.getcwd()}")
    logger.info(f"Путь к скрипту: {__file__}")
    logger.info(f"Python path: {sys.path}")
    
    sys.exit(main())
