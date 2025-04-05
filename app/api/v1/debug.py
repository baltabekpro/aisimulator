"""
Debug endpoints for development and testing purposes.
These endpoints should be disabled in production.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import UUID4
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from uuid import UUID
import os
from pathlib import Path
import json

from app.db.session import get_db
from app.auth.jwt import get_current_user, get_current_user_optional
from core.models import User
from core.utils.conversation_logger import get_recent_conversations

router = APIRouter()

@router.get("/conversations/{character_id}")
async def get_character_conversations(
    character_id: UUID,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> List[Dict[str, Any]]:
    """
    Get recent conversation logs for a character.
    This endpoint is for debugging purposes.
    
    Args:
        character_id: Character ID
        limit: Maximum number of logs to return
        
    Returns:
        List of conversation logs
    """
    # Check if user is admin
    if not current_user or not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access debug data"
        )
    
    # Get recent conversations
    logs = get_recent_conversations(str(character_id), limit)
    
    return logs

@router.get("/logs-status")
async def logs_status(
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get status of conversation logging.
    
    Returns:
        Status information
    """
    try:
        from pathlib import Path
        
        # Get log directory
        log_dir = Path("logs/conversations")
        
        # Check if directory exists
        exists = log_dir.exists()
        
        # Count files and directories
        character_dirs = []
        total_files = 0
        
        if exists:
            # Get all character directories
            for char_dir in log_dir.iterdir():
                if char_dir.is_dir():
                    # Count files in this directory
                    files = list(char_dir.glob("*.json"))
                    file_count = len(files)
                    
                    # Get most recent file
                    most_recent = None
                    if files:
                        most_recent = max(files, key=lambda x: x.stat().st_mtime)
                        most_recent = {
                            "path": str(most_recent),
                            "timestamp": most_recent.stat().st_mtime
                        }
                    
                    # Add to character directories
                    character_dirs.append({
                        "character_id": char_dir.name,
                        "file_count": file_count,
                        "most_recent": most_recent
                    })
                    
                    total_files += file_count
        
        return {
            "logs_enabled": True,
            "logs_directory": str(log_dir),
            "logs_directory_exists": exists,
            "character_count": len(character_dirs),
            "total_log_files": total_files,
            "character_directories": character_dirs
        }
    except Exception as e:
        return {
            "logs_enabled": False,
            "error": str(e)
        }

