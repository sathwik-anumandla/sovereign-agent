#!/usr/bin/env bash
# scripts/start_postgres.sh - Launches Postgres + pgvector via Docker Compose
# Supports macOS (Colima / Docker Desktop) and Linux

set -e

echo "[INFO] Checking Docker daemon status..."

if ! docker info >/dev/null 2>&1; then
    if command -v colima >/dev/null 2>&1; then
        echo "[INFO] Colima detected. Starting Colima Docker VM..."
        colima start
    else
        echo "[ERROR] Docker daemon is not running. Please start Docker Desktop or Colima."
        exit 1
    fi
fi

if [ -z "$POSTGRES_PORT" ]; then
    OCCUPIED_BY_OTHER=false
    if lsof -i :5432 >/dev/null 2>&1 || nc -z 127.0.0.1 5432 >/dev/null 2>&1; then
        if docker ps --filter "name=^sovereign_postgres$" --filter "status=running" --format '{{.Ports}}' | grep -q "5432->"; then
            export POSTGRES_PORT=5432
        else
            OCCUPIED_BY_OTHER=true
        fi
    fi

    if [ "$OCCUPIED_BY_OTHER" = true ]; then
        echo "[INFO] Host port 5432 is occupied by another service (e.g. gatekeeper-postgres). Defaulting POSTGRES_PORT to 5433."
        export POSTGRES_PORT=5433
    elif [ -z "$POSTGRES_PORT" ]; then
        export POSTGRES_PORT=5432
    fi
fi

echo "[INFO] Starting PostgreSQL + pgvector container via Docker Compose on port $POSTGRES_PORT..."
if docker compose version >/dev/null 2>&1; then
    docker compose up -d postgres
elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose up -d postgres
else
    echo "[ERROR] Neither 'docker compose' nor 'docker-compose' was found."
    exit 1
fi

echo "[INFO] Waiting for PostgreSQL container health check..."
until [ "$(docker inspect -f "{{.State.Health.Status}}" sovereign_postgres 2>/dev/null)" == "healthy" ]; do
    sleep 1
done

echo "[SUCCESS] PostgreSQL + pgvector is READY at localhost:$POSTGRES_PORT (Database: sovereign_workbench)"
