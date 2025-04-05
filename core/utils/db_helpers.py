"""
Database helper utilities.

This module provides helper functions for working with the database.
"""
import logging
from sqlalchemy import text, inspect
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

def ensure_string_id(id_value):
    """
    Convert any ID value (UUID, int, etc.) to a string.
    
    Args:
        id_value: The ID value to convert
        
    Returns:
        str: The string representation of the ID
    """
    if id_value is None:
        return None
    
    if isinstance(id_value, UUID):
        return str(id_value)
    
    return str(id_value)

def reset_db_connection(db_session):
    """
    Reset a database session that might be in a failed state.
    
    Args:
        db_session: SQLAlchemy session to reset
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Try to rollback any pending transaction
        db_session.rollback()
        return True
    except Exception as e:
        logger.error(f"Error resetting database connection: {e}")
        
        # Try to close and create a new session
        try:
            db_session.close()
            return True
        except:
            return False

def execute_safe_query(db_session, query, params=None):
    """
    Execute a query with proper error handling.
    
    Args:
        db_session: SQLAlchemy session
        query: SQL query string
        params: Query parameters
        
    Returns:
        Result object or None if error
    """
    try:
        # Reset connection if needed
        reset_db_connection(db_session)
        
        # Execute query
        if params:
            result = db_session.execute(text(query), params)
        else:
            result = db_session.execute(text(query))
            
        return result
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return None

def check_model_table_alignment(db_session, model_class):
    """
    Check if a model's columns match its database table.
    
    Args:
        db_session: SQLAlchemy session
        model_class: SQLAlchemy model class to check
        
    Returns:
        dict: Alignment status information
    """
    try:
        # Get table name from model
        table_name = model_class.__tablename__
        
        # Reset any failed transaction first
        reset_failed_transaction(db_session)
        
        # Get model columns
        model_columns = [column.name for column in model_class.__table__.columns]
        
        # Get database table columns - use safer query execution
        if 'postgresql' in str(db_session.bind.url).lower():
            result = execute_safe_query(db_session, 
                "SELECT column_name FROM information_schema.columns WHERE table_name = :table_name",
                {"table_name": table_name})
            db_columns = [row[0] for row in result] if result else []
        else:
            result = execute_safe_query(db_session, f"PRAGMA table_info({table_name})")
            db_columns = [row[1] for row in result] if result else []
        
        # Check for mismatches
        model_only = set(model_columns) - set(db_columns)
        db_only = set(db_columns) - set(model_columns)
        
        # Check for type mismatches in PostgreSQL
        type_mismatches = []
        if 'postgresql' in str(db_session.bind.url).lower():
            for col in model_columns:
                if col in db_columns:
                    try:
                        model_type = str(model_class.__table__.columns[col].type)
                        result = execute_safe_query(db_session,
                            "SELECT data_type FROM information_schema.columns WHERE table_name = :table_name AND column_name = :column_name",
                            {"table_name": table_name, "column_name": col})
                        db_type = result.scalar() if result else None
                        
                        # Compare types (basic comparison)
                        if db_type and not is_compatible_type(model_type, db_type):
                            type_mismatches.append({
                                "column": col,
                                "model_type": model_type,
                                "db_type": db_type
                            })
                    except Exception as e:
                        logger.error(f"Error comparing types for column {col}: {e}")
        
        return {
            "table_name": table_name,
            "aligned": len(model_only) == 0 and len(db_only) == 0 and len(type_mismatches) == 0,
            "model_columns": model_columns,
            "db_columns": db_columns,
            "model_only": list(model_only),
            "db_only": list(db_only),
            "type_mismatches": type_mismatches
        }
    except Exception as e:
        logger.error(f"Error checking model-table alignment for {model_class.__name__}: {e}")
        return {
            "aligned": False,
            "error": str(e)
        }

def is_compatible_type(model_type, db_type):
    """Check if model type is compatible with database type"""
    # Normalize types for comparison
    model_type = model_type.lower()
    db_type = db_type.lower()
    
    # Common compatible types
    compatible_pairs = [
        # String types
        ('varchar', 'character varying'),
        ('string', 'character varying'),
        ('text', 'character varying'),
        # Integer types
        ('integer', 'int'),
        ('bigint', 'int'),
        ('smallint', 'int'),
        # Boolean types
        ('boolean', 'bool'),
        # UUID types
        ('uuid', 'character varying'),
        ('uuid', 'varchar'),
        # JSON types
        ('json', 'text'),
        ('jsonb', 'text'),
        # Date/time types
        ('timestamp', 'timestamp without time zone'),
        ('timestamp', 'timestamp with time zone'),
        ('datetime', 'timestamp without time zone'),
        ('datetime', 'timestamp with time zone'),
    ]
    
    # Direct match
    if model_type == db_type:
        return True
        
    # Check compatible pairs
    for m_type, d_type in compatible_pairs:
        if (m_type in model_type and d_type in db_type) or (d_type in model_type and m_type in db_type):
            return True
    
    # For UUID fields, treat character varying as compatible
    if 'uuid' in model_type and ('varchar' in db_type or 'character varying' in db_type):
        return True
    
    # For JSON fields, treat text as compatible
    if ('json' in model_type or 'jsonb' in model_type) and 'text' in db_type:
        return True
    
    return False

def save_message_safely(db_session, message_data):
    """
    Save a message to the database, handling missing columns gracefully
    """
    try:
        # Get existing columns
        if 'postgresql' in str(db_session.bind.url).lower():
            result = db_session.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='messages'"
            ))
            existing_columns = [row[0] for row in result]
        else:
            result = db_session.execute(text("PRAGMA table_info(messages)"))
            existing_columns = [row[1] for row in result]
        
        # Filter to include only columns that exist in the database
        filtered_data = {}
        for key, value in message_data.items():
            # Handle timestamp vs created_at mapping
            if key == 'timestamp' and 'created_at' in existing_columns:
                filtered_data['created_at'] = value
            elif key in existing_columns:
                filtered_data[key] = value
        
        # Ensure we have an ID
        if 'id' not in filtered_data and 'id' in existing_columns:
            filtered_data['id'] = str(uuid4())
        
        # Skip null values for updated_at
        if 'updated_at' in filtered_data and filtered_data['updated_at'] is None:
            filtered_data.pop('updated_at')
        
        # Build SQL insert
        column_names = ", ".join(filtered_data.keys())
        placeholders = ", ".join([f":{key}" for key in filtered_data.keys()])
        
        query = f"INSERT INTO messages ({column_names}) VALUES ({placeholders})"
        db_session.execute(text(query), filtered_data)
        db_session.commit()
        
        return True
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        try:
            db_session.rollback()
        except:
            pass
        return False

def update_message_safely(db_session, message_id, update_data):
    """
    Update a message in the database, handling missing columns gracefully.
    
    Args:
        db_session: SQLAlchemy session
        message_id: ID of the message to update
        update_data: Dictionary with data to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the actual columns in the messages table
        if 'postgresql' in str(db_session.bind.url).lower():
            result = db_session.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='messages'"
            ))
            existing_columns = [row[0] for row in result]
        else:
            result = db_session.execute(text("PRAGMA table_info(messages)"))
            existing_columns = [row[1] for row in result]
        
        # Filter update_data to only include columns that exist in the table
        filtered_data = {}
        for key, value in update_data.items():
            if key in existing_columns:
                filtered_data[key] = value
        
        # Check if we have any data to update
        if not filtered_data:
            logger.error("No valid columns to update")
            return False
        
        # Build the SET part of the SQL query
        set_clause = ", ".join([f"{key} = :{key}" for key in filtered_data.keys()])
        
        # Add message_id to the parameters
        filtered_data['id'] = message_id
        
        query = f"UPDATE messages SET {set_clause} WHERE id = :id"
        db_session.execute(text(query), filtered_data)
        db_session.commit()
        
        logger.info(f"✅ Message {message_id} updated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating message: {e}")
        try:
            db_session.rollback()
        except:
            pass
        return False

