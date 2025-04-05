"""
Test script to verify memory extraction from messages.
This is useful for debugging memory issues.

Usage:
    python -m tools.test_memory_extraction
"""

import sys
import os
import logging
import json
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

def test_memory_extraction():
    """Test extracting memories from sample messages"""
    try:
        # Import memory manager
        from core.ai.memory_manager import MemoryManager
        memory_manager = MemoryManager()
        
        test_messages = [
            "Привет, меня зовут Балтабек",
            "Меня зовут Алексей, мне 28 лет",
            "Я работаю программистом в крупной компании",
            "Мое хобби - горные лыжи и путешествия",
            "Я живу в Москве",
            "Завтра у нас свидание в 7 вечера",
            "Мне нравятся умные и независимые девушки",
            "Я Балтабек",
            "Моя работа связана с IT",
            "А меня кстати Михаил зовут"
        ]
        
        # Test each message
        results = {}
        for msg in test_messages:
            memories = memory_manager.extract_memories_from_message(msg)
            results[msg] = memories
            
            if memories:
                logger.info(f"Message: '{msg}'")
                logger.info(f"Extracted {len(memories)} memories:")
                for mem in memories:
                    logger.info(f"  - {mem['category']}: {mem['content']}")
            else:
                logger.warning(f"No memories extracted from: '{msg}'")
                
        # Save results to file
        output_file = "memory_extraction_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Results saved to {output_file}")
        
        return 0
    except Exception as e:
        logger.exception(f"Error testing memory extraction: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_memory_extraction())
