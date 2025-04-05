# filepath: admin_panel/routes/dashboard.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import text

from admin_panel.app import db
from core.utils.db_helpers import (
    safe_count_query, 
    execute_safe_query, 
    reset_db_connection
)

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard page with system overview"""
    try:
        # Reset any failed transaction
        reset_db_connection(db)
        
        # Get table counts using safe method
        stats = {
            "users": safe_count_query(db, "users"),
            "characters": safe_count_query(db, "characters"),
            "messages": safe_count_query(db, "messages"),
            "total_memory_entries": safe_count_query(db, "memory_entries")
        }
        
        # Get recent messages directly using SQL with created_at instead of timestamp
        recent_messages_query = text("""
            SELECT id, sender_id, sender_type, recipient_id, recipient_type, 
                   content, emotion, created_at
            FROM messages
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        result = execute_safe_query(db, recent_messages_query)
        recent_messages = [dict(row) for row in result] if result else []
        
        # Get recent users
        recent_users_query = text("""
            SELECT user_id, username, email, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        result = execute_safe_query(db, recent_users_query)
        recent_users = [dict(row) for row in result] if result else []
        
        # Get recent characters
        recent_characters_query = text("""
            SELECT id, name, gender, age
            FROM characters
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        result = execute_safe_query(db, recent_characters_query)
        recent_characters = [dict(row) for row in result] if result else []
        
        return render_template(
            "dashboard.html",
            stats=stats,
            recent_messages=recent_messages,
            recent_users=recent_users,
            recent_characters=recent_characters
        )
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template("dashboard.html", stats={}, recent_messages=[], recent_users=[], recent_characters=[])

# Add other dashboard routes as needed
