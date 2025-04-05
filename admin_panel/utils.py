import logging
from sqlalchemy import text
from core.utils.db_helpers import (
    reset_db_connection, 
    safe_count_query, 
    get_recent_messages,
    execute_safe_query
)
from core.db.session import get_db_session

logger = logging.getLogger(__name__)

def get_safe_dashboard_stats(db_session):
    """
    Get dashboard statistics safely using direct SQL queries
    instead of ORM to avoid column mismatches
    """
    try:
        stats = {
            'users': safe_count_query(db_session, 'users'),
            'characters': safe_count_query(db_session, 'characters'),
            'messages': safe_count_query(db_session, 'messages'),
            'memory_entries': safe_count_query(db_session, 'memory_entries')
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {
            'users': 0,
            'characters': 0,
            'messages': 0,
            'memory_entries': 0
        }

def get_recent_database_items(db_session):
    """Get recent items from database tables using direct SQL"""
    results = {}
    
    # Reset any failed transaction
    reset_db_connection(db_session)
    
    # Get recent messages
    try:
        # Use created_at instead of timestamp
        message_query = """
        SELECT id, sender_id, sender_type, recipient_id, recipient_type, 
               content, emotion, created_at 
        FROM messages 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        result = execute_safe_query(db_session, message_query)
        if result:
            results['recent_messages'] = [dict(row) for row in result]
        else:
            results['recent_messages'] = []
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        results['recent_messages'] = []
        
    # Get recent users
    try:
        user_query = """
        SELECT user_id, username, email, name, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 5
        """
        result = execute_safe_query(db_session, user_query)
        if result:
            results['recent_users'] = [dict(row) for row in result]
        else:
            results['recent_users'] = []
    except Exception as e:
        logger.error(f"Error getting recent users: {e}")
        results['recent_users'] = []
        
    # Get recent characters
    try:
        char_query = """
        SELECT id, name, gender, created_at
        FROM characters
        ORDER BY created_at DESC
        LIMIT 5
        """
        result = execute_safe_query(db_session, char_query)
        if result:
            results['recent_characters'] = [dict(row) for row in result]
        else:
            results['recent_characters'] = []
    except Exception as e:
        logger.error(f"Error getting recent characters: {e}")
        results['recent_characters'] = []
    
    return results
