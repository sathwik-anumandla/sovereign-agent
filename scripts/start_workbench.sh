#!/usr/bin/env bash
# ==============================================================================
# Sovereign AI Workbench Unified Startup Launcher (SIH PS 26117)
# ==============================================================================
# Automatically verifies dependencies, starts Ollama server, launches FastAPI
# backend (port 8000), and starts the Vite React frontend (port 3000).
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

mkdir -p logs

echo "======================================================================"
echo "      [START] STARTING SOVEREIGN AI WORKBENCH (SIH PS 26117)"
echo "======================================================================"

# 1. Check & Start Ollama Server
echo -n "[1/4] Checking Ollama server (http://127.0.0.1:11434)... "
if curl -s -f http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo "[OK] Running"
else
    echo "[WARNING] Not running. Launching 'ollama serve'..."
    ollama serve > logs/ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo "     Ollama started in background (PID: $OLLAMA_PID, log: logs/ollama.log)"
    
    # Wait for Ollama to become ready
    MAX_WAIT=10
    COUNT=0
    while ! curl -s -f http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
        sleep 1
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $MAX_WAIT ]; then
            echo "[ERROR] Error: Ollama failed to respond after ${MAX_WAIT}s. Check logs/ollama.log"
            exit 1
        fi
    done
    echo "     Ollama server is now ready!"
fi

# 2. Check Installed Ollama Models
echo "[2/4] Verifying required Ollama model tags..."
INSTALLED_MODELS=$(curl -s http://127.0.0.1:11434/api/tags | python3 -c "import sys, json; data=json.load(sys.stdin); print(' '.join([m.get('name','') for m in data.get('models',[])]))")
echo "     Available models: $INSTALLED_MODELS"

# 3. Check & Start FastAPI Backend Server
echo -n "[3/4] Checking FastAPI backend server (http://localhost:8000)... "
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "[OK] Running"
else
    echo "[WARNING] Not running. Launching FastAPI backend..."
    python3 server.py > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "     Backend started in background (PID: $BACKEND_PID, log: logs/backend.log)"
    
    # Wait for backend to be ready
    MAX_WAIT=10
    COUNT=0
    while ! curl -s http://localhost:8000/docs > /dev/null 2>&1; do
        sleep 1
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $MAX_WAIT ]; then
            echo "[ERROR] Error: Backend failed to respond after ${MAX_WAIT}s. Check logs/backend.log"
            exit 1
        fi
    done
    echo "     FastAPI backend API is ready at http://localhost:8000"
fi

# 4. Check & Start React Frontend
echo -n "[4/4] Checking React Frontend dev server (http://localhost:3000)... "
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "[OK] Running"
else
    echo "[WARNING] Not running. Launching React frontend..."
    (cd frontend && npm run dev > ../logs/frontend.log 2>&1 &)
    FRONTEND_PID=$!
    echo "     Frontend started in background (PID: $FRONTEND_PID, log: logs/frontend.log)"
    
    # Wait for frontend to be ready
    MAX_WAIT=15
    COUNT=0
    while ! curl -s http://localhost:3000 > /dev/null 2>&1; do
        sleep 1
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $MAX_WAIT ]; then
            echo "[WARNING] Frontend startup taking time. Access http://localhost:3000 shortly."
            break
        fi
    done
fi

echo "======================================================================"
echo "  [SUCCESS] SOVEREIGN AGENT AI WORKBENCH IS UP AND RUNNING!"
echo "======================================================================"
echo "  • React Frontend UI : http://localhost:3000"
echo "  • FastAPI API Docs  : http://localhost:8000/docs"
echo "  • Ollama Server     : http://127.0.0.1:11434"
echo "  • Service Logs      : logs/ollama.log, logs/backend.log, logs/frontend.log"
echo "======================================================================"
