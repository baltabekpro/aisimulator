# Import all routers
from admin_panel.routes import (
    auth,
    dashboard,
    users,
    characters,
    messages,
    settings,
    memories
)

# Include all routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(characters.router)
app.include_router(messages.router)
app.include_router(settings.router)
app.include_router(memories.router)