"""
router/metadata_check.py (SIH PS 26117)
========================================
Stage 1: Deterministic file metadata inspection guard.
Matches file extension against code extensions for 100% confidence routing.
"""

from typing import Optional, List
from router.schemas import FileMetadata, RouteDecision

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", 
    ".go", ".rs", ".ipynb", ".sh", ".bash", ".pyw"
}


def check_metadata(file_metadata: Optional[List[FileMetadata]] = None) -> Optional[RouteDecision]:
    """
    Stage 1 Waterfall check.
    If any input file extension is a code extension, route immediately to coding.
    """
    if not file_metadata:
        return None

    for meta in file_metadata:
        ext = meta.extension.strip().lower()
        if not ext.startswith("."):
            ext = f".{ext}"
            
        if ext in CODE_EXTENSIONS:
            return RouteDecision(
                role="coding",
                confidence=1.0,
                method="metadata"
            )

    return None
