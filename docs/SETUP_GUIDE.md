# Sovereign AI Workbench — Setup & Deployment Guide

> **Smart India Hackathon (SIH 2026) — PS 26117**  
> *Cross-Platform Air-Gapped Setup Guide for macOS, Linux, and Windows 10/11*

--- ## Hardware & Software Prerequisites

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | macOS 13+, Ubuntu 20.04+, Windows 10/11 | macOS Sonoma / Ubuntu 22.04 LTS / Windows 11 |
| **CPU / GPU** | Apple M1 (8GB) / NVIDIA GTX 1660 (6GB VRAM) | Apple M2/M3 Pro (18GB+) / NVIDIA RTX 3080+ (12GB+ VRAM) |
| **RAM** | 16 GB | 32 GB |
| **Python** | 3.10 or higher | 3.11 / 3.12 |
| **Node.js** | v18.0 or higher | v20.0 (LTS) |
| **Ollama** | Installed locally (`http://127.0.0.1:11434`) | Latest Ollama release |

--- ## 1. Ollama Model Setup

1. **Install Ollama**:
   - **macOS / Linux**: Download from [Ollama.com](https://ollama.com) or run `curl -fsSL https://ollama.com/install.sh | sh`
   - **Windows**: Download the installer from [Ollama.com/download/windows](https://ollama.com/download/windows)

2. **Pull Required Open-Weight Models**:
   ```bash
   # Reasoning & Vision Model (Primary)
   ollama pull qwen3.5:4b-q4_K_M

   # Coding Sandbox Model
   ollama pull qwen2.5-coder:3b

   # RAG Vector Embedding Model
   ollama pull nomic-embed-text
   ```

--- ## 2. Python Environment Setup

1. **Clone Repository & Navigate to Directory**:
   ```bash
   git clone https://github.com/sathwik-anumandla/sovereign-agent.git
   cd sovereign-agent
   ```

2. **Create & Activate Virtual Environment**:
   - **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows (CMD / PowerShell)**:
     ```cmd
     python -m venv venv
     venv\Scripts\activate
     ```

3. **Install Python Dependencies**:
   ```bash
   pip install pydantic sympy pandas openpyxl python-docx python-pptx \
               opencv-python scikit-learn ollama langgraph \
               langgraph-checkpoint-sqlite paddleocr paddlex pypdfium2 \
               chromadb langchain-text-splitters uvicorn fastapi sse-starlette PyJWT
   ```

--- ## 3. Frontend Web UI Setup

```bash
cd frontend
npm install
cd ..
```

--- ## [START] 4. Launching the Workbench

All launcher scripts are located in the `scripts/` directory.

### macOS & Linux
```bash
./scripts/start_workbench.sh
```
To stop all services:
```bash
./scripts/stop_workbench.sh
```

### Windows (Command Prompt)
```cmd
scripts\start_workbench.bat
```
To stop all services:
```cmd
scripts\stop_workbench.bat
```

### Windows (PowerShell)
```powershell
.\scripts\start_workbench.ps1
```
To stop all services:
```powershell
.\scripts\stop_workbench.ps1
```

--- ## 5. Service Endpoints

Once started, access the workbench endpoints locally:

- **React Web Application**: `http://localhost:3000`
- **FastAPI REST API Docs**: `http://localhost:8000/docs`
- **Ollama API Server**: `http://127.0.0.1:11434`
- **Service Logs**: `logs/ollama.log`, `logs/backend.log`, `logs/frontend.log`

--- ## 6. Troubleshooting & Diagnostics

- **Scikit-Learn Version Mismatch (`multi_class` attribute error)**:
  If a model pickled on another machine fails, run:
  ```bash
  python scripts/train_router_classifier.py
  ```
- **Inspect SQLite Thread Checkpoints**:
  To inspect conversation thread history:
  ```bash
  python scripts/inspect_run.py <thread_id>
  ```
- **Run Integration Test Suite**:
  ```bash
  python tests/run_all.py
  ```
