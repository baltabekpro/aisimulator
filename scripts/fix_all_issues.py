"""
Comprehensive script to fix all identified issues with:
1. Database session handling
2. UUID type handling in PostgreSQL 
3. Transaction errors
4. Circular imports
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from dotenv import load_dotenv
import importlib
import subprocess

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_script(script_name):
    """Run another script as a subprocess"""
    script_path = os.path.join("scripts", script_name)
    logger.info(f"Running {script_path}...")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"✅ {script_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {script_name} failed with error:")
        logger.error(e.stderr)
        return False

def fix_uuid_handling():
    """Create UUID handling functions for PostgreSQL"""
    # Run the fix_db_issues.py script which creates UUID handling helpers
    run_script("fix_db_issues.py")
    
    # Apply additional PostgreSQL type casting functions
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if db_url and 'postgresql' in db_url.lower():
        logger.info("Creating additional UUID comparison functions for PostgreSQL...")
        
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url)
            
            with engine.connect() as conn:
                with conn.begin():
                    # Create additional helper functions
                    conn.execute(text("""
                        CREATE OR REPLACE FUNCTION to_uuid_safely(txt TEXT)
                        RETURNS UUID AS $$
                        BEGIN
                            BEGIN
                                RETURN txt::uuid;
                            EXCEPTION WHEN OTHERS THEN
                                RETURN NULL;
                            END;
                        END;
                        $$ LANGUAGE plpgsql;
                    """))
                    
                    conn.execute(text("""
                        CREATE OR REPLACE FUNCTION compare_uuid_or_text(col1 ANYELEMENT, col2 TEXT)
                        RETURNS BOOLEAN AS $$
                        BEGIN
                            -- Convert to text and then compare
                            RETURN col1::text = col2;
                        END;
                        $$ LANGUAGE plpgsql;
                    """))
                    
                    logger.info("✅ Created additional UUID helper functions")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating UUID helper functions: {e}")
            return False
    
    return True

def fix_gemini_module():
    """Fix issues in the gemini.py file with text reference"""
    gemini_path = os.path.join("core", "ai", "gemini.py")
    
    if not os.path.exists(gemini_path):
        logger.warning(f"⚠️ {gemini_path} not found, skipping")
        return False
        
    try:
        # Read the file
        with open(gemini_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if we can identify the problematic line
        error_line = None
        for i, line in enumerate(content.splitlines()):
            if "text" in line and "=" in line and ("not defined" in line or line.strip().startswith("text")):
                error_line = i
                break
                
        if error_line is not None:
            logger.info(f"Found potential text reference issue at line {error_line+1}")
            
            # Apply a general fix to all potential occurrences
            fixed_content = content.replace(
                "text = ", 
                "response_text = response.get('text', '') "
            ).replace(
                "text=", 
                "response_text=response.get('text', '') "
            )
            
            # Write the fixed content
            with open(gemini_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
                
            logger.info(f"✅ Applied fixes to {gemini_path}")
            return True
        else:
            logger.warning(f"⚠️ Could not identify text reference issue in {gemini_path}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error fixing gemini module: {e}")
        return False

def fix_all_issues():
    """Run all fixes to address the identified issues"""
    fixes = [
        ("fix_session_module.py", "Fix session module"),
        ("create_missing_models.py", "Create missing models"),
        ("fix_uuid_handling", "Fix UUID handling"),
        ("fix_gemini_module", "Fix gemini module"),
        ("validate_db_models.py", "Validate database models")
    ]
    
    results = {}
    
    for fix_name, description in fixes:
        logger.info(f"Running {description}...")
        
        try:
            if fix_name.endswith(".py"):
                success = run_script(fix_name)
            else:
                # Call the local function
                func = globals()[fix_name]
                success = func()
                
            results[fix_name] = success
        except Exception as e:
            logger.error(f"❌ Error in {fix_name}: {e}")
            results[fix_name] = False
    
    # Print summary
    logger.info("\n=== Fix Results Summary ===")
    for fix_name, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        logger.info(f"{fix_name}: {status}")
    
    if all(results.values()):
        logger.info("✅ All fixes applied successfully!")
    else:
        logger.warning("⚠️ Some fixes failed. Check the logs for details.")
    
    return all(results.values())

if __name__ == "__main__":
    fix_all_issues()
