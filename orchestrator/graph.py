"""
orchestrator/graph.py (SIH PS 26117)
====================================
ReAct LangGraph Orchestrator Loop with Tool Execution & PostgreSQL Checkpoint Persistence.

Topology:
  START -> route_node -> infer_node -> (should_continue) -> tool_node -> infer_node -> ... -> END

Persistent State Storage:
  PostgresSaver (pgvector enabled PostgreSQL container)
"""

import os
import re
import json
import shutil
import logging
from pathlib import Path
from uuid import uuid4
from typing import Optional, List, Dict, Any, Tuple
from pydantic import ValidationError
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver

from router.route import route
from router.schemas import FileMetadata, RouteDecision
from phase1_inference import run_inference_raw, MODEL_REGISTRY, ROLE_SYSTEM_PROMPTS
from tool_interface import ToolStatus, ToolResult, validate_workspace_path
from tools.registry import TOOL_REGISTRY, TOOL_INPUT_TYPES, OLLAMA_TOOL_SCHEMAS
from orchestrator.state import WorkbenchState
from tools.db import get_db_url, execute_query

logger = logging.getLogger(__name__)
IMAGE_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


# ============================================================================
# HELPER UTILITIES & FALLBACK PARSERS
# ============================================================================

def parse_json_tool_call(content: str) -> Optional[Dict[str, Any]]:
    """
    Fallback parser for models (e.g. qwen2.5-coder) that output JSON tool calls
    in text content rather than native Ollama tool_calls payloads.
    Strips markdown code fences, parses JSON, and validates against TOOL_REGISTRY.
    """
    if not content or not content.strip():
        return None

    text = content.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = fence_match.group(1).strip() if fence_match else text

    start_idx = candidate.find("{")
    end_idx = candidate.rfind("}")
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None

    json_str = candidate[start_idx : end_idx + 1]

    try:
        data = json.loads(json_str, strict=False)
    except (json.JSONDecodeError, ValueError, TypeError):
        try:
            cleaned = re.sub(r",\s*([\}\]])", r"\1", json_str)
            data = json.loads(cleaned, strict=False)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    if isinstance(data, dict):
        name = data.get("name")
        arguments = data.get("arguments") or data.get("args") or {}
        if name and isinstance(name, str) and name in TOOL_REGISTRY:
            return {
                "id": f"fallback_call_{str(uuid4())[:8]}",
                "function": {
                    "name": name,
                    "arguments": arguments if isinstance(arguments, dict) else {},
                },
            }

    return None


def detect_pseudo_json_tool_call(content: str) -> Optional[str]:
    """Returns function name if content contains a pseudo-JSON object with an un-registered function name."""
    if not content or not content.strip():
        return None
    text = content.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = fence_match.group(1).strip() if fence_match else text
    start_idx = candidate.find("{")
    end_idx = candidate.rfind("}")
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None
    try:
        data = json.loads(candidate[start_idx:end_idx+1], strict=False)
        if isinstance(data, dict) and "name" in data and isinstance(data["name"], str):
            fn_name = data["name"]
            if fn_name not in TOOL_REGISTRY:
                return fn_name
    except Exception:
        pass
    return None


def _stage_workspace_files(file_metadata: Optional[List[FileMetadata]], session_id: str, target_session_id: str):
    """Pre-execution file staging: copies input files from host paths into session workspace directories."""
    if not file_metadata:
        return

    for fm in file_metadata:
        src_path_str = getattr(fm, "filepath", None) or getattr(fm, "path", None) or fm.filename
        src_path = Path(src_path_str)
        if src_path.exists() and src_path.is_file():
            for sid in set([target_session_id, session_id, "workbench_session", "default_session"]):
                try:
                    target_workspace_path = validate_workspace_path(fm.filename, sid, create_parents=True)
                    if not target_workspace_path.exists() or target_workspace_path.stat().st_size != src_path.stat().st_size:
                        shutil.copy2(src_path, target_workspace_path)
                except Exception:
                    pass


# ============================================================================
# GRAPH NODES
# ============================================================================

