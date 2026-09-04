# Sovereign On-Premise Agentic AI Workbench

> **Smart India Hackathon (SIH) 2026 -- PS 26117**  
> *Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work*  
> Target Industry: Mangalore Refinery and Petrochemicals Limited (MRPL) / PSU / Defence / Air-Gapped Infrastructures

---

## Project Overview

An on-premise, air-gapped, zero-cloud AI agent workbench designed for confidential PSU operations, refinery management, and industrial engineering work. Runs entirely on local open-weight multimodal LLMs (Ollama engine) with strict workspace sandboxing, security audit trails, persistent SQLite workflow checkpointing, ReAct tool execution loops, confidence-gated OCR pipelines, and zero outbound network data leakage.

---

## Key Features

* **100% Air-Gapped Sovereignty**: Zero external API dependencies, running locally on Apple Silicon Metal GPU / CUDA.
* **Abstract Multi-Model Role Registry**: Decouples agent tasks into model roles (`reasoning` using `qwen3.5:4b-q4_K_M`, `coding` using `qwen2.5-coder:3b`, `vision`, `ocr`) with dynamic tag resolution and `keep_alive="5m"` VRAM caching.
* **3-Stage Waterfall Router (Phase 2 & 4)**:
  1. *Stage 1 (Metadata)*: Code extension inspection guard (`.py`, `.ipynb`, `.js`, etc. -- `conf=1.00`) and OCR auto-detection (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp`).
  2. *Stage 2 (Keyword)*: Word-boundary precision heuristic (~35 intent terms -- `conf=0.85`).
  3. *Stage 3 (Classifier)*: Offline TF-IDF + Logistic Regression ML classifier for ambiguous prompts.
* **ReAct LangGraph Orchestrator Loop (Phase 5 & 6)**:
  * End-to-end execution pipeline (`START -> route -> infer -> (conditional) -> tool_node -> infer -> ... -> END`).
  * Ollama native function calling with dynamically generated Pydantic tool schemas (`OLLAMA_TOOL_SCHEMAS`).
  * Single `tool_node` dispatcher handling 3 failure stages:
    * Stage 1: Unknown tool name (`failure_type="unknown_tool"`)
    * Stage 2: Malformed tool arguments (`failure_type="invalid_args"`)
    * Stage 3: Tool execution failure (`failure_type="execution_error"`)
  * Loop safety iteration bounds (`max_tool_iterations=5`).
  * Persistent SQLite checkpointing (`workbench_checkpoints.db` via `SqliteSaver`) surviving process restarts.
  * Unique invocation `thread_id` tracing (via `uuid4`).
* **Confidence-Gated OCR & Vision Pipeline (Phase 7)**:
  * Primary Engine: Fast PaddleOCR (PP-Structure / PP-OCRv6) for layout analysis and text recognition.
  * In-Memory PDF Rendering: Converts PDF document pages into high-resolution images via `pypdfium2` at 2x scaling.
  * Dual-Format Parsing: Robust parsing supporting both PaddleOCR 3.7+ (`rec_texts`, `rec_scores`) and legacy list response formats.
  * Confidence Threshold Gating: Evaluates mean OCR confidence per document against `OCR_CONFIDENCE_THRESHOLD = 0.90`.
  * Vision-Language Model Fallback: Automatically routes to local VLM (`qwen3-vl` / `qwen2.5-vl` via `run_inference`) when confidence is < 0.90 or when explicitly inspecting engineering diagrams (`input_type="diagram"` / `extract_mode="describe"`).
* **Audited Standalone Agent Tool Layer (Phase 3 & 4)**:
  * `math_eval`: Safe symbolic math evaluation, calculus, LaTeX formatting, and step-by-step intermediate output via SymPy (zero raw `eval()`).
  * `file_io`: Workspace-bounded file operations (`/workspace/<session_id>/`) with path traversal guards and zero file deletion.
  * `code_sandbox`: Isolated Python code execution sandbox with hard timeout guards, plot capture, and execution timing.
  * `spreadsheet`: Pandas & OpenPyXL tabular data analysis layer (`filter`, `aggregate`, `compute`).
  * `doc_gen`: Deliverable generator producing formatted Word (`.docx`), PowerPoint (`.pptx`), and Excel (`.xlsx`) documents from shared content primitives.
  * `ocr_vlm`: Confidence-gated layout analysis, text recognition, PDF page rendering, and VLM fallback.

---

## Project Architecture & Directory Structure

```text
sovereign-agent/
├── README.md                      # Comprehensive Architecture & Setup Guide
├── .gitignore                     # Git ignore rules for Python, local workspace & logs
├── phase1_inference.py            # Local Ollama Inference SDK, Role Registry & Tool Calling
├── tool_interface.py              # Base Pydantic models, @audited_tool decorator, & Path Validator
├── train_router_classifier.py     # Offline ML training script for Stage 3 Router Classifier
├── inspect_run.py                 # Standalone thread checkpoint history inspector
├── router_vectorizer.pkl          # Trained TF-IDF Vectorizer artifact
├── router_classifier.pkl          # Trained Logistic Regression Classifier artifact
│
├── tests/                         # Dedicated Test Suite Package
│   ├── __init__.py
│   ├── run_all.py                 # Master integration test runner across all phases (1-7)
│   ├── test_tools.py              # Standalone test suite for all agent tools
│   ├── test_router.py             # Standalone test suite for 3-stage waterfall router
│   ├── test_orchestrator.py       # Standalone test suite for LangGraph orchestrator
│   ├── test_phase6.py             # Standalone test suite for Phase 6 ReAct tool loop
│   ├── test_phase7.py             # Standalone test suite for Phase 7 confidence-gated OCR
│   └── test_ocr_user_files.py     # OCR validation test suite against user test PDFs
│
├── orchestrator/                  # ReAct LangGraph Orchestrator Package
│   ├── __init__.py
│   ├── state.py                   # WorkbenchState Pydantic model with ReAct fields
│   ├── checkpoint.py              # SQLite persistent checkpointer configuration
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
│   └── ocr_vlm.py                 # Confidence-gated OCR, PDF rendering & VLM fallback
│
└── router/                        # Phase 2 & 4 Router Package
    ├── __init__.py
    ├── schemas.py                 # FileMetadata, RouteDecision models
    ├── metadata_check.py          # Stage 1: Extension matching & OCR auto-detection
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
pip install pydantic sympy pandas openpyxl python-docx python-pptx opencv-python scikit-learn ollama langgraph langgraph-checkpoint-sqlite paddleocr paddlex pypdfium2
```

---

## Running Test Suites & Inspection Helpers

### Run Master Integration Test Runner (Phases 1 - 7 + E2E Workflows)
```bash
python3 tests/run_all.py
```

### Run Phase 7 Confidence-Gated OCR Tests
```bash
python3 tests/test_phase7.py
```

### Run OCR Validation on User Test PDFs
```bash
python3 tests/test_ocr_user_files.py
```

### Run Phase 6 ReAct Tool Integration Tests
```bash
python3 tests/test_phase6.py
```

### Run LangGraph Orchestrator Skeleton Tests (Phase 5)
```bash
python3 tests/test_orchestrator.py
```

### Run 3-Stage Waterfall Router Tests (Phase 4)
```bash
python3 tests/test_router.py
```

### Run Agent Tool Layer Tests (Phase 2)
```bash
python3 tests/test_tools.py
```

### Inspect Persistent Checkpoint Thread History
```bash
# Inspect most recent thread or specific thread ID
python3 inspect_run.py <thread_id>
```

---

## License & Compliance
Built for SIH 2026 PS 26117. Zero external cloud connectivity required.
