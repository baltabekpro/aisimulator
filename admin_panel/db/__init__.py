"""
Database package for the admin panel.
Exports session management functions for convenience.
"""
from admin_panel.db.session import get_engine, get_session

# Make these functions available when importing the db package
__all__ = ['get_engine', 'get_session']

