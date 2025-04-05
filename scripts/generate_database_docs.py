"""
Script to generate comprehensive database documentation based on current schema.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import logging
import importlib
import inspect as py_inspect
from datetime import datetime

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_database_docs():
    """Generate comprehensive database documentation"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Using database: {db_url}")
    engine = create_engine(db_url)
    
    # Get database tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Import models to get documentation from docstrings
    try:
        from core.db.models.user import User
        from core.db.models.message import Message
        from core.db.models.character import Character
        from core.db.models.chat_history import ChatHistory
        from core.db.models.memory_entry import MemoryEntry
        
        models = {
            "users": User,
            "messages": Message, 
            "characters": Character,
            "chat_history": ChatHistory,
            "memory_entries": MemoryEntry
        }
    except ImportError as e:
        logger.error(f"Error importing models: {e}")
        models = {}
    
    # Create a markdown document
    doc_content = f"""# Database Schema Documentation

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Tables Overview

This document describes the database schema used in this application, including tables, columns, and relationships.

"""
    # Add each table to the documentation
    with engine.connect() as conn:
        for table_name in sorted(tables):
            # Skip SQLAlchemy internal tables
            if table_name.startswith('alembic_'):
                continue
                
            doc_content += f"## {table_name}\n\n"
            
            # Add model docstring if available
            if table_name in models:
                model_doc = models[table_name].__doc__
                if model_doc:
                    doc_content += f"{model_doc.strip()}\n\n"
            
            # Get columns
            columns = inspector.get_columns(table_name)
            doc_content += "### Columns\n\n"
            doc_content += "| Column | Type | Nullable | Default | Description |\n"
            doc_content += "|--------|------|----------|---------|-------------|\n"
            
            for column in columns:
                column_name = column['name']
                column_type = str(column['type'])
                nullable = "Yes" if column.get('nullable', True) else "No"
                default = str(column.get('default', "None")).replace("\n", " ")
                
                # Try to get column comment
                comment = ""
                try:
                    if 'postgresql' in db_url.lower():
                        comment_query = text(f"""
                            SELECT pg_description.description
                            FROM pg_description
                            JOIN pg_class ON pg_description.objoid = pg_class.oid
                            JOIN pg_attribute ON pg_class.oid = pg_attribute.attrelid
                            WHERE pg_class.relname = '{table_name}'
                            AND pg_attribute.attname = '{column_name}'
                            AND pg_attribute.attnum = pg_description.objsubid
                        """)
                        result = conn.execute(comment_query)
                        comment_row = result.fetchone()
                        if comment_row and comment_row[0]:
                            comment = comment_row[0]
                except:
                    pass
                
                doc_content += f"| {column_name} | {column_type} | {nullable} | {default} | {comment} |\n"
            
            # Get indexes
            indexes = inspector.get_indexes(table_name)
            if indexes:
                doc_content += "\n### Indexes\n\n"
                doc_content += "| Name | Columns | Unique |\n"
                doc_content += "|------|---------|--------|\n"
                
                for index in indexes:
                    name = index['name']
                    columns = ", ".join(index['column_names'])
                    unique = "Yes" if index.get('unique', False) else "No"
                    
                    doc_content += f"| {name} | {columns} | {unique} |\n"
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)
            if foreign_keys:
                doc_content += "\n### Foreign Keys\n\n"
                doc_content += "| Column | References | On Delete | On Update |\n"
                doc_content += "|--------|------------|-----------|----------|\n"
                
                for fk in foreign_keys:
                    ref_columns = ", ".join(fk['constrained_columns'])
                    ref_table = fk['referred_table']
                    ref_fields = ", ".join(fk['referred_columns'])
                    on_delete = fk.get('options', {}).get('ondelete', "")
                    on_update = fk.get('options', {}).get('onupdate', "")
                    
                    doc_content += f"| {ref_columns} | {ref_table}({ref_fields}) | {on_delete} | {on_update} |\n"
            
            doc_content += "\n"
    
    # Write the documentation to a file
    docs_dir = os.path.join("docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    doc_path = os.path.join(docs_dir, "database_schema.md")
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(doc_content)
    
    logger.info(f"✅ Database documentation generated: {doc_path}")
    return True

if __name__ == "__main__":
    generate_database_docs()
