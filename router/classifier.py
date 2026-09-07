"""
router/classifier.py (SIH PS 26117)
====================================
Stage 3: Machine Learning fallback classifier for ambiguous prompts.
Loads pre-trained TF-IDF vectorizer and Logistic Regression model once at import time.
Self-healing: Auto-retrains model locally if scikit-learn version incompatibility is detected.
"""

import os
import pickle
import logging
from pathlib import Path
from router.schemas import RouteDecision

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

VECTORIZER_PATH = Path(__file__).parent.parent / "router_vectorizer.pkl"
CLASSIFIER_PATH = Path(__file__).parent.parent / "router_classifier.pkl"

_vectorizer = None
_classifier = None


def _load_models():
    global _vectorizer, _classifier
    if _vectorizer is None or _classifier is None:
        need_retrain = False
        if not VECTORIZER_PATH.exists() or not CLASSIFIER_PATH.exists():
            need_retrain = True
        else:
            try:
                with open(VECTORIZER_PATH, "rb") as f:
                    _vectorizer = pickle.load(f)
                with open(CLASSIFIER_PATH, "rb") as f:
                    _classifier = pickle.load(f)
                # Verify that model works with current scikit-learn version
                dummy_x = _vectorizer.transform(["test prompt"])
                _classifier.predict_proba(dummy_x)
            except Exception as e:
                logging.warning(f"[ROUTER] Pickle incompatibility detected ({e}). Re-training router classifier locally...")
                need_retrain = True

        if need_retrain:
            try:
                from train_router_classifier import train
                train()
                with open(VECTORIZER_PATH, "rb") as f:
                    _vectorizer = pickle.load(f)
                with open(CLASSIFIER_PATH, "rb") as f:
                    _classifier = pickle.load(f)
            except Exception as retrain_err:
                logging.error(f"[ROUTER] Auto-retrain failed: {retrain_err}")
                raise retrain_err


CONFIDENCE_THRESHOLD = 0.60


def classify(prompt: str) -> RouteDecision:
    """
    Stage 3 Waterfall fallback.
    Uses TF-IDF + Logistic Regression to classify ambiguous prompts.
    Falls back to 'reasoning' role if confidence < CONFIDENCE_THRESHOLD or on error.
    """
    clean_prompt = prompt.strip() if prompt else ""
    try:
        _load_models()
        X = _vectorizer.transform([clean_prompt])
        
        probs = _classifier.predict_proba(X)[0]
        classes = _classifier.classes_
        
        max_idx = int(probs.argmax())
        predicted_role = str(classes[max_idx])
        confidence = float(probs[max_idx])

        if predicted_role == "coding" and confidence < CONFIDENCE_THRESHOLD:
            predicted_role = "reasoning"

        return RouteDecision(
            role=predicted_role,
            confidence=round(confidence, 2),
            method="classifier"
        )
    except Exception as ex:
        logging.error(f"[ROUTER] Classification failed ({ex}). Defaulting to 'reasoning' role.")
        return RouteDecision(
            role="reasoning",
            confidence=0.50,
            method="classifier_fallback"
        )