def find_message_by_id_safely(db_session, sender_id=None, recipient_id=None, limit=1):
    """
    Find messages by sender or recipient ID, handling type mismatches safely
    """
    try:
        # Convert IDs to strings
        sender_id_str = ensure_string_id(sender_id) if sender_id else None
        recipient_id_str = ensure_string_id(recipient_id) if recipient_id else None
        
        # Use direct SQL with proper type casting for PostgreSQL
        if 'postgresql' in str(db_session.bind.url).lower():
            # Build the WHERE clause with safe CAST
            where_clause = []
            params = {}
            
            if sender_id_str:
                where_clause.append("sender_id::text = :sender_id")
                params['sender_id'] = sender_id_str
                
            if recipient_id_str:
                where_clause.append("recipient_id::text = :recipient_id")
                params['recipient_id'] = recipient_id_str
                
            if not where_clause:
                return None
                
            # Build the complete query with explicit type casting
            where_sql = " OR ".join(where_clause)
            query = f"""
            SELECT * FROM messages 
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit
            """
            
            params['limit'] = limit
            result = db_session.execute(text(query), params)
        else:
            # For SQLite, direct comparison should work
            where_clause = []
            params = {}
            
            if sender_id_str:
                where_clause.append("sender_id = :sender_id")
                params['sender_id'] = sender_id_str
                
            if recipient_id_str:
                where_clause.append("recipient_id = :recipient_id")
                params['recipient_id'] = recipient_id_str
                
            if not where_clause:
                return None
                
            where_sql = " OR ".join(where_clause)
            query = f"""
            SELECT * FROM messages 
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit
            """
            
            params['limit'] = limit
            result = db_session.execute(text(query), params)
            
        return result.fetchall()
    except Exception as e:
        logger.error(f"❌ Error finding messages: {e}")
        return None

def get_recent_messages(db_session, limit=10):
    """
    Get recent messages using raw SQL to avoid ORM mapping issues
    """
    try:
        # Use created_at instead of timestamp
        result = db_session.execute(text(
            """
            SELECT * FROM messages 
            ORDER BY created_at DESC 
            LIMIT :limit
            """
        ), {"limit": limit})
        return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error fetching recent messages: {e}")
        return []

