from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, characters, matches, notifications, users, purchases, subscriptions

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(characters.router, prefix="/characters", tags=["characters"])
api_router.include_router(matches.router, prefix="/matches", tags=["matches"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(purchases.router, prefix="/purchases", tags=["purchases"])
api_router.include_router(subscriptions.router, prefix="/subscription", tags=["subscription"])
