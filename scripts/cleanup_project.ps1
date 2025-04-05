<#
.SYNOPSIS
    Cleans up and organizes the AiSimulator project structure.

.DESCRIPTION
    This script organizes the project by:
    - Moving diagnostic tools to a dedicated directory
    - Organizing log files
    - Cleaning up temporary Python files
    - Creating a proper structure for utilities

.EXAMPLE
    .\cleanup_project.ps1
#>

# Create necessary directories if they don't exist
$diagnosticsDir = "c:\Users\workb\Downloads\AiSimulator\tools\diagnostics"
$tempDir = "c:\Users\workb\Downloads\AiSimulator\_temp_files"
$logsArchiveDir = "c:\Users\workb\Downloads\AiSimulator\logs\archive"

Write-Host "Creating necessary directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $diagnosticsDir -Force | Out-Null
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
New-Item -ItemType Directory -Path $logsArchiveDir -Force | Out-Null

# Move diagnostic tools to the diagnostics directory
$diagnosticTools = @(
    "debug_tg_message_issue.py",
    "verify_models.py",
    "analyze_conversations.py",
    "analyze_api_requests.py",
    "analyze_message_flow.py",
    "api_log_analyzer.py",
    "test_api_routes.py"
)

Write-Host "Moving diagnostic tools to $diagnosticsDir..." -ForegroundColor Cyan
foreach ($tool in $diagnosticTools) {
    $sourcePath = "c:\Users\workb\Downloads\AiSimulator\tools\$tool"
    if (Test-Path $sourcePath) {
        Move-Item -Path $sourcePath -Destination "$diagnosticsDir\" -Force
        Write-Host "  Moved $tool" -ForegroundColor Green
    }
}

# Move debug files to temp directory
Write-Host "Moving debug files to temporary directory..." -ForegroundColor Cyan
Get-ChildItem -Path "c:\Users\workb\Downloads\AiSimulator" -Filter "debug_request_*.json" | 
    ForEach-Object {
        Move-Item -Path $_.FullName -Destination "$tempDir\" -Force
        Write-Host "  Moved $($_.Name)" -ForegroundColor Green
    }

# Move analysis reports to temp directory
Get-ChildItem -Path "c:\Users\workb\Downloads\AiSimulator" -Filter "*_analysis_report.json" | 
    ForEach-Object {
        Move-Item -Path $_.FullName -Destination "$tempDir\" -Force
        Write-Host "  Moved $($_.Name)" -ForegroundColor Green
    }

# Archive old logs
$oldLogs = Get-ChildItem -Path "c:\Users\workb\Downloads\AiSimulator\logs" -Recurse -File |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }

if ($oldLogs.Count -gt 0) {
    Write-Host "Archiving $($oldLogs.Count) old log files..." -ForegroundColor Cyan
    foreach ($log in $oldLogs) {
        # Create the same directory structure inside archive folder
        $relativeDir = $log.DirectoryName.Replace("c:\Users\workb\Downloads\AiSimulator\logs\", "")
        $archiveTargetDir = Join-Path -Path $logsArchiveDir -ChildPath $relativeDir
        
        # Create target directory if it doesn't exist
        if (-not (Test-Path $archiveTargetDir)) {
            New-Item -ItemType Directory -Path $archiveTargetDir -Force | Out-Null
        }
        
        # Move the file
        Move-Item -Path $log.FullName -Destination $archiveTargetDir -Force
        Write-Host "  Archived $($log.Name)" -ForegroundColor Green
    }
}

# Clean up Python cache files
Write-Host "Cleaning up Python cache files..." -ForegroundColor Cyan
$cacheFiles = Get-ChildItem -Path "c:\Users\workb\Downloads\AiSimulator" -Recurse -Include "*.pyc", "__pycache__"
$cacheCount = 0

foreach ($cache in $cacheFiles) {
    if ($cache.PSIsContainer) {
        # It's a directory
        Remove-Item -Path $cache.FullName -Recurse -Force
        $cacheCount++
    } else {
        # It's a file
        Remove-Item -Path $cache.FullName -Force
        $cacheCount++
    }
}

Write-Host "  Removed $cacheCount cache files/directories" -ForegroundColor Green

# Create empty __init__.py files to ensure proper package structure
$initDirs = @(
    "c:\Users\workb\Downloads\AiSimulator\tools\diagnostics",
    "c:\Users\workb\Downloads\AiSimulator\utils"
)

Write-Host "Creating empty __init__.py files for proper package structure..." -ForegroundColor Cyan
foreach ($dir in $initDirs) {
    $initFile = Join-Path -Path $dir -ChildPath "__init__.py"
    if (-not (Test-Path $initFile)) {
        New-Item -ItemType File -Path $initFile -Force | Out-Null
        Write-Host "  Created $initFile" -ForegroundColor Green
    }
}

# Summary
Write-Host "`nProject cleanup completed!" -ForegroundColor Green
Write-Host "1. Diagnostic tools moved to: $diagnosticsDir"
Write-Host "2. Temporary files moved to: $tempDir"
Write-Host "3. Old logs archived to: $logsArchiveDir"
Write-Host "4. Python cache files cleaned up"
Write-Host "5. Package structure optimized"
Write-Host
Write-Host "To run the script:" -ForegroundColor Yellow
Write-Host "1. Open PowerShell"
Write-Host "2. Navigate to your project directory: cd c:\Users\workb\Downloads\AiSimulator"
Write-Host "3. Run the script: .\cleanup_project.ps1"
