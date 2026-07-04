# SupportOps Copilot — start web app (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "=== SupportOps Copilot ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment (first time only)..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "WARNING: .env file not found!" -ForegroundColor Red
    Write-Host "1. Copy .env.example to .env"
    Write-Host "2. Paste your real OpenAI key (starts with sk-)"
    Write-Host "3. Run this script again"
    Write-Host ""
    if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example — edit it and add your key." -ForegroundColor Yellow
        notepad .env
        exit 1
    }
}

Write-Host "Starting web app..." -ForegroundColor Green
Write-Host "Keep this window OPEN. Then open browser:" -ForegroundColor Green
Write-Host "  http://localhost:8501" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor DarkGray
Write-Host ""

.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true
