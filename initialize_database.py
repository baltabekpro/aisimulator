import logging
from core.db.init_db import init_db, create_test_data

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting complete database initialization...")
    
    # Initialize database (drop all tables and recreate)
    init_db()
    
    # Create test data
    create_test_data()
    
    logger.info("Database initialization complete!")
    logger.info("You can now start the application with: python -m app.main")
