# Handle torch import more robustly
try:
    import torch
    # Only try to access library attribute if torch version is new enough
    try:
        if not hasattr(torch, "library") or not hasattr(torch.library, "register_fake"):
            # Create dummy register_fake function if it doesn't exist
            class DummyLibrary:
                @staticmethod
                def register_fake(*args, **kwargs):
                    pass
            
            if not hasattr(torch, "library"):
                torch.library = DummyLibrary()
            else:
                torch.library.register_fake = DummyLibrary.register_fake
    except Exception as e:
        print(f"Error patching torch: {e}")
except ImportError:
    # Create dummy torch module for compatibility
    class DummyLibrary:
        @staticmethod
        def register_fake(*args, **kwargs):
            pass
    
    class DummyTorch:
        def __init__(self):
            self.library = DummyLibrary()
    
    torch = DummyTorch()
    print("PyTorch not available, using dummy implementation")

from datetime import datetime
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Add missing imports
from app.config import settings
# Also import core.config settings to ensure both are available
from core.config import settings as core_settings
from app.api.v1 import auth, chat, debug, interactions

# Explicitly load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Explicitly log environment variables for debugging
logger.info(f"API BASE URL: {os.environ.get('API_BASE_URL')}")
logger.info(f"DATABASE URL: {os.environ.get('DATABASE_URL')}")
openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
if openrouter_key:
    masked_key = openrouter_key[:4] + "..." + openrouter_key[-4:] if len(openrouter_key) > 8 else "***masked***"
    logger.info(f"OpenRouter API key found in environment: {masked_key}")
else:
    logger.error("OpenRouter API key not found in environment variables!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events using modern lifespan API"""
    # Initialize database
    try:
        # Import here to avoid circular imports
        from core.db.init_db import init_db, create_test_data
        logger.info("Checking database schema...")
        
        # Skip the schema fix function which has the UUID import issue
        logger.info("Database schema check skipped - will rely on SQLAlchemy's create_all")
        
        # Then initialize database tables
        try:
            init_db()
            logger.info("Database tables initialized")
        except Exception as init_error:
            logger.error(f"Error initializing database tables: {init_error}")
        
        # Create test data for development
        if settings.debug:
            try:
                logger.info("Creating test data for development...")
                create_test_data()
            except Exception as test_data_error:
                logger.error(f"Error creating test data: {test_data_error}")
    except Exception as e:
        logger.error(f"Error during database initialization process: {e}")
    
    # Startup: Check if OpenRouter API key is configured properly
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.error("ERROR: No OpenRouter API key found. AI responses will not work.")
        logger.error("Please set OPENROUTER_API_KEY in your .env file or environment variables.")
    else:
        # Log success but mask the key for security
        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
        logger.info(f"OpenRouter API key configured: {masked_key}")
        
        # Test the API key by making a simple request
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3-opus:beta"),
                "messages": [{"role": "user", "content": "Hello"}]
            }
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            if response.status_code == 200:
                logger.info("✅ OpenRouter API key verified successfully!")
                # Store the working API key in the settings (use the already imported core_settings)
                core_settings.OPENROUTER_API_KEY = api_key
                core_settings.OPENROUTER_WORKING = True
            else:
                logger.error(f"❌ OpenRouter API test failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"❌ Error testing OpenRouter API: {e}")
    
    # Use the proper settings reference that we imported at the module level
    logger.info(f"Using OpenRouter model: {core_settings.OPENROUTER_MODEL}")
    
    # Add additional startup verifications if needed
    if settings.DATABASE_URL:
        logger.info(f"Using database: {settings.DATABASE_URL}")
    else:
        logger.warning("No database URL configured, using default SQLite")
    
    logger.info("All services initialized. API is ready!")
    
    yield  # This is where the app runs
    
    # Cleanup code (if any) goes here
    logger.info("Shutting down...")

# Create FastAPI instance with lifespan handler
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API для взаимодействия с AI персонажами",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
    debug=True  # Enable debug mode
)

# Настраиваем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене нужно ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["auth"]
)

app.include_router(
    chat.router,
    prefix=f"{settings.API_V1_PREFIX}/chat",
    tags=["chat"]
)

# Add the new interactions router
app.include_router(
    interactions.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["interactions"]
)

# Fix for debug router - make sure it's being included unconditionally or based on debug setting
if settings.debug:
    app.include_router(
        debug.router,
        prefix=f"{settings.API_V1_PREFIX}/debug",
        tags=["debug"]
    )
else:
    # If not in debug mode but we want the debug routes anyway, enable them
    app.include_router(
        debug.router, 
        prefix=f"{settings.API_V1_PREFIX}/debug",
        tags=["debug"]
    )

# Add a diagnostic endpoint to verify router registration
@app.get("/router-info")
def router_info():
    """Debug endpoint to show registered routers"""
    # Extract info from the FastAPI app route registry
    routes = [
        {
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods) if hasattr(route, "methods") else [],
            "tags": getattr(route, "tags", []),
        }
        for route in app.routes
    ]
    
    # Sort by path for easier reading
    routes.sort(key=lambda x: x["path"])
    
    # Group routes by their first path segment
    grouped_routes = {}
    for route in routes:
        path = route["path"]
        segments = path.split("/")
        if len(segments) > 1:
            prefix = segments[1]  # First non-empty segment
            if prefix not in grouped_routes:
                grouped_routes[prefix] = []
            grouped_routes[prefix].append(route)
    
    return {
        "total_routes": len(app.routes),
        "grouped_routes": grouped_routes
    }

# Add a direct debug endpoint to verify routing
@app.post(f"{settings.API_V1_PREFIX}/chat/characters/{{character_id}}/gift-debug")
def gift_debug(character_id: str):
    """Debug endpoint to check gift routing"""
    return {"message": "Gift debug endpoint works", "character_id": character_id}

