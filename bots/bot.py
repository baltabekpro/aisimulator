import os
import json
import logging
import asyncio
import aiohttp
import sys
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardRemove
import datetime
import re
import io
from io import BytesIO
from aiogram.types import InputFile

# Add the parent directory to system path to allow imports from 'core'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Add this import at the top of the file
from core.api.client import ApiClient

# Fallback implementation for when core module is unavailable
class FallbackAI:
    """Fallback AI implementation when the core.ai.gemini module can't be imported"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.warning("Using FallbackAI because core.ai.gemini could not be imported")
    
    def generate_response(self, context: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Generate a simple fallback response when the real AI is unavailable"""
        self.logger.info(f"FallbackAI received message: {message[:30]}...")
        return {
            "text": "Извините, я сейчас не могу обработать ваше сообщение. Наши системы временно недоступны. Пожалуйста, попробуйте позже.",
            "emotion": "neutral",
            "relationship_changes": {"general": 0}
        }
    
    def get_memories(self, character_id: str) -> List[Dict[str, Any]]:
        """Fallback for memory retrieval"""
        return []

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования с увеличенной детализацией
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Токен бота
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable is not set!")
    logger.error("Please create a .env file from .env.example and set your Telegram bot token.")
    exit(1)

# URL API и JWT токен
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
API_KEY = os.getenv("API_KEY", "")
logger.info(f"Using API base URL: {API_BASE_URL}")

# For testing purposes, let's add a way to authenticate or use a test token
API_KEY = os.getenv("API_KEY", "test_token_for_development")
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXJfaWQiLCJleHAiOjE3MTY1MDE5MDl9.QmfxDG9xPnxzp1EzVH5byMkKEW3K6JGlsOrKMR-fdJU"

# Use the test token if no API key is provided
if not API_KEY or API_KEY == "your_api_jwt_token_here":
    API_KEY = TEST_TOKEN
    logger.info("Using test token for API authentication")

# Get API key from environment
API_KEY = os.getenv("BOT_API_KEY")
if not API_KEY:
    logger.warning("BOT_API_KEY not found in environment, API authentication may fail")
    API_KEY = "secure_bot_api_key_12345"  # Fallback to default from .env

# Initialize API client with API key
api_client = ApiClient(api_key=API_KEY)

# Get MinIO URL mapping from environment
def get_minio_url_mapping():
    """
    Получает маппинг для URL MinIO из переменных окружения
    Returns:
        dict: Словарь с маппингом внутренних URL на публичные
    """
    # Базовый маппинг
    default_mapping = {
        "http://minio:9000": "http://localhost:9000",
        "https://minio:9000": "https://localhost:9000"
    }
    
    try:
        # Сначала проверим специфичную для MinIO переменную
        minio_url_mapping = os.getenv("MINIO_URL_MAPPING")
        if (minio_url_mapping):
            try:
                # Попытаемся распарсить JSON
                import json
                mapping = json.loads(minio_url_mapping)
                logger.info(f"Используем MINIO_URL_MAPPING из переменных окружения: {mapping}")
                return mapping
            except Exception as e:
                logger.error(f"Ошибка при парсинге MINIO_URL_MAPPING: {e}")
        
        # Проверим наличие публичного URL для MinIO
        minio_public_url = os.getenv("MINIO_PUBLIC_URL")
        if minio_public_url:
            # Добавим маппинг для внутреннего адреса на публичный
            default_mapping["http://minio:9000"] = minio_public_url
            default_mapping["https://minio:9000"] = minio_public_url
            logger.info(f"Используем MINIO_PUBLIC_URL из переменных окружения: {minio_public_url}")
        
        return default_mapping
    except Exception as e:
        logger.error(f"Ошибка при получении маппинга URL MinIO: {e}")
        return default_mapping

# Функция для корректировки URL MinIO
def fix_minio_url(url):
    """
    Исправляет URL MinIO для правильного доступа
    
    Args:
        url (str): Исходный URL
        
    Returns:
        str: Исправленный URL
    """
    if not url:
        return url
        
    # Получаем маппинг
    url_mapping = get_minio_url_mapping()
    
    # Применяем маппинг
    for internal_url, public_url in url_mapping.items():
        if internal_url in url:
            return url.replace(internal_url, public_url)
    
    return url

# Функция для скачивания аватара с несколькими попытками и альтернативами
async def download_avatar(avatar_url, character_id=None, max_retries=3):
    """
    Скачивает аватар с несколькими попытками и альтернативными URL
    
    Args:
        avatar_url (str): URL аватара
        character_id (str, optional): ID персонажа для логов
        max_retries (int, optional): Максимальное количество попыток
        
    Returns:
        tuple: (bytes_data, content_type) или (None, None) в случае ошибки
    """
    if not avatar_url:
        return None, None
    
    # Применяем маппинг к начальному URL
    avatar_url = fix_minio_url(avatar_url)
    
    logger.info(f"Скачиваем аватар с URL: {avatar_url} для персонажа {character_id or 'unknown'}")
    
    # Пробуем все возможные URL
    urls_to_try = [
        avatar_url,  # Начальный URL (уже с примененным маппингом)
        avatar_url.replace("localhost:9000", "minio:9000"),  # На случай если мы внутри Docker
        avatar_url.replace("minio:9000", "localhost:9000"),  # На случай если мы вне Docker
        avatar_url.replace("http://", "https://"),  # HTTP -> HTTPS
        avatar_url.replace("https://", "http://")   # HTTPS -> HTTP
    ]
    
    # Удаляем дубликаты
    urls_to_try = list(dict.fromkeys(urls_to_try))
    
    # Пробуем скачать с каждого URL
    for i, url in enumerate(urls_to_try):
        try:
            logger.debug(f"Попытка {i+1}/{len(urls_to_try)}: {url}")
            
            async with aiohttp.ClientSession() as session:
                for attempt in range(1, max_retries + 1):
                    try:
                        async with session.get(url, timeout=5) as response:
                            if response.status == 200:
                                data = await response.read()
                                content_type = response.content_type
                                logger.info(f"Аватар успешно скачан ({len(data)} байт)")
                                return data, content_type
                            else:
                                logger.warning(f"Ошибка при скачивании аватара: HTTP {response.status}")
                    except aiohttp.ClientError as e:
                        logger.warning(f"Ошибка сетевого соединения (попытка {attempt}/{max_retries}): {e}")
                        if attempt < max_retries:
                            await asyncio.sleep(1)  # Небольшая пауза перед следующей попыткой
        except Exception as e:
            logger.error(f"Неожиданная ошибка при скачивании аватара с {url}: {e}")
    
    # Проверяем локальный путь как последнюю альтернативу
    if character_id:
        local_paths = [
            f"/app/avatars/{character_id}.png",
            f"/app/avatars/{character_id}.jpg",
            f"/app/avatars/{character_id}.jpeg",
            f"avatars/{character_id}.png",
            f"avatars/{character_id}.jpg"
        ]
        
        for path in local_paths:
            try:
                if os.path.exists(path):
                    logger.info(f"Найден локальный файл аватара: {path}")
                    with open(path, "rb") as f:
                        # Определяем content_type по расширению
                        ext = path.lower().split('.')[-1]
                        content_type = f"image/{ext}"
                        if ext == "jpg":
                            content_type = "image/jpeg"
                        return f.read(), content_type
            except Exception as e:
                logger.error(f"Ошибка при чтении локального файла {path}: {e}")
    
    logger.error(f"Не удалось скачать аватар после всех попыток")
    return None, None

# Определение состояний FSM
class BotStates(StatesGroup):
    selecting_character = State()
    chatting = State()
    generating_character = State()
    confirming_character = State()
    sending_gift = State()
    confirming_gift = State()
    editing_character = State()
    viewing_memories = State()

# Эмоциональные эмодзи
EMOTION_EMOJIS = {
    "happy": "😊",
    "sad": "😢",
    "angry": "😠",
    "excited": "😀",
    "anxious": "😰",
    "neutral": ""
}

# Список доступных подарков
AVAILABLE_GIFTS = [
    {"id": "flower", "name": "Букет цветов 💐", "price": 10, "effect": 3},
    {"id": "chocolate", "name": "Коробка конфет 🍫", "price": 15, "effect": 5},
    {"id": "jewelry", "name": "Украшение 💍", "price": 50, "effect": 15},
    {"id": "perfume", "name": "Духи 🧴", "price": 30, "effect": 10},
    {"id": "teddy", "name": "Плюшевый мишка 🧸", "price": 20, "effect": 7},
    {"id": "vip_gift", "name": "VIP Подарок ✨", "price": 100, "effect": 25}
]

