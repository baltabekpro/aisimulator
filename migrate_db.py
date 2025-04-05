"""
Database migration utility script

Usage:
    python migrate_db.py
"""
import logging
import argparse
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Database migration utility")
    parser.add_argument("--fix-only", action="store_true", help="Only fix schema issues without creating test data")
    args = parser.parse_args()
    
    try:
        from core.db.init_db import init_db, create_test_data, fix_schema_issues
        
        logger.info("Running database migrations...")
        
        # First fix any schema issues
        fix_schema_issues()
        
        # Initialize database
        init_db()
        
        # Create test data if needed
        if not args.fix_only:
            logger.info("Creating test data...")
            create_test_data()
        
        logger.info("Database migration completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
