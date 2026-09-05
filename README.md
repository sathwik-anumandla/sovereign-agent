# Sovereign On-Premise Agentic AI Workbench

> **Smart India Hackathon (SIH) 2026 -- PS 26117**  
> *Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work*  
> Target Industry: Mangalore Refinery and Petrochemicals Limited (MRPL) / PSU / Defence / Air-Gapped Infrastructures

---

## Project Overview

An on-premise, air-gapped, zero-cloud AI agent workbench designed for confidential PSU operations, refinery management, and industrial engineering work. Runs entirely on local open-weight multimodal LLMs (Ollama engine) with strict workspace sandboxing, security audit trails, persistent SQLite workflow checkpointing, ReAct tool execution loops, confidence-gated OCR pipelines, embedded vector knowledge bases (RAG), and zero outbound network data leakage.

---

## Key Features & Architecture Enhancements

* **100% Air-Gapped Sovereignty**: Zero external API dependencies, running locally on Apple Silicon Metal GPU / CUDA.
* **Abstract Multi-Model Role Registry**: Decouples agent tasks into model roles (`reasoning` using `qwen3.5:4b-q4_K_M`, `coding` using `qwen2.5-coder:3b`, `vision`, `ocr`, `embedding` using `nomic-embed-text`) with dynamic tag resolution and `keep_alive="5m"` VRAM caching.
* **Scaled Context Window (P9 Amendment)**: Enforces `num_ctx = 8192` across Ollama API calls to support large visual token payloads and extensive prompt histories.
* **4-Stage Waterfall Router (Phase 2 & 4 & 9)**:
  1. *Stage 0 (Multimodal Image Override)*: Instantly routes image attachments (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`) to `role="reasoning"`, `confidence=1.00`, `method="multimodal_override"`.
  2. *Stage 1 (Metadata)*: Code extension inspection guard (`.py`, `.ipynb`, `.js`, etc. -- `conf=1.00`) and OCR auto-detection (`.pdf`, `.png`, `.jpg`, etc.).
  3. *Stage 2 (Keyword)*: Word-boundary precision heuristic (~35 intent terms -- `conf=0.85`).
  4. *Stage 3 (Classifier)*: Offline TF-IDF + Logistic Regression ML classifier for ambiguous prompts.
* **ReAct LangGraph Orchestrator Loop (Phase 5, 6 & 9)**:
  * End-to-end execution topology (`START -> route -> infer -> (conditional) -> tool_node -> infer -> ... -> END`).
  * **Dual Tool Call Support**: Handles native Ollama tool-calling JSON payloads AND provides a robust regex/brace JSON fallback parser (`parse_json_tool_call` with `strict=False`, multiline string handling, and trailing comma cleanup) for models like `qwen2.5-coder:3b`.
  * **Session Workspace File-Staging**: Audited pre-execution step copying input files from host paths into `./workspace/<session_id>/` via `file_io` write prior to `code_sandbox` execution.
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
* **RAG & Knowledge Base Pipeline (Phase 8)**:
  * Embedded Vector Store: Disk-backed `ChromaDB` `PersistentClient` in `chroma_db/` collection `sovereign_kb`.
  * Direct Embedding Model: `nomic-embed-text` via Ollama (direct call, not routed).
  * Structure-Aware Chunking: `RecursiveCharacterTextSplitter` splitting WITHIN structural layout sections (paragraphs, tables, headings) from P7 OCR or text extractors (~512 tokens / 1500 chars).
  * `rag_kb` Tool Contract: Unified `@audited_tool` supporting `query`, `ingest`, `delete`, and `list` operations with structured chunk outputs (`text`, `source`, `chunk_index`, `section_type`, `score`).
  * Re-ingestion Safety: Overwrites prior document chunks (`collection.delete(where={"source": filename})`) to prevent stale residue.
  * Disk Reference Copies: Retains source document copy at `reference_files/<filename>`.
  * Live Reference List: Derived live from ChromaDB metadata to eliminate manifest drift.
  * Explicit Source Citation: System prompt instruction requiring models to cite source filenames (`[Source: filename]`) for RAG answers.
* **Audited Standalone Agent Tool Layer (Phase 3 & 4)**:
  * `math_eval`: Safe symbolic math evaluation, calculus, LaTeX formatting, and step-by-step intermediate output via SymPy (zero raw `eval()`).
  * `file_io`: Workspace-bounded file operations (`/workspace/<session_id>/`) with path traversal guards and zero file deletion.
  * `code_sandbox`: Isolated Python code execution sandbox with hard timeout guards, plot capture, and execution timing.
  * `spreadsheet`: Pandas & OpenPyXL tabular data analysis layer (`filter`, `aggregate`, `compute`).
  * `doc_gen`: Deliverable generator producing formatted Word (`.docx`), PowerPoint (`.pptx`), and Excel (`.xlsx`) documents with automatic LLM argument normalization (`output_format` $\rightarrow$ `format`, `docx_spec` $\rightarrow$ `spec`).
  * `ocr_vlm`: Confidence-gated layout analysis, text recognition, PDF page rendering, and VLM fallback.
  * `rag_kb`: Document retrieval and knowledge base ingestion/deletion management.

---

## Project Architecture & Directory Structure

```text
agent/
├── README.md                      # Comprehensive Architecture & Setup Guide
├── .gitignore                     # Git ignore rules for Python, local workspace, DBs & logs
├── cli.py                         # Interactive Terminal CLI & Workbench Command Runner
├── phase1_inference.py            # Ollama SDK, Role Registry (num_ctx=8192), Embeddings & Inference
├── tool_interface.py              # Base Pydantic models, @audited_tool decorator, & Path Validator
├── inspect_run.py                 # Standalone thread checkpoint history inspector
├── train_router_classifier.py     # Offline ML training script for Stage 3 Router Classifier
├── router_vectorizer.pkl          # Trained TF-IDF Vectorizer artifact
├── router_classifier.pkl          # Trained Logistic Regression Classifier artifact
│
├── test_code_prompt.py            # Flow 2 Harness: Pandas anomaly analysis in sandbox
├── test_text_prompt.py            # Flow 3 Harness: Direct vision & image reasoning
├── test_flow1_approval_note.py    # Flow 1 Harness: Scanned PDF -> OCR -> RAG -> DocGen (.docx)
├── test_flow1_thorough.py         # Flow 1 Thorough Suite: 4 multi-scenario PDF & AST audits
├── test_flow4_approval_note.py    # Flow 4 Harness: Full approval workflow suite
│
├── tests/                         # Master Test Suite Package
│   ├── __init__.py
│   ├── run_all.py                 # Master integration test runner across all phases (1-8)
│   ├── test_tools.py              # Standalone test suite for agent tools
│   ├── test_router.py             # Standalone test suite for 4-stage waterfall router
│   ├── test_orchestrator.py       # Standalone test suite for LangGraph orchestrator
│   ├── test_phase6.py             # Standalone test suite for Phase 6 ReAct tool loop
│   ├── test_phase7.py             # Standalone test suite for Phase 7 confidence-gated OCR
│   ├── test_phase8.py             # Standalone test suite for Phase 8 RAG Knowledge Base
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
│   ├── doc_gen.py                 # Word (.docx), PPT (.pptx), Excel (.xlsx) generator with LLM normalization
│   ├── ocr_vlm.py                 # Confidence-gated OCR, PDF rendering & VLM fallback
│   └── rag_kb.py                  # RAG Knowledge Base vector search & ingestion pipeline
│
└── router/                        # Phase 2 & 4 & 9 Router Package
    ├── __init__.py
    ├── schemas.py                 # FileMetadata, RouteDecision models
    ├── metadata_check.py          # Stage 1: Extension matching & OCR auto-detection
    ├── keyword_check.py           # Stage 2: Intent keyword matching
    ├── classifier.py              # Stage 3: ML model inference
    └── route.py                   # 4-Stage Waterfall Entrypoint (Stage 0 Multimodal Override)
```

---

## Setup & Installation

### 1. Prerequisites
* Python 3.10+
* [Ollama](https://ollama.com) installed and running locally on `http://localhost:11434`

### 2. Pull Required Models
```bash
# Pull Qwen3.5 4B Reasoning, Qwen2.5-Coder 3B Coding & nomic-embed-text Embedding models
ollama pull qwen3.5:4b-q4_K_M
ollama pull qwen2.5-coder:3b
ollama pull nomic-embed-text
```

### 3. Install Python Dependencies
```bash
pip install pydantic sympy pandas openpyxl python-docx python-pptx opencv-python scikit-learn ollama langgraph langgraph-checkpoint-sqlite paddleocr paddlex pypdfium2 chromadb langchain-text-splitters
```

---

## Interacting with the Workbench CLI

Make sure Ollama is running in a separate terminal:
```bash
ollama serve
```

### Option A: Interactive Chat Shell
```bash
python3 cli.py
```

### Option B: Direct Prompt Command
```bash
python3 cli.py "What is 15 * 24?"
```

### Option C: Attach a File to the Prompt
```bash
python3 cli.py --file /path/to/document.pdf "Summarize this file and extract key table metrics."
```

---

## Running Integration Flow Harnesses & Test Suites

### 1. Run Flow 1 Thorough Multi-Scenario Suite
```bash
PYTHONUNBUFFERED=1 python3 test_flow1_thorough.py
```

### 2. Run Flow 1 Approval Note Harness
```bash
PYTHONUNBUFFERED=1 python3 test_flow1_approval_note.py
```

### 3. Run Flow 2 Coding Sandbox Harness
```bash
PYTHONUNBUFFERED=1 python3 test_code_prompt.py
```

### 4. Run Flow 3 Vision Reasoning Harness
```bash
PYTHONUNBUFFERED=1 python3 test_text_prompt.py
```

### 5. Run Master Integration Test Runner (Phases 1 - 8)
```bash
python3 tests/run_all.py
```

### 6. Inspect Persistent Checkpoint Thread History
```bash
# Inspect specific thread ID or list recent threads
python3 inspect_run.py <thread_id>
python3 inspect_run.py --list
```

---

## License & Compliance
Built for SIH 2026 PS 26117. Zero external cloud connectivity required.
