# Sovereign On-Premise Agentic AI Workbench

> **Smart India Hackathon (SIH) 2026 -- PS 26117**  
> *Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work*  
> Target Industry: Mangalore Refinery and Petrochemicals Limited (MRPL) / PSU / Defence / Air-Gapped Infrastructures

---

## Project Overview

An on-premise, air-gapped, zero-cloud AI agent workbench designed for confidential PSU operations, refinery management, and industrial engineering work. Runs entirely on local open-weight multimodal LLMs (Ollama engine) with strict workspace sandboxing, security audit trails, persistent SQLite workflow checkpointing, ReAct tool execution loops, and zero outbound network data leakage.

---

## Key Features

* **100% Air-Gapped Sovereignty**: Zero external API dependencies, running locally on Apple Silicon Metal GPU / CUDA.
* **Abstract Multi-Model Role Registry**: Decouples agent tasks into model roles (`reasoning` using `qwen3.5:4b-q4_K_M`, `coding` using `qwen2.5-coder:3b`, `vision`, `ocr`) with dynamic tag resolution and `keep_alive="5m"` VRAM caching.
* **3-Stage Waterfall Router**:
  1. *Stage 1 (Metadata)*: Code extension inspection guard (`.py`, `.ipynb`, `.js`, etc. -- `conf=1.00`).
  2. *Stage 2 (Keyword)*: Word-boundary precision heuristic (~35 intent terms -- `conf=0.85`).
  3. *Stage 3 (Classifier)*: Offline TF-IDF + Logistic Regression ML classifier for ambiguous prompts.
* **ReAct LangGraph Orchestrator Loop (Phase 6)**:
  * End-to-end execution pipeline (`START -> route -> infer -> (conditional) -> tool_node -> infer -> ... -> END`).
  * Ollama native function calling with dynamically generated Pydantic tool schemas (`OLLAMA_TOOL_SCHEMAS`).
  * Single `tool_node` dispatcher handling 3 failure stages:
    * Stage 1: Unknown tool name (`failure_type="unknown_tool"`)
    * Stage 2: Malformed tool arguments (`failure_type="invalid_args"`)
    * Stage 3: Tool execution failure (`failure_type="execution_error"`)
  * Loop safety iteration bounds (`max_tool_iterations=5`).
  * Persistent SQLite checkpointing (`workbench_checkpoints.db` via `SqliteSaver`) surviving process restarts.
  * Unique invocation `thread_id` tracing (via `uuid4`).
* **Audited Standalone Agent Tool Layer**:
  * `math_eval`: Safe symbolic math evaluation, calculus, LaTeX formatting, and step-by-step intermediate output via SymPy (zero raw `eval()`).
  * `file_io`: Workspace-bounded file operations (`/workspace/<session_id>/`) with path traversal guards and zero file deletion.
  * `code_sandbox`: Isolated Python code execution sandbox with hard timeout guards, plot capture, and execution timing.
  * `spreadsheet`: Pandas & OpenPyXL tabular data analysis layer (`filter`, `aggregate`, `compute`).
  * `doc_gen`: Deliverable generator producing formatted Word (`.docx`), PowerPoint (`.pptx`), and Excel (`.xlsx`) documents from shared content primitives.
  * `ocr_vlm`: Image preprocessing (deskewing/denoising), OCR engine execution, confidence heuristic routing, and VLM fallback.

---

## Project Architecture & Directory Structure

```text
sovereign-agent/
├── README.md                      # Comprehensive Architecture & Setup Guide
├── .gitignore                     # Git ignore rules for Python & local workspace
├── phase1_inference.py            # Local Ollama Inference SDK, Role Registry & Tool Calling
├── tool_interface.py              # Base Pydantic models, @audited_tool decorator, & Path Validator
├── train_router_classifier.py     # Offline ML training script for Stage 3 Router Classifier
├── inspect_run.py                 # Standalone thread checkpoint history inspector
├── run_all_tests.py               # Master integration test runner across all phases (1-6)
├── test_tools.py                  # Standalone test suite for all 6 agent tools
├── test_router.py                 # Standalone test suite for 3-stage waterfall router
├── test_orchestrator.py           # Standalone test suite for LangGraph orchestrator
├── test_phase6.py                 # Standalone test suite for Phase 6 ReAct tool loop
├── router_vectorizer.pkl          # Trained TF-IDF Vectorizer artifact
├── router_classifier.pkl          # Trained Logistic Regression Classifier artifact
│
├── orchestrator/                  # ReAct LangGraph Orchestrator Package
│   ├── __init__.py
│   ├── state.py                   # WorkbenchState Pydantic model with ReAct fields
│   └── graph.py                   # StateGraph builder, route/infer/tool_node & SqliteSaver checkpointer
│
├── tools/                         # Agent Tool Layer Package
│   ├── __init__.py                # Tool exports & pre-computed Ollama schemas
│   ├── registry.py                # TOOL_REGISTRY, TOOL_INPUT_TYPES & build_tool_schemas()
│   ├── math_eval.py               # SymPy math solver & step-by-step derivation
│   ├── file_io.py                 # Scoped workspace file I/O (read/write/list)
│   ├── code_sandbox.py            # Isolated Python sandbox execution jail
│   ├── spreadsheet.py             # Data analysis layer (pandas/openpyxl)
│   ├── doc_gen.py                 # Word (.docx), PPT (.pptx), Excel (.xlsx) generator
│   └── ocr_vlm.py                 # Preprocessing, OCR & VLM fallback
│
└── router/                        # Phase 4 Router Package
    ├── __init__.py
    ├── schemas.py                 # FileMetadata, RouteDecision models
    ├── metadata_check.py          # Stage 1: Extension matching
    ├── keyword_check.py           # Stage 2: Intent keyword matching
    ├── classifier.py              # Stage 3: ML model inference
    └── route.py                   # 3-Stage Waterfall Entrypoint
```

---

## Setup & Installation

### 1. Prerequisites
* Python 3.10+
* [Ollama](https://ollama.com) installed and running locally on `http://localhost:11434`

### 2. Pull Required Models
```bash
# Pull Qwen3.5 4B Reasoning & Qwen2.5-Coder 3B Coding models
ollama pull qwen3.5:4b-q4_K_M
ollama pull qwen2.5-coder:3b
```

### 3. Install Python Dependencies
```bash
pip install pydantic sympy pandas openpyxl python-docx python-pptx opencv-python scikit-learn ollama langgraph langgraph-checkpoint-sqlite
```

---

## Running Test Suites & Inspection Helpers

### Run Master Integration Test Runner (Phases 1 - 6 + E2E Workflows)
```bash
python3 run_all_tests.py
```

### Run Phase 6 ReAct Tool Integration Tests
```bash
python3 test_phase6.py
```

### Run LangGraph Orchestrator Skeleton Tests (Phase 5)
```bash
python3 test_orchestrator.py
```

### Inspect Persistent Checkpoint Thread History
```bash
# Inspect most recent thread or specific thread ID
python3 inspect_run.py <thread_id>
```

### Run 3-Stage Waterfall Router Tests (Phase 4)
```bash
python3 test_router.py
```

### Run Agent Tool Layer Tests (Phase 2)
```bash
python3 test_tools.py
```

---

## License & Compliance
Built for SIH 2026 PS 26117. Zero external cloud connectivity required.
