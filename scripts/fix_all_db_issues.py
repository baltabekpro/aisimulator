"""
Comprehensive script to fix all known database issues:
1. UUID comparison issues
2. Column type mismatches
3. Transaction failures
4. Missing helper functions
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib
import logging
import subprocess

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_fix_script(script_name):
    """Run a fix script module"""
    try:
        logger.info(f"Running {script_name}...")
        module = importlib.import_module(f"scripts.{script_name}")
        
        # Try different function naming patterns
        if hasattr(module, script_name):
            # First try the exact name match
            main_func = getattr(module, script_name)
        elif hasattr(module, script_name.replace('fix_', 'fix_')):
            # Try with fix_ prefix
            main_func = getattr(module, script_name.replace('fix_', 'fix_'))
        elif hasattr(module, script_name.replace('fix_', '')):
            # Try without fix_ prefix
            main_func = getattr(module, script_name.replace('fix_', ''))
        else:
            # Use a default name as fallback
            main_func_name = next((name for name in dir(module) 
                                  if name.startswith('fix_') and callable(getattr(module, name))), 
                                 None)
            if main_func_name:
                main_func = getattr(module, main_func_name)
            else:
                raise AttributeError(f"Could not find a suitable function in {script_name}")
                
        # Call the function
        success = main_func()
        if success:
            logger.info(f"✅ {script_name} completed successfully")
            return True
        else:
            logger.warning(f"⚠️ {script_name} reported issues")
            return False
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import or run {script_name}: {e}")
        
        # Try running as subprocess instead
        try:
            script_path = os.path.join("scripts", f"{script_name}.py")
            if os.path.exists(script_path):
                subprocess.run([sys.executable, script_path], check=True)
                logger.info(f"✅ {script_name} completed successfully via subprocess")
                return True
        except subprocess.CalledProcessError:
            logger.error(f"❌ {script_name} failed when run as subprocess")
        
        return False

def fix_all_database_issues():
    """Run all database fix scripts"""
    fixes = [
        "fix_session_module",
        "fix_db_issues",
        "fix_event_columns",
        "fix_chat_history",
        "fix_chat_history_schema",
        "create_memory_schema",
        "fix_memory_constraints",  # Add our new constraints fix
        "fix_events_table",
        "migrate_memory_data",
        "fix_telegram_ids",
        "create_missing_models",
        "validate_db_models"
    ]
    
    results = {}
    
    for fix in fixes:
        success = run_fix_script(fix)
        results[fix] = success
    
    # Print summary
    logger.info("\n=== Database Fix Results ===")
    all_successful = True
    for fix, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        logger.info(f"{fix}: {status}")
        if not success:
            all_successful = False
    
    if all_successful:
        logger.info("✅ All database fixes completed successfully!")
    else:
        logger.warning("⚠️ Some database fixes encountered issues")
    
    return all_successful

if __name__ == "__main__":
    fix_all_database_issues()
