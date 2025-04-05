"""
Script to reset the database connection and fix any broken transactions.
This is useful when encountering 'current transaction is aborted' errors.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_database_connections():
    """Reset all database connections and abort any failed transactions"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database: {db_url}")
    
    # Connect to the database with a clean connection
    engine = create_engine(db_url, isolation_level="AUTOCOMMIT")
    
    try:
        with engine.connect() as conn:
            # For PostgreSQL, terminate all active connections
            if 'postgresql' in db_url.lower():
                # Get current connection PIDs
                result = conn.execute(text("SELECT pid, usename, application_name, state, query_start, query FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();"))
                connections = result.fetchall()
                
                logger.info(f"Found {len(connections)} active connections")
                
                for connection in connections:
                    pid = connection.pid
                    try:
                        # Terminate the connection
                        logger.info(f"Terminating connection with PID {pid}")
                        conn.execute(text(f"SELECT pg_terminate_backend({pid});"))
                    except Exception as e:
                        logger.error(f"Error terminating connection {pid}: {e}")
            
            logger.info("Database connections reset successfully")
            return True
    except Exception as e:
        logger.error(f"Error resetting database connections: {e}")
        return False

if __name__ == "__main__":
    reset_database_connections()
