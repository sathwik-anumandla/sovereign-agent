"""
orchestrator/graph.py (SIH PS 26117)
====================================
Phase 5 LangGraph Orchestrator Skeleton.
Linear Graph: START -> route_node -> infer_node -> END.
Persistent Checkpointing: SqliteSaver ('workbench_checkpoints.db').
"""

import sqlite3
from uuid import uuid4
from typing import Optional, List, Dict, Any, Tuple
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from router.route import route
from router.schemas import FileMetadata, RouteDecision
from phase1_inference import run_inference, MODEL_REGISTRY
from orchestrator.state import WorkbenchState

DB_FILENAME = "workbench_checkpoints.db"


def route_node(state: WorkbenchState) -> dict:
    """Node 1: Evaluates 3-stage router and returns route_decision."""
    decision = route(state.prompt, state.file_metadata)
    return {"route_decision": decision}


def infer_node(state: WorkbenchState) -> dict:
    """Node 2: Looks up model tag in registry and executes inference."""
    rd = state.route_decision
    if isinstance(rd, dict):
        role = rd.get("role", "reasoning")
    elif isinstance(rd, RouteDecision):
        role = rd.role
    else:
        role = "reasoning"

    model_tag = MODEL_REGISTRY.get(role, MODEL_REGISTRY["reasoning"])
    response = run_inference(state.prompt, role=role, model=model_tag)
    return {"response": response}


def build_orchestrator_graph():
    """Assembles the linear LangGraph StateGraph."""
    builder = StateGraph(WorkbenchState)
    builder.add_node("route", route_node)
    builder.add_node("infer", infer_node)
    builder.add_edge(START, "route")
    builder.add_edge("route", "infer")
    builder.add_edge("infer", END)
    return builder


def run_workbench(
    prompt: str,
    file_metadata: Optional[List[FileMetadata]] = None,
    thread_id: Optional[str] = None
) -> Tuple[Dict[str, Any], str]:
    """
    Executes the workbench orchestrator graph end-to-end.
    
    Args:
        prompt: User input text request.
        file_metadata: Optional list of attached FileMetadata objects.
        thread_id: Unique invocation thread ID (generated via uuid4 if None).
        
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
            "file_metadata": file_metadata
        }
        final_state = graph.invoke(initial_state, config=config)

    return final_state, selected_thread_id