@router.post("/clear-messages")
async def clear_all_messages(
    character_id: Optional[str] = None,
    clear_all: bool = False,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Очистить историю сообщений в базе данных.
    Требует прав администратора.
    
    Args:
        character_id: ID персонажа (если нужно очистить только для него)
        clear_all: Флаг для очистки всех сообщений
        
    Returns:
        Информация о результате операции
    """
    # Проверяем права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    
    try:
        # Импортируем утилиту очистки сообщений - updated import path
        from utils.clear_messages_utils import clear_messages
        
        # Проверяем параметры
        if not clear_all and not character_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Укажите character_id или установите clear_all=true"
            )
        
        # Очищаем сообщения
        deleted_count = clear_messages(character_id=character_id, clear_all=clear_all)
        
        # Возвращаем результат
        return {
            "success": deleted_count > 0,
            "deleted_count": deleted_count,
            "message": f"Удалено {deleted_count} сообщений" if deleted_count > 0 else "Сообщения не найдены"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при очистке сообщений: {str(e)}"
        )

@router.get("/clear-messages-ui", response_class=HTMLResponse)
async def clear_messages_ui():
    """
    Веб-интерфейс для очистки истории сообщений
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Очистка истории сообщений</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #e53935;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            .warning {
                background-color: #ffebee;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border-left: 4px solid #e53935;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            .form-group input[type="text"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                box-sizing: border-box;
            }
            .btn {
                display: inline-block;
                padding: 10px 20px;
                background-color: #e53935;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            .btn:hover {
                background-color: #c62828;
            }
            .btn-secondary {
                background-color: #757575;
            }
            .btn-secondary:hover {
                background-color: #616161;
            }
            .back-button {
                display: inline-block;
                background-color: #607d8b;
                color: white;
                padding: 8px 16px;
                text-decoration: none;
                border-radius: 4px;
                margin-bottom: 20px;
            }
            .result {
                margin-top: 20px;
                padding: 15px;
                border-radius: 5px;
                display: none;
            }
            .success {
                background-color: #e8f5e9;
                border-left: 4px solid #4caf50;
            }
            .error {
                background-color: #ffebee;
                border-left: 4px solid #e53935;
            }
        </style>
        <script>
            async function clearMessages(clearAll = false) {
                const resultDiv = document.getElementById('result');
                resultDiv.className = 'result';
                resultDiv.style.display = 'none';
                
                try {
                    // Если clearAll=true, очищаем все сообщения
                    // Иначе очищаем для конкретного персонажа
                    let url = '/api/v1/debug/clear-messages';
                    let params = new URLSearchParams();
                    
                    if (clearAll) {
                        params.append('clear_all', 'true');
                    } else {
                        const characterId = document.getElementById('character_id').value.trim();
                        if (!characterId) {
                            alert('Введите ID персонажа');
                            return;
                        }
                        params.append('character_id', characterId);
                    }
                    
                    // Делаем запрос к API
                    const response = await fetch(`${url}?${params.toString()}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    const data = await response.json();
                    
                    // Показываем результат
                    resultDiv.style.display = 'block';
                    
                    if (response.ok) {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `<h3>Успешно!</h3><p>${data.message}</p>`;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<h3>Ошибка!</h3><p>${data.detail || 'Произошла ошибка при очистке сообщений'}</p>`;
                    }
                } catch (error) {
                    console.error('Ошибка:', error);
                    resultDiv.style.display = 'block';
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `<h3>Ошибка!</h3><p>${error.message || 'Произошла неизвестная ошибка'}</p>`;
                }
            }
            
            // Подтверждение удаления всех сообщений
            function confirmClearAll() {
                if (confirm('ВНИМАНИЕ! Вы уверены, что хотите удалить ВСЕ сообщения? Это действие необратимо!')) {
                    clearMessages(true);
                }
            }
        </script>
    </head>
    <body>
        <div class="container">
            <a href="/api/v1/debug/chat-logs" class="back-button">← Назад к логам</a>
            
            <h1>Очистка истории сообщений</h1>
            
            <div class="warning">
                <strong>Внимание!</strong> Удаление сообщений - необратимая операция. 
                Удаленные сообщения нельзя восстановить.
            </div>
            
            <div class="form-group">
                <label for="character_id">ID персонажа:</label>
                <input type="text" id="character_id" placeholder="Введите UUID персонажа для удаления его сообщений">
            </div>
            
            <div>
                <button class="btn" onclick="clearMessages()">Очистить сообщения для персонажа</button>
                <button class="btn btn-secondary" onclick="confirmClearAll()">Очистить ВСЕ сообщения</button>
            </div>
            
            <div id="result" class="result"></div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/chat-logs", response_class=HTMLResponse)