def reset_db_connection(db_session):
    """
    Reset a database connection that might be in a failed transaction state.
    This is useful when a previous transaction has failed and subsequent
    operations are failing with "current transaction is aborted" errors.
    """
    try:
        # Close the current session
        db_session.close()
        
        # For PostgreSQL, directly roll back any active transaction
        if 'postgresql' in str(db_session.bind.url).lower():
            with db_session.bind.connect() as connection:
                connection.execute(text("ROLLBACK"))
                logger.info("Successfully reset PostgreSQL transaction")
        
        return True
    except Exception as e:
        logger.error(f"Error resetting database connection: {e}")
        return False

def safe_memory_entries_count(db_session):
    """
    Safely count memory entries using raw SQL
    """
    try:
        # First try to reset any failed transaction
        reset_db_connection(db_session)
        
        # Use a new connection to execute the count
        with db_session.bind.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) FROM memory_entries"))
            return result.scalar()
    except Exception as e:
        logger.error(f"Error counting memory entries: {e}")
        return 0

def get_recent_memory_entries(db_session, limit=10):
    """
    Get recent memory entries using raw SQL to avoid ORM issues
    """
    try:
        # Reset any failed transaction first
        reset_db_connection(db_session)
        
        # Use a new connection to execute the query
        with db_session.bind.connect() as connection:
            result = connection.execute(
                text("""
                SELECT * FROM memory_entries 
                ORDER BY created_at DESC 
                LIMIT :limit
                """),
                {"limit": limit}
            )
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error fetching recent memory entries: {e}")
        return []

def execute_safe_query(db_session, query, params=None):
    """
    Execute a query safely, with transaction recovery
    
    Args:
        db_session: SQLAlchemy session
        query: SQL query string
        params: Parameters for the query
        
    Returns:
        Query result or None if failed
    """
    try:
        # Try to reset any failed transaction first
        reset_db_connection(db_session)
        
        # Use a fresh connection to execute the query
        with db_session.bind.connect() as connection:
            if params:
                result = connection.execute(text(query), params)
            else:
                result = connection.execute(text(query))
            
            return result
    except Exception as e:
        logger.error(f"Error executing safe query: {e}")
        return None

def reset_failed_transaction(db_session):
    """Reset a database session that's in a failed transaction state"""
    try:
        # Close the current session
        db_session.close()
        
        # For PostgreSQL, create a new connection and execute a rollback
        if hasattr(db_session, 'bind') and 'postgresql' in str(db_session.bind.url).lower():
            with db_session.bind.connect() as conn:
                conn.execute(text("ROLLBACK"))
                logger.info("Successfully reset PostgreSQL transaction")
                
        return True
    except Exception as e:
        logger.error(f"Error resetting transaction: {e}")
        return False

def execute_with_retry(db_session, func, max_retries=3):
    """Execute a database function with automatic retry on transaction failures"""
    for attempt in range(max_retries):
        try:
            result = func()
            return result
        except Exception as e:
            if 'InFailedSqlTransaction' in str(e) and attempt < max_retries - 1:
                logger.warning(f"Transaction failed, resetting and retrying ({attempt+1}/{max_retries})")
                reset_failed_transaction(db_session)
                continue
            raise

def fix_uuid_comparison_in_query(db_session, query, params):
    """
    Modify a query to handle UUID comparisons correctly in PostgreSQL
    
    Args:
        db_session: SQLAlchemy session
        query: SQL query string
        params: Parameters dict
        
    Returns:
        tuple: (modified_query, modified_params)
    """
    # Only needed for PostgreSQL
    if not ('postgresql' in str(db_session.bind.url).lower()):
        return query, params
        
    # Look for parameters that might be UUIDs
    modified_params = params.copy() if params else {}
    modified_query = query
    
    # Check if the query contains any UUID comparisons
    uuid_columns = ["sender_id", "recipient_id", "character_id", "user_id", "id"]
    
    for col in uuid_columns:
        # Replace direct comparisons with text casts
        modified_query = modified_query.replace(
            f"{col} = :{col}", 
            f"{col}::text = :{col}"
        )
        
        # Also handle JOIN conditions
        modified_query = modified_query.replace(
            f"ON {col} = ", 
            f"ON {col}::text = "
        )
    
    return modified_query, modified_params

def execute_safe_uuid_query(db_session, query, params=None):
    """
    Execute a query with proper UUID handling for PostgreSQL
    
    Args:
        db_session: SQLAlchemy session
        query: SQL query string
        params: Parameters dict
        
    Returns:
        result: Query result or None if failed
    """
    # Fix the query for UUID comparisons
    safe_query, safe_params = fix_uuid_comparison_in_query(db_session, query, params)
    
    try:
        # First try to reset any failed transaction
        reset_db_connection(db_session)
        
        # Use a fresh connection to execute the query
        with db_session.bind.connect() as connection:
            if safe_params:
                result = connection.execute(text(safe_query), safe_params)
            else:
                result = connection.execute(text(safe_query))
            
            return result
    except Exception as e:
        logger.error(f"Error executing safe UUID query: {e}")
        return None