def route_node(state: WorkbenchState) -> dict:
    """
    Node 1: Evaluates 3-stage waterfall router and initializes workspace system prompts.
    """
    if state.route_decision:
        decision = state.route_decision
    else:
        decision = route(state.prompt, state.file_metadata)
    role = decision.role if decision else "reasoning"
    sys_prompt = ROLE_SYSTEM_PROMPTS.get(role, ROLE_SYSTEM_PROMPTS["reasoning"])

    workspace_context = ""
    if state.file_metadata:
        file_previews = []
        has_images = any(fm.extension.strip().lower() in IMAGE_FILE_EXTENSIONS for fm in state.file_metadata)
        for fm in state.file_metadata:
            fp = Path(getattr(fm, "filepath", None) or getattr(fm, "path", None) or fm.filename)
            if fm.extension.strip().lower() in (".csv", ".txt") and fp.exists():
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f_hdr:
                        header_line = f_hdr.readline().strip()
                        if header_line:
                            file_previews.append(f"'{fm.filename}' (columns: {header_line})")
                        else:
                            file_previews.append(f"'{fm.filename}'")
                except Exception:
                    file_previews.append(f"'{fm.filename}'")
            else:
                file_previews.append(f"'{fm.filename}'")

        if file_previews:
            workspace_context = (
                f"\n\n[Workspace Context]: The file(s) {', '.join(file_previews)} are available in your working directory. "
                "When referencing CSV columns in python code_sandbox or spreadsheet tools, use the exact column names provided in the header."
            )
            if has_images:
                workspace_context += (
                    "\n[Multimodal Vision Active]: The attached image(s) are passed directly into your visual vision context. "
                    "Analyze and describe the image(s) directly from your visual input. Do NOT invoke `ocr_vlm` or external tools."
                )

    fast_context = ""
    if hasattr(state, "thinking") and not state.thinking:
        fast_context = "\n\n[Fast Mode Active]: Provide a direct, concise response immediately. Do NOT output any <think>...</think> reasoning tags or internal thinking traces."

    system_msg = {"role": "system", "content": sys_prompt + workspace_context + fast_context}
    existing_messages = list(state.messages) if state.messages else []

    user_msg = {"role": "user", "content": state.prompt}
    if state.file_metadata:
        user_msg["attachedFiles"] = [
            {"filename": getattr(fm, "filename", str(fm)), "file_id": getattr(fm, "file_id", None)}
            for fm in state.file_metadata
        ]

    if existing_messages:
        if existing_messages[0].get("role") == "system":
            existing_messages[0] = system_msg
        else:
            existing_messages.insert(0, system_msg)
        existing_messages.append(user_msg)
        updated_messages = existing_messages
    else:
        updated_messages = [
            system_msg,
            user_msg
        ]

    return {
        "session_id": getattr(state, "session_id", None),
        "route_decision": decision,
        "messages": updated_messages
    }


def infer_node(state: WorkbenchState) -> dict:
    """
    Node 2: Executes Ollama LLM inference with tool schemas, image support, and fallback JSON parsing.
    """
    rd = state.route_decision
    if isinstance(rd, dict):
        role = rd.get("role", "reasoning")
    elif isinstance(rd, RouteDecision):
        role = rd.role
    else:
        role = "reasoning"

    model_tag = MODEL_REGISTRY.get(role, MODEL_REGISTRY["reasoning"])
    
    images = None
    if state.tool_iteration_count == 0 and state.file_metadata:
        for fm in state.file_metadata:
            ext = fm.extension.strip().lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            if ext in IMAGE_FILE_EXTENSIONS:
                img_path = getattr(fm, "filepath", None) or fm.filename
                images = [img_path]
                break

    msg_dict = run_inference_raw(
        messages=state.messages,
        role=role,
        model=model_tag,
        tools=OLLAMA_TOOL_SCHEMAS,
        images=images,
        thinking=getattr(state, "thinking", True)
    )

    raw_calls = msg_dict.get("tool_calls", []) or []
    content = msg_dict.get("content", "")

    fixed_calls = []
    for call in raw_calls:
        if isinstance(call, dict):
            c_dict = dict(call)
            if not c_dict.get("id"):
                c_dict["id"] = f"call_{str(uuid4())[:8]}"
            fixed_calls.append(c_dict)
        else:
            fixed_calls.append(call)
    raw_calls = fixed_calls
    msg_dict = dict(msg_dict)
    if raw_calls:
        msg_dict["tool_calls"] = raw_calls

    if not raw_calls and content:
        fallback_call = parse_json_tool_call(content)
        if fallback_call:
            raw_calls = [fallback_call]
            msg_dict = dict(msg_dict)
            msg_dict["tool_calls"] = raw_calls
            msg_dict["content"] = ""
            content = ""
        else:
            pseudo_func = detect_pseudo_json_tool_call(content)
            if pseudo_func:
                fallback_msgs = list(state.messages) + [
                    {"role": "user", "content": f"Do not output JSON tool calls. Provide the complete code implementation for '{pseudo_func}' directly using markdown code blocks."}
                ]
                msg_dict = run_inference_raw(
                    messages=fallback_msgs,
                    role=role,
                    model=model_tag,
                    tools=None,
                    images=images,
                    thinking=getattr(state, "thinking", True)
                )
                content = msg_dict.get("content", "")

    updated_messages = list(state.messages) + [msg_dict]

    return {
        "session_id": getattr(state, "session_id", None),
        "messages": updated_messages,
        "tool_calls": raw_calls,
        "response": content if content else (state.response or "")
    }


