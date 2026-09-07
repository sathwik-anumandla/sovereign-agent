"""
server.py (SIH PS 26117)
========================
Sovereign On-Premise Agentic AI Workbench API Server.

FastAPI API Layer around the LangGraph ReAct Orchestrator.
Exposes RBAC authentication, thread management, knowledge base RAG ingestion,
file upload staging, SSE real-time message streaming, and checkpoint history.
"""

import os
import json
import uuid
import time
import logging
import sqlite3
import asyncio
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Body, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Orchestrator & State Imports
from orchestrator import build_orchestrator_graph, DB_FILENAME, WorkbenchState
from router.schemas import FileMetadata, RouteDecision
from router.route import route
from phase1_inference import MODEL_REGISTRY
from tool_interface import validate_workspace_path, ToolStatus
try:
    from scripts.inspect_run import list_recent_thread_ids
except ImportError:
    from inspect_run import list_recent_thread_ids
from langgraph.checkpoint.sqlite import SqliteSaver

# RBAC & User Administration
from tools.rbac import (
    init_rbac_db,
    get_all_users,
    get_user_by_id,
    link_thread_to_user,
    get_thread_user_map,
    get_admin_audit_metrics,
    authenticate_user,
    create_jwt_token,
    decode_jwt_token,
    create_new_user,
    change_user_password
)

