from fastapi import APIRouter
from api.v1.endpoints import auth, chat, users, health

api_router = APIRouter()

# Include the various endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
# Fix: explicitly set the prefix for the chat router to match expected routes
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
