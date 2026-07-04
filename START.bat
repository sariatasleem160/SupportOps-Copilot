@echo off
title SupportOps Copilot - Web Server
cd /d "%~dp0"

echo.
echo ========================================
echo   SupportOps Copilot - Starting...
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Installing packages first time only...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

if not exist "config.env" (
    echo.
    echo Creating config.env - paste your Anthropic key, save, run START.bat again.
    copy /Y .env.example config.env >nul
    notepad config.env
    pause
    exit /b 1
)

echo [OK] Using config.env for Anthropic API key
echo [OK] Server starting...
echo.
echo   Keep this window OPEN
echo   Open browser: http://127.0.0.1:8501
echo.
echo   Press Ctrl+C to stop.
echo.

.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501

pause
