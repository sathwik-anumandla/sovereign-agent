"""
orchestrator/graph.py (SIH PS 26117)
====================================
Phase 6 LangGraph ReAct Orchestrator Loop with Tool Calling.
Topology: START -> route_node -> infer_node -> (should_continue) -> tool_node -> infer_node -> ... -> END
Persistent Checkpointing: SqliteSaver ('workbench_checkpoints.db').
"""

import os
import re
import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from typing import Optional, List, Dict, Any, Tuple
from pydantic import ValidationError
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from router.route import route
from router.schemas import FileMetadata, RouteDecision
from phase1_inference import run_inference_raw, MODEL_REGISTRY, ROLE_SYSTEM_PROMPTS
from tool_interface import ToolStatus, ToolResult
from tools.registry import TOOL_REGISTRY, TOOL_INPUT_TYPES, OLLAMA_TOOL_SCHEMAS
from orchestrator.state import WorkbenchState

DB_FILENAME = "workbench_checkpoints.db"


def route_node(state: WorkbenchState) -> dict:
    """Node 1: Evaluates 3-stage router and initializes message history."""
    decision = route(state.prompt, state.file_metadata)
    
    role = decision.role if decision else "reasoning"
    sys_prompt = ROLE_SYSTEM_PROMPTS.get(role, ROLE_SYSTEM_PROMPTS["reasoning"])

    # Provide workspace relative file path instructions when input files are present
    workspace_context = ""
    if state.file_metadata:
        staged_files = [f"'{fm.filename}'" for fm in state.file_metadata]
        if staged_files:
            workspace_context = (
                f"\n\n[Workspace Context]: The file(s) {', '.join(staged_files)} are available in your execution working directory. "
                f"When writing or executing code in code_sandbox, open these files using relative file paths (e.g. {staged_files[0]}), NOT absolute host paths."
            )

    initial_messages = [
        {"role": "system", "content": sys_prompt + workspace_context},
        {"role": "user", "content": state.prompt}
    ]

    return {
        "route_decision": decision,
        "messages": initial_messages
    }


IMAGE_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def parse_json_tool_call(content: str) -> Optional[Dict[str, Any]]:
    """
    Fallback parser for models (e.g. qwen2.5-coder) that emit JSON tool calls in text content
    rather than native Ollama tool_calls payloads.
    Strips markdown code fences, parses JSON, and validates against TOOL_REGISTRY keys.
    """
    if not content or not content.strip():
        return None

    text = content.strip()

    # Match inner content inside ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = fence_match.group(1).strip() if fence_match else text

    # Locate outermost curly braces for valid JSON object
    start_idx = candidate.find("{")
    end_idx = candidate.rfind("}")

    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None

    json_str = candidate[start_idx : end_idx + 1]

    try:
        data = json.loads(json_str, strict=False)
    except (json.JSONDecodeError, ValueError, TypeError):
        try:
            # Trailing comma cleanup
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


def infer_node(state: WorkbenchState) -> dict:
    """Node 2: Runs Ollama inference with function tool schemas and image support."""
    rd = state.route_decision
    if isinstance(rd, dict):
        role = rd.get("role", "reasoning")
    elif isinstance(rd, RouteDecision):
        role = rd.role
    else:
        role = "reasoning"

    model_tag = MODEL_REGISTRY.get(role, MODEL_REGISTRY["reasoning"])
    
    # Extension-based check for image files in state.file_metadata
    # Only pass images on the first infer_node call of an invocation (tool_iteration_count == 0)
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

    # Execute inference with message history, tool schemas, and optional images
    msg_dict = run_inference_raw(
        messages=state.messages,
        role=role,
        model=model_tag,
        tools=OLLAMA_TOOL_SCHEMAS,
        images=images
    )

    # Extract tool_calls if present in assistant response
    raw_calls = msg_dict.get("tool_calls", []) or []
    content = msg_dict.get("content", "")

    # Fallback: if native tool_calls is empty, attempt JSON fallback parsing from content
    if not raw_calls and content:
        fallback_call = parse_json_tool_call(content)
        if fallback_call:
            raw_calls = [fallback_call]
            msg_dict = dict(msg_dict)
            msg_dict["tool_calls"] = raw_calls

    updated_messages = list(state.messages) + [msg_dict]

    return {
        "messages": updated_messages,
        "tool_calls": raw_calls,
        "response": content if content else (state.response or "")
    }


def should_continue(state: WorkbenchState) -> str:
    """Conditional Edge: Determines whether to route to tool_node or END."""
    has_tool_calls = bool(state.tool_calls)
    below_iteration_limit = state.tool_iteration_count < state.max_tool_iterations

    if has_tool_calls and below_iteration_limit:
        return "tool_node"
    return END


