#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h aibot-postgres-1 -p 5432 -U postgres; do
  sleep 2
done
echo "PostgreSQL is ready!"

# Create admin_users table if it doesn't exist
echo "Creating admin_users table if needed..."
psql "postgresql://postgres:postgres123@aibot-postgres-1:5432/aibot" <<-EOSQL
CREATE TABLE IF NOT EXISTS admin_users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    password_hash VARCHAR(200) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOSQL

# Create default admin user if it doesn't exist
echo "Creating default admin user if needed..."
psql "postgresql://postgres:postgres123@aibot-postgres-1:5432/aibot" <<-EOSQL
INSERT INTO admin_users (id, username, password_hash, is_active)
SELECT 
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 
  'admin', 
  'pbkdf2:sha256:150000\$KKgd0xN3\$d57b15c874bd9b5f30d7c1ef6006d1a162970a702e9e76bb51a1f7543b63212b', 
  true
WHERE NOT EXISTS (
  SELECT 1 FROM admin_users WHERE username = 'admin'
);
EOSQL

# Start gunicorn
echo "Starting admin panel..."
exec gunicorn "admin_panel.app:app" --bind "0.0.0.0:5000" --workers 2
