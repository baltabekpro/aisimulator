"""
Test script to verify memory database operations.
This can be used to diagnose issues with saving or loading memories from the database.

Usage:
    python -m tools.test_memory_database --character=UUID
"""

import sys
import os
import logging
import json
import argparse
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

def test_memory_db_operations(character_id: Optional[str] = None):
    """Test memory database operations with real database instance"""
    try:
        # Import required modules
        from core.ai.memory_manager import MemoryManager
        from app.db.session import SessionLocal
        
        # Create a memory manager instance
        memory_manager = MemoryManager()
        
        # Use supplied character ID or generate a random one
        if not character_id:
            character_id = str(uuid.uuid4())
            logger.info(f"No character ID provided, using generated ID: {character_id}")
        
        # Create test memories
        test_memories = [
            {
                "type": "personal_info",
                "category": "name",
                "content": "Имя пользователя: Тестер",
                "importance": 9
            },
            {
                "type": "personal_info",
                "category": "job",
                "content": "Профессия пользователя: Инженер",
                "importance": 7
            },
            {
                "type": "date",
                "category": "meeting",
                "content": "Встреча запланирована на завтра в 15:00",
                "importance": 8
            }
        ]
        
        # Get a database session
        db = SessionLocal()
        
        try:
            # Step 1: Clear any existing memories for this character
            logger.info(f"Testing memory operations for character: {character_id}")
            memory_manager.clear_memories(character_id)
            
            # Step 2: Add test memories
            for memory in test_memories:
                memory_manager.add_memory(character_id, memory)
            
            # Step 3: Save to database
            logger.info("Saving memories to database...")
            saved = memory_manager.save_to_database(db, character_id)
            
            if saved:
                logger.info("✅ Successfully saved memories to database")
            else:
                logger.error("❌ Failed to save memories to database")
                
            # Step 4: Clear the in-memory collection
            memory_manager.clear_memories(character_id)
            logger.info("Cleared in-memory memories")
            
            # Step 5: Load from database
            logger.info("Loading memories from database...")
            loaded = memory_manager.load_from_database(db, character_id)
            
            if loaded:
                logger.info("✅ Successfully loaded memories from database")
                
                # Step 6: Verify the loaded memories
                loaded_memories = memory_manager.get_all_memories(character_id)
                logger.info(f"Loaded {len(loaded_memories)} memories")
                
                # Verify each memory was loaded correctly
                for i, memory in enumerate(loaded_memories):
                    logger.info(f"Memory {i+1}: {json.dumps(memory, ensure_ascii=False)}")
            else:
                logger.error("❌ Failed to load memories from database")
                
            # Log the formatted memories
            formatted = memory_manager.format_memories_for_prompt(character_id)
            logger.info(f"Formatted memories for prompt:\n{formatted}")
                
        finally:
            db.close()
            
        return 0
            
    except Exception as e:
        logger.exception(f"Error testing memory database operations: {e}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test memory database operations")
    parser.add_argument("--character", type=str, help="Character UUID to use for testing")
    args = parser.parse_args()
    
    sys.exit(test_memory_db_operations(args.character))
