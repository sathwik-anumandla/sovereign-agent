# PowerShell stop script for Sovereign AI Workbench on Windows
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "      [STOP] STOPPING ALL SOVEREIGN AI WORKBENCH SERVICES (WINDOWS)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Kill port 8000
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "• Stopping FastAPI backend server (PID: $($port8000.OwningProcess))..." -ForegroundColor Yellow
    Stop-Process -Id $port8000.OwningProcess -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "• FastAPI backend server is not running." -ForegroundColor Gray
}

# Kill port 3000
$port3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($port3000) {
    Write-Host "• Stopping React Frontend dev server (PID: $($port3000.OwningProcess))..." -ForegroundColor Yellow
    Stop-Process -Id $port3000.OwningProcess -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "• React Frontend dev server is not running." -ForegroundColor Gray
}

# Kill Ollama
$ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollamaProc) {
    Write-Host "• Stopping Ollama local server process..." -ForegroundColor Yellow
    Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "• Ollama server is not running." -ForegroundColor Gray
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  [OK] ALL WORKBENCH SERVICES & OLLAMA SERVER STOPPED SUCCESSFULLY" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
