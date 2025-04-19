import json
import logging
import datetime
import uuid  # Add this import for UUID generation
from typing import Dict, List, Any, Optional, Set
from uuid import UUID
import re
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import our universal ID handler
from core.utils.universal_id import ensure_uuid, get_user_id_formats

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manages the storage and retrieval of user information and important dates
    that the AI has learned during conversations.
    """
    
    def __init__(self):
        # Dictionary to store user information by character_id and user_id
        self.memories = {}
        # Maximum number of memories to store per user
        self.max_memories = 50
        self.logger = logging.getLogger(__name__)
        
    def add_memory(self, character_id: str, memory_data: Dict[str, Any]) -> bool:
        """
        Store a new memory item related to the user.
        
        Args:
            character_id: Unique identifier for the character
            memory_data: Dictionary with memory information
                {
                    "type": "personal_info"|"date"|"preference"|"fact",
                    "content": "Content of the memory",
                    "category": "Optional category",
                    "importance": 1-10 value,
                    "timestamp": "When this was learned"
                }
                
        Returns:
            Success status
        """
        if not character_id or not memory_data:
            logger.warning("Invalid memory data or character_id")
            return False
            
        if character_id not in self.memories:
            self.memories[character_id] = []
        
        # Add timestamp if not provided
        if "timestamp" not in memory_data:
            memory_data["timestamp"] = datetime.datetime.now().isoformat()
            
        # Add importance if not provided (default to medium importance)
        if "importance" not in memory_data:
            memory_data["importance"] = 5
            
        # Add memory ID for easier reference
        if "id" not in memory_data:
            memory_data["id"] = len(self.memories[character_id]) + 1
            
        # Check for duplicates
        if not self._is_duplicate(character_id, memory_data):
            # Add the memory
            self.memories[character_id].append(memory_data)
            
            # Trim if we exceed max memories by sorting by importance and keeping most important
            if len(self.memories[character_id]) > self.max_memories:
                self.memories[character_id].sort(key=lambda x: x.get("importance", 0), reverse=True)
                self.memories[character_id] = self.memories[character_id][:self.max_memories]
                
            # Enhanced logging with special formatting to make memory additions stand out
            memory_type = memory_data.get("type", "general")
            category = memory_data.get("category", "undefined")
            importance = memory_data.get("importance", 5)
            content = memory_data.get("content", "")
            
            # ANSI color codes for highlighted output
            CYAN = "\033[96m"
            YELLOW = "\033[93m"
            BOLD = "\033[1m"
            RESET = "\033[0m"
            
            # Format based on importance
            if importance >= 8:  # High importance
                logger.info(f"{BOLD}{YELLOW}🧠 CRITICAL MEMORY ADDED [{character_id}]{RESET}")
                logger.info(f"{BOLD}{YELLOW}➡️ Type: {memory_type}, Category: {category}, Importance: {importance}/10{RESET}")
                logger.info(f"{BOLD}{YELLOW}📝 Content: {content}{RESET}")
            else:  # Medium or low importance
                logger.info(f"{CYAN}🧠 MEMORY ADDED [{character_id}]{RESET}")
                logger.info(f"{CYAN}➡️ Type: {memory_type}, Category: {category}, Importance: {importance}/10{RESET}")
                logger.info(f"{CYAN}📝 Content: {content}{RESET}")
                
            return True
        else:
            logger.debug(f"Skipped duplicate memory: {memory_data['content'][:50]}...")
            return False
            
    def get_memories(self, character_id: str, memory_type: Optional[str] = None, 
                    category: Optional[str] = None, max_count: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve memories for a character, optionally filtered by type and category.
        
        Args:
            character_id: Character identifier
            memory_type: Optional filter for memory type
            category: Optional filter for memory category
            max_count: Maximum number of memories to return
            
        Returns:
            List of memory dictionaries
        """
        if character_id not in self.memories:
            return []
            
        results = self.memories[character_id]
        
        # Apply filters
        if memory_type:
            results = [m for m in results if m.get("type") == memory_type]
        if category:
            results = [m for m in results if m.get("category") == category]
            
        # Sort by importance and return limited results
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return results[:max_count]
    
    def get_all_memories(self, character_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a character, sorted by importance.
        
        Args:
            character_id: Character identifier
            
        Returns:
            List of all memories
        """
        if character_id not in self.memories:
            return []
            
        # Sort by importance and return
        memories = self.memories[character_id]
        memories.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return memories
    
    def clear_memories(self, character_id: str) -> bool:
        """
        Clear all memories for a character.
        
        Args:
            character_id: Character identifier
            
        Returns:
            Whether any memories were cleared
        """
        if character_id in self.memories:
            del self.memories[character_id]
            logger.info(f"Cleared all memories for character {character_id}")
            return True
        return False
    
    def extract_memories_from_message(self, text: str, detect_dates: bool = True, 
                                    detect_personal_info: bool = True) -> List[Dict[str, Any]]:
        """
        Extract potential memories from a user message.
        
        Args:
            text: User message text
            detect_dates: Whether to detect important dates
            detect_personal_info: Whether to detect personal information
            
        Returns:
            List of potential memory items
        """
        if not text or not isinstance(text, str):
            return []
            
        memories = []
        
        # Skip special commands and UI button texts
        special_commands = ["🧠 Память", "❤️ Отношения", "📱 Профиль", "💬 Меню", "❓ Помощь", "🎁 Отправить подарок"]
        if text in special_commands:
            logger.info(f"Skipping memory extraction for UI command: {text}")
            return []
        
        # More precise name patterns - only match with common name-related phrases
        name_patterns = [
            # Direct name statements with highest priority
            r'(?:меня\s+зовут|моё\s+имя|мое\s+имя)\s+([А-Я][а-я]{2,}|\b[A-Z][a-z]{2,})',
            
            # Less certain but still valid contextual name patterns
            r'(?:^|\.\s+|\n)(?:я|меня)\s+([А-Я][а-я]{2,})',
            
            # Signature style name
            r'(?:^\с*|,\с*|\.\с+)(?:[Сс]|[Пп]одпись)(?:\с+-)?\с+([А-Я][а-я]{2,})'
        ]
        
        # Check full name patterns first
        found_name = False
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found_name = True
                # Only add the first name match with high importance
                name = matches[0].strip()
                
                # Filter out common words mistakenly matched as names
                common_words = ["привет", "меня", "зовут", "хочу", "тебя", "знаю", "имя", "память", 
                               "как", "все", "лежу", "мое", "нет", "забей", "люблю", "цвет", "завтра"]
                
                if name.lower() in common_words:
                    logger.info(f"Filtered out common word falsely matched as name: {name}")
                    continue
                    
                if len(name) < 3:
                    logger.info(f"Filtered out too short name: {name}")
                    continue
                    
                memory = {
                    "type": "personal_info",
                    "category": "name",
                    "content": f"Имя пользователя: {name}",
                    "importance": 9
                }
                memories.append(memory)
                
                # Log the extracted name
                logger.info(f"📌 Extracted name with confidence: {name}")
                break

        # Detect birthday/special events with high importance
        birthday_patterns = [
            r'(?:у меня|мой|моё)\с+(?:день рождения|др)(?:\с+завтра|\с+скоро|\с+сегодня|\с+послезавтра)',
            r'(?:завтра|сегодня|скоро)\с+(?:у меня|мой|моё)\с+(?:день рождения|др)',
            r'(?:др|день рождения)\с+(?:у меня|мой|моё)\с+(?:завтра|сегодня|скоро|послезавтра)'
        ]
        
        for pattern in birthday_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Extract the date reference (tomorrow, today, etc.)
                date_match = re.search(r'(завтра|сегодня|скоро|послезавтра)', text, re.IGNORECASE)
                date_ref = date_match.group(1) if date_match else "скоро"
                
                memory = {
                    "type": "date",
                    "category": "birthday",
                    "content": f"День рождения пользователя: {date_ref}",
                    "importance": 10  # Highest importance for birthdays
                }
                memories.append(memory)
                logger.info(f"📌 Extracted birthday information: {date_ref}")
                break

        # Detect dates if enabled
        if detect_dates:
            date_memories = self._extract_dates(text)
            memories.extend(date_memories)
            
        # Detect personal information if enabled
        if detect_personal_info:
            personal_memories = self._extract_personal_info(text)
            memories.extend(personal_memories)
        
        # Enhancement: Add special handling for upcoming events/meetings
        event_memories = self._extract_events(text)
        memories.extend(event_memories)
        
        # Deduplicate memories before returning
        if memories:
            # Use a set to track unique content
            unique_contents = set()
            unique_memories = []
            
            for memory in memories:
                memory_content = memory["content"]
                memory_type = memory.get("type", "")
                memory_category = memory.get("category", "")
                
                # Create a unique key for this memory
                memory_key = f"{memory_type}:{memory_category}:{memory_content}"
                
                if memory_key not in unique_contents:
                    unique_contents.add(memory_key)
                    unique_memories.append(memory)
                    
            # ANSI color codes for highlighted output
            GREEN = "\033[92m"
            BOLD = "\033[1m"
            RESET = "\033[0m"
            
            logger.info(f"{BOLD}{GREEN}✨ EXTRACTED {len(unique_memories)} MEMORIES FROM MESSAGE:{RESET}")
            for i, memory in enumerate(unique_memories):
                mem_type = memory.get("type", "general")
                mem_category = memory.get("category", "undefined")
                mem_content = memory.get("content", "")
                mem_importance = memory.get("importance", 5)
                
                logger.info(f"{GREEN} 🔹 Memory #{i+1}: [{mem_type}/{mem_category}] (Importance: {mem_importance}/10){RESET}")
                logger.info(f"{GREEN}    {mem_content}{RESET}")
            
            return unique_memories
        
        return memories

    def _extract_events(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract information about upcoming events or plans.
        
        Args:
            text: Text to extract from
            
        Returns:
            List of event memory items
        """
        memories = []
        
        # Patterns for events and meetings
        event_patterns = [
            # Свидания и встречи
            (r'(?:свидание|встреча|встретимся|увидимся)(?:\с+\w+){0,3}\с+(?:завтра|сегодня|послезавтра|в\s+\w+)', 
             'meeting', "Запланированная встреча: {}", 9),
             
            # События с указанием времени
            (r'(?:пойдем|поедем|сходим|будем)(?:\с+\w+){0,5}\с+(?:завтра|сегодня|послезавтра|в\s+\w+)', 
             'activity', "Запланированное событие: {}", 8),
             
            # Общие планы на будущее
            (r'(?:планирую|собираюсь|буду|намечается)(?:\с+\w+){0,5}\с+(?:завтра|сегодня|послезавтра|на\s+следующей\s+неделе|на\s+выходных)', 
             'plan', "Планы: {}", 7),
        ]
        
        for pattern, category, content_template, importance in event_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):  # Для случаев нескольких групп
                    match = ' '.join(match).strip()
                
                # Берем контекст вокруг события
                match_index = text.lower().find(match.lower())
                if (match_index >= 0):
                    start_index = max(0, match_index - 30)
                    end_index = min(len(text), match_index + len(match) + 30)
                    context = text[start_index:end_index].strip()
                else:
                    context = match
                
                # Форматируем контент с контекстом
                content = content_template.format(context)
                
                memory = {
                    "type": "date",
                    "category": category,
                    "content": content,
                    "importance": importance
                }
                memories.append(memory)
        
        return memories

    def _get_context(self, text: str, match: str) -> str:
        """
        Get surrounding context for a match in text.
        
        Args:
            text: Full text
            match: Matched string
            
        Returns:
            Context around match
        """
        try:
            match_index = text.lower().find(match.lower())
            if (match_index >= 0):
                start_index = max(0, match_index - 20)
                end_index = min(len(text), match_index + len(match) + 40)
                return text[start_index:end_index].strip()
            return match
        except:
            return match  

    def format_memories_for_prompt(self, character_id: str, limit: int = 15) -> str:
        """
        Format memories for inclusion in the AI prompt.
        
        Args:
            character_id: Character identifier
            limit: Maximum number of memories to include
            
        Returns:
            Formatted memories text
        """
        if character_id not in self.memories or not self.memories[character_id]:
            return "Нет сохраненной информации о пользователе."
            
        # Get important memories sorted by importance
        memories = sorted(self.memories[character_id], 
                         key=lambda x: x.get("importance", 0), 
                         reverse=True)[:limit]
        
        # Format the memories
        formatted = "## Важная информация о пользователе:\n"
        
        # Group memories by type
        grouped = {}
        for memory in memories:
            memory_type = memory.get("type", "fact")
            if memory_type not in grouped:
                grouped[memory_type] = []
            grouped[memory_type].append(memory)
        
        # Format each type
        for memory_type, type_memories in grouped.items():
            if memory_type == "personal_info":
                formatted += "\n### Личная информация:\н"
            elif memory_type == "date":
                formatted += "\n### Важные даты:\н"
            elif memory_type == "preference":
                formatted += "\н### Предпочтения:\н"
            else:
                formatted += f"\n### {memory_type.capitalize()}:\н"
                
            for memory in type_memories:
                formatted += f"- {memory['content']}\н"
                
        # Add explicit instruction for the AI to use this information
        formatted += "\nПожалуйста, используй эту информацию в разговоре. Обращайся к пользователю по имени, " + \
                    "если оно указано, и учитывай его предпочтения и интересы."
                    
        return formatted
    
    def _is_duplicate(self, character_id: str, memory_data: Dict[str, Any]) -> bool:
        """
        Check if a memory is a duplicate of an existing one.
        
        Args:
            character_id: Character identifier
            memory_data: Memory data to check
            
        Returns:
            Whether the memory is a duplicate
        """
        if character_id not in self.memories:
            return False
            
        # Simple check for exact content match, could be improved with semantic similarity
        content = memory_data.get("content", "").lower()
        for existing in self.memories[character_id]:
            existing_content = existing.get("content", "").lower()
            # If contents are similar (>80% match), consider it a duplicate
            if content and existing_content and (
                content in existing_content or existing_content in content or
                self._similarity(content, existing_content) > 0.8
            ):
                return True
        return False
    
    def _similarity(self, s1: str, s2: str) -> float:
        """
        Calculate simple similarity between two strings (0-1).
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Similarity score
        """
        # Simple word overlap similarity
        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        overlap = len(words1.intersection(words2))
        total = len(words1.union(words2))
        
        return overlap / total if total > 0 else 0.0
        
    def _extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract important dates from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            List of date memory items
        """
        memories = []
        
        # Regex patterns for various date formats
        date_patterns = [
            # День рождения
            (r'(?:мой|у меня|я родился|родилась|день рождения|др)(?:\с+\w+){0,3}\с+(\д{1,2}[\с\.\-]+(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*[\с\.\-]+\д{2,4})', 
             'birthday', 8),
            
            # День рождения (with month name)
            (r'(?:мой|у меня|я родился|родилась|день рождения|др)(?:\с+\w+){0,3}\с+(\д{1,2}[\с\.\-]+(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*)', 
             'birthday', 8),
            
            # Годовщина
            (r'(?:годовщина|отмечаем|празднуем|важная дата)(?:\с+\w+){0,3}\с+(\д{1,2}[\с\.\-]+(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*[\с\.\-]+\д{2,4})',
             'anniversary', 7),
            
            # Общие даты (числа месяца год)
            (r'(\д{1,2}[\с\.\-]+(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*[\с\.\-]+\д{2,4})',
             'date', 4),
             
            # Даты в формате число/месяц/год
            (r'(\д{1,2}[\.\/\-]\д{1,2}[\.\/\-]\д{2,4})',
             'date', 3)
        ]
        
        for pattern, category, importance in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Create a context around the date to capture the meaning
                date_index = text.find(match)
                start_index = max(0, date_index - 50)
                end_index = min(len(text), date_index + len(match) + 50)
                context = text[start_index:end_index]
                
                memory = {
                    "type": "date",
                    "category": category,
                    "date_value": match,
                    "content": f"Важная дата: {match} - {context}",
                    "importance": importance
                }
                memories.append(memory)
        
        return memories
        
    def _extract_personal_info(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract personal information from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            List of personal info memory items
        """
        memories = []
        
        # Patterns for various personal information
        info_patterns = [
            # Age
            (r'(?:мне|возраст|исполнилось|исполнится)\с+(\д{1,2})\с+(?:лет|год|года)', 
             'age', "Возраст пользователя: {}", 7),
            
            # Name
            (r'(?:меня зовут|моё имя|мое имя|я|зови меня)\с+([А-Я][а-я]+)', 
             'name', "Имя пользователя: {}", 8),
            
            # Job
            (r'(?:я работаю|моя работа|моя профессия|я по профессии|мой job)\с+([^\.,!?]+)', 
             'job', "Профессия пользователя: {}", 6),
             
            # Hobby
            (r'(?:я увлекаюсь|моё хобби|мое хобби|в свободное время я|люблю)\с+([^\.,!?]+)', 
             'hobby', "Хобби пользователя: {}", 5),
             
            # City/Location
            (r'(?:я живу в|я из|проживаю в|моё?\с+город|я живу в городе)\с+([А-Я][а-я]+)', 
             'location', "Место проживания пользователя: {}", 6),

            # Marital status
            (r'(?:я|у меня|статус)\с+(?:женат|замужем|не женат|холост|в разводе|вдовец|вдова|есть девушка|есть парень)',
             'relationship', "Семейное положение пользователя: {}", 5),
             
            # Children
            (r'(?:у меня|моему ребенку|моей дочери|моему сыну|моим детям)\с+(\д+)\с+(?:ребенка|детей|ребенок|сын|дочь|года|лет|месяцев)',
             'children', "Информация о детях пользователя: {}", 6),
             
            # Preferences
            (r'(?:я люблю|мне нравится|предпочитаю|обожаю|ненавижу|не люблю)\с+([^\.,!?]+)',
             'preference', "Предпочтение пользователя: {}", 4)
        ]
        
        for pattern, category, content_template, importance in info_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):  # Some regex can return tuples for group matches
                    match = ' '.join(match).strip()
                
                # Create a context around the information
                match_index = text.lower().find(match.lower())
                if match_index >= 0:
                    start_index = max(0, match_index - 20)
                    end_index = min(len(text), match_index + len(match) + 20)
                    context = text[start_index:end_index].strip()
                else:
                    context = match
                
                # Format the content with context
                content = content_template.format(context)
                
                memory = {
                    "type": "personal_info",
                    "category": category,
                    "value": match,
                    "content": content,
                    "importance": importance
                }
                memories.append(memory)
        
        return memories
        
    def save_to_database(self, db_session, character_id: str) -> bool:
        """
        Save memories to the database
        
        Args:
            db_session: SQLAlchemy session
            character_id: ID of the character
            
        Returns:
            bool: True if successful
        """
        memories = self.get_all_memories(character_id)
        if not memories:
            return True  # No memories to save
        
        try:
            # Make sure character_id is a string
            character_id_str = str(character_id)
            
            # First, reset any failed transaction
            from core.utils.db_helpers import reset_db_connection, execute_safe_query
            reset_db_connection(db_session)
            
            # Find a user_id for these memories
            user_result = execute_safe_query(db_session, """
                SELECT DISTINCT sender_id 
                FROM messages 
                WHERE recipient_id::text = :character_id AND sender_type = 'user'
                LIMIT 1
            """, {"character_id": character_id_str})
            
            user_row = user_result.fetchone() if user_result else None
            user_id = user_row[0] if user_row else None
            
            if not user_id:
                # Try the other direction
                user_result = execute_safe_query(db_session, """
                    SELECT DISTINCT recipient_id 
                    FROM messages 
                    WHERE sender_id::text = :character_id AND recipient_type = 'user'
                    LIMIT 1
                """, {"character_id": character_id_str})
                
                user_row = user_result.fetchone() if user_result else None
                user_id = user_row[0] if user_row else None
            
            # Используем системного пользователя, если user_id не найден
            if not user_id:
                self.logger.info("User ID not found, using system user (00000000-0000-0000-0000-000000000000)")
                user_id_str = "00000000-0000-0000-0000-000000000000"
            else:
                user_id_str = str(user_id)

            saved_count = 0
            # Всегда сохраняем в memory_entries (независимо от того, был найден user_id или нет)
            for memory in memories:
                # Check if this memory already exists
                memory_content = memory.get("content", "")
                if not memory_content:
                    continue
                    
                memory_type = memory.get("type", "unknown")
                category = memory.get("category", "general")
                importance = memory.get("importance", 5)
                
                # Check if memory exists
                exists_result = execute_safe_query(db_session, """
                    SELECT COUNT(*) FROM memory_entries
                    WHERE character_id::text = :character_id 
                    AND content = :content
                """, {
                    "character_id": character_id_str,
                    "content": memory_content
                })
                
                exists = exists_result.scalar() > 0 if exists_result else False
                
                if not exists:
                    # Insert the memory
                    memory_id = str(uuid.uuid4())
                    timestamp = datetime.datetime.now().isoformat()
                    
                    execute_safe_query(db_session, """
                        INSERT INTO memory_entries (
                            id, character_id, user_id, type, memory_type, category, content,
                            importance, is_active, created_at, updated_at
                        ) VALUES (
                            :id, :character_id, :user_id, :type, :memory_type, :category, :content,
                            :importance, :is_active, :created_at, :updated_at
                        )
                    """, {
                        "id": memory_id,
                        "character_id": character_id_str,
                        "user_id": user_id_str,
                        "type": memory_type,
                        "memory_type": memory_type,
                        "category": category,
                        "content": memory_content,
                        "importance": importance,
                        "is_active": True,
                        "created_at": timestamp,
                        "updated_at": timestamp
                    })
                    
                    saved_count += 1
                    self.logger.debug(f"✅ Saved memory: [{memory_type}/{category}] {memory_content[:50]}...")
            
            # Also save to events table as a batch for backward compatibility
            try:
                event_id = str(uuid.uuid4())
                timestamp = datetime.datetime.now().isoformat()
                
                execute_safe_query(db_session, """
                    INSERT INTO events (
                        id, character_id, user_id, event_type, data, created_at, updated_at
                    ) VALUES (
                        :id, :character_id, :user_id, :event_type, :data, :created_at, :updated_at
                    )
                """, {
                    "id": event_id,
                    "character_id": character_id_str,
                    "user_id": user_id_str,
                    "event_type": "memory",
                    "data": json.dumps(memories),
                    "created_at": timestamp,
                    "updated_at": timestamp
                })
                
                self.logger.info(f"✅ Saved memory batch to events table")
            except Exception as event_error:
                self.logger.warning(f"Failed to save memories to events table: {event_error}")
            
            # Commit all changes
            db_session.commit()
            
            if saved_count > 0:
                self.logger.info(f"✅ Successfully saved {saved_count} new memories to database")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving memories to database: {e}")
            if db_session:
                try:
                    db_session.rollback()
                except:
                    pass
            return False

    def load_from_database(self, db_session, character_id: str) -> bool:
        """
        Load memories from the database
        
        Args:
            db_session: SQLAlchemy session
            character_id: ID of the character
            
        Returns:
            bool: True if successful
        """
        try:
            # Clear existing in-memory data
            if character_id not in self.memories:
                self.memories[character_id] = []
            else:
                self.memories[character_id].clear()
            
            # Make sure character_id is a string
            character_id_str = str(character_id)
            
            # First try to reset any failed transaction
            from core.utils.db_helpers import reset_db_connection, execute_safe_query
            reset_db_connection(db_session)
            
            # Try to query memory_entries table, checking for both column names
            # First check if we have a memory_type column
            try:
                columns_result = execute_safe_query(db_session, """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'memory_entries'
                    AND column_name IN ('type', 'memory_type')
                """).fetchall()
                
                column_names = [col[0] for col in columns_result]
                
                has_type = 'type' in column_names
                has_memory_type = 'memory_type' in column_names
                
                # Dynamically build the query based on available columns
                column_to_use = None
                if has_memory_type:
                    column_to_use = 'memory_type'
                elif has_type:
                    column_to_use = 'type'
                    
                if column_to_use:
                    self.logger.info(f"Using '{column_to_use}' column to load memories")
                    
                    memory_entries = execute_safe_query(db_session, f"""
                        SELECT {column_to_use}, content, importance, is_active 
                        FROM memory_entries
                        WHERE character_id::text = :character_id
                        AND (is_active IS NULL OR is_active = TRUE)
                        ORDER BY importance DESC, created_at DESC
                    """, {"character_id": character_id_str}).fetchall()
                else:
                    # Try a more generic approach if neither column is found
                    self.logger.warning("Neither 'type' nor 'memory_type' column found, using fallback query")
                    memory_entries = execute_safe_query(db_session, """
                        SELECT content, importance, is_active 
                        FROM memory_entries
                        WHERE character_id::text = :character_id
                        AND (is_active IS NULL OR is_active = TRUE)
                        ORDER BY importance DESC, created_at DESC
                    """, {"character_id": character_id_str}).fetchall()
            except Exception as schema_err:
                self.logger.error(f"Error checking schema: {schema_err}")
                # Fallback to using memory_entries_view if available
                try:
                    memory_entries = execute_safe_query(db_session, """
                        SELECT memory_type, content, importance, is_active 
                        FROM memory_entries_view
                        WHERE character_id::text = :character_id
                        AND (is_active IS NULL OR is_active = TRUE)
                        ORDER BY importance DESC, created_at DESC
                    """, {"character_id": character_id_str}).fetchall()
                except Exception:
                    memory_entries = []
                    self.logger.error(f"Failed to use memory_entries_view fallback: {schema_err}")
            
            if memory_entries:
                for entry in memory_entries:
                    # Handle either query format
                    if len(entry) >= 4:  # We have type, content, importance, is_active
                        memory_type = entry[0] if entry[0] else "unknown"
                        content = entry[1]
                        importance = entry[2] if entry[2] is not None else 5
                        is_active = entry[3] if entry[3] is not None else True
                    elif len(entry) >= 3:  # We have content, importance, is_active (no type)
                        memory_type = "unknown"
                        content = entry[0]
                        importance = entry[1] if entry[1] is not None else 5
                        is_active = entry[2] if entry[2] is not None else True
                    else:
                        # Skip invalid entries
                        continue
                    
                    # Use a default category since it might not be in the database
                    category = "general"
                    
                    if content and is_active:  # Only load active memories with content
                        self.add_memory(character_id, {
                            "type": memory_type,
                            "category": category,
                            "content": content,
                            "importance": importance
                        })
                
                self.logger.info(f"Loaded {len(memory_entries)} memories from memory_entries table")
                return True
            else:
                # If no memories found in memory_entries, try the events table
                events = execute_safe_query(db_session, """
                    SELECT data
                    FROM events
                    WHERE character_id::text = :character_id AND event_type = 'memory'
                    ORDER BY created_at DESC
                """, {"character_id": character_id_str}).fetchall()
                
                event_memories_loaded = 0
                for event in events:
                    try:
                        # Parse the data - could be a JSON string or a list
                        event_data = event[0]
                        if isinstance(event_data, str):
                            try:
                                memory_data = json.loads(event_data)
                            except:
                                # If not valid JSON, skip this event
                                continue
                        else:
                            memory_data = event_data
                        
                        # It could be a list of memories or a single memory
                        if isinstance(memory_data, list):
                            for memory_item in memory_data:
                                if isinstance(memory_item, dict):
                                    memory_type = memory_item.get("type", "unknown")
                                    category = memory_item.get("category", "general")
                                    content = memory_item.get("content", "")
                                    importance = memory_item.get("importance", 5)
                                    
                                    if content:
                                        self.add_memory(character_id, {
                                            "type": memory_type,
                                            "category": category,
                                            "content": content,
                                            "importance": importance
                                        })
                                        event_memories_loaded += 1
                        elif isinstance(memory_data, dict):
                            memory_type = memory_data.get("type", "unknown")
                            category = memory_data.get("category", "general")
                            content = memory_data.get("content", "")
                            importance = memory_data.get("importance", 5)
                            
                            if content:
                                self.add_memory(character_id, {
                                    "type": memory_type,
                                    "category": category,
                                    "content": content,
                                    "importance": importance
                                })
                                event_memories_loaded += 1
                    except Exception as parse_err:
                        self.logger.error(f"Error parsing memory event data: {parse_err}")
                        continue
                
                if event_memories_loaded > 0:
                    self.logger.info(f"Loaded {event_memories_loaded} memories from events table")
                    return True
                else:
                    self.logger.info(f"No memories found for character {character_id}")
                    return False
            
        except Exception as e:
            self.logger.error(f"Error loading memories from database: {e}")
            return False

    def save_memories_to_database(self, memories, session=None, user_id=None, character_id=None):
        """Save extracted memories to the database"""
        try:
            # Create a new session if one wasn't provided
            should_close_session = False
            if (session is None):
                session = self.db.get_session()
                should_close_session = True
                
            # Если user_id не указан, используем системного пользователя
            if user_id is None:
                self.logger.info("User ID not provided to save_memories_to_database, using system user")
                user_id = "00000000-0000-0000-0000-000000000000"
                
            count = 0
            for memory in memories:
                # Format memory for database storage
                memory_entry = {
                    "id": str(uuid.uuid4()),
                    "character_id": character_id or self.character_id,
                    "user_id": user_id,  # Use provided user_id or system user
                    "memory_type": memory.get("type", "other"),  # Fixed: Using memory_type instead of type
                    "category": memory.get("category", "general"),
                    "content": memory.get("content", ""),
                    "importance": memory.get("importance", 5),
                    "created_at": datetime.datetime.now(),
                    "updated_at": datetime.datetime.now()
                }
                
                # Insert the memory into the database - updated to use memory_type
                query = text("""
                    INSERT INTO memory_entries 
                    (id, character_id, user_id, memory_type, category, content, importance, created_at, updated_at)
                    VALUES (:id, :character_id, :user_id, :memory_type, :category, :content, :importance, :created_at, :updated_at)
                """)
                
                session.execute(query, memory_entry)
                count += 1
                
                # Log the memory addition
                if memory.get("importance", 5) >= 7:
                    self.logger.info(f"🧠 CRITICAL MEMORY ADDED [{memory_entry['character_id']}]")
                else:
                    self.logger.info(f"🧠 MEMORY ADDED [{memory_entry['character_id']}]")
                    
                self.logger.info(f"➡️ Type: {memory_entry['memory_type']}, Category: {memory_entry['category']}, Importance: {memory_entry['importance']}/10")
                self.logger.info(f"📝 Content: {memory_entry['content']}")
                
            # Commit the transaction
            session.commit()
            
            if should_close_session:
                session.close()
                
            return count
        except Exception as e:
            self.logger.error(f"Error saving memories to database: {e}")
            if session:
                session.rollback()
                if should_close_session:
                    session.close()
            return 0

