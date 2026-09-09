@echo off
REM scripts/start_postgres.bat - Windows launcher for Docker Desktop

if "%POSTGRES_PORT%"=="" set POSTGRES_PORT=5432

echo [INFO] Starting PostgreSQL + pgvector container via Docker Compose on port %POSTGRES_PORT%...
docker compose up -d postgres

echo [SUCCESS] PostgreSQL + pgvector container started at localhost:%POSTGRES_PORT%.
