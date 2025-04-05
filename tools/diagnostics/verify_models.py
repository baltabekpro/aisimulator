"""
Simple utility to verify that all models can be properly imported.
This helps diagnose import errors in the model system.

Usage:
    python -m tools.verify_models
"""

import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def verify_imports():
    """Test importing all models both ways to verify they're correctly set up"""
    
    # Add the current directory to path
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, current_dir)
    
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Python path: {sys.path}")
    
    success = True
    
    # Try importing from core.models
    try:
        logger.info("Testing import from core.models...")
        from core.models import User, AIPartner, Message, Event, Gift, LoveRating
        logger.info("✅ Successfully imported all models from core.models")
    except ImportError as e:
        logger.error(f"❌ Error importing from core.models: {e}")
        success = False
    
    # Try importing directly from model modules
    try:
        logger.info("Testing direct imports from model modules...")
        from core.db.models.user import User
        from core.db.models.ai_partner import AIPartner
        from core.db.models.message import Message
        from core.db.models.event import Event
        from core.db.models.gift import Gift
        from core.db.models.love_rating import LoveRating
        logger.info("✅ Successfully imported all models directly from modules")
    except ImportError as e:
        logger.error(f"❌ Error importing directly from model modules: {e}")
        success = False
    
    # Print a summary
    if success:
        logger.info("All model imports are working correctly!")
    else:
        logger.error("Some model imports failed. Check the structure of your model packages.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(verify_imports())
