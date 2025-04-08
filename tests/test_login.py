import pytest
from flask import session
from admin_panel.app import app
from admin_panel.models import AdminUser

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Don't disable CSRF - we'll handle tokens properly
    # app.config['WTF_CSRF_ENABLED'] = False  
    with app.test_client() as client:
        with app.app_context():
            # Ensure admin user exists
            admin = AdminUser.query.filter_by(username='admin').first()
            if not admin:
                admin = AdminUser(
                    username='admin',
                    password_hash='pbkdf2:sha256:260000$k4sSp4bDTmhr9Mhn$16ba562d8ffe1eeea4ceb21a862ae7bd6d39ea66b35c452eb2670f31c6a677d6',
                    is_active=True
                )
                from admin_panel.extensions import db
                db.session.add(admin)
                db.session.commit()
        yield client

# Test login page loads
def test_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'AI Simulator' in response.data

# Test login with valid credentials
def test_login_valid_credentials(client):
    # First, get the login page to retrieve a CSRF token
    client.get('/login')
    # Now we can get the CSRF token from the session
    csrf_token = session.get('csrf_token', '')
    
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin_password',
        'csrf_token': csrf_token
    }, follow_redirects=True)
    assert response.status_code == 200
    # Decode response data to string for non-ASCII characters
    assert 'Успешный вход в систему!' in response.data.decode('utf-8')

# Test login with invalid credentials
def test_login_invalid_credentials(client):
    # First, get the login page to retrieve a CSRF token
    client.get('/login')
    # Now we can get the CSRF token from the session
    csrf_token = session.get('csrf_token', '')
    
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'wrong_password',
        'csrf_token': csrf_token
    }, follow_redirects=True)
    assert response.status_code == 200
    # Decode response data to string for non-ASCII characters
    assert 'Неверное имя пользователя или пароль' in response.data.decode('utf-8')

# Test login without CSRF token
def test_login_missing_csrf(client):
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin_password'
    }, follow_redirects=True)
    assert response.status_code == 400  # CSRF error should return 400
    # Decode response data to string for non-ASCII characters
    assert 'CSRF token missing' in response.data.decode('utf-8')