import logging
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

# Import all model files explicitly to ensure they're registered
from core.db.models.user import User
from core.db.models.ai_partner import AIPartner 
from core.db.models.message import Message
from core.db.models.love_rating import LoveRating

from core.db.base_class import Base
from core.db.session import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_models():
    """Print diagnostic information about model registration and foreign keys"""
    logger.info("Diagnosing model registration...")
    
    # Check Base.metadata for registered tables
    registered_tables = Base.metadata.tables
    logger.info(f"Registered tables in metadata: {', '.join(registered_tables.keys())}")
    
    # Check each table's foreign keys
    for table_name, table in registered_tables.items():
        logger.info(f"\nTable: {table_name}")
        
        # Get columns
        logger.info("Columns:")
        for column in table.columns:
            logger.info(f"  - {column.name}: {column.type}")
        
        # Get foreign keys
        logger.info("Foreign Keys:")
        for fk in table.foreign_keys:
            logger.info(f"  - {fk.parent} -> {fk.target_fullname}")

if __name__ == "__main__":
    diagnose_models()
    
    # Attempt to create tables to see specific errors
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error creating tables: {e}")
