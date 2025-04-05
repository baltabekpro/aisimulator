"""
Инструмент для исправления проблем с потерей контекста в разговорах.
Восстанавливает связь между сообщениями и ассоциированными с ними воспоминаниями.

Использование:
    python -m tools.fix_conversation_context --character=UUID
"""

import argparse
import logging
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import datetime
import uuid

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Добавляем корневую директорию в путь Python
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

def initialize_ai():
    """Инициализация AI-модели для работы с памятью и разговорами"""
    try:
        from core.ai.gemini import GeminiAI
        ai = GeminiAI()
        return ai
    except Exception as e:
        logger.exception(f"Ошибка инициализации AI: {e}")
        return None

def get_database_session():
    """Получение сессии базы данных"""
    try:
        from app.db.session import SessionLocal
        return SessionLocal()
    except Exception as e:
        logger.exception(f"Ошибка подключения к базе данных: {e}")
        return None

def fix_conversation_context(character_id: str):
    """
    Исправить проблемы с контекстом разговора для указанного персонажа.
    
    Args:
        character_id: UUID персонажа
    """
    logger.info(f"Запуск исправления контекста для персонажа {character_id}")
    
    # Инициализация AI
    ai = initialize_ai()
    if not ai:
        logger.error("Не удалось инициализировать AI")
        return False
    
    # Получение сессии базы данных
    db = get_database_session()
    if not db:
        logger.error("Не удалось подключиться к базе данных")
        return False
    
    try:
        # 1. Загрузка сообщений из базы данных
        logger.info("Загрузка сообщений из базы данных...")
        from core.models import Message
        from uuid import UUID
        
        try:
            char_uuid = UUID(character_id)
        except ValueError:
            logger.error(f"Неверный формат UUID: {character_id}")
            return False
        
        # Получаем все сообщения для персонажа
        messages = db.query(Message).filter(
            (Message.sender_id == char_uuid) | (Message.recipient_id == char_uuid)
        ).order_by(Message.created_at).all()
        
        logger.info(f"Загружено {len(messages)} сообщений")
        
        if not messages:
            logger.info("Нет сообщений для исправления")
            return True
        
        # 2. Преобразование сообщений в формат для AI
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "id": str(msg.id),
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "sender_type": "ai" if msg.sender_id == char_uuid else "user"
            }
            formatted_messages.append(formatted_msg)
        
        # 3. Обновление контекста разговора в AI
        logger.info("Обновление контекста разговора в AI...")
        
        # Сначала очищаем существующий контекст
        ai.conversation_manager.clear_conversation(character_id)
        
        # Затем импортируем историю сообщений
        from core.models import AIPartner
        character = db.query(AIPartner).filter(AIPartner.id == char_uuid).first()
        
        if not character:
            logger.error(f"Персонаж не найден: {character_id}")
            return False
        
        # Преобразуем персонажа в словарь для AI
        character_dict = {
            "id": str(character.id),
            "name": character.name,
            "age": character.age,
            "gender": character.gender,
            "personality_traits": character.personality_traits,
            "interests": character.interests,
            "background": character.background,
            "current_emotion": character.current_emotion
        }
        
        # Импортируем историю сообщений в AI
        ai.conversation_manager.import_history(
            character_id=character_id,
            message_history=formatted_messages,
            character_info=character_dict
        )
        
        # 4. Сохраняем обновленный контекст в базу данных
        logger.info("Сохранение обновленного контекста в базу данных...")
        ai.conversation_manager.save_conversation_to_database(character_id, db)
        
        # 5. Пересканируем сообщения для извлечения воспоминаний
        logger.info("Извлечение воспоминаний из сообщений...")
        
        # Очищаем существующие воспоминания
        ai.memory_manager.clear_memories(character_id)
        
        # Извлекаем воспоминания из сообщений пользователя
        user_messages = [msg for msg in formatted_messages if msg["sender_type"] == "user"]
        extracted_count = 0
        
        for msg in user_messages:
            memories = ai.memory_manager.extract_memories_from_message(msg["content"])
            if memories:
                for memory in memories:
                    ai.memory_manager.add_memory(character_id, memory)
                    extracted_count += 1
        
        logger.info(f"Извлечено {extracted_count} воспоминаний из {len(user_messages)} сообщений пользователя")
        
        # 6. Сохраняем обновленные воспоминания в базу данных
        if extracted_count > 0:
            logger.info("Сохранение воспоминаний в базу данных...")
            ai.memory_manager.save_to_database(db, character_id)
        
        logger.info("Исправление контекста разговора успешно завершено")
        return True
        
    except Exception as e:
        logger.exception(f"Ошибка при исправлении контекста разговора: {e}")
        return False
    finally:
        db.close()

def main():
    """Функция точки входа"""
    parser = argparse.ArgumentParser(description="Исправление проблем с контекстом разговора")
    parser.add_argument("--character", type=str, required=True, help="UUID персонажа")
    args = parser.parse_args()
    
    success = fix_conversation_context(args.character)
    
    if success:
        logger.info("✅ Исправление контекста успешно завершено")
        return 0
    else:
        logger.error("❌ Произошла ошибка при исправлении контекста")
        return 1

if __name__ == "__main__":
    sys.exit(main())
