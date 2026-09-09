# scripts/start_postgres.ps1 - Windows PowerShell launcher for Docker Desktop

if (-not $env:POSTGRES_PORT) { $env:POSTGRES_PORT = "5432" }

Write-Host "[INFO] Starting PostgreSQL + pgvector container via Docker Compose on port $env:POSTGRES_PORT..." -ForegroundColor Cyan
docker compose up -d postgres

Write-Host "[SUCCESS] PostgreSQL + pgvector is running at localhost:$env:POSTGRES_PORT (Database: sovereign_workbench)" -ForegroundColor Green
