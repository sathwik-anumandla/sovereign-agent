"""
router/route.py (SIH PS 26117)
==============================
Main entry point for Phase 4 Router / Classifier.
Implements 3-Stage Waterfall Routing:
  Stage 1: Metadata Extension Check (confidence=1.0)
  Stage 2: Keyword Heuristic Check (confidence=0.85)
  Stage 3: ML Classifier Fallback (confidence=predict_proba)
"""

from typing import Optional, List
from router.schemas import FileMetadata, RouteDecision
from router.metadata_check import check_metadata
from router.keyword_check import check_keywords
from router.classifier import classify


def route(prompt: str, file_metadata: Optional[List[FileMetadata]] = None) -> RouteDecision:
    """
    Decides whether a request should be handled by 'reasoning' or 'coding' model role.
    
    Args:
        prompt: User request prompt text.
        file_metadata: Optional list of attached file metadata objects.
        
    Returns:
        RouteDecision (role, confidence, method)
    """
    # Stage 1: Metadata Check
    decision = check_metadata(file_metadata)
    if decision:
        return decision

    # Stage 2: Keyword Check
    decision = check_keywords(prompt)
    if decision:
        return decision

    # Stage 3: ML Classifier Fallback
    return classify(prompt)
