"""
Инструмент для анализа запросов к API OpenRouter.
Помогает выявить проблемы, когда сообщения пользователей не передаются в запросах.

Использование:
    python -m tools.analyze_api_requests [--directory=logs/requests]
"""

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def analyze_request_file(file_path: Path) -> Dict[str, Any]:
    """Анализ одного файла с запросом API"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = data.get("messages", [])
        
        # Подсчет ролей в сообщениях
        role_counts = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            if role not in role_counts:
                role_counts[role] = 0
            role_counts[role] += 1
        
        # Проверка наличия сообщений пользователя
        has_user_messages = any(msg.get("role") == "user" for msg in messages)
        
        # Поиск последнего сообщения пользователя
        last_user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        # Анализ системных сообщений
        system_messages = [msg.get("content", "") for msg in messages if msg.get("role") == "system"]
        system_messages_preview = []
        for i, msg in enumerate(system_messages):
            preview = msg[:100] + "..." if len(msg) > 100 else msg
            system_messages_preview.append(f"System message {i+1}: {preview}")
        
        return {
            "file": str(file_path),
            "timestamp": file_path.stem.replace("openrouter_request_", ""),
            "message_count": len(messages),
            "role_counts": role_counts,
            "has_user_messages": has_user_messages,
            "last_user_message": last_user_message,
            "system_messages_count": len(system_messages),
            "system_messages_preview": system_messages_preview
        }
    except Exception as e:
        logger.error(f"Error analyzing file {file_path}: {e}")
        return {
            "file": str(file_path),
            "error": str(e)
        }

def analyze_requests_directory(directory: Path) -> Dict[str, Any]:
    """Анализ всей директории с запросами API"""
    if not directory.exists():
        logger.error(f"Directory {directory} does not exist")
        return {"error": f"Directory {directory} does not exist"}
    
    # Получение всех JSON файлов с запросами
    request_files = list(directory.glob("*.json"))
    request_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    total_files = len(request_files)
    logger.info(f"Found {total_files} request files in {directory}")
    
    # Анализ первых 20 файлов (самых новых)
    analysis_results = []
    files_to_analyze = request_files[:20]
    
    for file_path in files_to_analyze:
        result = analyze_request_file(file_path)
        analysis_results.append(result)
    
    # Подсчет проблемных запросов (без сообщений пользователя)
    problematic_requests = [r for r in analysis_results if not r.get("has_user_messages", True)]
    
    return {
        "total_files": total_files,
        "analyzed_files": len(files_to_analyze),
        "problematic_requests_count": len(problematic_requests),
        "problematic_requests": problematic_requests,
        "recent_requests": analysis_results
    }

def main():
    """Основная функция для запуска анализа"""
    parser = argparse.ArgumentParser(description="Analyze OpenRouter API requests")
    parser.add_argument("--directory", type=str, default="logs/requests", help="Directory with request log files")
    args = parser.parse_args()
    
    logger.info(f"Analyzing API requests in directory: {args.directory}")
    
    results = analyze_requests_directory(Path(args.directory))
    
    if "error" in results:
        logger.error(results["error"])
        return 1
    
    # Вывод общей статистики
    logger.info(f"Total request files: {results['total_files']}")
    logger.info(f"Analyzed files: {results['analyzed_files']}")
    logger.info(f"Problematic requests (no user messages): {results['problematic_requests_count']}")
    
    # Вывод информации о проблемных запросах
    if results['problematic_requests']:
        logger.info("\nDetails of problematic requests:")
        for req in results['problematic_requests']:
            logger.info(f"\nFile: {req['file']}")
            logger.info(f"Timestamp: {req['timestamp']}")
            logger.info(f"Message count: {req['message_count']}")
            logger.info(f"Role counts: {req['role_counts']}")
            
            # Показать первые несколько системных сообщений
            for i, preview in enumerate(req.get('system_messages_preview', [])[:3]):
                logger.info(preview)
            
            if len(req.get('system_messages_preview', [])) > 3:
                logger.info(f"... and {len(req.get('system_messages_preview', [])) - 3} more system messages")
    
    # Сохранение отчета в файл
    output_file = Path("api_requests_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nSaved analysis report to {output_file}")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
