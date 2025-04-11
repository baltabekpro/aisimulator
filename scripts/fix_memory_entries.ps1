# PowerShell script to fix memory entries database schema

Write-Host "Fixing memory entries database schema..." -ForegroundColor Cyan

# Go to project root directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir

# Set location to the root directory
Set-Location -Path $rootDir

# Run the Python fix script
python -m scripts.fix_memory_schema

Write-Host "Fix script completed!" -ForegroundColor Green