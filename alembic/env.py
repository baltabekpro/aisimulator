from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, inspect
from alembic import context
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import models
from core.db.base import Base
from core.db.models import User, AIPartner, LoveRating, Event, Message, Gift

# Get alembic config
config = context.config

# Override with DATABASE_URL environment variable if it exists
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    """Control which database objects are included in the migrations.
    Skip existing tables to avoid 'table already exists' errors.
    """
    if type_ == "table" and reflected and name != "alembic_version":
        return False
    return True

def get_url():
    return os.getenv("DATABASE_URL", "sqlite:///aibot.db")

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    
    # Detect if we're using SQLite and adjust accordingly
    is_sqlite = 'sqlite' in get_url().lower()
    
    config_args = {}
    if is_sqlite:
        # Special handling for SQLite
        # This replaces UUID types with String in SQLite
        from sqlalchemy.dialects import sqlite
        from sqlalchemy import TypeDecorator, String
        
        class StringUUID(TypeDecorator):
            impl = String
            cache_ok = True
            
            def process_bind_param(self, value, dialect):
                if value is not None:
                    return str(value)
                return value
                
            def process_result_value(self, value, dialect):
                if value is not None:
                    import uuid
                    try:
                        return uuid.UUID(value)
                    except ValueError:
                        return value
                return value
        
        # Register the type for SQLite
        from sqlalchemy.dialects.postgresql import UUID
        sqlite.pysqlite.dialect.type_compiler.visit_UUID = lambda self, type_: "VARCHAR"
        config_args = {"render_as_batch": True}
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            **config_args
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
