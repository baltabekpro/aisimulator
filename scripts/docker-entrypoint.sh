#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
# Try to use pg_isready if available, otherwise try direct connection with psql
if command -v pg_isready > /dev/null; then
  echo "Using pg_isready to check connection..."
  until pg_isready -h postgres -p 5432 -U aibot; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
  done
else
  echo "pg_isready not found, using psql to check connection..."
  until PGPASSWORD=postgres psql -h postgres -p 5432 -U aibot -c '\q'; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
  done
fi

echo "PostgreSQL is ready!"

# Create admin_users table if it doesn't exist
echo "Creating admin_users table if needed..."
PGPASSWORD=postgres psql "${DATABASE_URL:-postgresql://aibot:postgres@postgres:5432/aibot}" <<-EOSQL
CREATE TABLE IF NOT EXISTS admin_users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    password_hash VARCHAR(200) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOSQL

# Reset admin password using our dedicated script
if [ -f /app/scripts/reset-admin-password.sh ]; then
  echo "Resetting admin password with proper hash..."
  chmod +x /app/scripts/reset-admin-password.sh
  /app/scripts/reset-admin-password.sh
else
  # Create default admin user if it doesn't exist (fallback)
  echo "Reset script not found. Creating default admin user if needed..."
  PGPASSWORD=postgres psql "${DATABASE_URL:-postgresql://aibot:postgres@postgres:5432/aibot}" <<-EOSQL
  INSERT INTO admin_users (id, username, email, password_hash, is_active)
  SELECT 
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 
    'admin', 
    'admin@example.com',
    '$(python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('${ADMIN_PASSWORD:-admin_password}'))")', 
    true
  WHERE NOT EXISTS (
    SELECT 1 FROM admin_users WHERE username = 'admin'
  );
EOSQL
fi