# Add routes for debugging various problematic endpoints
@app.get("/debug-routes")
def debug_routes():
    """List all registered routes for detailed debugging"""
    route_info = []
    for route in app.routes:
        methods = list(route.methods) if hasattr(route, "methods") else ["GET"]
        route_info.append({
            "path": route.path,
            "name": route.name,
            "methods": methods,
            "endpoint": f"{route.endpoint.__module__}.{route.endpoint.__name__}" if hasattr(route, "endpoint") else "Unknown"
        })
    
    # Sort routes by path for easier reading
    route_info.sort(key=lambda x: x["path"])
    return {"routes": route_info}

# Add direct test endpoints for gift functionality
@app.post("/api/v1/chat/characters/{character_id}/gift-alt")
def gift_alt(character_id: str, gift_id: str = "test_gift"):
    """Secondary test endpoint for gift functionality"""
    return {
        "message": "Alternative gift endpoint works",
        "character_id": character_id,
        "gift_id": gift_id
    }

@app.get("/")
def root():
    """
    Корневой эндпоинт
    """
    return {"message": "API online", "docs": "/docs"}

@app.get("/health")
def health_check():
    """
    Эндпоинт для проверки здоровья приложения
    """
    return {"status": "ok"}

# Add API v1 health endpoint to match what the Telegram bot expects
@app.get(f"{settings.API_V1_PREFIX}/health")
def api_health_check():
    """
    API v1 эндпоинт для проверки здоровья приложения
    """
    return {"status": "ok"}

@app.post("/api/generate-character")
def generate_character():
    """
    Generate a random character
    """
    return {
        "id": "random-id-123",
        "name": "Алиса",
        "age": 25,
        "gender": "female",
        "personality_traits": ["friendly", "curious", "creative"],
        "interests": ["reading", "art", "technology"],
        "fetishes": [],
        "background": "Я выросла в маленьком городке и всегда мечтала о больших приключениях.",
        "height": 170,
        "weight": 58,
        "hair_color": "brown",
        "eye_color": "green",
        "body_type": "athletic",
        "photos": ["https://example.com/photos/alice1.jpg"],
        "current_emotion": {
            "name": "happy",
            "intensity": 0.8,
            "timestamp": datetime.utcnow()
        }
    }

@app.get("/api-routes")
def list_routes():
    """List all registered routes for debugging"""
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods) if hasattr(route, "methods") else []
        })
    return {"routes": routes}

# Add a diagnostic endpoint to check if the app is accessible
@app.get("/api-status")
def api_status():
    """
    Simple endpoint to check if the API is running
    """
    return {
        "status": "running",
        "version": "1.0.0",
        "api_prefix": settings.API_V1_PREFIX
    }

# Add a more comprehensive debug endpoint
@app.get("/chat-debug")
def chat_debug():
    """Debug endpoint for chat routes"""
    import inspect
    import api.v1.endpoints.chat
    
    # Get all functions from the chat module
    funcs = inspect.getmembers(api.v1.endpoints.chat, inspect.isfunction)
    
    # Extract routes from the router
    routes = []
    for route in api.v1.endpoints.chat.router.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods) if hasattr(route, "methods") else []
        })
    
    return {
        "functions": [f[0] for f in funcs],
        "routes": routes,
        "module_path": api.v1.endpoints.chat.__file__
    }

# Add a direct test endpoint for characters to verify routing works
@app.get(f"{settings.API_V1_PREFIX}/chat-characters-test")
def characters_test():
    """Debug endpoint to test chat/characters routing"""
    return {
        "message": "Chat characters test endpoint works",
        "characters": [
            {"id": "test-1", "name": "Test Character 1"},
            {"id": "test-2", "name": "Test Character 2"},
        ]
    }

@app.get("/database-info")
def database_info():
    """Debug endpoint to display database information"""
    from sqlalchemy import inspect
    from core.db.session import engine
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    table_data = {}
    for table in tables:
        columns = [col["name"] for col in inspector.get_columns(table)]
        row_count = None
        
        # Try to get row count
        try:
            from sqlalchemy import text
            with engine.connect() as connection:
                result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                row_count = result.scalar()
        except Exception as e:
            row_count = f"Error counting rows: {str(e)}"
        
        table_data[table] = {
            "columns": columns,
            "row_count": row_count
        }
    
    return {
        "tables": tables,
        "table_details": table_data
    }

# Add a diagnostic endpoint for API key testing
@app.get("/api/v1/debug/openrouter-key-status")
def openrouter_key_status():
    """Debug endpoint to check OpenRouter API key configuration"""
    api_key = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")
    is_configured = bool(api_key)
    is_working = getattr(settings, "OPENROUTER_WORKING", False)
    
    if is_configured:
        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
    else:
        masked_key = None
    
    return {
        "is_configured": is_configured,
        "is_working": is_working,
        "masked_key": masked_key,
        "model": settings.OPENROUTER_MODEL,
        "note": "If 'is_configured' is true but 'is_working' is false, there may be an issue with the API key or model."
    }

import os
import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)

def check_database():
    """Check if database is properly initialized"""
    try:
        # Simple query to check if database is accessible
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            
            # Check if users table has data
            result = connection.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            logger.info(f"Found {user_count} users in database")
            
            # Check if characters table has data
            result = connection.execute(text("SELECT COUNT(*) FROM characters"))
            character_count = result.scalar()
            logger.info(f"Found {character_count} characters in database")
            
            return True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False

# Call this function during startup
database_ok = check_database()
if not database_ok:
    logger.error("Database check failed - service may not function properly")
else:
    logger.info("Database check passed - service is ready")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting API server")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