# Создаем основную клавиатуру меню
def get_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Выбрать персонажа", callback_data="select_character")],
        [InlineKeyboardButton(text="🎁 Отправить подарок", callback_data="send_gift")],
        [InlineKeyboardButton(text="🔄 Очистить чат", callback_data="clear_chat")],
        [InlineKeyboardButton(text="✏️ Изменить персонажа", callback_data="edit_character")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])
    return keyboard

# Create a keyboard for the chat mode with quick actions
def get_chat_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎁 Отправить подарок"),
                KeyboardButton(text="💬 Меню")
            ],
            [
                KeyboardButton(text="❤️ Отношения"),
                KeyboardButton(text="📱 Профиль")
            ],
            [
                KeyboardButton(text="🧠 Память"),
                KeyboardButton(text="❓ Помощь")
            ],
            [
                KeyboardButton(text="📋 Сжать диалог")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Напишите сообщение или выберите действие..."
    )
    return keyboard

# Update API URL handling to be more robust
async def health_check():
    try:
        url = f"{API_BASE_URL}/health"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if (response.status == 200):
                    return True
                else:
                    logger.error(f"API health check failed with status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"API health check error: {e}")
        return False

async def start_handler(message: types.Message, state: FSMContext):
    try:
        api_available = await health_check()
        
        if not api_available:
            await message.answer("⚠️ API сервер недоступен. Пожалуйста, попробуйте позже.")
            return
            
        headers = {"Authorization": f"Bearer {API_KEY}"}
        logger.debug(f"Using authorization headers: {headers}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE_URL}/chat/characters",
                headers=headers,
                timeout=10
            ) as response:
                if (response.status != 200):
                    logger.warning(f"API returned status {response.status}")
                    await message.answer("Ошибка при получении списка персонажей. Пожалуйста, попробуйте позже.")
                    return
                
                characters = await response.json()
                logger.info(f"Retrieved {len(characters)} characters from API")
        
        await state.update_data(characters=characters)
        
        message_text = "👋 Добро пожаловать в AI Simulator!\n\nВыберите персонажа для общения, отправив его номер:\n\n"
        for i, character in enumerate(characters, 1):
            message_text += f"{i}. {character['name']} - {character.get('age', 'Н/Д')} лет\n"
        
        await message.answer(message_text, reply_markup=get_main_menu_keyboard())
        await state.set_state(BotStates.selecting_character)
    
    except Exception as e:
        logger.exception(f"Unexpected error in start_handler: {e}")
        await message.answer(
            "Произошла ошибка при запуске бота. Пожалуйста, попробуйте позже or свяжитесь с администратором."
        )

async def select_character_handler(message: types.Message, state: FSMContext):
    try:
        if not message.text.isdigit():
            await message.answer("Пожалуйста, введите число.")
            return
        
        choice = int(message.text)
        
        user_data = await state.get_data()
        characters = user_data.get("characters", [])
        
        if (choice < 1 or choice > len(characters)):
            await message.answer(f"Пожалуйста, выберите номер от 1 до {len(characters)}.")
            return
        
        selected_character = characters[choice - 1]
        await state.update_data(
            character=selected_character,
            character_id=selected_character["id"],
            character_name=selected_character["name"]
        )
        
        headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/chat/characters/{selected_character['id']}/start-chat",
                headers=headers
            ) as response:
                if (response.status != 200):
                    await message.answer("Ошибка при начале диалога. Попробуйте выбрать другого персонажа.")
                    return
                
                chat_response = await response.json()
        
        messages = chat_response.get("messages", [])
        first_message = messages[0]["content"] if messages else "Привет! Давай пообщаемся."
        
        await message.answer(
            f"Вы общаетесь с {selected_character['name']}.\n\n"
            f"{first_message}\n\n"
            "Отправьте сообщение для ответа or выберите действие.",
            reply_markup=get_chat_keyboard()
        )
        await state.set_state(BotStates.chatting)
    
    except Exception as e:
        logger.error(f"Error in select_character_handler: {e}")
        await message.answer("Произошла ошибка при выборе персонажа. Пожалуйста, попробуйте снова: /start")
        await state.clear()

async def ensure_user_exists(telegram_id: int) -> str:
    """
    Проверяет существование пользователя в базе данных и создаёт его если нужно.
    Возвращает UUID пользователя для использования с API памяти.
    
    Args:
        telegram_id: ID пользователя в Telegram
    
    Returns:
        str: UUID пользователя в формате строки
    """
    try:
        headers = {"Authorization": f"Bearer {API_KEY}", "X-API-Key": API_KEY}
        
        # Преобразуем Telegram ID в надежный UUID формат
        user_uuid = await get_user_uuid_for_telegram_id(telegram_id, None)
        user_id_str = user_uuid[0] if isinstance(user_uuid, tuple) else user_uuid
        logger.info(f"Проверяю/создаю пользователя с ID: {user_id_str} для Telegram ID: {telegram_id}")
        
        # Сначала проверим, существует ли пользователь
        async with aiohttp.ClientSession() as session:
            try:
                # Попытаемся получить пользователя по UUID
                check_user_url = f"{API_BASE_URL}/users/{user_id_str}"
                async with session.get(check_user_url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        logger.info(f"Пользователь найден: {user_data.get('username', 'Unknown')}")
                        return user_id_str
            except Exception as e:
                logger.warning(f"Ошибка при проверке пользователя: {e}")
        
        # Пользователь не найден, создаем нового
        try:
            # Формируем хуманизированное имя пользователя
            username = f"telegram_{telegram_id}"
            email = f"user_{telegram_id}@telegram.local"
            name = f"Telegram User {telegram_id}"
            
            user_data = {
                "user_id": user_id_str,  # Предопределенный UUID на основе Telegram ID
                "username": username,
                "email": email,
                "name": name,
                "is_active": True
            }
            
            # Пробуем через разные эндпоинты API создать пользователя
            create_endpoints = [
                f"{API_BASE_URL}/users/create",
                f"{API_BASE_URL}/auth/register",
                f"{API_BASE_URL}/users"
            ]
            
            for endpoint in create_endpoints:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            endpoint, 
                            json=user_data,
                            headers=headers
                        ) as response:
                            if response.status in [200, 201]:
                                created_user = await response.json()
                                logger.info(f"Пользователь успешно создан через {endpoint}")
                                return user_id_str
                            else:
                                logger.warning(f"Ошибка создания пользователя через {endpoint}: {response.status}")
                except Exception as endpoint_error:
                    logger.warning(f"Ошибка при обращении к {endpoint}: {endpoint_error}")
            
            # Если все API вызовы не сработали, используем SQL напрямую через системный эндпоинт
            try:
                system_sql_url = f"{API_BASE_URL}/admin/execute-sql"
                sql_query = f"""
                INSERT INTO users (user_id, username, email, name, password_hash, created_at, is_active)
                VALUES ('{user_id_str}', '{username}', '{email}', '{name}', 
                        '$2b$12$K8uw2YYdIzp2XvRWMs9vpO6STRyI53aUEym.Oi4XwqVgRvG/f7kUC', 
                        NOW(), true)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING user_id::text;
                """
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        system_sql_url, 
                        json={"query": sql_query},
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            logger.info(f"Пользователь создан через SQL: {user_id_str}")
                            return user_id_str
                        else:
                            logger.warning(f"Ошибка создания пользователя через SQL: {response.status}")
            except Exception as sql_error:
                logger.warning(f"Ошибка SQL: {sql_error}")
                
            # Финальная попытка через системный эндпоинт
            try:
                system_endpoint = f"{API_BASE_URL}/system/ensure-user"
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        system_endpoint, 
                        json={"telegram_id": telegram_id, "user_id": user_id_str},
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            logger.info(f"Пользователь создан через системный эндпоинт: {user_id_str}")
                            return user_id_str
            except Exception as sys_error:
                logger.warning(f"Ошибка системного эндпоинта: {sys_error}")
        
        except Exception as create_error:
            logger.error(f"Ошибка создания пользователя: {create_error}")
        
        # Если все попытки не удались, просто возвращаем UUID
        logger.warning(f"Не удалось создать пользователя, используем UUID напрямую: {user_id_str}")
        return user_id_str
    
    except Exception as e:
        logger.exception(f"Общая ошибка в ensure_user_exists: {e}")
        # Возвращаем UUID в формате строки как запасной вариант
        fallback_uuid = f"c7cb5b5c-e469-586e-8e87-{str(telegram_id).replace(' ', '')}"
        return fallback_uuid

