@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."

echo ======================================================================
echo       [START] STARTING SOVEREIGN AI WORKBENCH (WINDOWS BATCH)
echo ======================================================================

if not exist logs mkdir logs

rem 1. Check Ollama Server
echo | set /p="[1/4] Checking Ollama server (http://127.0.0.1:11434)... "
curl -s -f http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Running
) else (
    echo [WARNING] Not running. Launching 'ollama serve'...
    start /B ollama serve > logs\ollama.log 2>&1
    echo      Ollama started in background (log: logs\ollama.log)
    timeout /t 3 /nobreak >nul
)

rem 2. Verify Models
echo [2/4] Verifying required Ollama model tags...
curl -s http://127.0.0.1:11434/api/tags > logs\models_temp.json 2>nul
python -c "import json; data=json.load(open('logs/models_temp.json')); print('     Available models:', ' '.join([m.get('name','') for m in data.get('models',[])]))" 2>nul
if exist logs\models_temp.json del logs\models_temp.json

rem 3. Check & Start FastAPI Backend
echo | set /p="[3/4] Checking FastAPI backend server (http://localhost:8000)... "
curl -s http://localhost:8000/docs >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Running
) else (
    echo [WARNING] Not running. Launching FastAPI backend...
    start /B python server.py > logs\backend.log 2>&1
    echo      FastAPI backend started in background (log: logs\backend.log)
    timeout /t 3 /nobreak >nul
)

rem 4. Check & Start React Frontend
echo | set /p="[4/4] Checking React Frontend dev server (http://localhost:3000)... "
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Running
) else (
    echo [WARNING] Not running. Launching React frontend...
    start /B cmd /c "cd frontend && npm run dev > ..\logs\frontend.log 2>&1"
    echo      Frontend started in background (log: logs\frontend.log)
)

echo ======================================================================
echo   [SUCCESS] SOVEREIGN AGENT AI WORKBENCH IS UP AND RUNNING!
echo ======================================================================
echo   • React Frontend UI : http://localhost:3000
echo   • FastAPI API Docs  : http://localhost:8000/docs
echo   • Ollama Server     : http://127.0.0.1:11434
echo   • Service Logs      : logs\ollama.log, logs\backend.log, logs\frontend.log
echo ======================================================================
