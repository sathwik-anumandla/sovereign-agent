"""
Tool Interface Core Module (SIH PS 26117)
=========================================
Contains base Pydantic models, @audited_tool decorator, and shared workspace boundary validator.
"""

import os
import time
import logging
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class ToolInput(BaseModel):
    """Base Pydantic model for all tool inputs."""
    pass


class ToolResult(BaseModel):
    """Base Pydantic model for all tool outputs."""
    status: ToolStatus
    error: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


def audited_tool(func):
    """
    Decorator for logging, timing, and containment.
    Ensures sovereignty audit trail for all agent actions.
    """
    def wrapper(*args, **kwargs):
        start = time.time()
        tool_name = func.__name__
        try:
            result = func(*args, **kwargs)
            if not isinstance(result, ToolResult):
                raise TypeError(f"Tool {tool_name} returned invalid type {type(result)}, expected ToolResult")
            
            result.metadata.update({
                "tool_name": tool_name,
                "duration_ms": round((time.time() - start) * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            logging.info(f"[AUDIT LOG] Tool '{tool_name}' executed -> {result.status.value} ({result.metadata['duration_ms']}ms)")
            return result
        except Exception as e:
            logging.error(f"[AUDIT LOG] Tool '{tool_name}' FAILED: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                metadata={
                    "tool_name": tool_name,
                    "duration_ms": round((time.time() - start) * 1000, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
    return wrapper


def validate_workspace_path(path_str: str, session_id: str, create_parents: bool = True) -> Path:
    """
    Shared security helper to validate and enforce workspace boundaries.
    Mandatory rule: Every file path must resolve strictly inside /workspace/<session_id>/
    Rejects path traversal ('..') or absolute paths pointing outside root.
    """
    if not session_id or not session_id.strip():
        raise ValueError("session_id is required for workspace boundary validation")

    # Determine base workspace directory
    base_workspace = os.getenv("WORKBENCH_WORKSPACE_ROOT")
    if not base_workspace:
        # Fallback to local project directory workspace
        base_workspace = os.path.join(os.getcwd(), "workspace")

    session_root = Path(base_workspace).joinpath(session_id.strip()).resolve()

    # Pre-pass check for traversal attempts
    if ".." in path_str.split("/") or ".." in path_str.split("\\"):
        raise PermissionError(f"Security Alert: Path traversal '..' detected in path '{path_str}'")

    # Resolve target path
    raw_path = Path(path_str)
    if raw_path.is_absolute():
        target_path = raw_path.resolve()
    else:
        target_path = session_root.joinpath(raw_path).resolve()

    # Enforce boundary: target_path must be relative to session_root
    try:
        target_path.relative_to(session_root)
    except ValueError:
        raise PermissionError(f"Security Violation: Access denied for path '{path_str}'. Path lies outside workspace boundary '{session_root}'.")

    if create_parents:
        target_path.parent.mkdir(parents=True, exist_ok=True)

    return target_path
