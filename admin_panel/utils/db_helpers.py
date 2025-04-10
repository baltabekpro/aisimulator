from sqlalchemy import text
import uuid
from typing import Dict, Any, Optional, List, Tuple, Union

def fix_case_statement_query(query_str: str) -> str:
    """
    Исправляет SQL запрос с CASE выражениями, 
    добавляя явное приведение типов для UUID
    """
    # Заменяем все ELSE m.sender_id на ELSE m.sender_id::text
    query_str = query_str.replace("ELSE m.sender_id ", "ELSE m.sender_id::text ")
    query_str = query_str.replace("ELSE m.recipient_id ", "ELSE m.recipient_id::text ")
    
    return query_str

def safe_execute_query(db, query_str: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Безопасное выполнение SQL запроса с обработкой ошибок
    и исправлением типов данных
    """
    try:
        fixed_query = fix_case_statement_query(query_str)
        result = db.execute(text(fixed_query), params or {})
        return [dict(row) for row in result]
    except Exception as e:
        print(f"Ошибка выполнения SQL запроса: {e}")
        return []

def ensure_uuid(value: Union[str, uuid.UUID, int]) -> str:
    """
    Убедиться, что значение является строковым представлением UUID
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    
    if isinstance(value, int):
        return f"c7cb5b5c-e469-586e-8e87-{value:012d}"
    
    if isinstance(value, str):
        try:
            # Проверяем, является ли это корректным UUID
            uuid_obj = uuid.UUID(value)
            return str(uuid_obj)
        except ValueError:
            try:
                # Пробуем интерпретировать как число
                int_val = int(value)
                return ensure_uuid(int_val)
            except ValueError:
                # Генерируем новый UUID если ничего не подошло
                return str(uuid.uuid4())
    
    # Если ничего не подходит, просто генерируем новый UUID
    return str(uuid.uuid4())