def should_continue(state: WorkbenchState) -> str:
    """
    Conditional Edge: Routes to tool_node if tool calls exist and iteration count is below max limit.
    """
    has_tool_calls = bool(state.tool_calls)
    below_iteration_limit = state.tool_iteration_count < state.max_tool_iterations

    if has_tool_calls and below_iteration_limit:
        return "tool_node"
    return END


def tool_node(state: WorkbenchState) -> dict:
    """
    Node 3: Single Tool Dispatcher Node.
    Executes tool calls across 3 failure containment stages:
      Stage 1: Unknown tool name -> failure_type="unknown_tool"
      Stage 2: Invalid/malformed args -> failure_type="invalid_args"
      Stage 3: Tool execution exception -> failure_type="execution_error"
    """
    updated_messages = list(state.messages)
    accumulated_results = list(state.tool_results)
    session_id = getattr(state, "session_id", None) or "workbench_session"

    for call in state.tool_calls:
        call_id = call.get("id") or str(uuid4())
        tool_name = ""
        raw_args = {}

        if isinstance(call, dict):
            func_info = call.get("function", {})
            tool_name = func_info.get("name") or call.get("name") or ""
            raw_args = func_info.get("arguments") or call.get("arguments") or {}
        else:
            tool_name = getattr(call, "name", "")
            raw_args = getattr(call, "arguments", {})

        if isinstance(raw_args, dict):
            raw_args["session_id"] = session_id

        tool_result = None

        if tool_name not in TOOL_REGISTRY:
            tool_result = ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown tool: '{tool_name}'",
                metadata={"failure_type": "unknown_tool", "tool_name": tool_name}
            )
        else:
            input_cls = TOOL_INPUT_TYPES[tool_name]
            validated_input = None
            try:
                if isinstance(raw_args, dict):
                    validated_input = input_cls(**raw_args)
                else:
                    validated_input = input_cls.model_validate(raw_args)
            except (ValidationError, TypeError, ValueError) as ve:
                tool_result = ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Invalid arguments for tool '{tool_name}': {str(ve)}",
                    metadata={"failure_type": "invalid_args", "tool_name": tool_name}
                )

            if validated_input is not None:
                try:
                    target_session_id = session_id
                    _stage_workspace_files(state.file_metadata, session_id, target_session_id)

                    tool_func = TOOL_REGISTRY[tool_name]
                    tool_result = tool_func(validated_input)

                    if tool_result and tool_result.status == ToolStatus.SUCCESS:
                        possible_paths = []
                        if hasattr(tool_result, "output_path") and getattr(tool_result, "output_path"):
                            possible_paths.append(getattr(tool_result, "output_path"))
                        if isinstance(getattr(tool_result, "data", None), dict):
                            for k in ("output_path", "filepath", "path", "file_path", "output_filepath"):
                                if tool_result.data.get(k):
                                    possible_paths.append(tool_result.data[k])
                        for p_str in possible_paths:
                            try:
                                val_p = validate_workspace_path(p_str, target_session_id, create_parents=False)
                                if val_p.exists() and val_p.is_file():
                                    register_generated_file_metadata(target_session_id, val_p)
                            except Exception:
                                pass
                except Exception as ex:
                    tool_result = ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Tool execution failed for '{tool_name}': {str(ex)}",
                        metadata={"failure_type": "execution_error", "tool_name": tool_name}
                    )

        accumulated_results.append(tool_result)

        tool_msg = {
            "role": "tool",
            "content": tool_result.model_dump_json(),
            "tool_call_id": call_id
        }
        updated_messages.append(tool_msg)

    return {
        "session_id": session_id,
        "messages": updated_messages,
        "tool_results": accumulated_results,
        "tool_iteration_count": state.tool_iteration_count + 1,
        "tool_calls": []
    }


# ============================================================================
# ORCHESTRATOR BUILDER & ENTRYPOINT
# ============================================================================

def build_orchestrator_graph():
    """Assembles the ReAct LangGraph StateGraph with conditional tool loop."""
    builder = StateGraph(WorkbenchState)
    builder.add_node("route", route_node)
    builder.add_node("infer", infer_node)
    builder.add_node("tool_node", tool_node)

    builder.add_edge(START, "route")
    builder.add_edge("route", "infer")
    
    builder.add_conditional_edges(
        "infer",
        should_continue,
        {
            "tool_node": "tool_node",
            END: END
        }
    )
    
    builder.add_edge("tool_node", "infer")
    return builder


