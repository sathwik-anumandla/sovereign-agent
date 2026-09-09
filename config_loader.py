"""
config_loader.py (SIH PS 26117)
================================
Centralized configuration loader for global Ollama model registry and options.
Reads models_config.json from project root and provides dynamic fallbacks.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

CONFIG_FILE_PATH = Path(__file__).parent / "models_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "models": {
        "reasoning": {"tag": "qwen3.5:4b-q4_K_M", "label": "Reasoning", "context_window": 8192, "supports_thinking": True},
        "vision": {"tag": "qwen3.5:4b-q4_K_M", "label": "Vision", "context_window": 8192, "supports_thinking": True},
        "coding": {"tag": "qwen2.5-coder:3b", "label": "Coding", "context_window": 8192, "supports_thinking": False},
        "ocr": {"tag": "qwen2.5-vl:3b", "label": "OCR VLM", "context_window": 8192, "supports_thinking": False},
        "vision_ocr": {"tag": "qwen2.5-vl:3b", "label": "Vision OCR", "context_window": 8192, "supports_thinking": False},
        "embedding": {"tag": "nomic-embed-text", "label": "Embedding", "context_window": 2048, "supports_thinking": False}
    },
    "options": [
        {"id": "auto", "role": "auto", "label": "Auto (Router)", "desc": "Dynamic Waterfall Routing"},
        {"id": "reasoning", "role": "reasoning", "label": "Reasoning", "desc": "Step-by-step reasoning & math"},
        {"id": "coding", "role": "coding", "label": "Coding", "desc": "Code generation & execution"}
    ]
}


def load_models_config() -> Dict[str, Any]:
    """Loads and returns the model configuration dictionary from models_config.json."""
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "models" in data:
                    return data
        except Exception as e:
            print(f"[Warning] Error reading models_config.json: {e}. Using default model config.")
    return DEFAULT_CONFIG


def get_model_registry() -> Dict[str, str]:
    """Returns dictionary mapping role -> model tag string."""
    cfg = load_models_config()
    models = cfg.get("models", {})
    return {role: meta.get("tag", "") for role, meta in models.items()}


def get_role_context_windows() -> Dict[str, int]:
    """Returns dictionary mapping role -> max context window integer."""
    cfg = load_models_config()
    models = cfg.get("models", {})
    return {role: meta.get("context_window", 8192) for role, meta in models.items() if "context_window" in meta}
