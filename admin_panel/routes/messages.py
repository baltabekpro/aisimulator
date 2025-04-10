import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import text
from datetime import datetime
# Fix import path for login_required - using Flask-Login's standard implementation
from flask_login import login_required
# Fix the import path for get_db
from admin_panel.database import get_db

logger = logging.getLogger(__name__)

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/messages')
@login_required
def messages_list():
    """Отображение списка сообщений с правильным приведением типов"""
    try:
        # Получаем страницу и количество записей на страницу
        page = request.args.get('page', 1, type=int)
        per_page = 100
        
        # Создаем правильный SQL запрос с явным приведением типов для PostgreSQL
        # Решение проблемы с CASE types uuid and character varying cannot be matched
        query = text("""
            SELECT 
                m.id, 
                m.sender_id, 
                m.sender_type, 
                m.recipient_id, 
                m.recipient_type, 
                m.content, 
                m.emotion, 
                m.created_at,
                CASE 
                    WHEN m.sender_type = 'user' AND u1.username IS NOT NULL THEN u1.username::text
                    WHEN m.sender_type = 'character' AND c1.name IS NOT NULL THEN c1.name::text
                    ELSE m.sender_id::text
                END as sender_name,
                CASE 
                    WHEN m.recipient_type = 'user' AND u2.username IS NOT NULL THEN u2.username::text
                    WHEN m.recipient_type = 'character' AND c2.name IS NOT NULL THEN c2.name::text
                    ELSE m.recipient_id::text
                END as recipient_name
            FROM messages m
            LEFT JOIN users u1 ON m.sender_id::text = u1.user_id::text AND m.sender_type = 'user'
            LEFT JOIN characters c1 ON m.sender_id::text = c1.id::text AND m.sender_type = 'character'
            LEFT JOIN users u2 ON m.recipient_id::text = u2.user_id::text AND m.recipient_type = 'user'
            LEFT JOIN characters c2 ON m.recipient_id::text = c2.id::text AND m.recipient_type = 'character'
            ORDER BY m.created_at DESC
            LIMIT :limit
            OFFSET :offset
        """)
        
        # Выполняем запрос
        db = get_db()
        result = db.execute(query, {"limit": per_page, "offset": (page - 1) * per_page})
        messages = [dict(row) for row in result]
        
        return render_template('messages/list.html', messages=messages, page=page)
    except Exception as e:
        logger.error(f"Error loading messages: {e}")
        flash(f"Ошибка при загрузке сообщений: {e}", "danger")
        return render_template('messages/list.html', messages=[])
