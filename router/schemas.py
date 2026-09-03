"""
router/schemas.py (SIH PS 26117)
================================
Pydantic data models for router input and route decision outputs.
"""

from typing import Literal
from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    filename: str
    extension: str  # e.g., ".py", ".pdf", ".docx", ".ipynb"


class RouteDecision(BaseModel):
    role: Literal["reasoning", "coding"]
    confidence: float = Field(ge=0.0, le=1.0)
    method: Literal["metadata", "keyword", "classifier"]
