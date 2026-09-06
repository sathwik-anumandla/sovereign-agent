#!/usr/bin/env bash
# ==============================================================================
# Sovereign AI Workbench Stop Script (SIH PS 26117)
# ==============================================================================
# Gracefully stops running FastAPI backend (port 8000), React frontend (port 3000),
# and the local Ollama server process.
# ==============================================================================

echo "======================================================================"
echo "      🛑 STOPPING ALL SOVEREIGN AI WORKBENCH SERVICES"
echo "======================================================================"

# 1. Stop FastAPI backend on port 8000
BACKEND_PIDS=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$BACKEND_PIDS" ]; then
    echo "• Stopping FastAPI backend server (PIDs: $BACKEND_PIDS)..."
    kill -9 $BACKEND_PIDS 2>/dev/null || true
    echo "  Backend stopped."
else
    echo "• FastAPI backend server is not running."
fi

# 2. Stop React Vite frontend on port 3000
FRONTEND_PIDS=$(lsof -ti :3000 2>/dev/null || true)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "• Stopping React Frontend dev server (PIDs: $FRONTEND_PIDS)..."
    kill -9 $FRONTEND_PIDS 2>/dev/null || true
    echo "  Frontend stopped."
else
    echo "• React Frontend dev server is not running."
fi

# 3. Stop Ollama local server process
if pgrep -f "ollama serve" > /dev/null 2>&1 || pgrep -x "ollama" > /dev/null 2>&1; then
    echo "• Stopping Ollama local server..."
    pkill -f "ollama serve" 2>/dev/null || pkill -x "ollama" 2>/dev/null || true
    echo "  Ollama server stopped."
else
    echo "• Ollama server is not running."
fi

echo "======================================================================"
echo "  ✅ ALL WORKBENCH SERVICES & OLLAMA SERVER STOPPED SUCCESSFULLY"
echo "======================================================================"
