from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
import uuid

from admin_panel.dependencies import templates, get_current_admin_user
from admin_panel.database import get_db
from sqlalchemy import text

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_class=HTMLResponse)
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """List all users"""
    # Get users with raw SQL to avoid UUID issues
    users = db.execute(text("""
        SELECT id, username, email, created_at, is_active 
        FROM users
        ORDER BY created_at DESC
    """)).fetchall()
    
    # Convert to list of dicts
    user_list = []
    for user in users:
        user_list.append({
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "created_at": user[3].strftime("%Y-%m-%d %H:%M:%S") if hasattr(user[3], "strftime") else str(user[3]),
            "is_active": user[4]
        })
    
    return templates.TemplateResponse(
        "users/list.html",
        {
            "request": request,
            "title": "Users",
            "users": user_list
        }
    )

@router.get("/create", response_class=HTMLResponse)
async def create_user_form(
    request: Request,
    current_user = Depends(get_current_admin_user)
):
    """Display user creation form"""
    return templates.TemplateResponse(
        "users/create.html",
        {
            "request": request,
            "title": "Create User"
        }
    )

@router.post("/create")
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Create a new user"""
    # Check if user already exists
    existing = db.execute(text("""
        SELECT id FROM users WHERE username = :username OR email = :email
    """), {"username": username, "email": email}).fetchone()
    
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Create hashed password
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(password)
    
    # Add the user
    user_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO users (id, username, email, password_hash, is_active)
        VALUES (:id, :username, :email, :password_hash, TRUE)
    """), {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": hashed_password
    })
    
    db.commit()
    
    return RedirectResponse(url="/users", status_code=303)