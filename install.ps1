# AI Remote PC Control — Windows Production Installer
# Sets up Python virtual environment, dependencies, configuration, and background execution guide.

[CmdletBinding()]
param(
    [switch]$SkipVenv
)

$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "    AI Remote PC Control — Windows Installer        " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Check Python
Write-Host "`n[1/4] Checking Python environment..." -ForegroundColor Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.10+ from python.org."
}

$pyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "✓ Found Python $pyVersion" -ForegroundColor Green

# 2. Virtual Environment
$venvPath = Join-Path $PSScriptRoot "agent\.venv"
if (-not $SkipVenv) {
    Write-Host "`n[2/4] Setting up Python virtual environment..." -ForegroundColor Cyan
    if (-not (Test-Path $venvPath)) {
        python -m venv $venvPath
        Write-Host "✓ Created virtual environment at agent\.venv" -ForegroundColor Green
    } else {
        Write-Host "✓ Virtual environment already exists." -ForegroundColor Green
    }

    $pipExe = Join-Path $venvPath "Scripts\pip.exe"
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    & $pipExe install --upgrade pip
    & $pipExe install -r (Join-Path $PSScriptRoot "agent\requirements.txt")
    & $pipExe install pytest pywin32
    Write-Host "✓ Python packages installed successfully." -ForegroundColor Green
}

# 3. Environment configuration
Write-Host "`n[3/4] Initializing configuration..." -ForegroundColor Cyan
$envPath = Join-Path $PSScriptRoot ".env"
$examplePath = Join-Path $PSScriptRoot ".env.example"
if (-not (Test-Path $envPath)) {
    Copy-Item $examplePath $envPath
    Write-Host "✓ Created .env file from .env.example" -ForegroundColor Green
} else {
    Write-Host "✓ .env file already present." -ForegroundColor Green
}

# 4. Summary & Instructions
Write-Host "`n[4/4] Setup complete!" -ForegroundColor Green
Write-Host "`nQuick run commands (from PowerShell):" -ForegroundColor Yellow
Write-Host "  1. Start MCP Server:       .\agent\.venv\Scripts\python.exe agent\main.py"
Write-Host "  2. Start Streaming Server: .\agent\.venv\Scripts\python.exe streaming\server.py"
Write-Host "  3. Launch Desktop Viewer:  .\agent\.venv\Scripts\python.exe viewer\viewer.py"
Write-Host "====================================================" -ForegroundColor Cyan