async def chat_handler(message: types.Message, state: FSMContext):
    # Intercept special button commands
    if (message.text == "🧠 Память"):
        await memory_button_handler(message, state)
        return
    elif (message.text == "❤️ Отношения"):
        await show_relationship_stats(message, state)
        return
    elif (message.text == "📱 Профиль"):
        await character_info_handler(message, state)
        return
    elif (message.text == "💬 Меню"):
        await menu_command(message)
        return
    elif (message.text == "❓ Помощь"):
        await help_handler(message)
        return
    elif (message.text == "🎁 Отправить подарок"):
        await send_gift_handler(message, state)
        return
    elif (message.text == "📋 Сжать диалог"):
        await compress_dialog_handler(message, state)
        return
        
    # Continue with regular message handling
    try:
        state_data = await state.get_data()
        character_id = state_data.get("character_id")
        
        if not character_id:
            await message.answer("Пожалуйста, выберите персонажа сначала!")
            return
        
        chat_history = await get_chat_history(character_id, message.from_user.id)
        logger.info(f"Получено {len(chat_history)} сообщений из истории для персонажа {character_id}")
        
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        character = await get_character(character_id)
        if not character:
            await message.answer("Ошибка! Персонаж не найден.")
            return
            
        current_emotion = "neutral"
        if chat_history:
            for msg in reversed(chat_history):
                if (msg.get("sender_type") == "ai" and msg.get("emotion")):
                    current_emotion = msg.get("emotion")
                    break
                    
        if (isinstance(character, dict) and "current_emotion" not in character):
            character["current_emotion"] = current_emotion
        
        context = {
            "character": character,
            "history": chat_history,
            "user_id": str(message.from_user.id)
        }
        
        logger.info(f"Подготовлен контекст для запроса. История: {len(chat_history)} сообщений.")
        if chat_history:
            logger.info(f"Последнее сообщение в истории: {chat_history[-1].get('content', '')[:50]}...")
        
        await save_message(
            sender_id=message.from_user.id,
            recipient_id=character_id,
            content=message.text,
            sender_type="user"
        )
        
        # Try to import the GeminiAI, fall back to our simple implementation if it fails
        try:
            # Use absolute import with main project directory in sys.path
            from core.ai.gemini import GeminiAI
            ai = GeminiAI()
            logger.info("Successfully imported and created GeminiAI instance")
        except ImportError as e:
            logger.error(f"Failed to import GeminiAI: {e}")
            ai = FallbackAI()
        
        response = ai.generate_response(context, message.text)
        
        if not response or "text" not in response:
            logger.error(f"Ошибка! Пустой ответ от AI: {response}")
            await message.answer("Извините, произошла ошибка. Пожалуйста, попробуйте еще раз.")
            return
        
        response_text = clean_text_for_telegram(response.get("text", "Извините, я не смогла сформулировать ответ."))
        emotion = response.get("emotion", "neutral")
        
        emoji = EMOTION_EMOJIS.get(emotion, "")
        
        relationship_changes = response.get("relationship_changes", {})
        relationship_text = format_relationship_changes(relationship_changes)
        
        full_response = f"{response_text} {emoji}\n\n{relationship_text}"
        await message.answer(full_response)
        
        await save_message(
            sender_id=character_id,
            recipient_id=message.from_user.id,
            content=response_text,
            sender_type="ai",
            emotion=emotion,
            relationship_changes=relationship_changes
        )
        
        if ("memory" in response):
            memory_data = response.get("memory", [])
            logger.info(f"Извлечены новые воспоминания: {len(memory_data)} записей")
            
            # Проверяем/создаем пользователя перед сохранением памяти
            user_id_str = await ensure_user_exists(message.from_user.id)
            logger.info(f"Использую UUID пользователя для сохранения памяти: {user_id_str}")
            
            # Добавляем сохранение в базу данных через API
            for memory in memory_data:
                if (isinstance(memory, dict) and "content" in memory):
                    try:
                        # Добавляем user_id, если его нет
                        if "user_id" not in memory or not memory["user_id"]:
                            memory["user_id"] = user_id_str
                            
                        # Отправляем запрос на создание памяти через API
                        headers = {
                            "Authorization": f"Bearer {API_KEY}", 
                            "X-API-Key": API_KEY
                        }
                        memory_url = f"{API_BASE_URL}/chat/characters/{character_id}/memories"
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                memory_url,
                                json=memory,
                                headers=headers
                            ) as memory_response:
                                if memory_response.status == 200 or memory_response.status == 201:
                                    logger.info(f"✅ Память успешно сохранена: {memory['content'][:50]}...")
                                else:
                                    # Если ошибка связана с внешним ключом пользователя, пробуем fallback на system user
                                    text = await memory_response.text()
                                    if 'violates foreign key constraint' in text and 'fk_user' in text:
                                        logger.warning(f"Ошибка внешнего ключа пользователя, пробуем сохранить с system user")
                                        memory["user_id"] = "00000000-0000-0000-0000-000000000000"
                                        async with session.post(
                                            memory_url,
                                            json=memory,
                                            headers=headers
                                        ) as sys_response:
                                            if sys_response.status == 200 or sys_response.status == 201:
                                                logger.info(f"✅ Память сохранена с system user: {memory['content'][:50]}...")
                                            else:
                                                logger.error(f"⚠️ Ошибка сохранения памяти даже с system user: {sys_response.status}")
                                    else:
                                        logger.error(f"⚠️ Ошибка сохранения памяти: {memory_response.status}")
                    except Exception as mem_error:
                        logger.error(f"❌ Ошибка при сохранении памяти: {mem_error}")
            
            memories_text = []
            for memory in memory_data:
                if (isinstance(memory, dict) and "content" in memory):
                    memories_text.append(f"- {memory['content']}")
            
            if memories_text:
                logger.info(f"Новые воспоминания:\n{chr(10).join(memories_text)}")
        
    except Exception as e:
        logger.exception(f"Ошибка при обработке сообщения: {e}")
        await message.answer("Извините, произошла ошибка при обработке вашего сообщения.")

async def compress_dialog_handler(message: types.Message, state: FSMContext):
    """Handle compression of dialog history to maintain context while reducing tokens"""
    try:
        state_data = await state.get_data()
        character_id = state_data.get("character_id")
        
        if not character_id:
            await message.answer("⚠️ Пожалуйста, сначала выберите персонажа для общения.")
            return
        
        # Show processing message
        processing_msg = await message.answer("🔄 Сжимаю историю диалога, пожалуйста, подождите...")
        
        # Call the API endpoint to compress the conversation
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        async with aiohttp.ClientSession() as session:
            compression_url = f"{API_BASE_URL}/chat/characters/{character_id}/compress"
            
            try:
                async with session.post(compression_url, headers=headers) as response:
                    response_json = await response.json()
                    logger.info(f"Compression API response: {response_json}")
                    
                    if not response_json.get("success", False):
                        error_code = response_json.get("error", "unknown_error")
                        message_count = response_json.get("message_count", 0)
                        
                        await processing_msg.delete()
                        
                        if (error_code == "insufficient_messages"):
                            await message.answer(
                                f"ℹ️ Недостаточно сообщений для сжатия истории ({message_count}/3 мин.). "
                                f"Продолжайте общение и попробуйте позже."
                            )
                        else:
                            await message.answer(f"❌ Ошибка при сжатии диалога: {response_json.get('message', 'Неизвестная ошибка')}")
                            logger.error(f"Compression error: {response_json.get('error', 'Unknown')}")
                        return
                    
                    # Process successful compression
                    summary = response_json.get("summary", "")
                    original_count = response_json.get("original_messages", 0)
                    compressed_count = response_json.get("compressed_messages", 0)
                    
                    # Delete the processing message
                    await processing_msg.delete()
                    
                    # Show success message with summary
                    await message.answer(
                        f"✅ История диалога успешно сжата!\n\n"
                        f"📊 Статистика:\n"
                        f"• Сообщений до сжатия: {original_count}\n"
                        f"• Сообщений после сжатия: {compressed_count}\n\n"
                        f"📝 Резюме диалога:\n{summary}",
                        parse_mode="Markdown"
                    )
                    
                    logger.info(f"Successfully compressed dialog for character {character_id}")
                    return
            except aiohttp.ClientError as e:
                await processing_msg.delete()
                await message.answer("❌ Не удалось подключиться к серверу. Пожалуйста, попробуйте позже.")
                logger.error(f"Connection error during compression: {e}")
                return
        
    except Exception as e:
        logger.exception(f"Error in compress_dialog_handler: {e}")
        await message.answer("❌ Произошла ошибка при сжатии диалога. Пожалуйста, попробуйте позже.")

