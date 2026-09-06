"""
router/classifier.py (SIH PS 26117)
====================================
Stage 3: Machine Learning fallback classifier for ambiguous prompts.
Loads pre-trained TF-IDF vectorizer and Logistic Regression model once at import time.
"""

import os
import pickle
from pathlib import Path
from router.schemas import RouteDecision

VECTORIZER_PATH = Path(__file__).parent.parent / "router_vectorizer.pkl"
CLASSIFIER_PATH = Path(__file__).parent.parent / "router_classifier.pkl"

_vectorizer = None
_classifier = None


def _load_models():
    global _vectorizer, _classifier
    if _vectorizer is None or _classifier is None:
        if not VECTORIZER_PATH.exists() or not CLASSIFIER_PATH.exists():
            raise FileNotFoundError(
                f"Router model files missing! Ensure '{VECTORIZER_PATH}' and '{CLASSIFIER_PATH}' exist. Run train_router_classifier.py."
            )
        with open(VECTORIZER_PATH, "rb") as f:
            _vectorizer = pickle.load(f)
        with open(CLASSIFIER_PATH, "rb") as f:
            _classifier = pickle.load(f)


CONFIDENCE_THRESHOLD = 0.60


def classify(prompt: str) -> RouteDecision:
    """
    Stage 3 Waterfall fallback.
    Uses TF-IDF + Logistic Regression to classify ambiguous prompts.
    Falls back to 'reasoning' role if confidence < CONFIDENCE_THRESHOLD.
    """
    _load_models()
    
    clean_prompt = prompt.strip() if prompt else ""
    X = _vectorizer.transform([clean_prompt])
    
    probs = _classifier.predict_proba(X)[0]
    classes = _classifier.classes_
    
    # Get index of highest probability
    max_idx = int(probs.argmax())
    predicted_role = str(classes[max_idx])
    confidence = float(probs[max_idx])

    method = "classifier"
    # If confidence is below threshold, default ambiguous requests to reasoning role
    if predicted_role == "coding" and confidence < CONFIDENCE_THRESHOLD:
        predicted_role = "reasoning"

    return RouteDecision(
        role=predicted_role,
        confidence=round(confidence, 2),
        method=method
    )
