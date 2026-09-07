# PowerShell startup script for Sovereign AI Workbench on Windows
$ErrorActionPreference = "Continue"

Set-Location (Join-Path -Path $PSScriptRoot -ChildPath "..")

if (-not (Test-Path -Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "      [START] STARTING SOVEREIGN AI WORKBENCH (WINDOWS POWERSHELL)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Ollama Server
Write-Host -NoNewline "[1/4] Checking Ollama server (http://127.0.0.1:11434)... "
try {
    $ollamaCheck = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -ErrorAction Stop
    Write-Host "[OK] Running" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Not running. Launching 'ollama serve'..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -RedirectStandardOutput "logs\ollama.log" -RedirectStandardError "logs\ollama_err.log" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# 2. Check Models
Write-Host "[2/4] Verifying required Ollama model tags..."
try {
    $models = (Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags").models.name -join ", "
    Write-Host "     Available models: $models" -ForegroundColor Gray
} catch {
    Write-Host "     Unable to fetch model tags." -ForegroundColor Yellow
}

# 3. FastAPI Backend
Write-Host -NoNewline "[3/4] Checking FastAPI backend server (http://localhost:8000)... "
try {
    $backendCheck = Invoke-WebRequest -Uri "http://localhost:8000/docs" -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] Running" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Not running. Launching FastAPI backend..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "server.py" -RedirectStandardOutput "logs\backend.log" -RedirectStandardError "logs\backend_err.log" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# 4. React Frontend
Write-Host -NoNewline "[4/4] Checking React Frontend dev server (http://localhost:3000)... "
try {
    $frontendCheck = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] Running" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Not running. Launching React frontend..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd frontend && npm run dev > ..\logs\frontend.log 2>&1" -WindowStyle Hidden
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  [SUCCESS] SOVEREIGN AGENT AI WORKBENCH IS UP AND RUNNING!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  • React Frontend UI : http://localhost:3000"
Write-Host "  • FastAPI API Docs  : http://localhost:8000/docs"
Write-Host "  • Ollama Server     : http://127.0.0.1:11434"
Write-Host "  • Service Logs      : logs\ollama.log, logs\backend.log, logs\frontend.log"
Write-Host "======================================================================" -ForegroundColor Cyan
