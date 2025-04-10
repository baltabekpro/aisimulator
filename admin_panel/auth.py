from functools import wraps
from flask import session, redirect, url_for, request, flash

def login_required(f):
    """
    Decorator to require login for routes.
    Redirects to login page if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Пожалуйста, войдите в систему для доступа к этой странице", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