def tool_node(state: WorkbenchState) -> dict:
    """
    Node 3: Single Tool Dispatcher Node.
    Dispatches tool calls through 3 distinct try/except failure stages:
      Stage 1: Unknown tool name -> failure_type="unknown_tool"
      Stage 2: Invalid/malformed args -> failure_type="invalid_args"
      Stage 3: Tool execution failure -> failure_type="execution_error"
    """
    updated_messages = list(state.messages)
    accumulated_results = list(state.tool_results)
    
    # Synthesize session_id if not present in state
    session_id = getattr(state, "session_id", None) or "workbench_session"

    for call in state.tool_calls:
        # Step 8: Tool Call ID handling (Synthesize UUID if missing)
        call_id = call.get("id") or str(uuid4())
        
        tool_name = ""
        raw_args = {}

        # Handle dict or function call object
        if isinstance(call, dict):
            func_info = call.get("function", {})
            tool_name = func_info.get("name") or call.get("name") or ""
            raw_args = func_info.get("arguments") or call.get("arguments") or {}
        else:
            tool_name = getattr(call, "name", "")
            raw_args = getattr(call, "arguments", {})

        # Ensure session_id is injected into input args if required by tool
        if isinstance(raw_args, dict) and "session_id" not in raw_args:
            raw_args["session_id"] = session_id

        tool_result = None

        # Stage 1: Unknown Tool Name Check
        if tool_name not in TOOL_REGISTRY:
            tool_result = ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown tool: '{tool_name}'",
                metadata={"failure_type": "unknown_tool", "tool_name": tool_name}
            )
        else:
            # Stage 2: Invalid / Malformed Arguments Check
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

            # Stage 3: Tool Execution Failure Check
            if validated_input is not None:
                try:
                    # File-staging step for code execution: stage input files into session workspace via audited file_io write
                    if tool_name == "code_sandbox" and state.file_metadata:
                        for fm in state.file_metadata:
                            src_path_str = getattr(fm, "filepath", None) or getattr(fm, "path", None) or fm.filename
                            src_path = Path(src_path_str)
                            if src_path.exists() and src_path.is_file():
                                try:
                                    with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
                                        file_content = f.read()
                                    file_io_tool = TOOL_REGISTRY.get("file_io")
                                    file_io_cls = TOOL_INPUT_TYPES.get("file_io")
                                    if file_io_tool and file_io_cls:
                                        stage_in = file_io_cls(
                                            operation="write",
                                            path=fm.filename,
                                            content=file_content,
                                            session_id=session_id
                                        )
                                        stage_res = file_io_tool(stage_in)
                                        accumulated_results.append(stage_res)
                                except Exception:
                                    pass

                    tool_func = TOOL_REGISTRY[tool_name]
                    tool_result = tool_func(validated_input)
                except Exception as ex:
                    tool_result = ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Tool execution failed for '{tool_name}': {str(ex)}",
                        metadata={"failure_type": "execution_error", "tool_name": tool_name}
                    )

        accumulated_results.append(tool_result)

        # Step 9: Feed tool result back to model with tool_call_id
        tool_msg = {
            "role": "tool",
            "content": tool_result.model_dump_json(),
            "tool_call_id": call_id
        }
        updated_messages.append(tool_msg)

    new_iteration_count = state.tool_iteration_count + 1

    return {
        "messages": updated_messages,
        "tool_results": accumulated_results,
        "tool_iteration_count": new_iteration_count,
        "tool_calls": []  # Reset tool_calls after processing
    }


def build_orchestrator_graph():
    """Assembles the ReAct LangGraph StateGraph with tool loop."""
    builder = StateGraph(WorkbenchState)
    builder.add_node("route", route_node)
    builder.add_node("infer", infer_node)
    builder.add_node("tool_node", tool_node)

    builder.add_edge(START, "route")
    builder.add_edge("route", "infer")
    
    # ReAct Conditional Tool Loop
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


def run_workbench(
    prompt: str,
    file_metadata: Optional[List[FileMetadata]] = None,
    thread_id: Optional[str] = None,
    max_tool_iterations: int = 5
) -> Tuple[Dict[str, Any], str]:
    """
    Executes the workbench orchestrator graph end-to-end.
    
    Args:
        prompt: User input text request.
        file_metadata: Optional list of attached FileMetadata objects.
        thread_id: Unique invocation thread ID (generated via uuid4 if None).
        max_tool_iterations: Maximum loop safety iteration count (default 5).
        
    Returns:
        Tuple of (final_state_dict, thread_id)
    """
    selected_thread_id = thread_id or str(uuid4())
    config = {"configurable": {"thread_id": selected_thread_id}}

    builder = build_orchestrator_graph()

    with SqliteSaver.from_conn_string(DB_FILENAME) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        initial_state = {
            "prompt": prompt,
            "file_metadata": file_metadata,
            "max_tool_iterations": max_tool_iterations
        }
        final_state = graph.invoke(initial_state, config=config)

    return final_state, selected_thread_id
