"""
orchestrator/state.py (SIH PS 26117)
====================================
Pydantic WorkbenchState schema for Phase 6 ReAct LangGraph orchestrator loop.
Includes messages, tool_calls, tool_results, iteration bounds, and route decision.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from router.schemas import FileMetadata, RouteDecision
from tool_interface import ToolResult


class WorkbenchState(BaseModel):
    prompt: str
    file_metadata: Optional[List[FileMetadata]] = None
    route_decision: Optional[RouteDecision] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    tool_iteration_count: int = 0
    max_tool_iterations: int = 5
    response: Optional[str] = None
