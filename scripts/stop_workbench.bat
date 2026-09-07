@echo off
echo ======================================================================
echo       [STOP] STOPPING ALL SOVEREIGN AI WORKBENCH SERVICES (WINDOWS)
echo ======================================================================

echo • Stopping FastAPI backend server (port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo • Stopping React Frontend dev server (port 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo • Stopping Ollama local server process...
taskkill /F /IM ollama.exe >nul 2>&1
taskkill /F /IM "ollama app.exe" >nul 2>&1

echo ======================================================================
echo   [OK] ALL WORKBENCH SERVICES & OLLAMA SERVER STOPPED SUCCESSFULLY
echo ======================================================================
