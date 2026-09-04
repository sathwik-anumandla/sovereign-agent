"""
router/schemas.py (SIH PS 26117)
================================
Pydantic data models for router input and route decision outputs.
Includes file metadata with OCR hint flagging.
"""

from typing import Literal
from pydantic import BaseModel, Field

OCR_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}


class FileMetadata(BaseModel):
    filename: str
    extension: str  # e.g., ".py", ".pdf", ".docx", ".ipynb", ".png"
    likely_needs_ocr: bool = False

    def __init__(self, **data):
        super().__init__(**data)
        ext = self.extension.strip().lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        if ext in OCR_EXTENSIONS:
            self.likely_needs_ocr = True
        else:
            self.likely_needs_ocr = False


class RouteDecision(BaseModel):
    role: Literal["reasoning", "coding"]
    confidence: float = Field(ge=0.0, le=1.0)
    method: Literal["metadata", "keyword", "classifier"]
