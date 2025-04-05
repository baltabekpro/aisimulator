"""
Script to fix the events table by ensuring data is properly stored.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
import json

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def execute_with_reset(conn, sql, params=None, description=None):
    """Execute a query with auto-reset on failure"""
    try:
        if description:
            logger.info(f"Executing: {description}")
        if params:
            return conn.execute(text(sql), params)
        else:
            return conn.execute(text(sql))
    except Exception as e:
        logger.warning(f"Error executing SQL: {e}")
        # Try to reset and continue
        try:
            conn.execute(text("ROLLBACK"))
            logger.info("Rolled back transaction after error")
            return None
        except:
            logger.warning("Could not rollback transaction")
            return None

def fix_events_table():
    """Fix the events table data format"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database: {db_url}")
    engine = create_engine(db_url)
    
    # Check if events table exists
    with engine.connect() as conn:
        events_exists = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events')"
        )).scalar()
        
        if not events_exists:
            logger.warning("Events table does not exist, nothing to fix")
            return True
        
        # Get events table columns
        columns = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'events'"
        )).fetchall()
        
        column_types = {col[0]: col[1] for col in columns}
        logger.info(f"Events table columns: {column_types}")
    
    # Operation 1: Create JSONB index - in a separate transaction
    if 'postgresql' in db_url.lower() and 'data' in column_types:
        with engine.connect() as conn:
            with conn.begin():
                try:
                    # Create a function to safely check if string is valid JSON - marked as IMMUTABLE
                    conn.execute(text("""
                        CREATE OR REPLACE FUNCTION is_valid_json(txt TEXT) 
                        RETURNS BOOLEAN 
                        LANGUAGE plpgsql IMMUTABLE AS $$
                        BEGIN
                            RETURN (txt ~ '^\\s*[\\{\\[].*[\\}\\]]\\s*$');
                            EXCEPTION WHEN OTHERS THEN
                                RETURN FALSE;
                        END;
                        $$;
                    """))
                    logger.info("Created is_valid_json function with IMMUTABLE flag")
                    
                    # Try to create an expression index for faster JSON operations
                    try:
                        conn.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_events_data_json
                            ON events (data)
                            WHERE is_valid_json(data);
                        """))
                        logger.info("Created index for JSON data")
                    except Exception as idx_err:
                        logger.warning(f"Could not create JSON index: {idx_err}")
                except Exception as e:
                    logger.warning(f"Error creating JSON function: {e}")
    
    # Operation 2: Fix NULL or empty created_at values - in a separate transaction
    if 'created_at' in column_types:
        with engine.connect() as conn:
            with conn.begin():
                try:
                    logger.info("Fixing created_at/updated_at columns in events table")
                    conn.execute(text("""
                        UPDATE events
                        SET created_at = NOW()
                        WHERE created_at IS NULL OR created_at = ''
                    """))
                    logger.info("Fixed NULL or empty created_at values")
                except Exception as date_err:
                    logger.warning(f"Error fixing date values: {date_err}")
    
    # Operation 3: Fix invalid data - in a separate transaction
    with engine.connect() as conn:
        with conn.begin():
            try:
                # Check if there are any events with invalid JSON data
                invalid_events = conn.execute(text("""
                    SELECT id, data FROM events 
                    WHERE event_type = 'memory' 
                    AND (data IS NULL OR data = '' OR data = '[]' OR data = '{}')
                """)).fetchall()
                
                if invalid_events:
                    logger.warning(f"Found {len(invalid_events)} events with invalid data")
                    for event in invalid_events:
                        logger.info(f"Fixing empty data for event {event[0]}")
                        
                        # Set a minimal valid JSON structure
                        conn.execute(text("""
                            UPDATE events 
                            SET data = :data
                            WHERE id = :id
                        """), {
                            "id": event[0],
                            "data": json.dumps([{
                                "type": "system",
                                "category": "info",
                                "content": "Memory placeholder created by repair script",
                                "importance": 1
                            }])
                        })
                    
                    logger.info(f"Fixed {len(invalid_events)} events with invalid data")
                else:
                    logger.info("No events with invalid data found")
            except Exception as e:
                logger.warning(f"Error fixing invalid event data: {e}")
    
    logger.info("Events table fix attempts completed")
    return True

if __name__ == "__main__":
    fix_events_table()