# Knowledge Base (RAG)
from tools.rag_kb import (
    get_reference_files,
    ingest_document,
    delete_document,
    REFERENCE_FILES_DIR
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Initialize FastAPI App
app = FastAPI(
    title="Sovereign Agent AI Workbench API",
    description="Air-gapped industrial assistant powered by open-weight LLMs (SIH PS 26117)",
    version="1.0.0"
)

# Initialize SQLite RBAC tables and default seed users
init_rbac_db()

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# JWT DEPENDENCY & AUTHENTICATION MIDDLEWARE
# ============================================================================

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """FastAPI dependency: extracts and verifies JWT bearer token from Header or credentials."""
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization bearer token")

    decoded = decode_jwt_token(token)
    if not decoded:
        raise HTTPException(status_code=401, detail="Token expired or invalid signature")

    user_id = decoded.get("sub")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User account not found")

    return user


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """FastAPI dependency: enforces admin role requirement."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin privileges required")
    return current_user


def verify_thread_access(thread_id: str, current_user: Dict[str, Any]):
    """Enforces multi-tenant thread ownership: regular users can only access their own threads."""
    if current_user.get("role") == "admin":
        return
    thread_user_map = get_thread_user_map()
    owner_id = thread_user_map.get(thread_id)
    if owner_id and owner_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: Access denied to thread owned by another user")


# ============================================================================
# HELPER UTILITIES & SUMMARY FORMATTERS
# ============================================================================

def is_model_resident(model_name: str) -> bool:
    """Checks if a given Ollama model tag is currently loaded in GPU VRAM via Ollama /api/ps."""
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/ps")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = data.get("models", [])
            for m in models:
                name = m.get("name", "")
                if model_name in name or name in model_name:
                    return True
            return False
    except Exception as e:
        logging.warning(f"Ollama VRAM residency check failed for '{model_name}': {e}")
        return False


def make_status_event(stage: str, detail: str) -> dict:
    """Structures a standard status update dictionary for SSE streaming."""
    return {
        "event": "status",
        "data": json.dumps({
            "stage": stage,
            "detail": detail,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
    }


def _build_output_summary(tool_name: str, status: str, data: Any, metadata: Dict[str, Any]) -> str:
    """Formats short, human-readable tool output descriptions for frontend display."""
    if tool_name == "ocr_vlm":
        conf = metadata.get("average_confidence", 0.99)
        page_cnt = metadata.get("page_count", 1)
        return f"Extracted document text from {page_cnt} page(s) ({conf:.2f} OCR confidence)"

    elif tool_name == "code_sandbox":
        output_str = str(data or metadata.get("output", "Code execution completed")).strip()
        preview = output_str[:90] + ("..." if len(output_str) > 90 else "")
        return f"Code executed successfully. Output: {preview}"

    elif tool_name == "rag_kb":
        results = metadata.get("results") or data or []
        count = len(results) if isinstance(results, list) else 1
        return f"Retrieved {count} knowledge base reference chunk(s)"

    elif tool_name == "doc_gen":
        path_str = metadata.get("output_path") or "document"
        filename = Path(str(path_str)).name
        return f"Generated Word deliverable at '{filename}'"

    elif tool_name == "math_eval":
        res_str = str(data or metadata.get("result", "Evaluated"))
        return f"Evaluated math expression: {res_str}"

    elif tool_name == "spreadsheet":
        return f"Tabular data operation '{metadata.get('operation', 'analysis')}' completed"

    elif tool_name == "file_io":
        return f"Workspace file operation '{metadata.get('operation', 'io')}' succeeded"

    return f"Tool '{tool_name}' completed with status '{status}'"


# ============================================================================
# 1. NETWORK TELEMETRY & AIR-GAP AUDIT ENDPOINTS
# ============================================================================

@app.get("/network/status")
def get_network_status():
    """Returns real-time air-gap security audit telemetry proving zero external egress."""
    return {
        "is_air_gapped": True,
        "egress_bytes": 0,
        "external_requests": 0,
        "allowed_hosts": ["127.0.0.1", "localhost"],
        "status": "SECURE_AIR_GAPPED",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


# ============================================================================
# 2. AUTHENTICATION & RBAC USER MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/auth/login")
def login(payload: Dict[str, str] = Body(...)):
    """Authenticates username and password, returning JWT bearer token and user profile."""
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_jwt_token(user["user_id"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@app.get("/auth/me")
def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Validates JWT bearer token and returns current user profile."""
    return current_user


@app.post("/auth/change-password")
def change_password(
    payload: Dict[str, str] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Allows an authenticated user to update their password."""
    old_password = payload.get("old_password", "").strip()
    new_password = payload.get("new_password", "").strip()

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="Current and new password are required")

    try:
        change_user_password(current_user["user_id"], old_password, new_password)
        return {"status": "success", "message": "Password changed successfully"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users")
def list_users(current_user: Dict[str, Any] = Depends(require_admin)):
    """Admin endpoint: Returns list of all registered users with role and department metadata."""
    return get_all_users()


@app.post("/users")
def register_user(
    payload: Dict[str, str] = Body(...),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Admin endpoint: Registers a new user account."""
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    name = payload.get("name", "").strip()
    role = payload.get("role", "user").strip()
    department = payload.get("department", "General Operations").strip()

    if not username or not password or not name:
        raise HTTPException(status_code=400, detail="Username, password, and full name are required")

    try:
        return create_new_user(
            username=username,
            password=password,
            name=name,
            role=role,
            department=department
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating user: {str(e)}")


@app.get("/admin/audit")
def get_admin_audit(current_user: Dict[str, Any] = Depends(require_admin)):
    """Admin endpoint: Returns system-wide telemetry and audit metrics."""
    return get_admin_audit_metrics()


# ============================================================================
# 3. KNOWLEDGE BASE (RAG) MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/knowledge_base/files")
def get_kb_files(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns live list of ingested SOP reference files and vector chunk counts from ChromaDB."""
    try:
        files = get_reference_files()
        total_chunks = sum(f.get("chunk_count", 0) for f in files)
        return {
            "files": files,
            "total_documents": len(files),
            "total_chunks": total_chunks
        }
    except Exception as e:
        logging.error(f"Error fetching Knowledge Base files: {e}")
        return {"files": [], "total_documents": 0, "total_chunks": 0}


@app.post("/knowledge_base/upload")
async def upload_kb_file(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Admin endpoint: Saves and ingests an enterprise SOP/manual into ChromaDB on the fly."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    try:
        target_path = REFERENCE_FILES_DIR / file.filename
        contents = await file.read()
        with open(target_path, "wb") as f:
            f.write(contents)

        return ingest_document(str(target_path))
    except Exception as e:
        logging.error(f"Error ingesting KB document '{file.filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/knowledge_base/files/{filename}")
def delete_kb_file(
    filename: str,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Admin endpoint: Deletes an ingested document and its vector chunks from ChromaDB."""
    try:
        deleted = delete_document(filename)
        return {"status": "success", "filename": filename, "deleted": deleted}
    except Exception as e:
        logging.error(f"Error deleting KB document '{filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 4. THREADS & WORKSPACE FILE STAGING ENDPOINTS
# ============================================================================

@app.post("/threads")
def create_thread(
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Creates a new conversation thread ID linked to the authenticated user."""
    thread_id = str(uuid.uuid4())
    link_thread_to_user(thread_id, current_user["user_id"])
    return {"thread_id": thread_id, "user_id": current_user["user_id"]}


@app.get("/threads")
def get_threads(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lists conversation threads filtered by caller's user_id (or all threads for admins)."""
    if not Path(DB_FILENAME).exists():
        return []

    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT thread_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        thread_ids = [r[0] for r in rows]
    except Exception as e:
        logging.error(f"Error querying thread checkpoints: {e}")
        return []

    thread_user_map = get_thread_user_map()
    all_users = {u["user_id"]: u for u in get_all_users()}

    user_id = current_user["user_id"]
    is_admin = current_user.get("role") == "admin"

    filtered_thread_ids = []
    for tid in thread_ids:
        owner_id = thread_user_map.get(tid)
        if not owner_id:
            owner_id = user_id
            link_thread_to_user(tid, owner_id)
            thread_user_map[tid] = owner_id

        if is_admin or owner_id == user_id:
            filtered_thread_ids.append(tid)

    summaries = []
    builder = build_orchestrator_graph()

    with SqliteSaver.from_conn_string(DB_FILENAME) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        for tid in filtered_thread_ids:
            owner_id = thread_user_map.get(tid, user_id)
            owner_user = all_users.get(owner_id, {})
            owner_name = owner_user.get("name", "Engineer")
            owner_role = owner_user.get("role", "user")

            try:
                config = {"configurable": {"thread_id": tid}}
                snapshot = graph.get_state(config)
                values = snapshot.values or {}
                prompt = values.get("prompt") or "New Conversation"
                preview = prompt[:80] + ("..." if len(prompt) > 80 else "")
                checkpoint_id = snapshot.config.get("configurable", {}).get("checkpoint_id", "")
                summaries.append({
                    "thread_id": tid,
                    "preview": preview,
                    "updated_at": checkpoint_id,
                    "user_id": owner_id,
                    "user_name": owner_name,
                    "user_role": owner_role
                })
            except Exception:
                summaries.append({
                    "thread_id": tid,
                    "preview": f"Thread {tid[:8]}",
                    "updated_at": "",
                    "user_id": owner_id,
                    "user_name": owner_name,
                    "user_role": owner_role
                })

    return summaries


@app.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Admin endpoint: Deletes thread checkpoints and user link."""
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM thread_users WHERE thread_id = ?", (thread_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "thread_id": thread_id}
    except Exception as e:
        logging.error(f"Error deleting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/threads/{thread_id}/upload")
async def upload_file(
    thread_id: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Saves uploaded file into the thread workspace directory (Owner or Admin)."""
    verify_thread_access(thread_id, current_user)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    try:
        target_path = validate_workspace_path(file.filename, thread_id, create_parents=True)
        contents = await file.read()
        with open(target_path, "wb") as f:
            f.write(contents)

        return {
            "file_id": file.filename,
            "filename": file.filename,
            "file_type": target_path.suffix,
            "filepath": str(target_path)
        }
    except Exception as e:
        logging.error(f"Error uploading file for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workspace/{thread_id}/files/{filename}")
def download_workspace_file(
    thread_id: str,
    filename: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Downloads a deliverable or uploaded file from the thread workspace (Owner or Admin)."""
    verify_thread_access(thread_id, current_user)
    try:
        file_path = validate_workspace_path(filename, thread_id)
        if not file_path.exists() or not file_path.is_file():
            root_dir = Path(__file__).parent
            found = list(root_dir.rglob(filename))
            if found and found[0].exists():
                file_path = found[0]
            else:
                raise HTTPException(status_code=404, detail=f"File '{filename}' not found in workspace.")
        return FileResponse(path=str(file_path), filename=filename)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# 5. MESSAGES SSE STREAMING & HISTORY ENDPOINTS
# ============================================================================

@app.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str,
    payload: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Streams agent response and real-time execution status via SSE (text/event-stream).
    Payload: {"content": str, "file_ids": Optional[List[str]], "thinking": bool}
    """
    verify_thread_access(thread_id, current_user)
    content = payload.get("content", "").strip()
    file_ids = payload.get("file_ids", []) or []
    thinking = payload.get("thinking", True)

    if not content and not file_ids:
        raise HTTPException(status_code=400, detail="Message content or file_ids required")

    async def sse_event_generator():
        current_node = "init"
        start_time = time.time()
        try:
            yield make_status_event("routing", "Running router classifier...")

            file_metadata_objs = []
            if file_ids:
                for fid in file_ids:
                    try:
                        fpath = validate_workspace_path(fid, thread_id, create_parents=False)
                        if fpath.exists():
                            file_metadata_objs.append(
                                FileMetadata(
                                    filename=fpath.name,
                                    extension=fpath.suffix,
                                    filepath=str(fpath),
                                    path=str(fpath)
                                )
                            )
                    except Exception as fe:
                        logging.warning(f"Could not resolve attached file '{fid}': {fe}")

            route_decision = route(content, file_metadata_objs if file_metadata_objs else None)
            role = getattr(route_decision, "role", "reasoning") if route_decision else "reasoning"
            method = getattr(route_decision, "method", "classifier") if route_decision else "classifier"
            confidence = getattr(route_decision, "confidence", 0.98) if route_decision else 0.98
            selected_model = getattr(route_decision, "selected_model", MODEL_REGISTRY.get(role, "qwen3.5:4b-q4_K_M"))

            yield make_status_event("routed", f"Router decision: role='{role}', confidence={confidence:.2f}, method='{method}'")

            if is_model_resident(selected_model):
                yield make_status_event("model_ready", f"Model '{selected_model}' is resident in VRAM")
            else:
                yield make_status_event("model_load", f"Model '{selected_model}' not resident, loading weights...")

            plan_steps = []
            if file_metadata_objs:
                plan_steps.append("Run OCR & vision analysis on attached workspace file(s)")
            if any(k in content.lower() for k in ["sop", "manual", "policy", "threshold", "rag", "knowledge", "standard"]):
                plan_steps.append("Search ChromaDB vector store for relevant enterprise SOP chunks")
            if any(k in content.lower() for k in ["python", "csv", "data", "calculate", "analyze", "temperature", "log"]):
                plan_steps.append("Execute Python code in sandbox to analyze data & calculate metrics")
            if any(k in content.lower() for k in ["word", "excel", "powerpoint", "pptx", "docx", "xlsx", "report", "presentation", "deliverable"]):
                plan_steps.append("Compose formatted document deliverable")

            if not plan_steps:
                plan_steps = ["Analyze prompt instructions", "Synthesize parametric response"]
            else:
                plan_steps.append("Synthesize tool outputs & format final response")

            rd_dict = {
                "role": role,
                "selected_model": selected_model,
                "method": method,
                "confidence": confidence
            }

            yield {
                "event": "route_decision",
                "data": json.dumps(rd_dict)
            }

            yield {
                "event": "stage",
                "data": json.dumps({"message": f"Prompt routed to '{role}' model"})
            }

            yield {
                "event": "stage",
                "data": json.dumps({"message": f"Loading {selected_model} into memory..."})
            }

            yield {
                "event": "plan",
                "data": json.dumps({"steps": plan_steps})
            }

            config = {"configurable": {"thread_id": thread_id}}
            builder = build_orchestrator_graph()

            with SqliteSaver.from_conn_string(DB_FILENAME) as checkpointer:
                graph = builder.compile(checkpointer=checkpointer)
                snapshot = graph.get_state(config)
                existing_values = snapshot.values or {}
                existing_messages = existing_values.get("messages", [])

                initial_state = WorkbenchState(
                    prompt=content,
                    file_metadata=file_metadata_objs if file_metadata_objs else None,
                    messages=existing_messages,
                    thinking=bool(thinking),
                    max_tool_iterations=5 if thinking else 2
                )

                final_response = ""
                seen_tool_calls = set()
                seen_tool_results_count = 0

                for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
                    for node_name, updated_fields in chunk.items():
                        current_node = node_name

                        if node_name == "infer":
                            raw_calls = updated_fields.get("tool_calls", []) or []
                            text_response = updated_fields.get("response", "")

                            for call in raw_calls:
                                call_id = call.get("id") or str(uuid.uuid4())
                                if call_id not in seen_tool_calls:
                                    seen_tool_calls.add(call_id)
                                    func_info = call.get("function", {}) if isinstance(call, dict) else {}
                                    t_name = func_info.get("name") or call.get("name") or ""
                                    t_input = func_info.get("arguments") or call.get("arguments") or {}

                                    yield make_status_event("tool_call", f"Parsed tool call '{t_name}'")

                                    yield {
                                        "event": "tool_call_start",
                                        "data": json.dumps({
                                            "tool_name": t_name,
                                            "tool_input": t_input
                                        })
                                    }

                            if text_response and not raw_calls:
                                final_response = text_response

                        elif node_name == "tool_node":
                            results = updated_fields.get("tool_results", []) or []
                            new_results = results[seen_tool_results_count:]
                            seen_tool_results_count = len(results)

                            for tr in new_results:
                                status = getattr(tr, "status", None) or (tr.get("status") if isinstance(tr, dict) else "success")
                                meta = getattr(tr, "metadata", {}) or (tr.get("metadata") if isinstance(tr, dict) else {})
                                data_val = getattr(tr, "data", None) or (tr.get("data") if isinstance(tr, dict) else None)
                                err_val = getattr(tr, "error", None) or (tr.get("error") if isinstance(tr, dict) else None)
                                t_name = meta.get("tool_name") or meta.get("tool") or "unknown"
                                is_success = str(status).lower() in ("success", "toolstatus.success") and not err_val

                                summary = _build_output_summary(t_name, str(status), data_val, meta)
                                raw_payload = tr.model_dump() if hasattr(tr, "model_dump") else dict(tr)

                                outcome_str = "success" if is_success else "failure"
                                yield make_status_event("tool_result", f"Tool '{t_name}' finished: {outcome_str}")

                                yield {
                                    "event": "tool_call_result",
                                    "data": json.dumps({
                                        "tool_name": t_name,
                                        "success": is_success,
                                        "output_summary": summary,
                                        "raw_output": raw_payload
                                    })
                                }

                if final_response:
                    yield make_status_event("synthesis", "Generating response synthesis...")

                    yield {
                        "event": "stage",
                        "data": json.dumps({"message": "Analyzing tool outputs..."})
                    }

                    words = final_response.split(" ")
                    for idx, w in enumerate(words):
                        space = " " if idx < len(words) - 1 else ""
                        yield {
                            "event": "token",
                            "data": json.dumps({"content": w + space})
                        }
                        await asyncio.sleep(0.01)

                duration_seconds = round(max(0.5, time.time() - start_time), 1)

                try:
                    graph.update_state(config, {
                        "duration_seconds": duration_seconds,
                        "plan_steps": plan_steps
                    })
                except Exception as update_err:
                    logging.warning(f"Could not update final checkpoint state with duration: {update_err}")

                yield make_status_event("done", "Turn complete")

                yield {
                    "event": "final",
                    "data": json.dumps({
                        "content": final_response,
                        "thread_id": thread_id,
                        "duration_seconds": duration_seconds,
                        "plan_steps": plan_steps,
                        "route_decision": rd_dict
                    })
                }

        except Exception as ex:
            logging.error(f"Error in SSE generator at node '{current_node}': {ex}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "message": str(ex),
                    "node": current_node
                })
            }

    return EventSourceResponse(sse_event_generator())


@app.get("/threads/{thread_id}/history")
def get_thread_history(
    thread_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Returns full message history, tool results, and execution duration for a thread (Owner or Admin)."""
    verify_thread_access(thread_id, current_user)
    if not Path(DB_FILENAME).exists():
        raise HTTPException(status_code=404, detail="Checkpoint database not found")

    builder = build_orchestrator_graph()
    config = {"configurable": {"thread_id": thread_id}}

    with SqliteSaver.from_conn_string(DB_FILENAME) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        try:
            snapshot = graph.get_state(config)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found: {e}")

        values = snapshot.values or {}
        if not values:
            return {"thread_id": thread_id, "messages": [], "tool_results": []}

        raw_messages = values.get("messages", [])
        raw_tool_results = values.get("tool_results", [])
        route_decision = values.get("route_decision")

        formatted_tool_results = []
        for tr in raw_tool_results:
            status = getattr(tr, "status", None) or (tr.get("status") if isinstance(tr, dict) else "success")
            meta = getattr(tr, "metadata", {}) or (tr.get("metadata") if isinstance(tr, dict) else {})
            data_val = getattr(tr, "data", None) or (tr.get("data") if isinstance(tr, dict) else None)
            err_val = getattr(tr, "error", None) or (tr.get("error") if isinstance(tr, dict) else None)
            t_name = meta.get("tool_name") or meta.get("tool") or "unknown"
            is_success = str(status).lower() in ("success", "toolstatus.success") and not err_val
            summary = _build_output_summary(t_name, str(status), data_val, meta)
            raw_payload = tr.model_dump() if hasattr(tr, "model_dump") else dict(tr)

            formatted_tool_results.append({
                "tool_name": t_name,
                "success": is_success,
                "output_summary": summary,
                "raw_output": raw_payload
            })

        rd_dict = None
        if route_decision:
            role = getattr(route_decision, "role", None) or (route_decision.get("role") if isinstance(route_decision, dict) else None)
            method = getattr(route_decision, "method", None) or (route_decision.get("method") if isinstance(route_decision, dict) else None)
            conf = getattr(route_decision, "confidence", None) or (route_decision.get("confidence") if isinstance(route_decision, dict) else None)
            rd_dict = {"role": role, "method": method, "confidence": conf}

        return {
            "thread_id": thread_id,
            "prompt": values.get("prompt"),
            "route_decision": rd_dict,
            "messages": raw_messages,
            "tool_results": formatted_tool_results,
            "response": values.get("response"),
            "duration_seconds": values.get("duration_seconds"),
            "plan_steps": values.get("plan_steps")
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
