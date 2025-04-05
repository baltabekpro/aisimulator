"""
Утилита для анализа сохраненных диалогов и проверки извлечения памяти AI

Использование:
    python -m tools.analyze_conversations

Эта утилита:
1. Сканирует директорию с журналами разговоров
2. Анализирует, где AI должна была выделить память, но этого не сделала
3. Создает отчет для улучшения работы извлечения памяти
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
import sys

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LOGS_DIR = Path("logs/conversations")

def should_extract_memory(message: str) -> Tuple[bool, Set[str]]:
    """
    Проверяет, содержит ли сообщение пользователя информацию, которая должна быть добавлена в память
    
    Args:
        message: Сообщение пользователя
        
    Returns:
        (bool, set): Флаг наличия важной информации и набор найденных категорий
    """
    found_categories = set()
    
    # Шаблоны для разных типов информации
    patterns = {
        'name': [r'меня зовут\s+([А-Я][а-я]+|[A-Z][a-z]+)', 
                r'моё имя\s+([А-Я][а-я]+|[A-Z][a-z]+)'],
        'age': [r'мне (\d{1,2})\s+(?:год|года|лет)',
              r'мой возраст\s+(\d{1,2})'],
        'job': [r'я работаю\s+(\w+)', 
               r'моя работа\s+(\w+)',
               r'моя профессия\s+(\w+)'],
        'location': [r'я живу в\s+(\w+)',
                   r'я из\s+(\w+)'],
        'hobby': [r'моё хобби\s+(\w+)',
                r'я увлекаюсь\s+(\w+)',
                r'я люблю\s+(\w+)'],
        'meeting': [r'(?:завтра|сегодня|скоро)\s+(?:у нас|встретимся|будем|пойдем)',
                  r'(?:свидание|встреча|увидимся)'],
    }
    
    # Проверяем наличие каждой категории информации
    for category, category_patterns in patterns.items():
        for pattern in category_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                found_categories.add(category)
                break
    
    # Если нашли хотя бы одну категорию, должны сохранить в память
    return len(found_categories) > 0, found_categories

def analyze_conversation_logs() -> Dict[str, Any]:
    """
    Анализирует все журналы разговоров и находит случаи, 
    когда AI должна была сохранить память, но не сделала этого
    
    Returns:
        Словарь со статистикой и найденными проблемами
    """
    if not LOGS_DIR.exists():
        logger.error(f"Директория с журналами не найдена: {LOGS_DIR}")
        return {"error": "Logs directory not found"}
    
    # Обходим все файлы во всех директориях персонажей
    total_conversations = 0
    memory_opportunities = 0
    memory_extracted = 0
    missed_memory = []
    
    for char_dir in LOGS_DIR.iterdir():
        if not char_dir.is_dir():
            continue
            
        character_id = char_dir.name
        
        for log_file in char_dir.glob("*.json"):
            total_conversations += 1
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                
                # Получаем сообщение пользователя
                user_message = log_data.get("user_message", "")
                if not user_message:
                    continue
                
                # Проверяем, содержит ли сообщение информацию для памяти
                should_memorize, categories = should_extract_memory(user_message)
                
                if should_memorize:
                    memory_opportunities += 1
                    
                    # Проверяем, была ли память извлечена
                    ai_response = log_data.get("ai_response", {}).get("processed", {})
                    memory_data = ai_response.get("memory", []) if isinstance(ai_response, dict) else []
                    
                    if memory_data:
                        memory_extracted += 1
                    else:
                        # Сохраняем для анализа
                        missed_memory.append({
                            "file": str(log_file),
                            "user_message": user_message,
                            "ai_response": log_data.get("ai_response", {}).get("processed", {}).get("text", ""),
                            "categories": list(categories)
                        })
            except Exception as e:
                logger.error(f"Ошибка при анализе файла {log_file}: {e}")
    
    # Формируем отчет
    report = {
        "total_conversations": total_conversations,
        "memory_opportunities": memory_opportunities,
        "memory_extracted": memory_extracted,
        "missed_memory_count": len(missed_memory),
        "extraction_rate": f"{(memory_extracted / memory_opportunities * 100) if memory_opportunities > 0 else 0:.2f}%",
        "missed_memory_examples": missed_memory[:10]  # Показываем только первые 10 примеров
    }
    
    return report

def main():
    """Основная функция запуска анализа"""
    logger.info("Запуск анализа журналов разговоров...")
    
    report = analyze_conversation_logs()
    
    logger.info("Анализ завершен")
    logger.info(f"Всего проанализировано разговоров: {report.get('total_conversations')}")
    logger.info(f"Обнаружено возможностей для извлечения памяти: {report.get('memory_opportunities')}")
    logger.info(f"Успешно извлечено памяти: {report.get('memory_extracted')}")
    logger.info(f"Пропущено возможностей: {report.get('missed_memory_count')}")
    logger.info(f"Эффективность извлечения: {report.get('extraction_rate')}")
    
    # Сохраняем отчет в файл
    output_file = Path("memory_analysis_report.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Отчет сохранен в файл: {output_file}")
    
    # Показываем примеры пропущенных возможностей
    if report.get('missed_memory_examples'):
        logger.info("Примеры пропущенных возможностей для извлечения памяти:")
        for i, example in enumerate(report.get('missed_memory_examples', []), 1):
            logger.info(f"\n{i}. Категории: {', '.join(example.get('categories', []))}")
            logger.info(f"   Сообщение: {example.get('user_message')}")
            logger.info(f"   Ответ AI: {example.get('ai_response')}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
