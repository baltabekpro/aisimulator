"""
Helper functions for working with UUIDs in database queries.
"""
from uuid import UUID
from sqlalchemy import text

def safe_uuid_query(session, sql_query, params=None):
    """
    Execute a query with UUID parameters safely by using text casting.
    
    Args:
        session: SQLAlchemy session
        sql_query: SQL query string 
        params: Query parameters
        
    Returns:
        Query result
    """
    # Convert UUID objects to strings in parameters
    if params:
        safe_params = {}
        for key, value in params.items():
            if isinstance(value, UUID):
                safe_params[key] = str(value)
            else:
                safe_params[key] = value
    else:
        safe_params = params
        
    # Execute the query
    return session.execute(text(sql_query), safe_params)

def fix_uuid_comparison(query):
    """
    Add explicit text casting to UUID comparisons in a query.
    
    Args:
        query: SQL query string
        
    Returns:
        Modified query with proper text casting
    """
    # Common UUID column names
    uuid_columns = ["id", "user_id", "character_id", "sender_id", "recipient_id"]
    
    # Add explicit casting to each column
    fixed_query = query
    for column in uuid_columns:
        # Replace simple equality conditions
        fixed_query = fixed_query.replace(
            f"{column} = :", 
            f"{column}::text = :"
        )
        # Replace JOIN conditions
        fixed_query = fixed_query.replace(
            f"ON {column} = ", 
            f"ON {column}::text = "
        )
        # Replace IN conditions
        fixed_query = fixed_query.replace(
            f"{column} IN (", 
            f"{column}::text IN ("
        )
    
    return fixed_query
