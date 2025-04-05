REM filepath: c:\Users\workb\Downloads\AiSimulator\organize_files.bat
@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo AI Simulator Project Organization Tool
echo ==================================================
echo.
echo This script will organize files and clean up the project structure.
echo.
echo Press any key to start organization...
pause > nul

REM Create necessary directories if they don't exist
echo Creating directory structure...
mkdir "tools\diagnostics" 2>nul
mkdir "bots" 2>nul
mkdir "scripts" 2>nul
mkdir "db_tools" 2>nul
mkdir "_temp_files" 2>nul
mkdir "docs" 2>nul
mkdir "logs\archive" 2>nul

REM Create __init__.py files in new directories
echo Creating Python package structure...
echo. > "tools\__init__.py"
echo. > "tools\diagnostics\__init__.py"
echo. > "bots\__init__.py"
echo. > "scripts\__init__.py"
echo. > "db_tools\__init__.py"

REM Move diagnostic tools to proper location
echo Moving diagnostic tools to tools\diagnostics...
move /Y "tools\debug_tg_message_issue.py" "tools\diagnostics\" 2>nul
move /Y "tools\verify_models.py" "tools\diagnostics\" 2>nul
move /Y "tools\analyze_conversations.py" "tools\diagnostics\" 2>nul
move /Y "tools\analyze_api_requests.py" "tools\diagnostics\" 2>nul
move /Y "tools\analyze_message_flow.py" "tools\diagnostics\" 2>nul
move /Y "tools\api_log_analyzer.py" "tools\diagnostics\" 2>nul
move /Y "tools\test_api_routes.py" "tools\diagnostics\" 2>nul

REM Move bot files to bots directory
echo Moving bot files to bots directory...
if exist "telegram_bot_aiogram.py" (
    move /Y "telegram_bot_aiogram.py" "bots\" 2>nul
)
if exist "telegram\bot.py" (
    mkdir "bots\telegram" 2>nul
    move /Y "telegram\bot.py" "bots\telegram\" 2>nul
    echo. > "bots\telegram\__init__.py"
)

REM Move database tools to db_tools
echo Moving database tools to db_tools directory...
if exist "migrate_db.py" (
    move /Y "migrate_db.py" "db_tools\" 2>nul
)
if exist "scripts\migrate_db.py" (
    move /Y "scripts\migrate_db.py" "db_tools\" 2>nul
)

REM Move PowerShell scripts to scripts directory
echo Moving utility scripts to scripts directory...
move /Y "cleanup_project.ps1" "scripts\" 2>nul
move /Y "run_cleanup.ps1" "scripts\" 2>nul
move /Y "organize_project.ps1" "scripts\" 2>nul

REM Move batch files to scripts directory
move /Y "cleanup.bat" "scripts\" 2>nul
move /Y "run_telegram_bot.bat" "scripts\" 2>nul
move /Y "run_migrations.bat" "scripts\" 2>nul

REM Create proper run scripts that point to the new locations
echo Creating updated run scripts...
echo @echo off > "run_cleanup.bat"
echo powershell.exe -ExecutionPolicy Bypass -File "%%~dp0scripts\cleanup_project.ps1" >> "run_cleanup.bat"
echo pause >> "run_cleanup.bat"

echo @echo off > "run_bot.bat"
echo python -m bots.telegram_bot_aiogram >> "run_bot.bat"
echo pause >> "run_bot.bat"

echo @echo off > "run_migrate.bat"
echo python -m db_tools.migrate_db >> "run_migrate.bat"
echo pause >> "run_migrate.bat"

REM Move debug files to temp directory
echo Moving debug files to temporary directory...
move /Y "debug_request_*.json" "_temp_files\" 2>nul
move /Y "*_analysis_report.json" "_temp_files\" 2>nul

REM Move documentation to docs directory
if exist "API_DOCS.md" (
    move /Y "API_DOCS.md" "docs\" 2>nul
)

REM Clean up Python cache files
echo Cleaning up Python cache files...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul

REM Archive old logs
echo Archiving old logs...
if exist "logs" (
    forfiles /p "logs" /s /m *.log /d -7 /c "cmd /c move @path logs\archive\ 2>nul" 2>nul
)

echo.
echo ==================================================
echo Project organization complete!
echo ==================================================
echo.
echo The following changes were made:
echo.
echo 1. Created organized directory structure
echo 2. Moved diagnostic tools to tools\diagnostics
echo 3. Moved bot files to bots directory
echo 4. Moved database tools to db_tools
echo 5. Moved scripts to scripts directory
echo 6. Created new run scripts for common operations
echo 7. Moved debug files to _temp_files
echo 8. Moved documentation to docs directory
echo 9. Cleaned up Python cache files
echo 10. Archived old log files
echo.
echo Run your application using the new batch files:
echo - run_bot.bat: Start the Telegram bot
echo - run_migrate.bat: Run database migrations
echo - run_cleanup.bat: Clean up project files
echo.
echo Press any key to exit...
pause > nul