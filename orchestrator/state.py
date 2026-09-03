"""
orchestrator/state.py (SIH PS 26117)
====================================
Pydantic WorkbenchState schema for Phase 5 LangGraph orchestrator skeleton.
"""

from typing import Optional, List
from pydantic import BaseModel
from router.schemas import FileMetadata, RouteDecision


class WorkbenchState(BaseModel):
    prompt: str
    file_metadata: Optional[List[FileMetadata]] = None
    route_decision: Optional[RouteDecision] = None
    response: Optional[str] = None