async def memory_button_handler(message: types.Message, state: FSMContext):
    """Handle memory button click - directly fetch from database without AI response"""
    try:
        state_data = await state.get_data()
        character_id = state_data.get("character_id")
        
        if not character_id:
            await message.answer("Пожалуйста, сначала выберите персонажа!")
            return
        
        character = await get_character(character_id)
        if not character:
            await message.answer("Персонаж не найден.")
            return
            
        character_name = character.get("name", "Персонаж")
        
        # Show loading message
        loading_msg = await message.answer("🔍 Загрузка воспоминаний...")
        
        # Get the proper user ID from storage or mapping
        user_uuid = await get_user_uuid_for_telegram_id(message.from_user.id, character_id)
        logger.info(f"Using user UUID formats: {user_uuid} for Telegram ID: {message.from_user.id}")
        
        # Use the UUID-format user ID when fetching memories
        # The API client now knows how to handle tuples of ID formats
        memories = api_client.get_character_memories(character_id, user_uuid)
        
        # Delete loading message
        await loading_msg.delete()
        
        if not memories:
            await message.answer(f"🧠 {character_name} пока ничего не запомнила о вас.\n\nРасскажите что-нибудь о себе в процессе общения, и бот будет запоминать важную информацию.")
            return
        
        # Group memories by type
        memory_by_type = {}
        for memory in memories:
            memory_type = memory.get("type", "other")
            if memory_type not in memory_by_type:
                memory_by_type[memory_type] = []
            memory_by_type[memory_type].append(memory)
        
        # Create header message
        header_msg = f"🧠 Что {character_name} знает о вас:"
        await message.answer(header_msg)
        
        # List of messages to send
        memory_messages = []
        current_message = ""
        
        # Format memories by type
        memory_types = [
            ("personal_info", "👤 Личная информация:"),
            ("date", "📅 Важные даты:"),
            ("preference", "❤️ Предпочтения:"),
            # Add other known types with custom headings
            ("fact", "📚 Факты:"),
            ("relationship", "👫 Отношения:"),
            ("experience", "🌟 Опыт:")
        ]
        
        # Add known memory types first
        for memory_type, heading in memory_types:
            if memory_type in memory_by_type and memory_by_type[memory_type]:
                section = f"\n{heading}\n"
                
                for memory in memory_by_type[memory_type]:
                    content = memory.get("content", "")
                    memory_line = f"• {content}\n"
                    
                    # Check if adding this memory would exceed Telegram's limit
                    if len(current_message + section + memory_line) > 4000:
                        memory_messages.append(current_message.strip())
                        current_message = section + memory_line
                    elif not current_message:
                        current_message = section + memory_line
                    else:
                        if section in current_message:
                            current_message += memory_line
                        else:
                            current_message += section + memory_line
                
                # Remove the type from the dictionary to track what's left
                memory_by_type.pop(memory_type)
        
        # Add any remaining memory types
        for memory_type, memories_list in memory_by_type.items():
            if memories_list:
                section = f"\n📝 {memory_type.capitalize()}:\n"
                
                for memory in memories_list:
                    content = memory.get("content", "")
                    memory_line = f"• {content}\n"
                    
                    # Check if adding this memory would exceed Telegram's limit
                    if len(current_message + section + memory_line) > 4000:
                        memory_messages.append(current_message.strip())
                        current_message = section + memory_line
                    elif not current_message:
                        current_message = section + memory_line
                    else:
                        if section in current_message:
                            current_message += memory_line
                        else:
                            current_message += section + memory_line
        
        # Add the last message if not empty
        if current_message:
            memory_messages.append(current_message.strip())
        
        # Send all memory messages
        for msg in memory_messages:
            await message.answer(msg)
            
        # Show footer with count
        if len(memories) > 0:
            await message.answer(f"⭐ Всего воспоминаний: {len(memories)}")
        
    except Exception as e:
        logger.exception(f"Ошибка при получении воспоминаний: {e}")
        await message.answer("Извините, произошла ошибка при получении воспоминаний.")

async def get_user_uuid_for_telegram_id(telegram_id: int, character_id: str) -> str:
    """
    Get or create a UUID format user ID that matches the backend's conversion method.
    This ensures we use the same UUID format when retrieving memories.
    
    Args:
        telegram_id: Numeric Telegram user ID
        character_id: Character UUID to help with lookup
        
    Returns:
        str: UUID format user ID or tuple of multiple formats to try
    """
    # First try to get from cached mapping if available
    if hasattr(get_user_uuid_for_telegram_id, "mapping") and telegram_id in get_user_uuid_for_telegram_id.mapping:
        return get_user_uuid_for_telegram_id.mapping[telegram_id]
    
    # Initialize mapping cache if not exists
    if not hasattr(get_user_uuid_for_telegram_id, "mapping"):
        get_user_uuid_for_telegram_id.mapping = {}
    
    try:
        # Convert telegram_id to string and ensure it's a clean number
        telegram_id_str = str(telegram_id).strip()
        if not telegram_id_str.isdigit():
            # If not a valid numeric ID, create a hash-based stable ID
            import hashlib
            hash_obj = hashlib.md5(telegram_id_str.encode())
            hex_dig = hash_obj.hexdigest()
            user_uuid = f"c7cb5b5c-e469-586e-8e87-{hex_dig[-12:]}"
            logger.info(f"Created hash-based UUID for non-numeric ID: {user_uuid}")
            get_user_uuid_for_telegram_id.mapping[telegram_id] = user_uuid
            return user_uuid
            
        # Convert to integer for hex formatting
        telegram_id_int = int(telegram_id_str)
        
        # Create multiple UUID formats to try:
        
        # 1. Hex format (primary format used by memory_manager)
        user_uuid_hex = f"c7cb5b5c-e469-586e-8e87-{telegram_id_int:x}".replace(" ", "0")
        
        # 2. Decimal format with leading zeros
        user_uuid_decimal = f"c7cb5b5c-e469-586e-8e87-{telegram_id_int:012d}"
        
        # 3. Raw telegram ID (for direct parameter)
        user_uuid_raw = telegram_id_int
        
        # Combine all formats in a tuple to try all of them
        uuid_formats = (user_uuid_hex, user_uuid_decimal, user_uuid_raw)
        
        # Store in mapping for future use
        get_user_uuid_for_telegram_id.mapping[telegram_id] = uuid_formats
        logger.info(f"Created UUID formats for Telegram ID {telegram_id}: {user_uuid_hex, user_uuid_decimal}")
        
        # Return all formats to allow the API client to try them all
        return uuid_formats
        
    except Exception as e:
        logger.error(f"Error creating user UUID for Telegram ID {telegram_id}: {e}")
        # Fallback to a simple format
        fallback_uuid = f"c7cb5b5c-e469-586e-8e87-{telegram_id}"
        return (fallback_uuid, telegram_id)

async def get_character_memories_from_db(character_id: str, user_id: int = None) -> List[Dict[str, Any]]:
    """
    Directly fetch character memories from the database
    
    Args:
        character_id: ID of the character
        user_id: ID of the user or tuple containing multiple ID formats. If provided, only memories for this user are returned
    """
    try:
        # Pass the user_id tuple/format directly to the API client 
        # which now knows how to handle multiple formats
        memories = api_client.get_character_memories(character_id, user_id, include_all=False)
        
        if isinstance(user_id, tuple):
            display_id = user_id[0]  # Use the first format for logging
        else:
            display_id = user_id
            
        logger.info(f"Retrieved {len(memories)} memories for character {character_id} and user {display_id}")
        return memories
    except Exception as e:
        logger.exception(f"Error fetching memories from database: {e}")
        return []

