#!/bin/bash
set -e

# Script to initialize admin_users table for the admin panel
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE TABLE IF NOT EXISTS admin_users (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100),
        password_hash VARCHAR(200) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    INSERT INTO admin_users (id, username, password_hash, is_active)
    VALUES ('admin-user-id', 'admin', 'pbkdf2:sha256:150000\$KKgd0xN3\$d57b15c874bd9b5f30d7c1ef6006d1a162970a702e9e76bb51a1f7543b63212b', TRUE)
    ON CONFLICT (username) DO NOTHING;
EOSQL
