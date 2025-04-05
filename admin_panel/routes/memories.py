"""
Routes for managing character memories in the admin panel.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Dict
import uuid
import json
from datetime import datetime

from admin_panel.dependencies import templates, get_current_admin_user
from admin_panel.database import get_db
from sqlalchemy import text

router = APIRouter(prefix="/memories", tags=["memories"])

@router.get("/", response_class=HTMLResponse)
async def list_memories(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """List all memories"""
    # Get all characters that have memories
    characters = db.execute(text("""
        SELECT DISTINCT c.id, c.name
        FROM characters c
        JOIN memory_entries m ON c.id::text = m.character_id::text
        ORDER BY c.name
    """)).fetchall()
    
    # Get memory counts by character
    memory_counts = {}
    for char in characters:
        char_id = str(char[0])
        count = db.execute(text("""
            SELECT COUNT(*) FROM memory_entries
            WHERE character_id::text = :character_id
        """), {"character_id": char_id}).scalar()
        memory_counts[char_id] = count
    
    # Get recent memories
    recent_memories = db.execute(text("""
        SELECT 
            m.id, 
            m.character_id, 
            c.name as character_name,
            m.memory_type, 
            m.category, 
            m.content, 
            m.importance,
            m.created_at
        FROM memory_entries m
        LEFT JOIN characters c ON c.id::text = m.character_id::text  
        ORDER BY m.created_at DESC
        LIMIT 20
    """)).fetchall()
    
    # Convert to list of dicts
    recent_memory_list = []
    for m in recent_memories:
        created_at = m[7]
        if hasattr(created_at, 'strftime'):
            created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_at_str = str(created_at)
            
        recent_memory_list.append({
            "id": m[0],
            "character_id": m[1],
            "character_name": m[2] or "Unknown",
            "memory_type": m[3] or "unknown",
            "category": m[4] or "general",
            "content": m[5],
            "importance": m[6] if m[6] is not None else 5,
            "created_at": created_at_str
        })
    
    return templates.TemplateResponse(
        "memories/list.html",
        {
            "request": request,
            "title": "Memories",
            "characters": characters,
            "memory_counts": memory_counts,
            "recent_memories": recent_memory_list
        }
    )

@router.get("/character/{character_id}", response_class=HTMLResponse)
async def character_memories(
    request: Request,
    character_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """List memories for a specific character"""
    # Get character details
    character = db.execute(text("""
        SELECT id, name, age, gender
        FROM characters
        WHERE id::text = :character_id
    """), {"character_id": character_id}).fetchone()
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Get memories for this character
    memories = db.execute(text("""
        SELECT 
            m.id, 
            m.user_id,
            u.username as user_name,
            m.memory_type, 
            m.category, 
            m.content, 
            m.importance,
            m.is_active,
            m.created_at
        FROM memory_entries m
        LEFT JOIN users u ON u.id::text = m.user_id::text
        WHERE m.character_id::text = :character_id
        ORDER BY m.importance DESC, m.created_at DESC
    """), {"character_id": character_id}).fetchall()
    
    # Convert to list of dicts
    memory_list = []
    for m in memories:
        created_at = m[8]
        if hasattr(created_at, 'strftime'):
            created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_at_str = str(created_at)
            
        memory_list.append({
            "id": m[0],
            "user_id": m[1],
            "user_name": m[2] or "Unknown",
            "memory_type": m[3] or "unknown",
            "category": m[4] or "general",
            "content": m[5],
            "importance": m[6] if m[6] is not None else 5,
            "is_active": m[7] if m[7] is not None else True,
            "created_at": created_at_str
        })
    
    # Group by type and category
    memories_by_type = {}
    for memory in memory_list:
        memory_type = memory["memory_type"]
        if memory_type not in memories_by_type:
            memories_by_type[memory_type] = {}
        
        category = memory["category"]
        if category not in memories_by_type[memory_type]:
            memories_by_type[memory_type][category] = []
        
        memories_by_type[memory_type][category].append(memory)
    
    return templates.TemplateResponse(
        "memories/character.html",
        {
            "request": request,
            "title": f"Memories for {character[1]}",
            "character": {
                "id": character[0],
                "name": character[1],
                "age": character[2],
                "gender": character[3]
            },
            "memories": memory_list,
            "memories_by_type": memories_by_type
        }
    )

@router.post("/add")
async def add_memory(
    character_id: str = Form(...),
    memory_type: str = Form(...),
    category: str = Form(...),
    content: str = Form(...),
    importance: int = Form(5),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Add a new memory"""
    # Get character details
    character = db.execute(text("""
        SELECT id FROM characters WHERE id::text = :character_id
    """), {"character_id": character_id}).fetchone()
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Get any user associated with this character
    user = db.execute(text("""
        SELECT DISTINCT sender_id 
        FROM messages 
        WHERE recipient_id::text = :character_id AND sender_type = 'user'
        LIMIT 1
    """), {"character_id": character_id}).fetchone()
    
    if not user:
        # Try the other direction
        user = db.execute(text("""
            SELECT DISTINCT recipient_id 
            FROM messages 
            WHERE sender_id::text = :character_id AND recipient_type = 'user'
            LIMIT 1
        """), {"character_id": character_id}).fetchone()
    
    user_id = user[0] if user else uuid.uuid4()
    
    # Add the memory
    memory_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    db.execute(text("""
        INSERT INTO memory_entries (
            id, character_id, user_id, memory_type, category, content, 
            importance, is_active, created_at, updated_at
        ) VALUES (
            :id, :character_id, :user_id, :memory_type, :category, :content,
            :importance, TRUE, :created_at, :updated_at
        )
    """), {
        "id": memory_id,
        "character_id": character_id,
        "user_id": str(user_id),
        "memory_type": memory_type,
        "category": category,
        "content": content,
        "importance": importance,
        "created_at": timestamp,
        "updated_at": timestamp
    })
    
    db.commit()
    
    return RedirectResponse(url=f"/memories/character/{character_id}", status_code=303)

@router.post("/delete/{memory_id}")
async def delete_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Delete a memory"""
    # Get memory details to determine the character
    memory = db.execute(text("""
        SELECT character_id FROM memory_entries
        WHERE id::text = :memory_id
    """), {"memory_id": memory_id}).fetchone()
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    character_id = str(memory[0])
    
    # Delete the memory
    db.execute(text("""
        DELETE FROM memory_entries
        WHERE id::text = :memory_id
    """), {"memory_id": memory_id})
    
    db.commit()
    
    return RedirectResponse(url=f"/memories/character/{character_id}", status_code=303)
