import datetime
import os

def utility_processor():
    """
    Предоставляет утилитарные функции для шаблонов
    """
    return {
        'hasattr': hasattr,
        'getattr': getattr,
        'isinstance': isinstance,
        'str': str,
        'len': len,
        'current_year': datetime.datetime.now().year,
        'app_version': os.getenv('APP_VERSION', '1.0.0'),
        'is_admin': lambda user: user and hasattr(user, 'is_admin') and user.is_admin,
        'debug_mode': os.getenv('DEBUG', 'False').lower() == 'true'
    }
