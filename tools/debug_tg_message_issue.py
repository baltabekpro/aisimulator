"""
Инструмент для отладки проблем с передачей сообщений от Telegram бота к AI.
Позволяет симулировать обработку сообщения так же, как это делает Telegram бот.

Использование:
    python -m tools.debug_tg_message_issue --character=UUID --message="Тестовое сообщение"
"""

import argparse
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional  # Added List import here
import time
import uuid

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Добавление корневой директории в путь
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def load_character(character_id: str) -> Optional[Dict[str, Any]]:
    """Загрузка информации о персонаже из базы данных"""
    try:
        from sqlalchemy.orm import Session
        from core.db.session import SessionLocal
        from core.models import AIPartner
        from uuid import UUID
        
        db = SessionLocal()
        try:
            # Конвертация строки ID в UUID
            char_uuid = UUID(character_id) if character_id else None
            if not char_uuid:
                logger.error("Invalid character ID")
                return None
                
            # Поиск персонажа в базе данных
            character = db.query(AIPartner).filter(AIPartner.id == char_uuid).first()
            if not character:
                logger.error(f"Character not found: {character_id}")
                return None
                
            # Преобразование в словарь
            char_dict = {
                "id": str(character.id),
                "name": character.name,
                "age": character.age,
                "gender": character.gender,
                "description": character.description,
                "personality": character.personality,
                "appearance": character.appearance,
                "voice_id": character.voice_id,
                "user_id": str(character.user_id) if character.user_id else None,
                "updated_at": str(character.updated_at) if character.updated_at else None,
                "created_at": str(character.created_at) if character.created_at else None,
                # Добавьте другие поля при необходимости
            }
            
            logger.info(f"Successfully loaded character: {char_dict['name']} (ID: {char_dict['id']})")
            return char_dict
            
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error loading character: {e}")
        return None

def load_chat_history(character_id: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
    """Загрузка истории сообщений из базы данных"""
    try:
        from sqlalchemy.orm import Session
        from core.db.session import SessionLocal
        from core.models import Message
        from uuid import UUID
        
        db = SessionLocal()
        try:
            # Конвертация строки ID в UUID
            char_uuid = UUID(character_id) if character_id else None
            if not char_uuid:
                logger.error("Invalid character ID")
                return None
                
            # Поиск сообщений в базе данных
            messages = db.query(Message).filter(
                (Message.sender_id == char_uuid) | (Message.recipient_id == char_uuid)
            ).order_by(Message.created_at.desc()).limit(limit).all()
            
            # Преобразование в список словарей
            history = []
            for msg in messages:
                history.append({
                    "id": str(msg.id),
                    "sender_id": str(msg.sender_id),
                    "recipient_id": str(msg.recipient_id),
                    "content": msg.content,
                    "created_at": str(msg.created_at),
                    "is_from_character": msg.sender_id == char_uuid
                })
            
            # Развернуть историю в хронологическом порядке
            history.reverse()
            
            logger.info(f"Loaded {len(history)} messages for character {character_id}")
            return history
            
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error loading chat history: {e}")
        return None

def simulate_ai_request(character_id: str, message: str, include_history: bool = True) -> Dict[str, Any]:
    """Симулирует запрос к AI так же, как это делает Telegram бот"""
    # Загрузка персонажа
    character = load_character(character_id)
    if not character:
        return {"error": "Character not found"}
    
    # Загрузка истории сообщений
    history = []
    if include_history:
        history = load_chat_history(character_id) or []
    
    # Подготовка контекста
    context = {
        "character": character,
        "history": history,
        "user_message": message,
        "request_id": str(uuid.uuid4())
    }
    
    # Логирование подготовленного контекста
    logger.info(f"Context prepared for AI request:")
    logger.info(f"Character: {character['name']} (ID: {character['id']})")
    logger.info(f"History length: {len(history)}")
    logger.info(f"User message: '{message}'")
    
    try:
        # Импорт и инициализация AI
        from core.ai.gemini import GeminiAI
        ai = GeminiAI()
        
        # Измерение времени выполнения
        start_time = time.time()
        
        # Генерация ответа
        response = ai.generate_response(context, message)
        
        # Завершение измерения времени
        elapsed_time = time.time() - start_time
        logger.info(f"AI response generated in {elapsed_time:.2f} seconds")
        
        # Добавление данных о запросе в ответ для отладки
        debug_info = {
            "request_context": {
                "character_id": character_id,
                "message": message,
                "include_history": include_history,
                "history_length": len(history)
            },
            "timing": {
                "response_time_seconds": elapsed_time
            }
        }
        
        return {
            "response": response,
            "debug_info": debug_info
        }
        
    except Exception as e:
        logger.exception(f"Error generating AI response: {e}")
        return {"error": str(e)}

def main():
    """Основная функция для запуска отладки"""
    parser = argparse.ArgumentParser(description="Debug Telegram message processing")
    parser.add_argument("--character", required=True, help="Character UUID")
    parser.add_argument("--message", required=True, help="Test message to send")
    parser.add_argument("--no-history", action="store_true", help="Don't include chat history")
    args = parser.parse_args()
    
    logger.info(f"Starting debug session")
    logger.info(f"Character ID: {args.character}")
    logger.info(f"Test message: '{args.message}'")
    logger.info(f"Include history: {not args.no_history}")
    
    # Выполнение симуляции запроса
    result = simulate_ai_request(args.character, args.message, not args.no_history)
    
    # Проверка на ошибки
    if "error" in result:
        logger.error(f"Error during simulation: {result['error']}")
        return 1
    
    # Вывод результатов
    logger.info("\n=== AI RESPONSE ===")
    response = result.get("response", {})
    logger.info(f"Text: {response.get('text', 'No text')}")
    logger.info(f"Emotion: {response.get('emotion', 'No emotion')}")
    logger.info(f"Relationship changes: {json.dumps(response.get('relationship_changes', {}), ensure_ascii=False)}")
    
    # Проверка наличия памяти
    if "memory" in response:
        logger.info("\n=== MEMORY EXTRACTED ===")
        for i, mem in enumerate(response.get("memory", []), 1):
            logger.info(f"Memory {i}: {json.dumps(mem, ensure_ascii=False)}")
    else:
        logger.info("\n=== NO MEMORY EXTRACTED ===")
    
    # Сохранение полных результатов в файл
    output_file = Path(f"debug_request_{args.character}_{int(time.time())}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nSaved complete debug results to {output_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
