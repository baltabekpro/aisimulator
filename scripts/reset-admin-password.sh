#!/bin/bash
set -e

# Generate a proper password hash for Flask-Login with Werkzeug
echo "Generating password hash for admin user..."
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin_password}

# Use Python to generate the password hash
HASH=$(python3 - <<EOF
from werkzeug.security import generate_password_hash
print(generate_password_hash("${ADMIN_PASSWORD}"))
EOF
)

echo "Generated hash: ${HASH}"

# Update the admin user password in the database
echo "Updating admin user password in the database..."
PGPASSWORD=postgres psql "${DATABASE_URL:-postgresql://aibot:postgres@postgres:5432/aibot}" <<-EOSQL
UPDATE admin_users 
SET password_hash = '${HASH}' 
WHERE username = '${ADMIN_USERNAME}';

-- If no user exists, create one
INSERT INTO admin_users (id, username, email, password_hash, is_active)
SELECT 
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 
  '${ADMIN_USERNAME}', 
  '${ADMIN_USERNAME}@example.com',
  '${HASH}', 
  true
WHERE NOT EXISTS (
  SELECT 1 FROM admin_users WHERE username = '${ADMIN_USERNAME}'
);
EOSQL

echo "Admin password reset complete."
echo "You can now login with username: ${ADMIN_USERNAME} and password: ${ADMIN_PASSWORD}"