async def view_memories_handler(message: types.Message, state: FSMContext):
    """Command-based memory handler that calls the same function as the button"""
    await memory_button_handler(message, state)

async def stop_handler(message: types.Message, state: FSMContext):
    await message.answer(
        "Диалог завершен. Чтобы начать новый диалог, используйте /start",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

async def error_handler(update: types.Update, exception: Exception):
    logger.exception(f"Unhandled exception: {exception}")
    
    try:
        if update.message:
            await update.message.answer(
                "Произошла непредвиденная ошибка. Пожалуйста, повторите попытку позже or используйте /start для перезапуска бота."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

async def character_info_handler(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        character = user_data.get("character")
        
        if not character:
            await message.answer("Вы еще не выбрали персонажа. Используйте /start для выбора.")
            return
        
        # Send character avatar if available
        if character.get("avatar_url"):
            # Используем новую функцию для скачивания аватара с несколькими попытками
            data, content_type = await download_avatar(character["avatar_url"], character["id"])
            if data:
                # Успешно скачали аватар
                bio = BytesIO(data)
                bio.name = f"avatar_{character['id']}.png"
                await message.answer_photo(
                    photo=InputFile(bio),
                    caption=character.get("name", "")
                )
            else:
                logger.warning(f"Не удалось загрузить аватар для персонажа {character.get('name')}")

        # Display character info text regardless of avatar success
        info_text = f"🧑‍🤝‍🧑 *{character['name']}*\n\n"
        info_text += f"🎂 Возраст: {character.get('age', 'Неизвестно')} лет\n"
        
        traits = character.get('personality_traits', [])
        if traits:
            info_text += f"💭 Характер: {', '.join(traits)}\n"
            
        interests = character.get('interests', [])
        if interests:
            info_text += f"🔍 Интересы: {', '.join(interests)}\n"
            
        if ("background" in character and character["background"]):
            info_text += f"\n📝 *Биография*:\n{character['background']}"
        
        await message.answer(info_text, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Error in character_info_handler: {e}")
        await message.answer("Произошла ошибка при получении информации о персонаже.")

async def generate_handler(message: types.Message, state: FSMContext):
    try:
        api_available = await health_check()
        
        if not api_available:
            await message.answer("⚠️ API сервер недоступен. Пожалуйста, попробуйте позже.")
            return
        
        await message.answer(
            "Выберите тип персонажа, который хотите создать:\n\n"
            "1. Случайный персонаж\n"
            "2. Девушка с активной жизненной позицией\n"
            "3. Творческая и мечтательная девушка\n"
            "4. Умная и сдержанная девушка\n\n"
            "Отправьте номер варианта or опишите желаемого персонажа своими словами."
        )
        await state.set_state(BotStates.generating_character)
    
    except Exception as e:
        logger.exception(f"Unexpected error in generate_handler: {e}")
        await message.answer(
            "Произошла ошибка при запуске генерации персонажа. Пожалуйста, попробуйте позже."
        )

async def process_character_generation(message: types.Message, state: FSMContext):
    try:
        generation_prompt = message.text
        
        if (generation_prompt.isdigit() and 1 <= int(generation_prompt) <= 4):
            choice = int(generation_prompt)
            if (choice == 1):
                generation_prompt = "random"
            elif (choice == 2):
                generation_prompt = "active girl who loves sports and adventures"
            elif (choice == 3):
                generation_prompt = "creative and dreamy girl who loves art"
            elif (choice == 4):
                generation_prompt = "intelligent and reserved girl who loves science"
        
        await message.answer("⏳ Генерирую персонажа, пожалуйста, подождите...")
        
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/chat/generate-character",
                json={"prompt": generation_prompt},
                headers=headers,
                timeout=30
            ) as response:
                if (response.status != 200):
                    logger.warning(f"API returned status {response.status}")
                    await message.answer("Ошибка при генерации персонажа. Пожалуйста, попробуйте позже.")
                    await state.set_state(BotStates.selecting_character)
                    return
                
                new_character = await response.json()
        
        char_info = (
            f"✨ *Создан новый персонаж* ✨\n\n"
            f"👤 *{new_character['name']}*, {new_character['age']} лет\n\n"
            f"📝 *Биография*: {new_character['background']}\n\n"
            f"💭 *Характер*: {', '.join(new_character['personality_traits'])}\n"
            f"🔍 *Интересы*: {', '.join(new_character['interests'])}\n\n"
            f"Хотите начать общение с этим персонажем? (да/нет)"
        )
        
        await state.update_data(generated_character=new_character)
        
        await message.answer(char_info, parse_mode="Markdown")
        
        await state.set_state(BotStates.confirming_character)
        
    except Exception as e:
        logger.exception(f"Error in process_character_generation: {e}")
        await message.answer("Произошла ошибка при генерации персонажа. Пожалуйста, попробуйте снова: /generate")
        await state.set_state(BotStates.selecting_character)

async def confirm_generated_character(message: types.Message, state: FSMContext):
    try:
        answer = message.text.strip().lower()
        
        if (answer in ["да", "yes", "y", "д", "давай", "конечно"]):
            user_data = await state.get_data()
            selected_character = user_data.get("generated_character")
            
            if not selected_character:
                await message.answer("Информация о персонаже утеряна. Пожалуйста, сгенерируйте персонажа заново: /generate")
                await state.set_state(BotStates.selecting_character)
                return
            
            await state.update_data(
                character=selected_character,
                character_id=selected_character["id"],
                character_name=selected_character["name"]
            )
            
            headers = {"Authorization": f"Bearer {API_KEY}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_BASE_URL}/chat/characters/{selected_character['id']}/start-chat",
                    headers=headers
                ) as response:
                    if (response.status != 200):
                        await message.answer("Ошибка при начале диалога. Пожалуйста, попробуйте позже.")
                        await state.set_state(BotStates.selecting_character)
                        return
                    
                    chat_response = await response.json()
                    
                    messages = chat_response.get("messages", [])
                    first_message = messages[0]["content"] if messages else "Привет! Давай пообщаемся."
                    
                    await message.answer(
                        f"Вы общаетесь с {selected_character['name']}.\n\n"
                        f"{first_message}\n\n"
                        "Отправьте сообщение для ответа or выберите действие.",
                        reply_markup=get_chat_keyboard()
                    )
                    await state.set_state(BotStates.chatting)
                    
        else:
            await message.answer("Вы отказались от общения с этим персонажем. Используйте /start для выбора существующего персонажа or /generate для создания нового.")
            await state.set_state(BotStates.selecting_character)
            
    except Exception as e:
        logger.exception(f"Error in confirm_generated_character: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова: /start")
        await state.set_state(BotStates.selecting_character)

async def menu_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        action = callback_query.data
        
        if (action == "select_character"):
            await callback_query.answer("Выбор персонажа")
            await select_character_menu(callback_query.message, state)
            
        elif (action == "send_gift"):
            await callback_query.answer("Отправка подарка")
            await send_gift_handler(callback_query.message, state)
            
        elif (action == "clear_chat"):
            await callback_query.answer("Очистка чата")
            await clear_chat_handler(callback_query.message, state)
            
        elif (action == "edit_character"):
            await callback_query.answer("Редактирование персонажа")
            await edit_character_handler(callback_query.message, state)
            
        elif (action == "help"):
            await callback_query.answer("Справка")
            await help_handler(callback_query.message)
            
        elif (action == "generate_character"):
            await callback_query.answer("Создание нового персонажа")
            await generate_character_callback(callback_query.message, state)
            
        else:
            if (action.startswith("gift_")):
                await process_gift_selection(callback_query, state)
            elif (action.startswith("confirm_")):
                action_type = action.replace("confirm_", "")
                if (action_type == "gift"):
                    await confirm_gift_handler(callback_query, state)
                elif (action_type == "clear"):
                    await confirm_clear_chat(callback_query, state)
            elif (action == "cancel"):
                await cancel_action(callback_query, state)
    
    except Exception as e:
        logger.exception(f"Error in menu_callback_handler: {e}")
        await callback_query.answer("Произошла ошибка при обработке команды.")

async def generate_character_callback(message: types.Message, state: FSMContext):
    try:
        await message.edit_text(
            "Выберите тип персонажа, который хотите создать:\n\n"
            "1. Случайный персонаж\n"
            "2. Девушка с активной жизненной позицией\n"
            "3. Творческая и мечтательная девушка\n"
            "4. Умная и сдержанная девушка\n\n"
            "Отправьте номер варианта или опишите желаемого персонажа своими словами."
        )
        await state.set_state(BotStates.generating_character)
    except Exception as e:
        logger.exception(f"Error in generate_character_callback: {e}")
        await message.reply(
            "Произошла ошибка при запуске генерации персонажа. Пожалуйста, попробуйте позже."
        )

async def select_character_menu(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    characters = user_data.get("characters", [])
    
    if not characters:
        try:
            headers = {"Authorization": f"Bearer {API_KEY}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{API_BASE_URL}/chat/characters",
                    headers=headers,
                    timeout=10
                ) as response:
                    if (response.status != 200):
                        await message.answer("Не удалось получить список персонажей. Попробуйте позже.")
                        return
                    characters = await response.json()
                    await state.update_data(characters=characters)
        except Exception as e:
            logger.error(f"Error retrieving characters: {e}")
            await message.answer("Ошибка при получении списка персонажей.")
            return
    
    message_text = "👤 Выберите персонажа для общения:\n\n"
    keyboard = []
    
    # Define URL mapping based on environment variable or default value
    url_mapping = {"http://minio:9000": "http://localhost:9000"}
    try:
        # Try to parse MINIO_URL_MAPPING from env if available
        minio_url_mapping = os.getenv("MINIO_URL_MAPPING")
        if (minio_url_mapping):
            import json
            url_mapping = json.loads(minio_url_mapping)
    except Exception as e:
        logger.error(f"Error parsing MINIO_URL_MAPPING: {e}")
    
    # First, send character information with avatars
    for character in characters:
        char_name = character.get("name", "Персонаж")
        char_age = character.get("age", "")
        char_info = f"{char_name} ({char_age} лет)" if char_age else char_name
        
        # Send character avatar if available
        if "avatar_url" in character and character["avatar_url"]:
            # Fetch and send avatar via InputFile to avoid Telegram URL restrictions
            try:
                avatar_url = character["avatar_url"]
                for internal_url, public_url in url_mapping.items():
                    avatar_url = avatar_url.replace(internal_url, public_url)
                logger.info(f"Fetching character avatar: {avatar_url}")
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            bio = BytesIO(data)
                            bio.name = avatar_url.rsplit('/', 1)[-1]
                            await message.answer_photo(photo=InputFile(bio), caption=f"{char_info}\n\nИспользуйте меню ниже, чтобы выбрать персонажа.")
                        else:
                            logger.warning(f"Failed to fetch avatar: HTTP {resp.status}")
            except Exception as e:
                logger.error(f"Error sending character avatar: {e}")
    
    # Now build the keyboard for character selection
    for i in range(0, len(characters), 2):
        row = []
        for j in range(2):
            if (i + j < len(characters)):
                char = characters[i + j]
                btn_text = f"{char['name']} ({char['age']} лет)"
                row.append(InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"char_{char['id']}"
                ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(
        text="✨ Создать нового персонажа",
        callback_data="generate_character"
    )])
    
    keyboard.append([InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="back_to_menu"
    )])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(message_text, reply_markup=markup)
    await state.set_state(BotStates.selecting_character)

async def send_gift_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    character = user_data.get("character")
    
    if not character:
        await message.answer(
            "Сначала нужно выбрать персонажа для общения, чтобы отправить подарок.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    gift_keyboard = []
    for i in range(0, len(AVAILABLE_GIFTS), 2):
        row = []
        for j in range(2):
            if (i + j < len(AVAILABLE_GIFTS)):
                gift = AVAILABLE_GIFTS[i + j]
                btn_text = f"{gift['name']} ({gift['price']} монет)"
                row.append(InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"gift_{gift['id']}"
                ))
        gift_keyboard.append(row)
    
    gift_keyboard.append([InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="back_to_menu"
    )])
    
    markup = InlineKeyboardMarkup(inline_keyboard=gift_keyboard)
    await message.answer(
        f"🎁 Выберите подарок для {character['name']}:\n\n"
        f"Подарки помогают улучшать отношения и повышать настроение персонажа.",
        reply_markup=markup
    )
    await state.set_state(BotStates.sending_gift)

async def process_gift_selection(callback_query: types.CallbackQuery, state: FSMContext):
    gift_id = callback_query.data.replace("gift_", "")
    
    selected_gift = next((g for g in AVAILABLE_GIFTS if g["id"] == gift_id), None)
    if not selected_gift:
        await callback_query.answer("Подарок не найден")
        return
    
    user_data = await state.get_data()
    character = user_data.get("character")
    
    await state.update_data(selected_gift=selected_gift)
    
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_gift"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ])
    
    gift_message = (
        f"🎁 Вы выбрали: {selected_gift['name']}\n"
        f"💰 Стоимость: {selected_gift['price']} монет\n"
        f"❤️ Эффект на отношения: +{selected_gift['effect']} очков\n\n"
        f"Отправить подарок для {character['name']}?"
    )
    
    await callback_query.message.edit_text(gift_message, reply_markup=confirm_keyboard)
    await state.set_state(BotStates.confirming_gift)

async def confirm_gift_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("Отправляем подарок...")
    
    user_data = await state.get_data()
    character = user_data.get("character")
    selected_gift = user_data.get("selected_gift")
    character_id = user_data.get("character_id")
    
    if not character or not selected_gift or not character_id:
        await callback_query.message.edit_text(
            "Ошибка при отправке подарка. Попробуйте выбрать персонажа и подарок заново."
        )
        return
    
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Define our endpoints with their corresponding payload formats
        # Starting with the one we know works based on logs
        endpoints_with_payloads = [
            # Debug endpoint that works - put it first
            {
                "url": f"{API_BASE_URL}/chat/characters/{character_id}/gift-alt",
                "payload": {
                    "gift_id": selected_gift["id"],
                    "name": selected_gift["name"],
                    "effect": selected_gift["effect"],
                }
            },
            # Primary endpoint - full details
            {
                "url": f"{API_BASE_URL}/chat/characters/{character_id}/gift",
                "payload": {
                    "gift_id": selected_gift["id"],
                    "gift_name": selected_gift["name"],
                    "gift_effect": selected_gift["effect"],
                }
            },
            # Alternative endpoint - just gift_id
            {
                "url": f"{API_BASE_URL}/characters/{character_id}/gift",
                "payload": {"gift_id": selected_gift["id"]}
            }
        ]
        
        logger.debug(f"Attempting to send gift: {selected_gift['name']}")
        
        async with aiohttp.ClientSession() as session:
            response = None
            response_data = None
            
            for endpoint_config in endpoints_with_payloads:
                try:
                    url = endpoint_config["url"]
                    payload = endpoint_config["payload"]
                    logger.debug(f"Trying endpoint: {url} with payload: {payload}")
                    
                    async with session.post(
                        url,
                        json=payload,
                        headers=headers
                    ) as resp:
                        if resp.status == 200:
                            response = resp
                            response_data = await resp.json()
                            logger.info(f"Gift sent successfully using {url}")
                            break
                        else:
                            logger.warning(f"Endpoint {url} returned status {resp.status}")
                except Exception as e:
                    logger.error(f"Error with endpoint {url}: {e}")
                    continue
            
            if not response or not response_data:
                await callback_query.message.edit_text(
                    "Не удалось отправить подарок. Сервер недоступен.",
                    reply_markup=get_main_menu_keyboard()
                )
                return
                
            # Check for valid AI reaction
            reaction = response_data.get("reaction", {})
            
            # Process AI reaction
            if isinstance(reaction, dict) and "text" in reaction and reaction["text"].strip():
                reaction_text = reaction["text"]
            elif isinstance(reaction, str) and reaction.strip():
                reaction_text = reaction
            else:
                # No valid reaction - make explicit request for AI reaction
                logger.warning("No valid reaction in response, requesting explicit AI reaction")
                
                # Try to save gift as a memory directly through the chat message endpoint
                # instead of the memory endpoint which is having auth issues
                try:
                    # Use a simpler approach - send a message that tells the AI about the gift
                    chat_endpoint = f"{API_BASE_URL}/chat/characters/{character_id}/message"
                    
                    # Create special gift system message to ensure the AI knows about it
                    gift_context_message = {
                        "message": f"SYSTEM: Пользователь подарил тебе {selected_gift['name']}. Это важное событие, которое нужно запомнить.",
                        "is_system": True  # Mark as system message if API supports it
                    }
                    
                    # Try to send this as a system message first to register the gift
                    try:
                        async with session.post(
                            chat_endpoint,
                            json=gift_context_message,
                            headers=headers
                        ) as sys_resp:
                            if sys_resp.status == 200:
                                logger.info("Successfully sent gift system message")
                    except Exception as e:
                        logger.error(f"Error sending gift system message: {e}")
                    
                    # Now prompt the AI to react to the gift with a more detailed message
                    gift_prompt_message = {
                        "message": f"Я только что подарил(а) тебе {selected_gift['name']}. Как тебе такой подарок? Пожалуйста, опиши свою реакцию."
                    }
                    
                    async with session.post(
                        chat_endpoint,
                        json=gift_prompt_message,
                        headers=headers
                    ) as chat_resp:
                        if chat_resp.status == 200:
                            chat_data = await chat_resp.json()
                            if isinstance(chat_data, dict) and "response" in chat_data and chat_data["response"]:
                                reaction_text = chat_data["response"]
                                logger.info(f"Got explicit AI reaction via chat: {reaction_text[:50]}...")
                            elif isinstance(chat_data, dict) and "messages" in chat_data and chat_data["messages"]:
                                # Try to find AI response in messages array
                                for msg in reversed(chat_data["messages"]):
                                    if msg.get("sender_type") == "ai" and "content" in msg:
                                        reaction_text = msg["content"]
                                        logger.info(f"Found AI reaction in messages: {reaction_text[:50]}...")
                                        break
                            else:
                                # Final fallback to a personalized message with specific gift name
                                reaction_text = f"*смотрит на {selected_gift['name']} с восхищением* Ого! Это... для меня? Большое спасибо, это так неожиданно и приятно!"
                                logger.warning("Using personalized fallback reaction - no valid response format")
                        else:
                            logger.warning(f"Chat endpoint returned status {chat_resp.status}")
                            # Use personalized fallback with specific gift name
                            reaction_text = f"Спасибо за {selected_gift['name']}! Это так мило с твоей стороны."
                except Exception as e:
                    logger.exception(f"Error getting explicit AI reaction: {e}")
                    reaction_text = f"*с улыбкой принимает {selected_gift['name']}* Спасибо большое! Мне очень приятно."
            
            logger.info(f"Final reaction text: {reaction_text[:100]}...")
            
            # Send final response to user with gift confirmation and AI reaction
            await callback_query.message.edit_text(
                f"✨ Подарок успешно отправлен!\n\n"
                f"🎁 {selected_gift['name']}\n"
                f"❤️ +{selected_gift['effect']} к отношениям\n\n"
                f"*Реакция {character['name']}*:\n{reaction_text}",
                parse_mode="Markdown"
            )
            
            # Return to chatting state
            await state.set_state(BotStates.chatting)
    
    except Exception as e:
        logger.exception(f"Error sending gift: {e}")
        await callback_query.message.edit_text(
            "Произошла ошибка при отправке подарка. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )

async def clear_chat_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    character = user_data.get("character")
    
    if not character:
        await message.answer(
            "Сначала нужно выбрать персонажа для общения.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, очистить", callback_data="confirm_clear"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ])
    
    await message.answer(
        f"🗑 Вы уверены, что хотите очистить историю чата с {character['name']}?\n\n"
        "Это действие нельзя отменить.",
        reply_markup=confirm_keyboard
    )

async def confirm_clear_chat(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("Очищаем чат...")
    
    user_data = await state.get_data()
    character_id = user_data.get("character_id")
    character_name = user_data.get("character_name")
    
    if not character_id:
        await callback_query.message.edit_text(
            "Ошибка при очистке чата. Персонаж не выбран.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/chat/characters/{character_id}/clear-history",
                headers=headers
            ) as response:
                if (response.status != 200):
                    await callback_query.message.edit_text(
                        "Не удалось очистить историю чата. Попробуйте позже.",
                        reply_markup=get_main_menu_keyboard()
                    )
                    return
                
                async with session.post(
                    f"{API_BASE_URL}/chat/characters/{character_id}/start-chat",
                    headers=headers
                ) as start_response:
                    if (start_response.status != 200):
                        await callback_query.message.edit_text(
                            "История чата очищена, но не удалось начать новый диалог.",
                            reply_markup=get_main_menu_keyboard()
                        )
                        return
                    
                    chat_response = await start_response.json()
                    
                    messages = chat_response.get("messages", [])
                    first_message = messages[0]["content"] if messages else "Привет! Давай пообщаемся."
                    
                    await callback_query.message.edit_text(
                        f"🗑 История чата с {character_name} очищена!\n\n"
                        f"{character_name}: {first_message}",
                        reply_markup=get_main_menu_keyboard()
                    )
                    
                    await state.set_state(BotStates.chatting)
                    
    except Exception as e:
        logger.exception(f"Error clearing chat: {e}")
        await callback_query.message.edit_text(
            "Произошла ошибка при очистке чата. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )

async def edit_character_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    character = user_data.get("character")
    
    if not character:
        await message.answer(
            "Сначала нужно выбрать персонажа для редактирования.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    edit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 Изменить характер", callback_data="edit_personality")],
        [InlineKeyboardButton(text="🎯 Изменить интересы", callback_data="edit_interests")],
        [InlineKeyboardButton(text="📝 Изменить биографию", callback_data="edit_biography")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")]
    ])
    
    await message.answer(
        f"✏️ Редактирование персонажа: {character['name']}\n\n"
        f"Выберите, что вы хотите изменить:",
        reply_markup=edit_keyboard
    )
    await state.set_state(BotStates.editing_character)

async def help_handler(message: types.Message):
    help_text = (
        "🤖 *AI Simulator - Справка*\n\n"
        "*Основные команды:*\n"
        "/start - Начать общение и выбрать персонажа\n"
        "/stop - Завершить текущий диалог\n"
        "/info - Показать информацию о текущем персонаже\n"
        "/menu - Показать основное меню\n\n"
        
        "*Функции:*\n"
        "• *Выбор персонажа* - Вы можете выбрать персонажа для общения или создать нового\n"
        "• *Подарки* - Отправляйте подарки, чтобы улучшать отношения с персонажем\n"
        "• *Очистка чата* - Очистите историю общения и начните диалог заново\n"
        "• *Редактирование* - Измените характер, интересы или биографию персонажа\n"
        "• *Память* - Узнайте, что бот запомнил о вас\n"
        "• *Сжатие диалога* - Сохраните суть разговора в сжатом виде для продолжения позже\n\n"
        
        "*Отношения:*\n"
        "В процессе общения развиваются отношения с персонажем. На их уровень влияют:\n"
        "• Частота общения\n"
        "• Содержание сообщений\n"
        "• Подарки\n"
        "• События и свидания\n\n"
        
        "По вопросам и предложениям обращайтесь к разработчику."
    )
    
    await message.answer(help_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())

async def cancel_action(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    
    if (current_state in [BotStates.sending_gift.state, BotStates.confirming_gift.state]):
        await callback_query.answer("Отправка подарка отменена")
    elif (current_state == BotStates.editing_character.state):
        await callback_query.answer("Редактирование отменено")
    else:
        await callback_query.answer("Действие отменено")
    
    await callback_query.message.edit_text(
        "Действие отменено. Выберите другое действие:",
        reply_markup=get_main_menu_keyboard()
    )
    
    user_data = await state.get_data()
    if (user_data.get("character_id")):
        await state.set_state(BotStates.chatting)
    else:
        await state.set_state(BotStates.selecting_character)

async def menu_command(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=get_main_menu_keyboard())

async def back_to_menu_handler(callback_query: types.CallbackQuery):
    await callback_query.answer("Возврат в главное меню")
    await callback_query.message.edit_text("Выберите действие:", reply_markup=get_main_menu_keyboard())

async def character_selection_callback(callback_query: types.CallbackQuery, state: FSMContext):
    char_id = callback_query.data.replace("char_", "")
    
    user_data = await state.get_data()
    characters = user_data.get("characters", [])
    
    selected_character = next((c for c in characters if c["id"] == char_id), None)
    
    if not selected_character:
        await callback_query.answer("Персонаж не найден")
        return
    
    await callback_query.answer(f"Выбран персонаж: {selected_character['name']}")
    
    await state.update_data(
        character=selected_character,
        character_id=selected_character["id"],
        character_name=selected_character["name"]
    )
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/chat/characters/{selected_character['id']}/start-chat",
                headers=headers
            ) as response:
                if (response.status != 200):
                    await callback_query.message.edit_text(
                        "Ошибка при начале диалога. Попробуйте выбрать другого персонажа."
                    )
                    return
                
                chat_response = await response.json()
        
        messages = chat_response.get("messages", [])
        first_message = messages[0]["content"] if messages else "Привет! Давай пообщаемся."
        
        await callback_query.message.edit_text(
            f"Вы общаетесь с {selected_character['name']}.\n\n"
            f"{first_message}\n\n"
            "Отправьте сообщение для ответа or выберите действие."
        )
        await callback_query.message.answer(
            "Выберите действие:",
            reply_markup=get_chat_keyboard()
        )
        await state.set_state(BotStates.chatting)
        
    except Exception as e:
        logger.error(f"Error starting chat: {e}")
        await callback_query.message.edit_text(
            "Ошибка при начале диалога. Пожалуйста, попробуйте позже."
        )

async def show_relationship_stats(message: types.Message, state: FSMContext):
    try:
        state_data = await state.get_data()
        character_id = state_data.get("character_id")
        
        if not character_id:
            await message.answer("⚠️ Пожалуйста, сначала выберите персонажа для общения.")
            return
        
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        async with aiohttp.ClientSession() as session:
            relationship_url = f"{API_BASE_URL}/chat/characters/{character_id}/relationship"
            
            try:
                async with session.get(relationship_url, headers=headers) as response:
                    if (response.status == 200):
                        relationship_data = await response.json()
                        
                        rating = relationship_data.get("rating", {})
                        status = relationship_data.get("status", {})
                        emotions = relationship_data.get("emotions", {})
                        
                        friendship = emotions.get("friendship", {})
                        romance = emotions.get("romance", {})
                        trust = emotions.get("trust", {})
                        
                        # Fix the f-string quote issue by using single quotes for the inner strings
                        relationship_info = (
                            f"❤️ *Отношения с {state_data.get('character_name', 'персонажем')}*\n\n"
                            f"*Общая оценка:* {rating.get('value', 0)}% ({rating.get('label', 'Нейтральные')})\n"
                            f"*Статус:* {status.get('emoji', '👋')} {status.get('label', 'Знакомые')})\n"
                            f"*Описание:* {status.get('description', '')}\n\n"
                            f"*Детализация отношений:*\n"
                            f"🤝 Дружба: {friendship.get('percentage', 0)}%\n"
                            f"💖 Романтика: {romance.get('percentage', 0)}%\n"
                            f"🔒 Доверие: {trust.get('percentage', 0)}%\n\n"
                            f"_Улучшайте отношения через общение и подарки_"
                        )
                        
                        await message.answer(relationship_info, parse_mode="Markdown")
                    else:
                        await message.answer("❌ Не удалось получить информацию об отношениях. Попробуйте позже.")
            except aiohttp.ClientError as e:
                await message.answer("❌ Ошибка соединения при запросе отношений. Проверьте подключение к интернету.")
                logger.error(f"Connection error in relationship stats: {e}")
    except Exception as e:
        logger.exception(f"Error in show_relationship_stats: {e}")
        await message.answer("❌ Произошла ошибка при получении статистики отношений.")

async def get_chat_history(character_id: str, user_id: int) -> List[Dict[str, Any]]:
    if not hasattr(get_chat_history, "history"):
        get_chat_history.history = {}
    
    key = f"{user_id}_{character_id}"
    
    return get_chat_history.history.get(key, [])

async def get_character(character_id: str) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/chat/characters"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if (response.status == 200):
                    characters = await response.json()
                    for character in characters:
                        if (character.get("id") == character_id):
                            return character
                    logger.error(f"Character {character_id} not found in the response")
                    return {}
                else:
                    logger.error(f"Failed to get characters: {response.status}")
                    return {}
    except Exception as e:
        logger.exception(f"Error getting character: {e}")
        return {}

async def save_message(sender_id: Any, recipient_id: Any, content: str, sender_type: str,
                       emotion: str = "neutral", relationship_changes: Dict[str, float] = None) -> None:
    if not hasattr(get_chat_history, "history"):
        get_chat_history.history = {}
    
    key = f"{recipient_id if sender_type == 'ai' else sender_id}_{recipient_id if sender_type == 'user' else sender_id}"
    
    if (key not in get_chat_history.history):
        get_chat_history.history[key] = []
    
    get_chat_history.history[key].append({
        "content": content,
        "sender_type": sender_type,
        "emotion": emotion,
        "relationship_changes": relationship_changes or {},
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    if (len(get_chat_history.history[key]) > 50):
        get_chat_history.history[key] = get_chat_history.history[key][-50:]

def clean_text_for_telegram(text: str) -> str:
    text = text.replace('_', '\\_')
    text = text.replace('*', '\\*')
    text = text.replace('`', '\\`')
    text = text.replace('[', '\\[')
    
    text = re.sub(r'(?<!\\)\[([^\]]+)\]\(([^)]+)\)', r'\1: \2', text)
    
    text = re.sub(r'<[^>]+>', '', text)
    
    return text

def format_relationship_changes(changes: Dict[str, float]) -> str:
    if not changes:
        return ""
    
    formatted = []
    for relationship_type, value in changes.items():
        if (abs(value) < 0.001):
            continue
            
        emoji = "⬆️" if value > 0 else "⬇️"
        formatted.append(f"{get_relationship_label(relationship_type)}: {emoji} {abs(value):.2f}")
    
    if not formatted:
        return ""
    
    return "Изменения в отношениях:\n" + "\n".join(formatted)

def get_relationship_label(relationship_type: str) -> str:
    labels = {
        "general": "Общее отношение",
        "friendship": "Дружба",
        "romance": "Романтика",
        "trust": "Доверие"
    }
    return labels.get(relationship_type, relationship_type.capitalize())

async def get_character_memories(character_id):
    """Get memories for a character from the API"""
    try:
        # Ensure the API client uses the correct API key
        api_key = os.getenv("BOT_API_KEY")
        if not api_key:
            logger.warning("No BOT_API_KEY in environment, authentication may fail")
            
        # Create API client with explicit authorization
        headers = {"Authorization": f"Bearer {api_key}"}
        logger.debug(f"Using authorization headers: {headers}")
        
        memories = api_client.get_character_memories(character_id)
        logger.info(f"Retrieved {len(memories)} memories for character {character_id}")
        return memories
    except Exception as e:
        logger.error(f"Failed to get memories from API: {e}")
        return []

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set!")
        return
    
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    is_api_healthy = await health_check()
    if not is_api_healthy:
        logger.warning("API health check failed. Bot will operate with limited functionality.")
    
    dp.message.register(start_handler, Command("start"))
    dp.message.register(help_handler, Command("help"))
    dp.message.register(stop_handler, Command("stop"))
    dp.message.register(menu_command, Command("menu"))
    dp.message.register(view_memories_handler, Command("memory"))
    dp.message.register(chat_handler, StateFilter(BotStates.chatting))
    
    dp.callback_query.register(character_selection_callback, lambda c: c.data.startswith("char_"))
    dp.callback_query.register(back_to_menu_handler, lambda c: c.data == "back_to_menu")
    dp.callback_query.register(process_gift_selection, lambda c: c.data.startswith("gift_"))
    dp.callback_query.register(confirm_gift_handler, lambda c: c.data == "confirm_gift")
    dp.callback_query.register(cancel_action, lambda c: c.data == "cancel")
    dp.callback_query.register(menu_callback_handler, lambda c: c.data in [
        "select_character", "send_gift", "clear_chat", "edit_character", "help", "generate_character"
    ])
    
    logger.info("Starting bot...")
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    logger.info("Starting AI Simulator Telegram Bot")
    if __name__ == "__main__":
        logger.info("Starting AI Simulator Telegram Bot")
        asyncio.run(main())