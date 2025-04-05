@echo off
powershell.exe -ExecutionPolicy Bypass -File "%~dp0cleanup_project.ps1"
echo.
echo Cleanup completed! Press any key to exit.
pause > nul
