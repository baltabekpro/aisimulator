"""
Script to validate database models and session handling.
This script checks that all models can be loaded properly and that
sessions can be created and used correctly.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Important fix: Import text properly at the module level
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import logging
import importlib
import inspect as py_inspect
from uuid import uuid4
from werkzeug.security import generate_password_hash

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_database_setup():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database: {db_url}")
    
    # Check session module
    try:
        from core.db import session
        logger.info("✅ Session module imported successfully")
        
        # Check available functions
        session_funcs = [name for name, obj in py_inspect.getmembers(session) 
                        if py_inspect.isfunction(obj)]
        logger.info(f"Session functions: {session_funcs}")
        
        # Validate get_db_session
        if hasattr(session, 'get_db_session'):
            logger.info("✅ get_db_session function exists")
            db_session = session.get_db_session()
            logger.info(f"✅ Created session: {db_session}")
            db_session.close()
        else:
            logger.error("❌ get_db_session function is missing")
        
        # Validate get_session (alias)
        if hasattr(session, 'get_session'):
            logger.info("✅ get_session function exists")
            db_session = session.get_session()
            logger.info(f"✅ Created session: {db_session}")
            db_session.close()
        else:
            logger.warning("⚠️ get_session function is missing (alias for get_db_session)")
            
    except Exception as e:
        logger.error(f"❌ Error importing session module: {e}")
        return False
    
    # Validate model imports
    models_to_check = [
        "core.db.models.user",
        "core.db.models.message", 
        "core.db.models.character",
        "core.db.models.chat_history",
        "core.db.models.memory_entry"
    ]
    
    for model_path in models_to_check:
        try:
            model_module = importlib.import_module(model_path)
            logger.info(f"✅ {model_path} imported successfully")
            
            # Get model classes
            model_classes = [name for name, obj in py_inspect.getmembers(model_module)
                           if py_inspect.isclass(obj) and hasattr(obj, '__tablename__')]
            logger.info(f"Model classes in {model_path}: {model_classes}")
            
        except Exception as e:
            logger.error(f"❌ Error importing {model_path}: {e}")
    
    # Check if we can execute a simple query
    try:
        from core.db.session import get_db_session
        db = get_db_session()
        
        try:
            # Test simple query using the imported text function
            result = db.execute(text("SELECT 1")).scalar()
            logger.info(f"✅ Test query result: {result}")
            
            # Close and get a fresh session for transaction test
            db.close()
            db = get_db_session()
            
            # Test transaction separately
            try:
                with db.begin():
                    db.execute(text("SELECT 1"))
                logger.info("✅ Transaction test passed")
            except Exception as tx_error:
                logger.error(f"❌ Error in transaction test: {tx_error}")
                
        except Exception as e:
            logger.error(f"❌ Error executing query: {e}")
        finally:
            # Make sure to properly close the session
            try:
                db.close()
                logger.info("✅ Session closed successfully")
            except:
                pass
            
    except Exception as e:
        logger.error(f"❌ Error getting session for query test: {e}")
    
    # Test creating and updating a record
    try:
        from core.db.session import get_db_session
        db = get_db_session()
        
        try:
            # Create a test record in the admin_users table
            test_id = str(uuid4())
            test_user = f"test_user_{test_id[-8:]}"
            
            # Check if admin_users table exists
            table_check = db.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_users')"
            )).scalar()
            
            if table_check:
                logger.info("✅ admin_users table exists")
                
                # First check if user exists to avoid unique constraint errors
                user_exists = db.execute(text(
                    "SELECT COUNT(*) FROM admin_users WHERE username = :username"
                ), {"username": test_user}).scalar()
                
                if not user_exists:
                    # Insert test user
                    db.execute(text("""
                        INSERT INTO admin_users 
                        (id, username, email, password_hash, is_active, created_at) 
                        VALUES 
                        (:id, :username, :email, :password_hash, true, now())
                    """), {
                        "id": test_id,
                        "username": test_user,
                        "email": f"{test_user}@example.com",
                        "password_hash": generate_password_hash("test_password")
                    })
                    
                    # Commit the transaction
                    db.commit()
                    logger.info(f"✅ Created test admin user: {test_user}")
                    
                    # Query the user back
                    result = db.execute(text(
                        "SELECT id, username FROM admin_users WHERE id = :id"
                    ), {"id": test_id}).fetchone()
                    
                    if result:
                        logger.info(f"✅ Retrieved test user: {result.username}")
                    else:
                        logger.error("❌ Could not retrieve the test user")
                else:
                    logger.info(f"✅ Test user already exists")
            else:
                logger.info("⚠️ admin_users table does not exist, skipping record test")
                
        except Exception as e:
            logger.error(f"❌ Error in record test: {e}")
            # Rollback on error
            try:
                db.rollback()
            except:
                pass
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error in DB record test: {e}")
        
    logger.info("Database validation completed")
    return True

# Add a module-level function for running the validation
def validate_db_models():
    """
    Main function to run database model validation 
    (added to match the script import pattern)
    """
    return validate_database_setup()

if __name__ == "__main__":
    validate_database_setup()
