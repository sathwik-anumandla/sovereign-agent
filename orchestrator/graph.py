"""
orchestrator/graph.py (SIH PS 26117)
====================================
Phase 6 LangGraph ReAct Orchestrator Loop with Tool Calling.
Topology: START -> route_node -> infer_node -> (should_continue) -> tool_node -> infer_node -> ... -> END
Persistent Checkpointing: SqliteSaver ('workbench_checkpoints.db').
"""

import os
import json
import sqlite3
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

    initial_messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": state.prompt}
    ]

    return {
        "route_decision": decision,
        "messages": initial_messages
    }


def infer_node(state: WorkbenchState) -> dict:
    """Node 2: Runs Ollama inference with function tool schemas."""
    rd = state.route_decision
    if isinstance(rd, dict):
        role = rd.get("role", "reasoning")
    elif isinstance(rd, RouteDecision):
        role = rd.role
    else:
        role = "reasoning"

    model_tag = MODEL_REGISTRY.get(role, MODEL_REGISTRY["reasoning"])
    
    # Execute inference with message history & tool schemas
    msg_dict = run_inference_raw(
        messages=state.messages,
        role=role,
        model=model_tag,
        tools=OLLAMA_TOOL_SCHEMAS
    )

    updated_messages = list(state.messages) + [msg_dict]
    
    # Extract tool_calls if present in assistant response
    raw_calls = msg_dict.get("tool_calls", []) or []

    content = msg_dict.get("content", "")

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
