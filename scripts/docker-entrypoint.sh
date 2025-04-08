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

# Initialize the database
echo "Running database initialization..."
python -m admin_panel.init_db

# Start gunicorn
echo "Starting admin panel..."
# Enable debug mode for Gunicorn to see more logs
exec gunicorn "admin_panel.app:app" --bind "0.0.0.0:5000" --workers 2 --log-level debug