def register_generated_file_metadata(thread_id: str, file_path: Path, user_id: str = "system") -> Optional[str]:
    """Registers a tool-generated deliverable into PostgreSQL file_metadata table."""
    try:
        if not file_path.exists() or not file_path.is_file():
            return None
        clean_name = file_path.name
        existing = execute_query(
            "SELECT file_id FROM file_metadata WHERE thread_id = %s AND original_filename = %s",
            (thread_id, clean_name),
            fetch_one=True
        )
        if existing:
            return str(existing[0])

        file_id = str(uuid4())
        mime = "application/octet-stream"
        ext = file_path.suffix.lower()
        if ext in (".docx", ".doc"): mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext in (".pptx", ".ppt"): mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif ext in (".xlsx", ".xls"): mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif ext == ".pdf": mime = "application/pdf"
        elif ext == ".png": mime = "image/png"
        elif ext in (".jpg", ".jpeg"): mime = "image/jpeg"
        elif ext == ".csv": mime = "text/csv"

        execute_query(
            """
            INSERT INTO file_metadata (file_id, thread_id, user_id, original_filename, storage_path, mime_type, file_size_bytes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (file_id, thread_id, user_id, clean_name, str(file_path), mime, file_path.stat().st_size),
            commit=True
        )
        return file_id
    except Exception as e:
        logger.error(f"Error registering generated file metadata: {e}")
        return None


def save_messages_to_postgres(thread_id: str, messages: List[Dict[str, Any]]):
    """Saves human-readable chat messages into PostgreSQL messages table and links file_metadata records to specific message IDs."""
    try:
        existing_msgs = execute_query(
            "SELECT message_id, sender, content FROM messages WHERE thread_id = %s",
            (thread_id,),
            fetch_all=True
        ) or []
        existing_set = set((m[1], m[2]) for m in existing_msgs)

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                continue
            sender = "user" if role == "user" else ("assistant" if role == "assistant" else "tool")
            str_content = str(content)

            if (sender, str_content) in existing_set:
                continue

            tool_calls = json.dumps(msg.get("tool_calls")) if msg.get("tool_calls") else None
            tool_name = msg.get("tool_call_id") if role == "tool" else None
            
            res = execute_query(
                """
                INSERT INTO messages (thread_id, sender, content, tool_calls, tool_name)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING message_id
                """,
                (thread_id, sender, str_content, tool_calls, tool_name),
                fetch_one=True,
                commit=True
            )

            if res and res[0]:
                msg_id = str(res[0])
                if sender == "user":
                    execute_query(
                        """
                        UPDATE file_metadata 
                        SET message_id = %s 
                        WHERE thread_id = %s AND message_id IS NULL AND storage_path LIKE '%uploads%'
                        """,
                        (msg_id, thread_id),
                        commit=True
                    )
                elif sender == "assistant":
                    execute_query(
                        """
                        UPDATE file_metadata 
                        SET message_id = %s 
                        WHERE thread_id = %s AND message_id IS NULL
                        """,
                        (msg_id, thread_id),
                        commit=True
                    )
    except Exception as e:
        logger.error(f"Error saving messages to PostgreSQL: {e}")


def run_workbench(
    prompt: str,
    file_metadata: Optional[List[FileMetadata]] = None,
    thread_id: Optional[str] = None,
    max_tool_iterations: int = 5,
    thinking: bool = True
) -> Tuple[Dict[str, Any], str]:
    """Runs a complete workbench execution turn synchronously inside PostgresSaver context."""
    selected_thread_id = thread_id or str(uuid4())
    config = {"configurable": {"thread_id": selected_thread_id}}

    builder = build_orchestrator_graph()

    with PostgresSaver.from_conn_string(get_db_url()) as checkpointer:
        checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)
        snapshot = graph.get_state(config)
        existing_values = snapshot.values or {}
        existing_messages = existing_values.get("messages", [])

        initial_state = WorkbenchState(
            prompt=prompt,
            file_metadata=file_metadata,
            messages=existing_messages,
            max_tool_iterations=max_tool_iterations,
            thinking=thinking
        )
        final_state = graph.invoke(initial_state, config=config)

    # Ensure thread entry exists in threads table
    try:
        from tools.rbac import link_thread_to_user
        link_thread_to_user(selected_thread_id, "admin")
    except Exception:
        pass

    # Save messages to PostgreSQL messages table
    final_messages = final_state.get("messages", []) if isinstance(final_state, dict) else getattr(final_state, "messages", [])
    save_messages_to_postgres(selected_thread_id, final_messages)

    return final_state, selected_thread_id