def load_memories_for_character(db_session: Session, character_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Load memories for a character from the database
    
    Args:
        db_session: SQLAlchemy session
        character_id: UUID of the character
        limit: Maximum number of memories to return
    
    Returns:
        List of memory dictionaries
    """
    try:
        # First check if we have a memory_type or type column
        columns_result = db_session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'memory_entries'
            AND column_name IN ('type', 'memory_type')
        """)).fetchall()
        
        column_names = [col[0] for col in columns_result]
        
        has_type = 'type' in column_names
        has_memory_type = 'memory_type' in column_names
        
        # Dynamically build the query based on available columns
        type_column = None
        if has_memory_type:
            type_column = 'memory_type'
        elif has_type:
            type_column = 'type'

        # Check if category column exists
        has_category = db_session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'memory_entries' AND column_name = 'category'
            )
        """)).scalar()
            
        if type_column and has_category:
            query = text(f"""
                SELECT {type_column}, category, content, importance, is_active, created_at 
                FROM memory_entries
                WHERE character_id::text = :character_id
                AND (is_active IS NULL OR is_active = TRUE)
                ORDER BY importance DESC, created_at DESC
                LIMIT :limit
            """)
        elif type_column:
            query = text(f"""
                SELECT {type_column}, content, importance, is_active, created_at 
                FROM memory_entries
                WHERE character_id::text = :character_id
                AND (is_active IS NULL OR is_active = TRUE)
                ORDER BY importance DESC, created_at DESC
                LIMIT :limit
            """)
        else:
            # Fallback if no type column found
            query = text("""
                SELECT content, importance, is_active, created_at 
                FROM memory_entries
                WHERE character_id::text = :character_id
                AND (is_active IS NULL OR is_active = TRUE)
                ORDER BY importance DESC, created_at DESC
                LIMIT :limit
            """)
        
        result = db_session.execute(query, {
            "character_id": str(character_id),
            "limit": limit
        })
        
        memories = result.fetchall()
        
        # Convert to list of dictionaries
        memory_list = []
        for memory in memories:
            if type_column and has_category:
                memory_dict = {
                    "type": memory[0] if memory[0] else "unknown",
                    "category": memory[1] if memory[1] else "general",
                    "content": memory[2],
                    "importance": memory[3] if memory[3] is not None else 5,
                    "is_active": memory[4] if len(memory) > 4 and memory[4] is not None else True,
                    "created_at": memory[5] if len(memory) > 5 else None
                }
            elif type_column:
                memory_dict = {
                    "type": memory[0] if memory[0] else "unknown",
                    "category": "general",  # Default since column doesn't exist
                    "content": memory[1],
                    "importance": memory[2] if memory[2] is not None else 5,
                    "is_active": memory[3] if len(memory) > 3 and memory[3] is not None else True,
                    "created_at": memory[4] if len(memory) > 4 else None
                }
            else:
                memory_dict = {
                    "type": "unknown",  # Default type
                    "category": "general",  # Default category
                    "content": memory[0],
                    "importance": memory[1] if memory[1] is not None else 5,
                    "is_active": memory[2] if len(memory) > 2 and memory[2] is not None else True,
                    "created_at": memory[3] if len(memory) > 3 else None
                }
            memory_list.append(memory_dict)
            
        logger.info(f"Loaded {len(memory_list)} memories for character {character_id}")
        return memory_list
        
    except Exception as e:
        logger.error(f"Error loading memories from database: {e}")
        return []
        
def save_memory(db_session: Session, character_id: str, user_id: str, memory_data: Dict[str, Any]) -> bool:
    """
    Save a memory to the database
    
    Args:
        db_session: SQLAlchemy session
        character_id: UUID of the character
        user_id: UUID of the user
        memory_data: Memory data dictionary
    
    Returns:
        Success status
    """
    try:
        # Extract memory fields with defaults
        memory_type = memory_data.get("type", "fact")
        content = memory_data.get("content", "")
        importance = memory_data.get("importance", 5)
        category = memory_data.get("category", "general")
        
        if not content:
            logger.warning("Attempted to save memory with empty content")
            return False
        
        query = text("""
            INSERT INTO memory_entries 
            (id, character_id, user_id, memory_type, category, content, importance, is_active, created_at, updated_at)
            VALUES 
            (gen_random_uuid(), :character_id, :user_id, :memory_type, :category, :content, :importance, TRUE, NOW(), NOW())
        """)
        
        db_session.execute(query, {
            "character_id": character_id,
            "user_id": user_id,
            "memory_type": memory_type,  # Use the "type" field from memory_data but save it to "memory_type" column
            "category": category,
            "content": content,
            "importance": importance
        })
        
        db_session.commit()
        logger.info(f"Successfully saved memory for character {character_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        db_session.rollback()
        return False