async def view_chat_logs_ui():
    """
    User-friendly interface to browse chat logs
    """
    logs_dir = Path("logs/conversations")
    
    # Check if directory exists
    if not logs_dir.exists():
        return HTMLResponse(content="""
        <html>
            <head><title>Chat Logs</title></head>
            <body>
                <h1>Logs directory not found</h1>
                <p>No conversation logs found. The logs directory does not exist.</p>
            </body>
        </html>
        """)
    
    # Get all character directories
    character_dirs = [d for d in logs_dir.iterdir() if d.is_dir()]
    
    if not character_dirs:
        return HTMLResponse(content="""
        <html>
            <head><title>Chat Logs</title></head>
            <body>
                <h1>No conversations found</h1>
                <p>No conversation logs found. Start chatting with AI characters to generate logs.</p>
            </body>
        </html>
        """)
    
    # Count files for each character and get the most recent file
    characters = []
    for char_dir in character_dirs:
        files = list(char_dir.glob("*.json"))
        if files:
            most_recent = max(files, key=lambda x: x.stat().st_mtime)
            
            # Try to get character name from any log file
            character_name = char_dir.name  # Default to directory name
            try:
                with open(most_recent, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    ai_response = data.get('ai_response', {}).get('processed', {})
                    if isinstance(ai_response, dict) and 'text' in ai_response:
                        character_name = f"Character {char_dir.name}"
            except:
                pass
                
            characters.append({
                "id": char_dir.name,
                "name": character_name,
                "file_count": len(files),
                "most_recent": most_recent.stat().st_mtime
            })
    
    # HTML content with basic styling
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chat Logs</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            .character-list {
                list-style: none;
                padding: 0;
            }
            .character-item {
                margin-bottom: 10px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 5px;
                border-left: 5px solid #2196F3;
            }
            .character-item h2 {
                margin-top: 0;
                color: #2196F3;
            }
            .file-count {
                color: #666;
                font-size: 0.9em;
            }
            .view-button {
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 10px;
            }
            .view-button:hover {
                background-color: #45a049;
            }
            .no-logs {
                padding: 20px;
                background-color: #ffe0e0;
                border-radius: 5px;
                color: #d32f2f;
            }
            .action-buttons {
                margin-top: 20px;
                padding: 15px;
                background-color: #f5f5f5;
                border-radius: 5px;
                text-align: center;
            }
            .danger-button {
                display: inline-block;
                background-color: #e53935;
                color: white;
                padding: 8px 16px;
                text-decoration: none;
                border-radius: 4px;
                margin: 10px;
            }
            .danger-button:hover {
                background-color: #c62828;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI Simulator Chat Logs</h1>
            
            <p>Select a character to view conversation logs.</p>
            
            <div class="action-buttons">
                <a href="/api/v1/debug/clear-messages-ui" class="danger-button">Очистить историю сообщений</a>
            </div>
            
            <ul class="character-list">
    """
    
    # Add characters to the list
    for character in sorted(characters, key=lambda x: x["most_recent"], reverse=True):
        import datetime
        most_recent_date = datetime.datetime.fromtimestamp(character["most_recent"]).strftime("%Y-%m-%d %H:%M:%S")
        
        html_content += f"""
        <li class="character-item">
            <h2>{character["name"]}</h2>
            <div class="file-count">{character["file_count"]} conversation logs</div>
            <div>Last activity: {most_recent_date}</div>
            <a href="/api/v1/debug/character-logs/{character["id"]}" class="view-button">View Logs</a>
        </li>
        """
    
    html_content += """
            </ul>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/character-logs/{character_id}", response_class=HTMLResponse)
async def view_character_logs(character_id: str):
    """
    View logs for a specific character
    """
    logs_dir = Path("logs/conversations") / character_id
    
    if not logs_dir.exists():
        return HTMLResponse(content=f"<h1>No logs found for character {character_id}</h1>")
    
    # Get all JSON log files
    log_files = list(logs_dir.glob("*.json"))
    
    if not log_files:
        return HTMLResponse(content=f"<h1>No log files found for character {character_id}</h1>")
    
    # Sort by modification time (newest first)
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Generate HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chat Logs for Character {character_id}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }}
            .log-list {{
                list-style: none;
                padding: 0;
            }}
            .log-item {{
                margin-bottom: 10px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }}
            .log-item:hover {{
                background-color: #f0f0f0;
            }}
            .log-date {{
                font-weight: bold;
                color: #2196F3;
            }}
            .back-button {{
                display: inline-block;
                background-color: #607d8b;
                color: white;
                padding: 8px 16px;
                text-decoration: none;
                border-radius: 4px;
                margin-bottom: 20px;
            }}
            .back-button:hover {{
                background-color: #546e7a;
            }}
            .view-button {{
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 5px 10px;
                text-decoration: none;
                border-radius: 4px;
                margin-left: 10px;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/api/v1/debug/chat-logs" class="back-button">← Back to All Characters</a>
            
            <h1>Chat Logs for Character {character_id}</h1>
            
            <p>Total logs: {len(log_files)}</p>
            
            <ul class="log-list">
    """
    
    # Add each log file to the list
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            datetime_str = data.get("datetime", "Unknown date")
            user_message = data.get("user_message", "")
            ai_response = data.get("ai_response", {}).get("processed", {})
            
            if isinstance(ai_response, dict) and "text" in ai_response:
                ai_text = ai_response["text"]
            else:
                ai_text = str(ai_response)
            
            # Truncate messages if too long
            if len(user_message) > 100:
                user_message = user_message[:100] + "..."
                
            if len(ai_text) > 100:
                ai_text = ai_text[:100] + "..."
                
            html_content += f"""
            <li class="log-item">
                <div class="log-date">{datetime_str}</div>
                <div><strong>User:</strong> {user_message}</div>
                <div><strong>AI:</strong> {ai_text}</div>
                <a href="/api/v1/debug/view-log/{character_id}/{log_file.name}" class="view-button">View Full Log</a>
                <a href="/api/v1/debug/raw-log/{character_id}/{log_file.name}" class="view-button">Raw JSON</a>
            </li>
            """
        except Exception as e:
            html_content += f"""
            <li class="log-item">
                <div class="log-date">Error reading file {log_file.name}</div>
                <div><strong>Error:</strong> {str(e)}</div>
            </li>
            """
    
    html_content += """
            </ul>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/view-log/{character_id}/{log_file}", response_class=HTMLResponse)
async def view_log_content(character_id: str, log_file: str):
    """
    View the content of a specific log file
    """
    file_path = Path("logs/conversations") / character_id / log_file
    
    if not file_path.exists():
        return HTMLResponse(content=f"<h1>Log file not found</h1>")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        datetime_str = data.get("datetime", "Unknown date")
        user_message = data.get("user_message", "")
        
        # Get raw and processed responses
        ai_response_raw = data.get("ai_response", {}).get("raw", "")
        ai_response_processed = data.get("ai_response", {}).get("processed", {})
        
        if isinstance(ai_response_processed, dict) and "text" in ai_response_processed:
            ai_text = ai_response_processed["text"]
            emotion = ai_response_processed.get("emotion", "Unknown")
            relationship_changes = ai_response_processed.get("relationship_changes", {})
        else:
            ai_text = str(ai_response_processed)
            emotion = "Unknown"
            relationship_changes = {}
        
        # HTML content with styled components
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Conversation Log Details</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    line-height: 1.6;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }}
                .back-button {{
                    display: inline-block;
                    background-color: #607d8b;
                    color: white;
                    padding: 8px 16px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-bottom: 20px;
                }}
                .back-button:hover {{
                    background-color: #546e7a;
                }}
                .date {{
                    color: #666;
                    font-style: italic;
                    margin-bottom: 20px;
                }}
                .message-container {{
                    margin-bottom: 30px;
                }}
                .message-header {{
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .user-message {{
                    background-color: #e3f2fd;
                    padding: 15px;
                    border-radius: 5px;
                    white-space: pre-wrap;
                }}
                .ai-message {{
                    background-color: #f1f8e9;
                    padding: 15px;
                    border-radius: 5px;
                    white-space: pre-wrap;
                }}
                .raw-response {{
                    background-color: #f5f5f5;
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    white-space: pre-wrap;
                    font-family: monospace;
                    margin-top: 10px;
                    font-size: 0.9em;
                    overflow-x: auto;
                }}
                .metadata {{
                    margin-top: 10px;
                    padding: 10px;
                    background-color: #fafafa;
                    border-radius: 5px;
                }}
                .metadata-item {{
                    margin-bottom: 5px;
                }}
                .tab-buttons {{
                    display: flex;
                    margin-bottom: 10px;
                }}
                .tab-button {{
                    padding: 8px 16px;
                    background-color: #f0f0f0;
                    border: 1px solid #ddd;
                    cursor: pointer;
                    margin-right: 5px;
                }}
                .tab-button.active {{
                    background-color: #fff;
                    border-bottom: 1px solid #fff;
                }}
                .tab-content {{
                    display: none;
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 5px 5px;
                }}
                .tab-content.active {{
                    display: block;
                }}
                .memory-box {{
                    background-color: #fff8e1;
                    padding: 15px;
                    border-radius: 5px;
                    margin-top: 10px;
                }}
                .memory-item {{
                    margin-bottom: 5px;
                }}
            </style>
            <script>
                function showTab(tabId) {{
                    // Hide all tabs
                    document.querySelectorAll('.tab-content').forEach(tab => {{
                        tab.classList.remove('active');
                    }});
                    
                    // Remove active class from all buttons
                    document.querySelectorAll('.tab-button').forEach(button => {{
                        button.classList.remove('active');
                    }});
                    
                    // Show the selected tab
                    document.getElementById(tabId).classList.add('active');
                    
                    // Add active class to the clicked button
                    document.querySelector(`[onclick="showTab('${{tabId}}')"]`).classList.add('active');
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <a href="/api/v1/debug/character-logs/{character_id}" class="back-button">← Back to Logs</a>
                
                <h1>Conversation Log Details</h1>
                
                <div class="date">Timestamp: {datetime_str}</div>
                
                <div class="message-container">
                    <div class="message-header">User Message:</div>
                    <div class="user-message">{user_message}</div>
                </div>
                
                <div class="message-container">
                    <div class="message-header">AI Response:</div>
                    <div class="ai-message">{ai_text}</div>
                    
                    <div class="metadata">
                        <div class="metadata-item"><strong>Emotion:</strong> {emotion}</div>
                        
                        <div class="metadata-item"><strong>Relationship Changes:</strong></div>
                        <ul>
        """
        
        # Add relationship changes
        for rel_type, value in relationship_changes.items():
            html_content += f"<li>{rel_type}: {value}</li>"
            
        html_content += """
                        </ul>
                    </div>
                </div>
                
                <div class="tab-buttons">
                    <button class="tab-button active" onclick="showTab('rawResponse')">Raw AI Response</button>
                    <button class="tab-button" onclick="showTab('conversationHistory')">Conversation History</button>
                    <button class="tab-button" onclick="showTab('systemPrompt')">System Prompt</button>
                </div>
                
                <div id="rawResponse" class="tab-content active">
                    <div class="message-header">Raw AI Response:</div>
                    <div class="raw-response">
        """
        
        # Add raw response
        html_content += ai_response_raw.replace("<", "&lt;").replace(">", "&gt;")
        
        html_content += """
                    </div>
                </div>
                
                <div id="conversationHistory" class="tab-content">
                    <div class="message-header">Conversation History:</div>
        """
        
        # Add conversation history
        conversation_history = data.get("conversation_history", [])
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                
                if role == "system":
                    html_content += f"<div style='background-color: #e8eaf6; padding: 10px; margin-bottom: 5px; border-radius: 5px;'><strong>System:</strong> {content[:100]}{'...' if len(content) > 100 else ''}</div>"
                elif role == "user":
                    html_content += f"<div style='background-color: #e3f2fd; padding: 10px; margin-bottom: 5px; border-radius: 5px;'><strong>User:</strong> {content}</div>"
                elif role == "assistant":
                    html_content += f"<div style='background-color: #f1f8e9; padding: 10px; margin-bottom: 5px; border-radius: 5px;'><strong>Assistant:</strong> {content}</div>"
                else:
                    html_content += f"<div style='background-color: #f5f5f5; padding: 10px; margin-bottom: 5px; border-radius: 5px;'><strong>{role}:</strong> {content}</div>"
        else:
            html_content += "<p>No conversation history available</p>"
        
        html_content += """
                </div>
                
                <div id="systemPrompt" class="tab-content">
                    <div class="message-header">System Prompt:</div>
                    <div class="raw-response">
        """
        
        # Add system prompt
        system_prompt = data.get("system_prompt", "No system prompt available")
        html_content += system_prompt.replace("<", "&lt;").replace(">", "&gt;")
        
        html_content += """
                    </div>
                </div>
        """
        
        # Add memory information if available
        memory_data = None
        if isinstance(ai_response_processed, dict) and "memory" in ai_response_processed:
            memory_data = ai_response_processed["memory"]
        
        if memory_data:
            html_content += """
                <div class="memory-box">
                    <div class="message-header">Memory Information Extracted:</div>
            """
            
            if isinstance(memory_data, list):
                for memory in memory_data:
                    if isinstance(memory, dict):
                        memory_type = memory.get("type", "Unknown")
                        memory_category = memory.get("category", "")
                        memory_content = memory.get("content", "")
                        
                        html_content += f"""
                        <div class="memory-item">
                            <strong>{memory_type}{f' ({memory_category})' if memory_category else ''}:</strong> {memory_content}
                        </div>
                        """
            else:
                html_content += f"<div class='memory-item'>{str(memory_data)}</div>"
                
            html_content += """
                </div>
            """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        return HTMLResponse(content=f"""
        <h1>Error reading log file</h1>
        <p>An error occurred while processing the log file: {str(e)}</p>
        <a href="/api/v1/debug/character-logs/{character_id}">Back to logs</a>
        """)

@router.get("/raw-log/{character_id}/{log_file}")
async def get_raw_log(character_id: str, log_file: str):
    """
    Return the raw JSON log file
    """
    file_path = Path("logs/conversations") / character_id / log_file
    
    if not file_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "Log file not found"}
        )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error reading log file: {str(e)}"}
        )
