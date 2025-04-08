#!/bin/bash
set -e

# This script is executed by PostgreSQL container at initialization

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create admin_users table if it doesn't exist
    CREATE TABLE IF NOT EXISTS admin_users (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100),
        password_hash VARCHAR(200) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Insert default admin user if none exists
    INSERT INTO admin_users (id, username, password_hash, is_active)
    VALUES (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'admin',
        'pbkdf2:sha256:150000\$KKgd0xN3\$d57b15c874bd9b5f30d7c1ef6006d1a162970a702e9e76bb51a1f7543b63212b',
        true
    )
    ON CONFLICT (username) DO NOTHING;
    
    -- Set permissions
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
EOSQL

echo "PostgreSQL initialization completed"
