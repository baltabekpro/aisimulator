#!/bin/bash
set -e

# Initialize database
python -m admin_panel.init_db

# Create default admin user
python -m scripts.create_admin_user

# Start gunicorn
exec gunicorn "admin_panel.app:app" --bind "0.0.0.0:5000" --workers 2
