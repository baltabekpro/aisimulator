"""
Utility script to inspect the database schema and contents.
Useful for debugging database-related issues.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
from tabulate import tabulate
import json

def inspect_database():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get database URL directly from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    print(f"Using database: {db_url}")
    
    # Connect to the database
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            # Get the inspector
            insp = inspect(engine)
            
            # Get all tables
            tables = insp.get_table_names()
            print(f"Found {len(tables)} tables: {', '.join(tables)}")
            
            # For each table, show schema and sample data
            for table in tables:
                print(f"\n{'-'*40}")
                print(f"TABLE: {table}")
                print(f"{'-'*40}")
                
                # Show schema
                columns = insp.get_columns(table)
                print("\nCOLUMNS:")
                headers = ["Name", "Type", "Nullable", "Default"]
                rows = [[col['name'], col['type'], col['nullable'], col.get('default', '')] for col in columns]
                print(tabulate(rows, headers=headers))
                
                # Show sample data
                with conn.begin():
                    result = conn.execute(text(f"SELECT * FROM {table} LIMIT 5"))
                    sample_data = result.fetchall()
                    
                    if sample_data:
                        print(f"\nSAMPLE DATA ({min(len(sample_data), 5)} rows):")
                        headers = result.keys()
                        rows = []
                        for row in sample_data:
                            processed_row = []
                            for col in row:
                                # Format complex values and truncate long strings
                                if isinstance(col, (dict, list)):
                                    val = json.dumps(col)[:50] + "..." if len(json.dumps(col)) > 50 else json.dumps(col)
                                elif isinstance(col, str) and len(col) > 50:
                                    val = col[:50] + "..."
                                else:
                                    val = col
                                processed_row.append(val)
                            rows.append(processed_row)
                        print(tabulate(rows, headers=headers))
                    else:
                        print("\nNo data in this table")
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_database()