# Ensure memory tables have the correct schema (with both type and memory_type columns)
echo "Ensuring memory tables have the correct schema..."
PGPASSWORD=postgres psql "${DATABASE_URL:-postgresql://aibot:postgres@postgres:5432/aibot}" <<-EOSQL
-- Check if memory_entries table exists
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'memory_entries') THEN
    -- Create memory_entries table with both type and memory_type columns
    CREATE TABLE memory_entries (
      id VARCHAR(36) PRIMARY KEY,
      character_id VARCHAR(36) NOT NULL,
      user_id VARCHAR(36) NOT NULL,
      type VARCHAR(50) NOT NULL DEFAULT 'unknown',
      memory_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
      category VARCHAR(50) NOT NULL DEFAULT 'general',
      content TEXT NOT NULL,
      importance INTEGER DEFAULT 5,
      is_active BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Create sync triggers to keep type and memory_type in sync
    CREATE OR REPLACE FUNCTION sync_memory_type_to_type()
    RETURNS TRIGGER AS \$\$
    BEGIN
      NEW.type = NEW.memory_type;
      RETURN NEW;
    END;
    \$\$ LANGUAGE plpgsql;
    
    CREATE OR REPLACE FUNCTION sync_type_to_memory_type()
    RETURNS TRIGGER AS \$\$
    BEGIN
      NEW.memory_type = NEW.type;
      RETURN NEW;
    END;
    \$\$ LANGUAGE plpgsql;
    
    CREATE TRIGGER sync_memory_type_trigger
    BEFORE INSERT OR UPDATE OF memory_type ON memory_entries
    FOR EACH ROW
    WHEN (NEW.memory_type IS DISTINCT FROM NEW.type)
    EXECUTE FUNCTION sync_memory_type_to_type();
    
    CREATE TRIGGER sync_type_trigger
    BEFORE INSERT OR UPDATE OF type ON memory_entries
    FOR EACH ROW
    WHEN (NEW.type IS DISTINCT FROM NEW.memory_type)
    EXECUTE FUNCTION sync_type_to_memory_type();
    
    -- Create indexes
    CREATE INDEX idx_memory_entries_character_id ON memory_entries(character_id);
    CREATE INDEX idx_memory_entries_user_id ON memory_entries(user_id);
    CREATE INDEX idx_memory_entries_type ON memory_entries(type);
    CREATE INDEX idx_memory_entries_memory_type ON memory_entries(memory_type);
    CREATE INDEX idx_memory_entries_category ON memory_entries(category);
    CREATE INDEX idx_memory_entries_character_id_text ON memory_entries((character_id::text));
    CREATE INDEX idx_memory_entries_user_id_text ON memory_entries((user_id::text));
  
  ELSE
    -- Table already exists, check for missing columns
    -- Add memory_type column if needed
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'memory_entries' AND column_name = 'memory_type') THEN
      ALTER TABLE memory_entries ADD COLUMN memory_type VARCHAR(50) DEFAULT 'unknown';
      -- Copy values from type column if it exists
      UPDATE memory_entries SET memory_type = type WHERE type IS NOT NULL;
    END IF;
    
    -- Add type column if needed
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'memory_entries' AND column_name = 'type') THEN
      ALTER TABLE memory_entries ADD COLUMN type VARCHAR(50) DEFAULT 'unknown';
      -- Copy values from memory_type column if it exists
      UPDATE memory_entries SET type = memory_type WHERE memory_type IS NOT NULL;
    END IF;
    
    -- Ensure sync triggers exist
    -- We use CREATE OR REPLACE to avoid errors if they already exist
    CREATE OR REPLACE FUNCTION sync_memory_type_to_type()
    RETURNS TRIGGER AS \$\$
    BEGIN
      NEW.type = NEW.memory_type;
      RETURN NEW;
    END;
    \$\$ LANGUAGE plpgsql;
    
    CREATE OR REPLACE FUNCTION sync_type_to_memory_type()
    RETURNS TRIGGER AS \$\$
    BEGIN
      NEW.memory_type = NEW.type;
      RETURN NEW;
    END;
    \$\$ LANGUAGE plpgsql;
    
    -- Drop triggers if they exist to avoid conflicts
    DROP TRIGGER IF EXISTS sync_memory_type_trigger ON memory_entries;
    DROP TRIGGER IF EXISTS sync_type_trigger ON memory_entries;
    
    -- Recreate triggers
    CREATE TRIGGER sync_memory_type_trigger
    BEFORE INSERT OR UPDATE OF memory_type ON memory_entries
    FOR EACH ROW
    WHEN (NEW.memory_type IS DISTINCT FROM NEW.type)
    EXECUTE FUNCTION sync_memory_type_to_type();
    
    CREATE TRIGGER sync_type_trigger
    BEFORE INSERT OR UPDATE OF type ON memory_entries
    FOR EACH ROW
    WHEN (NEW.type IS DISTINCT FROM NEW.memory_type)
    EXECUTE FUNCTION sync_type_to_memory_type();
    
    -- Create indexes if they don't exist
    CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(type);
    CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type ON memory_entries(memory_type);
  END IF;
END;
\$\$;

-- Make sure data is consistent between columns
UPDATE memory_entries SET memory_type = type WHERE type IS NOT NULL AND (memory_type IS NULL OR memory_type != type);
UPDATE memory_entries SET type = memory_type WHERE memory_type IS NOT NULL AND (type IS NULL OR type != memory_type);
EOSQL

echo "Memory schema setup complete."

# Now fix the admin view query that's causing the error
echo "Creating admin memory view..."
PGPASSWORD=postgres psql "${DATABASE_URL:-postgresql://aibot:postgres@postgres:5432/aibot}" <<-EOSQL
-- Create or replace the view used by admin panel for memories
CREATE OR REPLACE VIEW admin_memories_view AS
SELECT m.id, m.character_id, c.name as character_name, 
       m.type, m.memory_type, COALESCE(m.category, 'general') as category, m.content, m.importance,
       m.user_id, m.created_at
FROM memory_entries m
LEFT JOIN characters c ON c.id::text = m.character_id::text
ORDER BY m.created_at DESC;
EOSQL

echo "Admin memory view created."

# Initialize the database
echo "Running database initialization..."
python -m admin_panel.init_db

# Start gunicorn
echo "Starting admin panel..."
# Enable debug mode for Gunicorn to see more logs
exec gunicorn "admin_panel.app:app" --bind "0.0.0.0:5000" --workers 2 --log-level debug
